from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
import pandas as pd
import joblib
import json
from typing import Optional, Dict, Any
import httpx
import os

# static files moved to `web/` directory — serve from there
app = Flask(__name__, static_folder='web', static_url_path='')


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'webpage.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({'error': 'expected a list in json body'}), 400

    # Directly pass list to prediction_core
    try:
        prob = predict_probability(data)
        print(prob)
        return jsonify({'probability': prob})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def predict_probability(data_list):
    """
    Predict cardiovascular disease probability from a list of input features.

    Args:
        data_list (list): List of features in order: [age_years, bmi, ap_hi, ap_lo, cholesterol, gluc, active]

    Returns:
        float: Predicted probability of cardiovascular disease (positive class)
    """
    # Load the pickled model
    model_path = Path(__file__).parent / 'cardio_prediction_model.pkl'
    if not model_path.exists():
        raise FileNotFoundError(f'Model file not found: {model_path}')
    
    model = joblib.load(model_path)
    
    # Feature names in order
    feature_names = ['age_years', 'bmi', 'ap_hi', 'ap_lo', 'cholesterol', 'gluc', 'active']
    
    # Create DataFrame from list
    if len(data_list) != len(feature_names):
        raise ValueError(f'Expected {len(feature_names)} features, got {len(data_list)}')
    
    df = pd.DataFrame([data_list], columns=feature_names)
    
    # Predict probability
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(df)
        return float(proba[0][1])  # Probability of positive class
    elif hasattr(model, 'decision_function'):
        score = model.decision_function(df)
        return float(score[0])
    else:
        pred = model.predict(df)
        return float(pred[0])

class APIError(Exception):
    pass


def _load_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise APIError(f"Config file not found: {path}")
    return json.loads(p.read_text(encoding='utf-8'))


def _load_key(credentials_path: Optional[str]) -> Optional[str]:
    if not credentials_path:
        return None
    p = Path(credentials_path)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding='utf-8'))
    return data.get('api_key') or data.get('apiKey')


def call_model(prompt: str, config_path: str = 'para.json', credentials_path: str = 'credentials.json') -> str:
    """Call model synchronously and return resulting text.

    Input:
      - prompt: user prompt string
      - config_path: path to a JSON config file
      - credentials_path: path to JSON containing api_key
    Output: model text
    """
    cfg = _load_json(config_path)
    key = _load_key(credentials_path) or None

    base_url = cfg.get('base_url', 'https://api.anthropic.com').rstrip('/')
    model = cfg.get('model')
    temperature = cfg.get('temperature', 0.0)
    max_tokens = cfg.get('max_tokens', 1024)
    anthropic_version = cfg.get('anthropic_version')
    system_prompt = cfg.get('system', 'You are a helpful assistant.')

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if key and str(key).startswith('sk-ant-'):
        headers['x-api-key'] = key
    elif key:
        headers['Authorization'] = f'Bearer {key}'

    if anthropic_version:
        headers['anthropic-version'] = anthropic_version

    # Decide endpoint and payload
    if isinstance(model, str) and 'haiku' in model.lower():
        url = f"{base_url}/v1/messages"
        payload = {
            'model': model,
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
    else:
        url = f"{base_url}/v1/complete"
        # anthopic older style: if anthropic_version indicates the Human/Assistant format, wrap
        if anthropic_version == '2023-06-01':
            payload_prompt = f"\n\nHuman: {prompt}\n\nAssistant:"
        else:
            payload_prompt = prompt
        payload = {
            'model': model,
            'prompt': payload_prompt,
            'max_tokens_to_sample': max_tokens,
            'temperature': temperature,
        }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            # raise for common HTTP errors so we can present a single error
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        # include response body for debugging
        text = e.response.text if e.response is not None else str(e)
        raise APIError(f"HTTP error {e.response.status_code}: {text}")
    except Exception as e:
        raise APIError(f"Request failed: {e}")

    # Extract text from common fields
    if isinstance(data, dict):
        for k in ('completion', 'output', 'response'):
            if k in data and isinstance(data[k], str):
                return data[k]
        if 'choices' in data and isinstance(data['choices'], list) and data['choices']:
            first = data['choices'][0]
            if isinstance(first, dict) and 'text' in first:
                return first['text']
        if 'messages' in data and isinstance(data['messages'], list) and data['messages']:
            first = data['messages'][0]
            if isinstance(first, dict) and 'content' in first:
                return first['content']
    # fallback: stringify
    return json.dumps(data, ensure_ascii=False)

if __name__ == '__main__':
    # dev server
    app.run(host='0.0.0.0', port=11451, debug=True)
