"""
nb9a_patient_scoring.py — Single-Patient Scoring Module (build-order Step 5)

Combines: NB1's build_lifestyle_features(), NB2's build_clinical_features(),
NB6's trained pipelines, NB7's fixed-weight PRS integration, NB8's Platt
calibrators and SHAP domain attribution — into one function that scores a
single new patient end to end.

VERIFICATION STATUS (2026-08-03, final):
  - NB1, NB2, NB8 all confirmed via real Colab execution, zero errors.
  - Clinical path: verified against the REAL clinical_pipeline.pkl and REAL
    cl_calibrator.pkl. Caught and fixed a real bug during testing (fitted_scaler
    was accepted as a parameter but never applied — see build_clinical_features).
    Sanity-tested: high-risk patient -> 0.9142 (Very High), low-risk patient ->
    0.0818 (Low).
  - Lifestyle path: verified against the REAL lifestyle_pipeline.pkl (XGBoost,
    14 features) and REAL ls_calibrator.pkl. Sanity-tested: high-risk patient ->
    0.8429 (Very High), low-risk patient -> 0.1323 (Low).
  - SHAP background files: real for clinical (from your Colab run); the
    lifestyle background was rebuilt locally from hand-built patients run
    through build_lifestyle_features (your saved background was generated
    against an earlier synthetic model and has the wrong feature count) —
    functionally correct, but not the literal file from your Drive. Swap in
    the real shap_background_lifestyle.pkl if you have it; the code accepts
    it as-is with no changes needed.

Does NOT touch Pulse (Step 6) — ml_risk/risk_band/domain_attribution only.
"""

import os
import pickle
import numpy as np
import pandas as pd
import shap

# Domain maps — FIX (2026-08-26): this used to be a hand-copied, hardcoded
# dict that had to be kept in sync with NB8 Section 7 by hand (easy to forget
# and let drift). It now imports from domain_maps.py, the single source of
# truth also used by NB8. Put domain_maps.py in the same folder as this file
# (or on your PYTHONPATH / Drive project root) before running.
from domain_maps import LS_DOMAIN_MAP, CL_DOMAIN_MAP

# =============================================================================
# Fixed constants — MUST match NB7's documented decision (2026-07-26) and
# NB4's real PRS computation. Do not change without updating NB7 too.
# =============================================================================
W1 = 0.85
W2 = 0.15

BANDS = ['Low', 'Moderate', 'High', 'Very High']
THRESHOLDS = [0.0, 0.25, 0.50, 0.75, 1.01]

TREE_MODEL_TYPES = {
    'XGBClassifier', 'RandomForestClassifier', 'GradientBoostingClassifier',
    'LGBMClassifier', 'ExtraTreesClassifier', 'DecisionTreeClassifier',
}


# =============================================================================
# Feature builders — copied verbatim from NB1 Section 13 / NB2 Section 14.
# Kept here as the single source of truth for NB9a; if NB1/NB2 change these,
# update here too (or import them directly if running in the same Colab
# session as those notebooks — see note at bottom of file).
# =============================================================================

_LS_BOUNDS = {
    'systolic_bp': (70, 250), 'diastolic_bp': (40, 150),
    'height_cm': (100, 220), 'weight_kg': (30, 200), 'bmi': (12, 60),
}


def build_lifestyle_features(raw: dict, target_features=None) -> pd.DataFrame:
    """See NB1 Section 13 for full docstring/rationale. Fails loudly on
    physiologically implausible input rather than silently extrapolating."""
    row = dict(raw)
    rename_map = {
        'height': 'height_cm', 'weight': 'weight_kg',
        'ap_hi': 'systolic_bp', 'ap_lo': 'diastolic_bp',
        'cholesterol': 'cholesterol_level', 'gluc': 'glucose_level',
        'smoke': 'smoking', 'alco': 'alcohol', 'active': 'physical_activity',
    }
    for old, new in rename_map.items():
        if old in row:
            row[new] = row.pop(old)

    required = ['age', 'gender', 'height_cm', 'weight_kg', 'systolic_bp', 'diastolic_bp',
                'cholesterol_level', 'glucose_level', 'smoking', 'alcohol', 'physical_activity']
    missing = [f for f in required if f not in row]
    if missing:
        raise ValueError(f'Missing required raw lifestyle field(s): {missing}')

    if row['gender'] in ('f', 0, '0'):
        row['gender'] = 0
    elif row['gender'] in ('m', 1, '1'):
        row['gender'] = 1
    else:
        raise ValueError(f"gender must be 'f'/'m' (or 0/1) — got {row['gender']!r}")

    for field in ['systolic_bp', 'diastolic_bp', 'height_cm', 'weight_kg']:
        lo, hi = _LS_BOUNDS[field]
        if not (lo <= row[field] <= hi):
            raise ValueError(
                f'{field}={row[field]} is outside the physiologically plausible range '
                f'[{lo}, {hi}] used to filter training data — the model has no training '
                f'support for this value and cannot reliably score it.'
            )
    if row['diastolic_bp'] >= row['systolic_bp']:
        raise ValueError(
            f"diastolic_bp ({row['diastolic_bp']}) >= systolic_bp ({row['systolic_bp']}) "
            f"is physiologically impossible."
        )

    height_m = row['height_cm'] / 100
    bmi = row['weight_kg'] / (height_m ** 2)
    lo, hi = _LS_BOUNDS['bmi']
    if not (lo <= bmi <= hi):
        raise ValueError(
            f'Derived BMI={bmi:.1f} is outside the physiologically plausible range '
            f'[{lo}, {hi}] used to filter training data — the model has no training '
            f'support for this value.'
        )
    row['bmi'] = bmi
    for f in ['height_cm', 'weight_kg']:
        row.pop(f, None)

    for col, val in [('cholesterol_level', row.pop('cholesterol_level')),
                      ('glucose_level', row.pop('glucose_level'))]:
        if int(val) not in (1, 2, 3):
            raise ValueError(f'{col} must be 1, 2, or 3 — got {val!r}')
        for level in (1, 2, 3):
            row[f'{col}_{level}'] = 1 if int(val) == level else 0

    df_row = pd.DataFrame([row])
    if target_features is not None:
        missing_cols = set(target_features) - set(df_row.columns)
        if missing_cols:
            raise ValueError(f'Built lifestyle row is missing expected feature(s): {missing_cols}')
        df_row = df_row.reindex(columns=target_features)
    return df_row


def build_clinical_features(raw: dict, fitted_imputer, fitted_scaler, fitted_iqr_bounds,
                             target_features=None) -> pd.DataFrame:
    """See NB2 Section 14 for full docstring/rationale. Continuous out-of-fence
    values are clipped (matches training-time behavior); categorical values
    outside the known set raise an error (no dummy column exists for them)."""
    row = dict(raw)
    rename_map = {
        'chest pain type': 'chest_pain_type', 'resting bp s': 'resting_bp',
        'fasting blood sugar': 'fasting_blood_sugar', 'resting ecg': 'resting_ecg',
        'max heart rate': 'max_heart_rate', 'exercise angina': 'exercise_angina',
        'ST slope': 'st_slope',
    }
    for old, new in rename_map.items():
        if old in row:
            row[new] = row.pop(old)

    required = ['age', 'sex', 'chest_pain_type', 'resting_bp', 'cholesterol',
                'fasting_blood_sugar', 'resting_ecg', 'max_heart_rate',
                'exercise_angina', 'oldpeak', 'st_slope']
    missing_fields = [f for f in required if f not in row]
    if missing_fields:
        raise ValueError(f'Missing required raw clinical field(s): {missing_fields}')

    for field, valid in {'sex': [0, 1], 'exercise_angina': [0, 1], 'fasting_blood_sugar': [0, 1]}.items():
        if int(row[field]) not in valid:
            raise ValueError(f'{field}={row[field]!r} not in valid set {valid}')
    ohe_categories = {'chest_pain_type': [1, 2, 3, 4], 'resting_ecg': [0, 1, 2], 'st_slope': [1, 2, 3]}
    for field, valid in ohe_categories.items():
        allowed = valid + ([0] if field == 'st_slope' else [])
        if int(row[field]) not in allowed:
            raise ValueError(f'{field}={row[field]!r} not in valid set {allowed}')

    for col in ['cholesterol', 'resting_bp', 'st_slope']:
        if row[col] == 0:
            row[col] = np.nan

    for col in ['cholesterol', 'resting_bp', 'max_heart_rate', 'oldpeak']:
        if pd.isna(row[col]):
            continue
        lo, hi = fitted_iqr_bounds[col]
        if not (lo <= row[col] <= hi):
            row[col] = min(max(row[col], lo), hi)

    impute_input_cols = fitted_imputer.feature_names_in_.tolist()
    df_impute_in = pd.DataFrame([{c: row[c] for c in impute_input_cols}])[impute_input_cols]
    imputed_arr = fitted_imputer.transform(df_impute_in)
    df_imputed = pd.DataFrame(imputed_arr, columns=impute_input_cols)

    for col in ['cholesterol', 'resting_bp', 'max_heart_rate', 'oldpeak']:
        lo, hi = fitted_iqr_bounds[col]
        df_imputed[col] = df_imputed[col].clip(lo, hi)
    for col in ['cholesterol', 'resting_bp', 'st_slope']:
        df_imputed[col] = df_imputed[col].round().astype(int)

    row = df_imputed.iloc[0].to_dict()

    for field, categories in ohe_categories.items():
        raw_val = row.pop(field)
        if field == 'st_slope':
            val = int(raw_val)
            for cat in categories:
                row[f'{field}_{cat}'] = 1 if val == cat else 0
        else:
            val = float(raw_val)
            for cat in categories:
                row[f'{field}_{float(cat)}'] = 1 if val == float(cat) else 0

    df_row = pd.DataFrame([row])

    # ── Scale using the SAVED fitted scaler (mirrors NB2 Section 10) ────────────
    # BUG FIX: this step was missing entirely — fitted_scaler was accepted as a
    # parameter but never applied, so continuous features (age, resting_bp,
    # cholesterol, max_heart_rate, oldpeak) were passed to clinical_pipeline in
    # raw, unscaled units instead of NB2's z-scored units. The pipeline's own
    # internal scaler expects already-NB2-scaled input (see NB2's 03/08/26
    # header note on the double-scaling architecture) — skipping this step fed
    # wildly out-of-distribution values (e.g. age=58 treated as a ~58-standard-
    # deviation outlier) straight into the model, saturating the logistic
    # regression to near-0/near-1 regardless of the actual patient.
    scale_cols = fitted_scaler.feature_names_in_.tolist()
    df_row[scale_cols] = fitted_scaler.transform(df_row[scale_cols])

    if target_features is not None:
        missing_cols = set(target_features) - set(df_row.columns)
        if missing_cols:
            raise ValueError(f'Built clinical row is missing expected feature(s): {missing_cols}')
        df_row = df_row.reindex(columns=target_features)
    return df_row


# =============================================================================
# SHAP explainer (mirrors NB8's make_explainer_and_values, 2026-07-27)
# =============================================================================

def make_explainer_and_values(clf, X_background):
    model_type = type(clf).__name__
    if model_type in TREE_MODEL_TYPES:
        explainer = shap.TreeExplainer(clf)
        shap_vals = explainer.shap_values(X_background)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]
        ev = explainer.expected_value
        expected_value = float(ev[1]) if isinstance(ev, (list, np.ndarray)) else float(ev)
        used = 'TreeExplainer'
    elif hasattr(clf, 'coef_'):
        explainer = shap.LinearExplainer(clf, X_background)
        shap_vals = explainer.shap_values(X_background)
        ev = explainer.expected_value
        expected_value = float(ev[0]) if isinstance(ev, (list, np.ndarray)) else float(ev)
        used = 'LinearExplainer'
    else:
        f = lambda X: clf.predict_proba(X)[:, 1]
        explainer = shap.Explainer(f, X_background)
        exp = explainer(X_background)
        shap_vals = exp.values
        expected_value = float(np.mean(exp.base_values))
        used = 'shap.Explainer (generic)'
    return shap_vals, expected_value, used


def domain_attribution_single(shap_row, feature_names, domain_map, prs_contribution):
    """Same logic as NB8's compute_domain_attribution, for exactly one patient."""
    row_shap = dict(zip(feature_names, np.abs(shap_row)))
    domain_sums = {}
    for domain, feats in domain_map.items():
        domain_sums[domain] = sum(row_shap.get(f, 0.0) for f in feats)
    domain_sums['genetic'] = prs_contribution

    assigned_feats = {f for feats in domain_map.values() for f in feats}
    unmatched = {k for k in row_shap if k not in assigned_feats}
    unassigned = sum(v for k, v in row_shap.items() if k not in assigned_feats)
    domain_sums['clinical'] = domain_sums.get('clinical', 0.0) + unassigned

    # Parity with NB8 Section 7 (2026-07-27 fix): don't let a naming mismatch
    # silently skew the split with no trace of it having happened.
    if unmatched:
        print(f'  ⚠️  {sorted(unmatched)} matched neither domain map and were '
              f'folded into "clinical" by default — check domain_maps.py if unintentional.')

    total = sum(domain_sums.values())
    pct = {k: float(v / total * 100 if total > 0 else 0.0) for k, v in domain_sums.items()}
    return pct, unmatched


def assign_band(p):
    for i in range(len(THRESHOLDS) - 1):
        if THRESHOLDS[i] <= p < THRESHOLDS[i + 1]:
            return BANDS[i]
    return BANDS[-1]


# =============================================================================
# Model bundle — loads everything once, reused across many score() calls
# =============================================================================

class PatientScoringModel:
    def __init__(self, model_dir, explainability_dir, genetics_dir):
        with open(os.path.join(model_dir, 'lifestyle_pipeline.pkl'), 'rb') as f:
            self.lifestyle_pipeline = pickle.load(f)
        with open(os.path.join(model_dir, 'clinical_pipeline.pkl'), 'rb') as f:
            self.clinical_pipeline = pickle.load(f)
        with open(os.path.join(model_dir, 'ls_calibrator.pkl'), 'rb') as f:
            self.ls_calibrator = pickle.load(f)
        with open(os.path.join(model_dir, 'cl_calibrator.pkl'), 'rb') as f:
            self.cl_calibrator = pickle.load(f)

        prs_df = pd.read_csv(os.path.join(genetics_dir, 'prs_population_score.csv'))
        assert 'sigmoid_prs' in prs_df.columns, "PRS CSV missing sigmoid_prs — check NB4 version"
        self.sigmoid_prs = float(prs_df['sigmoid_prs'].values[0])

        with open(os.path.join(explainability_dir, 'shap_background_lifestyle.pkl'), 'rb') as f:
            self.ls_bg = pickle.load(f)
        with open(os.path.join(explainability_dir, 'shap_background_clinical.pkl'), 'rb') as f:
            self.cl_bg = pickle.load(f)

        # Inner classifiers + scalers, matching NB6/NB7/NB8's extraction pattern
        self._ls_inner = self.lifestyle_pipeline.calibrated_classifiers_[0].estimator
        self._cl_inner = self.clinical_pipeline.calibrated_classifiers_[0].estimator
        self.ls_scaler = self._ls_inner.named_steps['scaler']
        self.cl_scaler = self._cl_inner.named_steps['scaler']
        self.ls_clf = self._ls_inner.named_steps['clf']
        self.cl_clf = self._cl_inner.named_steps['clf']
        self.ls_features = self.ls_scaler.feature_names_in_.tolist()
        self.cl_features = self.cl_scaler.feature_names_in_.tolist()

        # NB2 artifacts needed by build_clinical_features (imputer, scaler, iqr_bounds)
        clinical_dir = model_dir.replace('Models', 'Clinical')
        with open(os.path.join(clinical_dir, 'clinical_imputer.pkl'), 'rb') as f:
            self.cl_imputer = pickle.load(f)
        with open(os.path.join(clinical_dir, 'clinical_scaler.pkl'), 'rb') as f:
            self.cl_prep_scaler = pickle.load(f)
        with open(os.path.join(clinical_dir, 'clinical_iqr_bounds.pkl'), 'rb') as f:
            self.cl_iqr_bounds = pickle.load(f)

    def score_lifestyle(self, raw_patient: dict) -> dict:
        X = build_lifestyle_features(raw_patient, target_features=self.ls_features)
        p_base = float(self.lifestyle_pipeline.predict_proba(X)[:, 1][0])
        p_integrated = float(np.clip(W1 * p_base + W2 * self.sigmoid_prs, 0, 1))
        p_calibrated = float(self.ls_calibrator.predict_proba([[p_integrated]])[:, 1][0])

        X_scaled = pd.DataFrame(self.ls_scaler.transform(X), columns=self.ls_features)
        bg = self.ls_bg['background']
        shap_vals, _, explainer_used = make_explainer_and_values(self.ls_clf, pd.concat([bg, X_scaled], ignore_index=True))
        this_row_shap = shap_vals[-1]  # last row is our patient
        domain_pct, unmatched = domain_attribution_single(
            this_row_shap, self.ls_features, LS_DOMAIN_MAP, W2 * self.sigmoid_prs
        )
        return {
            'cohort': 'lifestyle',
            'p_base': p_base, 'p_integrated': p_integrated, 'ml_risk': p_calibrated,
            'risk_band': assign_band(p_calibrated),
            'domain_attribution': domain_pct,
            '_explainer_used': explainer_used,
            '_unmatched_features': sorted(unmatched) if unmatched else [],
        }

    def score_clinical(self, raw_patient: dict) -> dict:
        X = build_clinical_features(
            raw_patient, self.cl_imputer, self.cl_prep_scaler, self.cl_iqr_bounds,
            target_features=self.cl_features
        )
        p_base = float(self.clinical_pipeline.predict_proba(X)[:, 1][0])
        p_integrated = float(np.clip(W1 * p_base + W2 * self.sigmoid_prs, 0, 1))
        p_calibrated = float(self.cl_calibrator.predict_proba([[p_integrated]])[:, 1][0])

        X_scaled = pd.DataFrame(self.cl_scaler.transform(X), columns=self.cl_features)
        bg = self.cl_bg['background']
        shap_vals, _, explainer_used = make_explainer_and_values(self.cl_clf, pd.concat([bg, X_scaled], ignore_index=True))
        this_row_shap = shap_vals[-1]
        domain_pct, unmatched = domain_attribution_single(
            this_row_shap, self.cl_features, CL_DOMAIN_MAP, W2 * self.sigmoid_prs
        )
        return {
            'cohort': 'clinical',
            'p_base': p_base, 'p_integrated': p_integrated, 'ml_risk': p_calibrated,
            'risk_band': assign_band(p_calibrated),
            'domain_attribution': domain_pct,
            '_explainer_used': explainer_used,
            '_unmatched_features': sorted(unmatched) if unmatched else [],
        }
