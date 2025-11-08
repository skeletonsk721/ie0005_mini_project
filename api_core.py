"""Minimal API core for calling Claude-like service.
Single responsibility: accept prompt + config, return model response text (synchronous).

Function: call_model(prompt, config_path='para.json', credentials_path='credentials.json') -> str
- Reads config (strict JSON)
- Reads credentials JSON
- Chooses header style (x-api-key if key starts with sk-ant-, otherwise Bearer)
- If model name contains 'haiku' -> use /v1/messages with top-level 'system' and 'messages'
  (include max_tokens and temperature)
- Otherwise -> use /v1/complete with prompt or anthopic-style wrapping if anthropic_version requires

This core intentionally avoids CLI, async, streaming, or extra utilities.
"""
from pathlib import Path
from typing import Optional, Dict, Any
import json
import httpx


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
