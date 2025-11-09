from pathlib import Path
import json
from typing import Dict, Any

from prediction_core import load_model_params, predict_proba_from_sample, explain_contributions
from api_core import call_model, APIError


def process_input(input_path: str = 'input_sample.json', para_path: str = 'para.json', cred_path: str = 'credentials.json') -> Dict[str, Any]:
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f'Input JSON not found: {input_path}')
    data = json.loads(p.read_text(encoding='utf-8'))

    # Load model params
    params = load_model_params('model_params.json')

    # Predict
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


if __name__ == '__main__':
    # quick local test: read input_sample.json and print report
    res = process_input('input_sample.json')
    print(json.dumps(res, ensure_ascii=False, indent=2))
