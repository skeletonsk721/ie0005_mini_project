from pathlib import Path
import json
from typing import Dict, Any, Optional

from prediction_core import load_model_params, predict_proba_from_sample, explain_contributions
from api_core import call_model, APIError


def process_input(input_path: str = 'input_sample.json', para_path: str = 'llm_para.json', cred_path: str = 'credentials.json') -> Dict[str, Any]:
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f'Input JSON not found: {input_path}')
    data = json.loads(p.read_text(encoding='utf-8'))
    # Persist raw model input for audit/debug
    Path('model_input.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    # Load model params
    params = load_model_params('model_params.json')

    # Predict using raw input; prediction_core now handles preprocessing
    prob = predict_proba_from_sample(params, data)
    contribs = explain_contributions(params, data)

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
    # This function has been removed. prediction_core now accepts raw frontend
    # samples and performs the necessary preprocessing. Keep this stub in case
    # external callers reference it, but raise to make misuse explicit.
    raise RuntimeError('raw-to-model conversion moved to prediction_core')


if __name__ == '__main__':
    # quick local test: read input_sample.json and print report
    res = process_input('input_sample.json')
    print(json.dumps(res, ensure_ascii=False, indent=2))
