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
        LLM_response = call_model(f"User input: {data}\nPrediction: {prob}")
        print(LLM_response)
        return jsonify({'probability': prob, 'recommendations': LLM_response})
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


def call_model(prompt: str) -> str:
    """Call model synchronously and return resulting text.

    Input:
      - prompt: user prompt string
    Output: model text
    """

    credentials_path = 'code/credentials.json'
    key = _load_key(credentials_path) or None
    print(f"DEBUG: Key loaded: {key[:10] if key else 'None'}...")

    base_url = 'https://api.anthropic.com'
    model = 'claude-haiku-4-5-20251001'
    print(f"DEBUG: Model: {model}")
    temperature = 0.0
    max_tokens = 1024
    anthropic_version = "2023-06-01"
    system_prompt = '"You are a cardiovascular health assistant. Based on the user\'s health data and predicted cardiovascular disease probability, provide personalized health recommendations.\n\nInput format: User input: [age_years, bmi, systolic_bp, diastolic_bp, cholesterol_level, glucose_level, physical_activity]\nPrediction: probability (0-1, higher means higher risk)\n\nData mapping:\n- age_years: Age in years\n- bmi: Body Mass Index (normal: 18.5-24.9)\n- systolic_bp/diastolic_bp: Blood pressure (normal: <120/80)\n- cholesterol_level: 1=normal, 2=above normal, 3=high\n- glucose_level: 1=normal, 2=above normal, 3=high\n- physical_activity: 0=no regular activity, 1=regular physical activity\n\nProvide:\n1. Risk assessment based on probability (<0.3=low, 0.3-0.7=medium, >0.7=high)\n2. Specific recommendations for each concerning health metric\n3. Lifestyle suggestions (diet, exercise, stress management)\n4. When to consult a doctor\n\nKeep response concise but informative, focus on actionable advice. Format: five bullet points of recommendations in plain text (no markdown). Nothing else are allowed."'

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
                content = first['content']
                if isinstance(content, list):
                    texts = [block['text'] for block in content if isinstance(block, dict) and block.get('type') == 'text']
                    return ''.join(texts)
                elif isinstance(content, str):
                    return content
        if 'content' in data:
            content = data['content']
            if isinstance(content, list):
                texts = [block['text'] for block in content if isinstance(block, dict) and block.get('type') == 'text']
                return ''.join(texts)
            elif isinstance(content, str):
                return content
    # fallback: stringify
    return json.dumps(data, ensure_ascii=False)

if __name__ == '__main__':
    # dev server
    app.run(host='0.0.0.0', port=11451, debug=True)
