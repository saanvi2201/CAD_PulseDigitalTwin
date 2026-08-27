import os
import sys
import json

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

PULSE_PYTHON = r"D:\pulse-engine\build\install\python"
PULSE_BIN = r"D:\pulse-engine\build\install\bin"

if PULSE_PYTHON not in sys.path:
    sys.path.insert(0, PULSE_PYTHON)

os.environ["PATH"] = PULSE_BIN + ";" + os.environ.get("PATH", "")


# ============================================================
# NB9a — ML SCORING
# ============================================================

from nb9a_patient_scoring import PatientScoringModel

MODEL_DIR = os.path.join(
    PROJECT_ROOT,
    "Outputs",
    "Models"
)

EXPLAINABILITY_DIR = os.path.join(
    PROJECT_ROOT,
    "Outputs",
    "Explainability"
)

GENETICS_DIR = os.path.join(
    PROJECT_ROOT,
    "Outputs",
    "Genetics"
)


# ============================================================
# NB9b — PULSE
# ============================================================

from nb9b_pulse_bridge import run_pulse_bridge


# ============================================================
# ONE TEST PATIENT
# ============================================================

patient = {

    # --------------------------------------------------------
    # Common patient information
    # --------------------------------------------------------

    "name": "NB9E_TestPatient",
    "age": 45,
    "sex": "male",

    # --------------------------------------------------------
    # Anthropometric information
    # --------------------------------------------------------

    "height_cm": 178,
    "weight_kg": 82,

    # --------------------------------------------------------
    # Baseline cardiovascular information
    # --------------------------------------------------------

    "systolic_bp": 120,
    "diastolic_bp": 80,

    # --------------------------------------------------------
    # Lifestyle model inputs
    # --------------------------------------------------------

    "gender": "m",
    "ap_hi": 120,
    "ap_lo": 80,

    "cholesterol_level": 1,
    "glucose_level": 1,
    "smoking": 0,
    "alcohol": 0,
    "physical_activity": 1,
}


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 80)
    print("NB9E — END-TO-END DIGITAL TWIN TEST")
    print("=" * 80)

    print("\nPATIENT")
    print("-" * 80)
    print(json.dumps(patient, indent=2))


    # ========================================================
    # STEP 1 — LOAD NB9a MODEL
    # ========================================================

    print("\n" + "=" * 80)
    print("STEP 1 — LOADING NB9a")
    print("=" * 80)

    model = PatientScoringModel(
        model_dir=MODEL_DIR,
        explainability_dir=EXPLAINABILITY_DIR,
        genetics_dir=GENETICS_DIR,
    )

    print("NB9a model loaded successfully.")


    # ========================================================
    # STEP 2 — ML RISK SCORING
    # ========================================================

    print("\n" + "=" * 80)
    print("STEP 2 — NB9a RISK SCORING")
    print("=" * 80)


    # --------------------------------------------------------
    # 2A — Lifestyle model
    # --------------------------------------------------------

    print("\nLifestyle scoring...")

    lifestyle_result = model.score_lifestyle(patient)

    print("\nLifestyle result:")
    print(
        json.dumps(
            lifestyle_result,
            indent=2,
            default=str
        )
    )


    # --------------------------------------------------------
    # 2B — Clinical model
    #
    # NB9a expects clinical sex as 0/1, while Pulse expects
    # the textual representation "male"/"female".
    #
    # Therefore we create a separate clinical representation
    # rather than changing the main patient object.
    # --------------------------------------------------------

    print("\nClinical scoring...")

    clinical_patient = patient.copy()

    clinical_patient["sex"] = 1

    clinical_patient.update({

        "chest_pain_type": 1,

        "resting_bp": 120,

        "cholesterol": 180,

        "fasting_blood_sugar": 0,

        "resting_ecg": 0,

        "max_heart_rate": 150,

        "exercise_angina": 0,

        "oldpeak": 0.0,

        "st_slope": 1,
    })

    clinical_result = model.score_clinical(
        clinical_patient
    )

    print("\nClinical result:")
    print(
        json.dumps(
            clinical_result,
            indent=2,
            default=str
        )
    )


    # ========================================================
    # STEP 3 — PULSE BASELINE
    # ========================================================

    print("\n" + "=" * 80)
    print("STEP 3 — PULSE BASELINE")
    print("=" * 80)

    # Only the variables supported by the Pulse bridge
    # are passed into the physiological engine.

    pulse_patient = {

        "name": patient["name"],

        "age": patient["age"],

        "sex": patient["sex"],

        "height_cm": patient["height_cm"],

        "weight_kg": patient["weight_kg"],

        "systolic_bp": patient["systolic_bp"],

        "diastolic_bp": patient["diastolic_bp"],
    }

    baseline_result = run_pulse_bridge(
        pulse_patient,
        intervention=None,
        advance_seconds=10,
    )

    print("\nPulse baseline:")
    print(
        json.dumps(
            baseline_result,
            indent=2,
            default=str
        )
    )


    # ========================================================
    # STEP 4 — EXERCISE COUNTERFACTUAL
    # ========================================================

    print("\n" + "=" * 80)
    print("STEP 4 — PULSE EXERCISE COUNTERFACTUAL")
    print("=" * 80)

    exercise_result = run_pulse_bridge(
        pulse_patient,

        intervention={
            "type": "exercise",
            "intensity": 0.0375,
            "comment": "NB9E exercise counterfactual",
        },

        advance_seconds=360,
    )

    print("\nPulse exercise result:")
    print(
        json.dumps(
            exercise_result,
            indent=2,
            default=str
        )
    )


    # ========================================================
    # STEP 5 — COMBINED END-TO-END RESULT
    # ========================================================

    combined = {

        "patient": patient,

        "ml": {

            "lifestyle": lifestyle_result,

            "clinical": clinical_result,
        },

        "pulse": {

            "baseline": baseline_result,

            "exercise_counterfactual": exercise_result,
        },
    }


    # ========================================================
    # SAVE RESULT
    # ========================================================

    output_file = os.path.join(
        PROJECT_ROOT,
        "validation",
        "nb9e_end_to_end_result.json",
    )

    os.makedirs(
        os.path.dirname(output_file),
        exist_ok=True,
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            combined,
            f,
            indent=2,
            default=str,
        )


    # ========================================================
    # COMPLETE
    # ========================================================

    print("\n" + "=" * 80)
    print("NB9E COMPLETE")
    print("=" * 80)

    print("\nCombined result saved to:")
    print(output_file)