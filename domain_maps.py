"""
domain_maps.py — Single source of truth for SHAP domain attribution buckets.

Created 2026-08-26 to close a doc/code sync gap: NB8 Section 7's markdown table
said age/sex belonged to "Lifestyle," while the code in the same section (and
the hand-copied version in nb9a_patient_scoring.py) put them under "Clinical."
The code was internally consistent (NB8 and NB9a already agreed with each
other) — only the markdown text was wrong. This file is now the one place
that defines the split; NB8 and NB9a should both import from here instead of
each keeping their own literal copy, so they cannot drift apart again.

DOMAIN DEFINITION (2026-08-26 decision — record the reasoning if you revisit this):
  - "lifestyle" = behavioral / modifiable-by-the-patient factors: smoking,
    alcohol, physical activity, BMI.
  - "clinical"  = measured / non-modifiable-by-behavior factors: age, sex,
    blood pressure, cholesterol, glucose, and all clinical-cohort markers
    (resting ECG, oldpeak, max heart rate, etc.). Age and sex are grouped
    here (not under "lifestyle") because they are demographic/non-modifiable
    risk factors, not behaviors a patient can change — this matches how
    "modifiable vs non-modifiable" risk factors are conventionally split in
    cardiovascular risk literature, and it's the grouping the code has
    actually been using all along.
  - "genetic"   = handled separately (fixed PRS offset), not part of either
    dict below.

If you decide instead that age/sex should count as "lifestyle," change ONLY
the lists below — do not re-introduce a second hardcoded copy anywhere else.
"""

LS_DOMAIN_MAP = {
    'lifestyle': [
        'smoke', 'alco', 'active', 'bmi',
        # Alternative naming variants from some preprocessing versions:
        'smoking', 'alcohol', 'physical_activity',
    ],
    'clinical': [
        'age', 'gender', 'height', 'weight',
        'systolic_bp', 'diastolic_bp',
        'cholesterol_level_1', 'cholesterol_level_2', 'cholesterol_level_3',
        'glucose_level_1', 'glucose_level_2', 'glucose_level_3',
        # Alternative naming variants:
        'ap_hi', 'ap_lo', 'cholesterol', 'gluc',
    ],
}

CL_DOMAIN_MAP = {
    'clinical': [
        'age', 'resting_bp', 'cholesterol', 'max_heart_rate', 'oldpeak',
        'fasting_blood_sugar',
        'resting_ecg_0.0', 'resting_ecg_1.0', 'resting_ecg_2.0',
        # Numerical/alternative variants:
        'sex', 'trestbps', 'chol', 'thalach', 'ca', 'thal',
    ],
    'lifestyle': [
        # In the clinical dataset lifestyle proxies are limited;
        # age and sex serve as demographic risk factors and live under
        # "clinical" (see module docstring), not here.
    ],
}
