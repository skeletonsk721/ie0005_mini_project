"""Utility to load exported model parameters and run deterministic predictions.

Provides:
- load_model_params(path) -> dict
- vectorize(sample_dict, params) -> numpy.ndarray
- predict_proba_from_vector(vector, params) -> float
- predict_proba_from_sample(params, sample_dict) -> float
- explain_contributions(params, sample_dict) -> dict of feature->contribution

The implementation mirrors the preprocessing in `explain_model.py` and
is careful about JSON `null` categories and unseen categories.
"""
from pathlib import Path
import json
import math
from typing import Any, Dict, List

import numpy as np


def load_model_params(path: str = 'model_params.json') -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"model params file not found: {path}")
    return json.loads(p.read_text(encoding='utf-8'))


def _cat_to_str(cat: Any) -> str:
    """Normalize a category value to the same string used in feature names.

    - None (JSON null) -> 'nan'
    - numpy.nan -> 'nan'
    - numbers/strings -> str(cat)
    """
    if cat is None:
        return 'nan'
    try:
        # pandas/numpy NaN
        if isinstance(cat, float) and math.isnan(cat):
            return 'nan'
    except Exception:
        pass
    return str(cat)


def vectorize(sample: Dict[str, Any], params: Dict[str, Any]) -> np.ndarray:
    """Convert a raw sample dict into the model feature vector (numpy array).

    Behavior:
    - Numeric missing values -> replaced by training mean
    - Categorical unseen values -> all-zero for those one-hot columns
    - Categorical None/np.nan handled as 'nan' category if present in training
    """
    feature_names: List[str] = params['feature_names']
    weights = params.get('weights', [])
    vec = np.zeros(len(feature_names), dtype=float)

    # helper: set by feature name
    name_to_idx = {n: i for i, n in enumerate(feature_names)}

    # numeric features: use scaler metadata
    num_features = params['scaler']['num_features']
    means = params['scaler']['mean']
    scales = params['scaler']['scale']
    for fname, mean, scale in zip(num_features, means, scales):
        raw = sample.get(fname, None)
        if raw is None:
            val = mean
        else:
            val = float(raw)
        if scale == 0 or scale is None:
            std = 0.0
        else:
            std = (val - mean) / scale
        if fname not in name_to_idx:
            # numeric features should appear in feature_names; skip if not
            continue
        vec[name_to_idx[fname]] = std

    # multi-class one-hot features
    onehot_map = params.get('onehot', {})
    # Build explicit list of onehot column names (matching feature_names) to ensure
    # we know which features correspond to which categories.
    onehot_feature_names = []
    for col, cats in onehot_map.items():
        for idx_cat, cat in enumerate(cats):
            if idx_cat == 0:
                # dropped baseline has no column
                continue
            cat_str = _cat_to_str(cat)
            onehot_feature_names.append(f"{col}_{cat_str}")

    for col, cats in onehot_map.items():
        sval = sample.get(col, None)
        for idx_cat, cat in enumerate(cats):
            if idx_cat == 0:
                continue
            feat_name = f"{col}_{_cat_to_str(cat)}"
            if feat_name not in name_to_idx:
                continue
            # match by raw equality or by normalized string
            if sval == cat or _cat_to_str(sval) == _cat_to_str(cat):
                vec[name_to_idx[feat_name]] = 1.0
            else:
                vec[name_to_idx[feat_name]] = 0.0

    # binary features (those not in numeric nor onehot)
    num_set = set(num_features)
    onehot_set = set(onehot_feature_names)
    binary_names = [n for n in feature_names if n not in num_set and n not in onehot_set]
    # fill binary values from sample (default 0)
    for b in binary_names:
        vec[name_to_idx[b]] = float(sample.get(b, 0))

    return vec


def predict_proba_from_vector(vec: np.ndarray, params: Dict[str, Any]) -> float:
    w = np.array(params['weights'], dtype=float)
    intercept = float(params.get('intercept', 0.0))
    logit = float(np.dot(w, vec) + intercept)
    # numerically stable sigmoid
    if logit >= 0:
        z = math.exp(-logit)
        prob = 1 / (1 + z)
    else:
        z = math.exp(logit)
        prob = z / (1 + z)
    return prob


def predict_proba_from_sample(params: Dict[str, Any], sample: Dict[str, Any]) -> float:
    vec = vectorize(sample, params)
    return predict_proba_from_vector(vec, params)


def explain_contributions(params: Dict[str, Any], sample: Dict[str, Any]) -> Dict[str, float]:
    """Return per-feature contribution (weight * standardized_value) and intercept.

    Returns a dict with keys 'intercept' and each feature name.
    """
    vec = vectorize(sample, params)
    w = np.array(params['weights'], dtype=float)
    contributions = {}
    for name, val, weight in zip(params['feature_names'], vec.tolist(), w.tolist()):
        contributions[name] = weight * val
    contributions['intercept'] = float(params.get('intercept', 0.0))
    return contributions


def predict_and_save(params: Dict[str, Any], sample: Dict[str, Any], out_path: str = 'prediction_data.json') -> Dict[str, Any]:
    """Run prediction and save core numeric + explanatory outputs to JSON.

    The saved JSON contains:
    - timestamp (ISO 8601)
    - feature_names, feature_vector (list), weights, intercept
    - logit, probability
    - contributions (per-feature and intercept)
    - model_input (the input sample provided)

    All numeric types are converted to native Python floats/ints to ensure
    JSON serializability for downstream agents.
    """
    from datetime import datetime

    vec = vectorize(sample, params)
    w = np.array(params.get('weights', []), dtype=float)
    intercept = float(params.get('intercept', 0.0))
    # compute logit and probability
    logit = float(np.dot(w, vec) + intercept)
    prob = predict_proba_from_vector(vec, params)

    # contributions (ensure native floats)
    contribs = explain_contributions(params, sample)
    contribs_native = {k: float(v) for k, v in contribs.items()}

    # feature vector native list
    feature_vector = [float(x) for x in vec.tolist()]

    payload = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'feature_names': list(params.get('feature_names', [])),
        'feature_vector': feature_vector,
        'weights': [float(x) for x in params.get('weights', [])],
        'intercept': intercept,
        'logit': logit,
        'probability': float(prob),
        'contributions': contribs_native,
        'model_input': _make_json_compatible(sample),
    }

    Path(out_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return payload


def _make_json_compatible(obj: Any) -> Any:
    """Recursively convert numpy/scalar types to native Python types for JSON."""
    if obj is None:
        return None
    if isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, (int, float)):
        # numpy scalar subclasses of int/float are instance of numbers.Number too,
        # but converting via float/int will normalize them.
        return obj
    if isinstance(obj, np.generic):
        try:
            return obj.item()
        except Exception:
            return float(obj)
    if isinstance(obj, dict):
        return {str(k): _make_json_compatible(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_compatible(v) for v in obj]
    try:
        # fallback for pandas types etc.
        return float(obj)
    except Exception:
        return str(obj)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Score a sample using exported model_params.json')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--sample-json', type=str, help='A JSON string representing the sample dict')
    group.add_argument('--sample-file', type=str, help='Path to a JSON file containing the sample dict')
    parser.add_argument('--params', type=str, default='model_params.json', help='Path to model_params.json')
    parser.add_argument('--show-contrib', action='store_true', help='Print per-feature contributions')
    args = parser.parse_args()

    params = load_model_params(args.params)

    if args.sample_json:
        sample = json.loads(args.sample_json)
    elif args.sample_file:
        sample = json.loads(Path(args.sample_file).read_text(encoding='utf-8'))
    else:
        # interactive: prompt for required fields (use training means/defaults)
        sample = {}
        print('No sample provided; building a default sample from training metadata...')
        for fname, mean in zip(params['scaler']['num_features'], params['scaler']['mean']):
            sample[fname] = mean
        for col, cats in params.get('onehot', {}).items():
            # choose the first training category (the dropped baseline)
            sample[col] = cats[0] if len(cats) > 0 else None
        # set binaries to 0 by default
        for b in params.get('feature_names', [])[-4:]:
            sample[b] = 0

    prob = predict_proba_from_sample(params, sample)
    print(f"Predicted probability: {prob:.6f}")

    # Save detailed prediction data for downstream agents
    out_path = 'prediction_data.json'
    payload = predict_and_save(params, sample, out_path=out_path)
    print(f"Wrote prediction data to {out_path}")

    if args.show_contrib:
        contribs = payload.get('contributions', {})
        items = sorted(((k, v) for k, v in contribs.items() if k != 'intercept'), key=lambda kv: abs(kv[1]), reverse=True)
        print('Top feature contributions:')
        for k, v in items[:10]:
            print(f"  {k}: {v:.6f}")
