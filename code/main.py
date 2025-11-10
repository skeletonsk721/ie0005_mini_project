from pathlib import Path
import json
from typing import Dict, Any, Optional
from datetime import datetime, date

from prediction_core import load_model_params, predict_proba_from_sample, explain_contributions
from api_core import call_model, APIError


def process_input(input_path: str = 'input_sample.json', para_path: str = 'para.json', cred_path: str = 'credentials.json') -> Dict[str, Any]:
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f'Input JSON not found: {input_path}')
    data = json.loads(p.read_text(encoding='utf-8'))
    # Convert raw front-end data to model input expected by prediction_core
    model_sample = _raw_to_model_sample(data)

    # persist processed model input for audit/debug
    Path('model_input.json').write_text(json.dumps(model_sample, ensure_ascii=False, indent=2), encoding='utf-8')

    # Load model params
    params = load_model_params('model_params.json')

    # Predict
    prob = predict_proba_from_sample(params, model_sample)
    contribs = explain_contributions(params, model_sample)

    # Build a prompt for api_core to generate a human-readable report
    prompt = (
        f"Patient data:\n{json.dumps(data, ensure_ascii=False, indent=2)}\n\n"
        f"Model predicted probability of cardiovascular disease: {prob:.4f}\n"
        f"Please produce a concise clinical-style report (3-6 sentences) summarizing the patient's risk, the top contributing features (name and contribution), and suggested next steps (lifestyle and clinical follow-up)."
    )

    report_text = None
    try:
        report_text = call_model(prompt, config_path=para_path, credentials_path=cred_path)
    except APIError as e:
        # Fallback to a simple templated report
        top = sorted(((k, v) for k, v in contribs.items() if k != 'intercept'), key=lambda kv: abs(kv[1]), reverse=True)[:3]
        top_summary = '; '.join([f"{k}: {v:.3f}" for k, v in top])
        report_text = (
            f"Predicted probability: {prob:.3f}. Top contributors: {top_summary}. "
            f"Recommendation: consider lifestyle changes (diet, exercise), monitor BP and lipids, and consult a clinician for personalised assessment."
        )

    out = {
        'probability': prob,
        'contributions': contribs,
        'report': report_text
    }
    return out


def _safe_int(v: Optional[Any], default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _safe_float(v: Optional[Any], default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _bmi_group(bmi: float) -> str:
    if bmi < 18.5:
        return 'underweight'
    if bmi < 25:
        return 'normal'
    if bmi < 30:
        return 'overweight'
    return 'obese'


def _bp_category(ap_hi: float, ap_lo: float) -> str:
    if ap_hi < 120 and ap_lo < 80:
        return 'normal'
    if (120 <= ap_hi < 140) or (80 <= ap_lo < 90):
        return 'pre_high'
    return 'high'


def _age_group(age_years: int) -> Optional[str]:
    if 30 <= age_years <= 39:
        return '30s'
    if 40 <= age_years <= 49:
        return '40s'
    if 50 <= age_years <= 59:
        return '50s'
    if 60 <= age_years <= 69:
        return '60s'
    return None


def _gender_code(g: Any) -> int:
    # default mapping: male->1, female->2. If integer already, pass through
    if isinstance(g, int):
        return g
    if not g:
        return 0
    s = str(g).lower()
    if s.startswith('m'):
        return 1
    return 2


def _raw_to_model_sample(raw: Dict[str, Any]) -> Dict[str, Any]:
    # raw: fields from frontend (birthday or direct age_years, gender, height, weight, systolic, diastolic, cholesterol, glucose, smoking, alcohol, physical)
    # produce keys expected by prediction_core
    # age_years
    age_years = None
    if raw.get('birthday'):
        try:
            bdate = datetime.fromisoformat(raw['birthday']).date()
            age_days = (date.today() - bdate).days
            age_years = int(age_days / 365)
        except Exception:
            age_years = None
    if age_years is None and raw.get('age_years') is not None:
        age_years = _safe_int(raw.get('age_years'), 0)
    if age_years is None:
        age_years = 0

    height = _safe_float(raw.get('height'))
    weight = _safe_float(raw.get('weight'))
    ap_hi = _safe_float(raw.get('systolic') or raw.get('ap_hi'))
    ap_lo = _safe_float(raw.get('diastolic') or raw.get('ap_lo'))
    cholesterol = _safe_int(raw.get('cholesterol'))
    gluc = _safe_int(raw.get('glucose') or raw.get('gluc'))
    smoke = _safe_int(raw.get('smoking') or raw.get('smoke'))
    alco = _safe_int(raw.get('alcohol') or raw.get('alco'))
    active = _safe_int(raw.get('physical') or raw.get('active'))

    # compute derived
    bmi = None
    if height > 0:
        try:
            bmi = weight / ((height / 100) ** 2)
        except Exception:
            bmi = None
    bmi_grp = _bmi_group(bmi) if bmi is not None else 'normal'
    bp_cat = _bp_category(ap_hi, ap_lo)
    age_grp = _age_group(age_years)
    age_chol = age_years * cholesterol
    gender = _gender_code(raw.get('gender'))

    model_sample = {
        'age_years': int(age_years),
        'height': float(height),
        'weight': float(weight),
        'ap_hi': float(ap_hi),
        'ap_lo': float(ap_lo),
        'age_cholesterol': age_chol,
        'cholesterol': int(cholesterol),
        'gluc': int(gluc),
        'bp_category': bp_cat,
        'age_group': age_grp,
        'bmi_group': bmi_grp,
        'gender': int(gender),
        'smoke': int(smoke),
        'alco': int(alco),
        'active': int(active)
    }
    return model_sample


if __name__ == '__main__':
    # quick local test: read input_sample.json and print report
    res = process_input('input_sample.json')
    print(json.dumps(res, ensure_ascii=False, indent=2))
