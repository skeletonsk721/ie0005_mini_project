# Mini-Project — Claude-backed report generator (core only)

This repository contains a minimal headless core to call a Claude-like API and a small test harness. It's intended as the backend/core for a report generator that converts patient features and a logistic regression model into a human-readable, explainable cardiovascular risk report.

Files of interest
- `api_core.py` — Minimal synchronous API core. Function: `call_model(prompt, config_path='para.json', credentials_path='credentials.json') -> str`. Reads `para.json` and `credentials.json` to build requests. Handles both Messages and Complete endpoints depending on `model` name and `anthropic_version`.
- `para.json` — Parameters for the API core (model name, temperature, max_tokens, base_url, anthropic_version, system). Edit this to control calls.
- `credentials.json` — Your API key (not checked into source control). Expected format: `{"api_key": "sk-ant-..."}` or `{"apiKey": "..."}`.
- `test_call.py` — Simple script that calls `call_model()` and prints the result.

Recommended workflow
1. Prepare `credentials.json` with your API key.
2. Edit `para.json` to set `model`, `temperature`, `max_tokens`, and `system` prompt as needed.
3. Use `api_core.call_model(prompt, config_path='para.json', credentials_path='credentials.json')` from your integration (UI/agent script) to generate report text.

Suggested I/O for the report generator (example)

Input (patients JSON):
```
{
  "patients": [
    {"id":"P001","name":"Alice","age":65,"sbp":140,"chol":5.6},
    {"id":"P002","name":"Bob","age":50,"sbp":130,"chol":6.1}
  ]
}
```

Model parameters (logistic regression JSON):
```
{
  "weights": {"age": 0.02, "sbp": 0.01, "chol": 0.5},
  "intercept": -3.0,
  "thresholds": [0.33, 0.66]
}
```

Suggested structured report output (recommended):
```
[
  {
    "id":"P001",
    "score": 0.4523,
    "category":"Medium",
    "report": {
      "summary":"一句话风险摘要",
      "rationale":"基于模型计算，age contributed X, sbp contributed Y...",
      "recommendations":[{"type":"lifestyle","text":"..."}],
      "follow_up_tests":["LDL cholesterol","ECG"]
    }
  }
]
```

Notes and best practices
- Keep `credentials.json` out of version control.
- `system` in `para.json` should hold global instructions for the LLM (role, required output format). Put behavior rules there rather than in each prompt when possible.
- For structured outputs, instruct the model to return strict JSON matching the schema. Implement a parser with fallback: try `json.loads`, if fails, call the model again asking to "only return valid JSON following this schema".
- Token/cost: split large multi-section reports into modular calls if cost or latency matter.

Next steps you can ask me to do
- Create a robust `agent.py` that implements the structured I/O you choose (A/B/C or the logistic-focused schema).
- Add `schema_logistic.json` to the repo and a small validator for LLM responses.
- Implement multi-call orchestration with caching and retries.

If you want, I can now write `schema_logistic.json` and a validator and re-create the `agent.py` scaffold to your chosen schema.

---
Generated on 2025-11-08
