"""
nb10c_run_demo.py — End-to-end demo: predefined dataset patient AND a saved
manual patient, both run through the long-term simulator, both rescored.

WHERE THIS FITS
-----------------------------------------------------------------------------
nb10b_patient_loader.py   -> gets a patient dict from somewhere
nb10_long_term_simulation.py -> runs an intervention, gives before/after risk
nb10c_run_demo.py (this file) -> wires the two together end-to-end so you
    can run ONE script and see: a real dataset patient going through the
    whole pipeline, AND a manually-entered patient being saved, reloaded,
    and rescored -- exactly the two workflows the UI will need to trigger.

Run this from your project root (same folder as nb9a_patient_scoring.py,
with Outputs/Models etc. present).
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nb9a_patient_scoring import PatientScoringModel
from nb10_long_term_simulation import LongTermSimulator
from nb10b_patient_loader import (
    load_real_lifestyle_patient,
    build_manual_patient,
    save_manual_patient,
    load_manual_patient,
    list_manual_patients,
    recheck_risk,
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- EDIT THESE PATHS to match your actual project layout ---
RAW_CARDIO_CSV = os.path.join(PROJECT_ROOT, "Data", "Raw", "Cardio_Data.csv")
MODEL_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Models")
EXPLAINABILITY_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Explainability")
GENETICS_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Genetics")


def main():
    model = PatientScoringModel(
        model_dir=MODEL_DIR,
        explainability_dir=EXPLAINABILITY_DIR,
        genetics_dir=GENETICS_DIR,
    )
    sim = LongTermSimulator(model)

    # =========================================================================
    # PART 1 — a REAL patient pulled from the predefined dataset. Reads
    # Data/Raw/Cardio_Data.csv directly (no processed/test file, no
    # matching) -- it already has real height/weight/BP/cholesterol/etc.
    # =========================================================================
    print("=" * 80)
    print("PART 1 — PREDEFINED DATASET PATIENT (row 0)")
    print("=" * 80)

    if os.path.isfile(RAW_CARDIO_CSV):
        real_patient = load_real_lifestyle_patient(
            raw_csv_path=RAW_CARDIO_CSV,
            row_index=0,
        )
        print("\nLoaded real patient (straight from Cardio_Data.csv):")
        print(json.dumps(real_patient, indent=2))

        # Recheck baseline risk before simulating anything (what a UI would
        # show the instant a patient is selected, before any what-if is run).
        baseline = recheck_risk(model, real_patient)
        print(f"\nCurrent baseline risk: {baseline['ml_risk']:.4f} "
              f"(band: {baseline.get('risk_band')})")

        # Run the actual long-term what-if.
        result = sim.simulate_lifestyle(
            real_patient,
            interventions={"exercise": True, "weight_loss_kg": 5.0},
        )
        print(f"\nProjected risk after exercise + 5kg weight loss: "
              f"{result['projected_risk_full_effect']['ml_risk']:.4f} "
              f"(delta: {result['delta_ml_risk']:+.4f})")
    else:
        print(
            f"\nSKIPPED — could not find {RAW_CARDIO_CSV}\n"
            "Edit RAW_CARDIO_CSV at the top of this script to match where "
            "Data/Raw/Cardio_Data.csv actually lives."
        )

    # =========================================================================
    # PART 2 — a MANUALLY ENTERED patient: build it, SAVE it (this is the
    # persistence step that was previously missing), reload it back by ID
    # exactly as the UI would after a user comes back to a saved entry, and
    # recheck its risk.
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 2 — MANUAL PATIENT (build -> save -> reload -> recheck)")
    print("=" * 80)

    manual_patient = build_manual_patient(
        cohort="lifestyle",
        age=54, gender_or_sex="f",
        systolic_bp=142, diastolic_bp=90,
        height_cm=160, weight_kg=78,
        cholesterol_level=3, glucose_level=2,
        smoking=0, alcohol=0, physical_activity=0,
    )

    patient_id = save_manual_patient(manual_patient)  # -> Data/Manual/manual_patients.csv
    print(f"\nSaved manual patient. patient_id = {patient_id}")
    print("(This lives in Data/Manual/manual_patients.csv — separate from "
          "the predefined dataset, never mixed in.)")

    reloaded_patient = load_manual_patient(patient_id)
    baseline_manual = recheck_risk(model, reloaded_patient)
    print(f"\nReloaded patient's current risk: {baseline_manual['ml_risk']:.4f} "
          f"(band: {baseline_manual.get('risk_band')})")

    manual_result = sim.simulate_lifestyle(
        reloaded_patient,
        interventions={"exercise": True, "smoking_cessation": {"quit": True, "years_since_quit": 0}}
        if reloaded_patient["smoking"] else {"exercise": True},
    )
    print(f"Projected risk after exercise: "
          f"{manual_result['projected_risk_full_effect']['ml_risk']:.4f} "
          f"(delta: {manual_result['delta_ml_risk']:+.4f})")

    print("\nAll saved manual patients so far:")
    print(list_manual_patients().to_string(index=False))

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()