"""Extract model parameters from cardio_train.csv by reproducing preprocessing and logistic regression.

Produces model_params.json with:
 - feature_names (post-preprocessing)
 - weights (coef)
 - intercept
 - scaler mean/scale for numeric features
 - onehot categories mapping
 - training metrics (AUC) and sample counts
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


def bmi_group(bmi):
    if bmi < 18.5:
        return 'underweight'
    elif bmi < 25:
        return 'normal'
    elif bmi < 30:
        return 'overweight'
    else:
        return 'obese'


def bp_category(row):
    if row['ap_hi'] < 120 and row['ap_lo'] < 80:
        return 'normal'
    elif (120 <= row['ap_hi'] < 140) or (80 <= row['ap_lo'] < 90):
        return 'pre_high'
    else:
        return 'high'


def build_pipeline_and_data(csv_path: Path):
    df = pd.read_csv(csv_path, sep=';')
    # feature engineering (same as notebook)
    df['age_years'] = (df['age'] / 365).astype(int)
    df['bmi'] = df['weight'] / (df['height'] / 100) ** 2
    df['bmi_group'] = df['bmi'].apply(bmi_group)
    df['bp_category'] = df.apply(bp_category, axis=1)
    df['age_group'] = pd.cut(df['age_years'], bins=[29, 39, 49, 59, 69], labels=['30s', '40s', '50s', '60s'])
    df['age_cholesterol'] = df['age_years'] * df['cholesterol']
    df = df.drop(columns=['id', 'age'])

    X = df.drop(columns=['cardio'])
    y = df['cardio']

    num_features = ['age_years', 'height', 'weight', 'ap_hi', 'ap_lo', 'age_cholesterol']
    binary_features = ['gender', 'smoke', 'alco', 'active']
    multi_cat_features = ['cholesterol', 'gluc', 'bp_category', 'age_group', 'bmi_group']

    # Construct OneHotEncoder in a version-compatible way
    try:
        # sklearn >=1.2 uses sparse_output
        ohe = OneHotEncoder(drop='first', sparse_output=False)
    except TypeError:
        # older sklearn uses sparse
        ohe = OneHotEncoder(drop='first', sparse=False)

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_features),
            ('multi_cat', ohe, multi_cat_features),
            ('binary', 'passthrough', binary_features)
        ]
    )

    model = Pipeline(steps=[('preprocess', preprocessor), ('logreg', LogisticRegression(max_iter=1000))])
    return model, X, y, num_features, multi_cat_features, binary_features


def extract_feature_names(preprocessor: ColumnTransformer, num_features, multi_cat_features, binary_features):
    # numeric features remain as is
    num_names = list(num_features)
    # onehot names
    ohe = preprocessor.named_transformers_['multi_cat']
    try:
        ohe_names = ohe.get_feature_names_out(multi_cat_features).tolist()
    except Exception:
        # fallback
        cats = ohe.categories_
        names = []
        for col, cat in zip(multi_cat_features, cats):
            for c in cat[1:]:
                names.append(f"{col}_{c}")
        ohe_names = names
    binary_names = list(binary_features)
    return num_names + ohe_names + binary_names


def main():
    csv_path = Path('cardio_train.csv')
    if not csv_path.exists():
        print('cardio_train.csv not found in cwd')
        return

    model, X, y, num_features, multi_cat_features, binary_features = build_pipeline_and_data(csv_path)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model.fit(X_train, y_train)

    # build full preprocessor to extract names
    pre = model.named_steps['preprocess']
    logreg = model.named_steps['logreg']

    feature_names = extract_feature_names(pre, num_features, multi_cat_features, binary_features)
    coefs = logreg.coef_[0].tolist()
    intercept = float(logreg.intercept_[0])

    # scaler info
    scaler = pre.named_transformers_['num']
    means = scaler.mean_.tolist()
    scales = scaler.scale_.tolist()

    # onehot mapping
    ohe = pre.named_transformers_['multi_cat']
    onehot_map = {}
    for col, cats in zip(multi_cat_features, ohe.categories_):
        onehot_map[col] = list(cats)

    # training metrics
    y_proba = model.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, y_proba))

    out = {
        'model_version': 'from_notebook',
        'feature_names': feature_names,
        'weights': coefs,
        'intercept': intercept,
        'scaler': {'num_features': num_features, 'mean': means, 'scale': scales},
        'onehot': onehot_map,
        'training_metrics': {'auc': auc},
        'training_sample_counts': {'n': int(len(X_train) + len(X_test)), 'pos': int(y.sum()), 'neg': int((y==0).sum())}
    }

    Path('model_params.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Wrote model_params.json')


if __name__ == '__main__':
    main()
