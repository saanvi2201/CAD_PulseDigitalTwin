"""
nb10b_patient_loader.py — Getting a patient INTO the NB10 long-term simulator

WHY THIS FILE EXISTS SEPARATELY FROM nb10_long_term_simulation.py
-----------------------------------------------------------------------------
NB10's LongTermSimulator (simulate_lifestyle / simulate_clinical) expects a
raw_patient dict in the SAME format score_lifestyle()/score_clinical() take
directly -- i.e. the pre-preprocessing representation (real age, real
height_cm/weight_kg, a single cholesterol_level category, etc.), NOT the
one-hot-encoded, standardized, BMI-engineered matrix your training pipeline
produces as df_lifestyle_test.csv / df_lifestyle_train.csv.

This module is the translation layer between "a row that actually exists in
one of our datasets" (or "values a user typed into a form") and "a dict
NB10/NB9a will accept." It does not implement any new intervention formulas
-- those all stay in nb10_long_term_simulation.py, unmodified.

TWO PATIENT SOURCES SUPPORTED
-----------------------------------------------------------------------------
1. load_real_lifestyle_patient() / load_real_clinical_patient()
   -- pull one row directly from the RAW predefined dataset files
      (Data/Raw/Cardio_Data.csv for lifestyle, the raw clinical csv for
      clinical). No preprocessing, matching, or reconstruction involved.
2. build_manual_patient() (+ save_manual_patient() / load_manual_patient())
   -- construct a patient dict from user-entered form values (e.g. hospital
      intake, or a UI "try your own numbers" mode), and persist it
      separately from the predefined dataset. Same downstream code path
      either way -- this is the whole point: the simulator does not care
      where the dict came from, so the UI layer just needs to call
      whichever of these functions produces the dict, then hand it to
      LongTermSimulator exactly as NB10 already does.

WHY THIS READS RAW FILES ONLY -- NOT df_lifestyle_test.csv
-----------------------------------------------------------------------------
An earlier version of this loader tried to source predefined lifestyle
patients from Outputs/Lifestyle/df_lifestyle_test.csv (the post-
preprocessing, model-ready matrix -- one-hot cholesterol/glucose, `bmi`
instead of raw height_cm/weight_kg) and recover the missing height/weight
by matching row_index against Cardio_Data.csv. That assumption failed:
NB1's train/test split does not preserve row order (confirmed: row 0 of
the processed file and row 0 of the raw file were two different people --
age 63.9 vs 50.4, BP 140/80 vs 110/80), and reverse-matching on shared
features isn't reliably unique either (some rows had multiple candidate
matches). There was never a need to go through the processed file for
this purpose anyway -- it exists for model evaluation, not patient
selection. Data/Raw/Cardio_Data.csv already has every raw feature needed
(real height, weight, BP, cholesterol category, etc.), so both loader
functions below just read a row from the appropriate RAW file directly.

Every patient dict this module returns carries a "_provenance" field
recording exactly which file/row (or "manual_entry") produced it, so
downstream code (UI, paper figures) can display that honestly.
"""

from __future__ import annotations
import os
import json
import uuid
from datetime import datetime, timezone
import pandas as pd

# Default location for manually-entered patients. Deliberately a SEPARATE
# file/folder from Data/Raw and Data/Processed -- manual patients must never
# be mixed into the predefined dataset, so this path is never the same file
# a loader function above reads from.
DEFAULT_MANUAL_PATIENTS_CSV = os.path.join("Data", "Manual", "manual_patients.csv")

# Plausibility bounds for manual entry validation. Kept intentionally wide
# (clinical extremes, not "typical" ranges) -- the point is to catch typos
# and impossible values, not to second-guess an unusual-but-real patient.
_MANUAL_BOUNDS = {
    "age": (18, 100),
    "height_cm": (120, 220),
    "weight_kg": (30, 250),
    "systolic_bp": (70, 250),
    "diastolic_bp": (40, 150),
    "resting_bp": (70, 250),
    "cholesterol_level": (1, 3),
    "glucose_level": (1, 3),
    "cholesterol": (100, 500),        # clinical cohort's continuous mg/dL field
}


def _validate_range(field: str, value: float):
    bounds = _MANUAL_BOUNDS.get(field)
    if bounds and not (bounds[0] <= value <= bounds[1]):
        raise ValueError(
            f"{field}={value} is outside the plausible range {bounds}. "
            f"If this is a genuine extreme value, widen _MANUAL_BOUNDS "
            f"deliberately rather than silently letting it through."
        )


# =============================================================================
# LIFESTYLE COHORT
# =============================================================================

def load_real_lifestyle_patient(raw_csv_path: str, row_index: int) -> dict:
    """
    Returns a raw_patient dict ready for LongTermSimulator.simulate_lifestyle().

    raw_csv_path: path to Data/Raw/Cardio_Data.csv -- the ORIGINAL raw file
        (columns: age, gender, height, weight, ap_hi, ap_lo, cholesterol,
        gluc, smoke, alco, active, target). This is the ONLY file this
        function reads.

    WHY THE OLD "Mode A / Mode B" APPROACH WAS DROPPED
    -----------------------------------------------------------------------
    The previous version tried to recover a processed-test-set patient's
    real height/weight by matching row_index against Cardio_Data.csv,
    assuming NB1's split preserved row order. It doesn't -- NB1 shuffles/
    splits the data, so row 0 of df_lifestyle_test.csv is a different
    person than row 0 of Cardio_Data.csv (confirmed: age 63.9 vs 50.4,
    BP 140/80 vs 110/80 in your actual run). Reverse-matching on shared
    features (age/BP/smoking/etc.) was tried and rejected too -- it isn't
    even guaranteed unique (row 9 alone had 5 candidate matches).

    The fix: there was never a need to go through df_lifestyle_test.csv in
    the first place. That file exists for MODEL EVALUATION, not for
    picking a predefined patient. For a "pick a patient from our dataset"
    UI feature, Data/Raw/Cardio_Data.csv already has every raw feature
    build_lifestyle_features() needs (real height_cm, weight_kg included)
    -- so we just read a row directly. No matching, no reconstruction,
    no approximation, no Mode A/B distinction needed anymore.

    NOTE: `target` (the raw file's outcome/label column) is intentionally
    never included in the returned patient dict -- it's the ground-truth
    label this dataset was built to predict, not an input feature.
    """
    df = pd.read_csv(raw_csv_path)
    if row_index >= len(df):
        raise IndexError(f"row_index={row_index} out of range for {raw_csv_path} "
                          f"({len(df)} rows).")
    row = df.iloc[row_index]

    gender_str = str(row["gender"]).lower()  # Cardio_Data.csv already stores 'm'/'f' directly
    if gender_str not in ("m", "f"):
        raise ValueError(f"Row {row_index}: unexpected gender value {row['gender']!r} "
                          f"-- expected 'm' or 'f'.")

    patient = {
        "age": float(row["age"]),
        "gender": gender_str,
        "height_cm": float(row["height"]),
        "weight_kg": float(row["weight"]),
        "systolic_bp": float(row["ap_hi"]),
        "diastolic_bp": float(row["ap_lo"]),
        "cholesterol_level": int(row["cholesterol"]),  # already 1/2/3 in the raw file
        "glucose_level": int(row["gluc"]),              # already 1/2/3 in the raw file
        "smoking": int(row["smoke"]),
        "alcohol": int(row["alco"]),
        "physical_activity": int(row["active"]),
        "_provenance": {
            "source_file": raw_csv_path,
            "row_index": row_index,
            "note": "Read directly from the raw dataset -- real height/weight, "
                    "no reconstruction or approximation involved.",
        },
    }
    return patient


# =============================================================================
# CLINICAL COHORT -- simpler: df_clinical_test_raw.csv is already the raw
# schema NB10/NB9a expect, confirmed by header inspection. No reconstruction.
# =============================================================================

def load_real_clinical_patient(raw_test_csv_path: str, row_index: int) -> dict:
    """
    Returns a raw_patient dict ready for LongTermSimulator.simulate_clinical().
    raw_test_csv_path: path to df_clinical_test_raw.csv (already unscaled/
        unprocessed -- confirmed columns: age, sex, chest_pain_type,
        resting_bp, cholesterol, fasting_blood_sugar, resting_ecg,
        max_heart_rate, exercise_angina, oldpeak, st_slope, target).
    """
    df = pd.read_csv(raw_test_csv_path)
    if row_index >= len(df):
        raise IndexError(f"row_index={row_index} out of range for {raw_test_csv_path} "
                          f"({len(df)} rows).")
    row = df.iloc[row_index]

    if pd.isna(row.get("cholesterol")):
        # confirmed present in your actual data (row 0 of df_clinical_test_raw.csv
        # has a blank cholesterol value) -- Cleveland/Hungarian/Statlog have known
        # missingness here. Do not silently impute a made-up value in this loader;
        # surface it so the caller decides (drop this row, or use NB2's saved
        # imputer if that's the intended handling for this field).
        raise ValueError(
            f"Row {row_index}: cholesterol is missing (NaN) in the raw source. "
            f"This is known missingness in this dataset family, not a loader bug. "
            f"Either pick a different row_index, or apply NB2's fitted imputer to "
            f"this value before calling simulate_clinical() -- do not guess a value here."
        )

    patient = {
        "age": float(row["age"]),
        "sex": int(row["sex"]),
        "chest_pain_type": int(row["chest_pain_type"]),
        "resting_bp": float(row["resting_bp"]),
        "cholesterol": float(row["cholesterol"]),
        "fasting_blood_sugar": int(row["fasting_blood_sugar"]),
        "resting_ecg": int(row["resting_ecg"]),
        "max_heart_rate": float(row["max_heart_rate"]),
        "exercise_angina": int(row["exercise_angina"]),
        "oldpeak": float(row["oldpeak"]),
        "st_slope": int(row["st_slope"]),
        "_provenance": {
            "source_file": raw_test_csv_path,
            "row_index": row_index,
            "note": "This file is already in raw/unprocessed form -- no reconstruction needed.",
        },
    }
    return patient


# =============================================================================
# MANUAL ENTRY -- same output shape as the loaders above, so downstream code
# (LongTermSimulator, UI) treats a typed-in patient identically to a real one.
# =============================================================================

def build_manual_patient(
    cohort: str,
    age: float,
    gender_or_sex,
    systolic_bp: float,
    diastolic_bp: float | None = None,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    cholesterol_level: int | None = None,     # lifestyle: 1/2/3
    glucose_level: int | None = None,          # lifestyle: 1/2/3
    smoking: int | None = None,
    alcohol: int | None = None,
    physical_activity: int | None = None,
    cholesterol_mgdl: float | None = None,     # clinical: continuous
    chest_pain_type: int | None = None,
    fasting_blood_sugar: int | None = None,
    resting_ecg: int | None = None,
    max_heart_rate: float | None = None,
    exercise_angina: int | None = None,
    oldpeak: float | None = None,
    st_slope: int | None = None,
) -> dict:
    """
    cohort: "lifestyle" or "clinical". Determines which fields are required
    and how the dict is shaped for LongTermSimulator.

    This is the function your UI's "enter patient details manually" form
    should call. Raises ValueError with a specific message on any missing
    required field or out-of-range value -- surface that message directly
    in the UI rather than catching-and-hiding it, since these are exactly
    the checks that keep manually-entered patients from silently producing
    nonsense downstream.
    """
    _validate_range("age", age)
    _validate_range("systolic_bp", systolic_bp)

    if cohort == "lifestyle":
        required = {"diastolic_bp": diastolic_bp, "height_cm": height_cm,
                    "weight_kg": weight_kg, "cholesterol_level": cholesterol_level,
                    "glucose_level": glucose_level, "smoking": smoking,
                    "alcohol": alcohol, "physical_activity": physical_activity}
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise ValueError(f"Manual lifestyle patient missing required field(s): {missing}")

        _validate_range("diastolic_bp", diastolic_bp)
        _validate_range("height_cm", height_cm)
        _validate_range("weight_kg", weight_kg)
        _validate_range("cholesterol_level", cholesterol_level)
        _validate_range("glucose_level", glucose_level)
        if diastolic_bp >= systolic_bp:
            raise ValueError(f"diastolic_bp ({diastolic_bp}) must be less than "
                              f"systolic_bp ({systolic_bp}).")

        gender_str = gender_or_sex if isinstance(gender_or_sex, str) else ("m" if gender_or_sex == 1 else "f")
        return {
            "age": float(age), "gender": gender_str,
            "height_cm": float(height_cm), "weight_kg": float(weight_kg),
            "systolic_bp": float(systolic_bp), "diastolic_bp": float(diastolic_bp),
            "cholesterol_level": int(cholesterol_level), "glucose_level": int(glucose_level),
            "smoking": int(smoking), "alcohol": int(alcohol),
            "physical_activity": int(physical_activity),
            "_provenance": {"source": "manual_entry"},
        }

    elif cohort == "clinical":
        required = {"chest_pain_type": chest_pain_type, "cholesterol_mgdl": cholesterol_mgdl,
                    "fasting_blood_sugar": fasting_blood_sugar, "resting_ecg": resting_ecg,
                    "max_heart_rate": max_heart_rate, "exercise_angina": exercise_angina,
                    "oldpeak": oldpeak, "st_slope": st_slope}
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise ValueError(f"Manual clinical patient missing required field(s): {missing}")

        _validate_range("cholesterol", cholesterol_mgdl)
        sex_int = gender_or_sex if isinstance(gender_or_sex, int) else (1 if str(gender_or_sex).lower().startswith("m") else 0)
        return {
            "age": float(age), "sex": int(sex_int),
            "chest_pain_type": int(chest_pain_type), "resting_bp": float(systolic_bp),
            "cholesterol": float(cholesterol_mgdl), "fasting_blood_sugar": int(fasting_blood_sugar),
            "resting_ecg": int(resting_ecg), "max_heart_rate": float(max_heart_rate),
            "exercise_angina": int(exercise_angina), "oldpeak": float(oldpeak),
            "st_slope": int(st_slope),
            "_provenance": {"source": "manual_entry"},
        }
    else:
        raise ValueError(f"cohort must be 'lifestyle' or 'clinical', got '{cohort}'.")


# =============================================================================
# PERSISTENT STORAGE FOR MANUALLY-ENTERED PATIENTS
# -----------------------------------------------------------------------------
# build_manual_patient() above only builds a dict in memory -- nothing was
# ever saved to disk. That's the gap GPT flagged. These three functions fix
# it: every manually-entered patient gets a unique ID + timestamp and is
# appended as one row to its OWN csv (DEFAULT_MANUAL_PATIENTS_CSV), never the
# predefined Cardio_Data.csv / heart_statlog csv. The full patient dict is
# stored as a JSON blob in one column (schemas differ between lifestyle and
# clinical, and manual patients don't need to be queried like a feature
# matrix) plus a handful of flat columns for quick browsing in a UI table.
# =============================================================================

def save_manual_patient(
    patient: dict,
    csv_path: str = DEFAULT_MANUAL_PATIENTS_CSV,
) -> str:
    """
    Appends a manually-built patient (output of build_manual_patient()) to
    the persistent manual-patients store. Returns the generated patient_id
    so the caller (UI) can look this patient up again later.

    Never call this with a row pulled from load_real_lifestyle_patient() /
    load_real_clinical_patient() -- those belong to the predefined dataset
    and mixing them in here defeats the whole point of keeping the two
    populations separate for the paper/UI.
    """
    if patient.get("_provenance", {}).get("source") != "manual_entry":
        raise ValueError(
            "save_manual_patient() refused to save a patient whose "
            "_provenance.source is not 'manual_entry'. This function is only "
            "for patients built with build_manual_patient() -- predefined "
            "dataset rows must stay in their original files, never copied "
            "into manual_patients.csv."
        )

    cohort = "lifestyle" if "height_cm" in patient else "clinical"
    patient_id = f"manual_{uuid.uuid4().hex[:10]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    row = {
        "patient_id": patient_id,
        "timestamp_utc": timestamp,
        "cohort": cohort,
        "age": patient.get("age"),
        "gender_or_sex": patient.get("gender", patient.get("sex")),
        "patient_json": json.dumps(patient),
    }

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    file_exists = os.path.isfile(csv_path)
    df_row = pd.DataFrame([row])
    df_row.to_csv(csv_path, mode="a", header=not file_exists, index=False)

    return patient_id


def load_manual_patient(
    patient_id: str,
    csv_path: str = DEFAULT_MANUAL_PATIENTS_CSV,
) -> dict:
    """
    Retrieves a previously-saved manual patient by patient_id and returns
    it in the exact same dict shape build_manual_patient() produced -- ready
    to hand straight to LongTermSimulator.simulate_lifestyle/_clinical(),
    or to re-score as-is for a "recheck current risk" action.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(
            f"No manual patients file found at {csv_path} -- has anyone "
            f"called save_manual_patient() yet?"
        )
    df = pd.read_csv(csv_path)
    match = df[df["patient_id"] == patient_id]
    if match.empty:
        raise KeyError(f"patient_id={patient_id!r} not found in {csv_path}.")
    return json.loads(match.iloc[0]["patient_json"])


def list_manual_patients(csv_path: str = DEFAULT_MANUAL_PATIENTS_CSV) -> pd.DataFrame:
    """
    Returns the flat browsing columns (id, timestamp, cohort, age, gender)
    for every saved manual patient -- what a UI "select a saved patient"
    dropdown would populate itself from. Does NOT include the full JSON
    (call load_manual_patient() for that once one is selected).
    """
    if not os.path.isfile(csv_path):
        return pd.DataFrame(columns=["patient_id", "timestamp_utc", "cohort", "age", "gender_or_sex"])
    df = pd.read_csv(csv_path)
    return df[["patient_id", "timestamp_utc", "cohort", "age", "gender_or_sex"]]


def delete_manual_patient(
    patient_id: str,
    csv_path: str = DEFAULT_MANUAL_PATIENTS_CSV,
) -> None:
    """Permanently remove one manually entered patient from its own CSV store.

    Predefined dataset records cannot reach this function. The caller must
    provide the exact generated manual patient ID, which makes the deletion
    target explicit and leaves all other saved records unchanged.
    """
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"No manual patients file found at {csv_path}.")

    df = pd.read_csv(csv_path)
    if patient_id not in set(df["patient_id"]):
        raise KeyError(f"patient_id={patient_id!r} not found in {csv_path}.")

    updated_df = df[df["patient_id"] != patient_id]
    updated_df.to_csv(csv_path, index=False)


# =============================================================================
# RECHECK / RESCORE -- get a fresh risk estimate for any patient dict
# (predefined-dataset OR manual, baseline OR already-modified) without
# necessarily running a full intervention simulation. Useful for a UI
# "recalculate risk" button after someone edits a saved manual patient, or
# just to display current risk before offering intervention options.
# =============================================================================

def recheck_risk(model, patient: dict) -> dict:
    """
    model: an already-constructed PatientScoringModel (from nb9a_patient_scoring).
    patient: any raw_patient dict produced by this module (real or manual).

    Cohort is auto-detected the same way save_manual_patient() does it:
    presence of 'height_cm' -> lifestyle cohort, otherwise -> clinical cohort.
    Strips '_provenance' before scoring since the model only expects the
    feature fields.
    """
    scoring_input = {k: v for k, v in patient.items() if k != "_provenance"}
    cohort = "lifestyle" if "height_cm" in patient else "clinical"
    if cohort == "lifestyle":
        result = model.score_lifestyle(scoring_input)
    else:
        result = model.score_clinical(scoring_input)
    return {"cohort": cohort, "provenance": patient.get("_provenance"), **result}


# =============================================================================
# SELF-TEST / SANITY CHECK -- mirrors the exact check ChatGPT's plan called
# out as important: baseline risk from the loaded real patient must equal
# baseline risk computed by calling score_lifestyle()/score_clinical()
# directly on the same dict. If these ever diverge, something in the loader
# (or in LongTermSimulator's field-name normalization) is silently wrong.
# =============================================================================

if __name__ == "__main__":
    import os
    import sys
    import json

    print("=" * 80)
    print("NB10B — PATIENT LOADER SELF-TEST")
    print("=" * 80)
    print(
        "\nThis only tests the loader functions' shape/validation logic.\n"
        "To test against your real model artifacts, run this from your project\n"
        "root with Outputs/Models etc. present, and uncomment the model-scoring\n"
        "block below.\n"
    )

    # --- Manual entry smoke test (no files / no model needed) ---
    manual_ls = build_manual_patient(
        cohort="lifestyle", age=50, gender_or_sex="m",
        systolic_bp=138, diastolic_bp=88, height_cm=175, weight_kg=88,
        cholesterol_level=2, glucose_level=1, smoking=1, alcohol=0, physical_activity=0,
    )
    print("Manual lifestyle patient built OK:")
    print(json.dumps(manual_ls, indent=2))

    try:
        build_manual_patient(cohort="lifestyle", age=50, gender_or_sex="m",
                              systolic_bp=90, diastolic_bp=120,  # invalid: dbp >= sbp
                              height_cm=175, weight_kg=88, cholesterol_level=2,
                              glucose_level=1, smoking=1, alcohol=0, physical_activity=0)
        print("ERROR: validation should have raised on dbp >= sbp and did not.")
    except ValueError as e:
        print(f"\nValidation correctly rejected an invalid manual patient: {e}")

    # --- Persistent manual-patient storage smoke test ---
    # Uses a throwaway test path so this never touches your real
    # Data/Manual/manual_patients.csv during a plain self-test run.
    test_csv = os.path.join("Data", "Manual", "manual_patients_selftest.csv")
    pid = save_manual_patient(manual_ls, csv_path=test_csv)
    print(f"\nSaved manual patient to {test_csv} with patient_id={pid}")

    reloaded = load_manual_patient(pid, csv_path=test_csv)
    assert reloaded == manual_ls, "Reloaded manual patient does not match what was saved."
    print("Reload check PASSED -- saved and reloaded patient are identical.")

    listing = list_manual_patients(csv_path=test_csv)
    print("\nCurrent manual patients in store:")
    print(listing.to_string(index=False))

    os.remove(test_csv)
    print(f"\n(Removed {test_csv} -- that was a self-test file, not your real store.)")

    # --- Uncomment and adjust paths to test against your real data + model ---
    #
    # sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # from nb9a_patient_scoring import PatientScoringModel
    # from nb10_long_term_simulation import LongTermSimulator
    #
    # model = PatientScoringModel(model_dir="Outputs/Models",
    #                              explainability_dir="Outputs/Explainability",
    #                              genetics_dir="Outputs/Genetics")
    #
    # real_ls_patient = load_real_lifestyle_patient(
    #     raw_csv_path="Data/Raw/Cardio_Data.csv",
    #     row_index=0,
    # )
    # print("\nReal lifestyle patient loaded:")
    # print(json.dumps(real_ls_patient, indent=2))
    #
    # # THE IMPORTANT CHECK: loader-produced baseline risk must equal a direct
    # # score_lifestyle() call on the identical dict.
    # direct_score = model.score_lifestyle({k: v for k, v in real_ls_patient.items() if k != "_provenance"})
    # sim = LongTermSimulator(model)
    # sim_result = sim.simulate_lifestyle(real_ls_patient, interventions={})  # no interventions = baseline only
    # assert abs(direct_score["ml_risk"] - sim_result["baseline_risk"]["ml_risk"]) < 1e-9, (
    #     "MISMATCH: loader's patient does not produce the same baseline risk as a "
    #     "direct score_lifestyle() call. Do not trust this loader until this passes."
    # )
    # print(f"\nSanity check PASSED: baseline ml_risk = {direct_score['ml_risk']:.4f} "
    #       f"(loader) == {sim_result['baseline_risk']['ml_risk']:.4f} (direct call)")

    print("\n" + "=" * 80)
    print("Self-test complete.")
    print("=" * 80)
