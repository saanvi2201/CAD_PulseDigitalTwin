import os
import sys
import pandas as pd

# ============================================================
# Pulse paths
# ============================================================

PULSE_PYTHON = r"D:\pulse-engine\build\install\python"
PULSE_BIN = r"D:\pulse-engine\build\install\bin"

if PULSE_PYTHON not in sys.path:
    sys.path.insert(0, PULSE_PYTHON)

os.environ["PATH"] = PULSE_BIN + ";" + os.environ.get("PATH", "")

# ============================================================
# Import the WORKING NB9b bridge
# ============================================================

from nb9b_pulse_bridge import (
    build_pulse_patient_configuration,
    make_engine,
    initialize_from_patient,
    extract_state,
)

from pulse.cdm.patient_actions import SEExercise


# ============================================================
# Test patient
# ============================================================

def make_test_patient():

    return {
        "name": "StandardMaleBridgeValidation",
        "sex": "male",
        "age": 44,
        "weight_kg": 77.1,
        "height_cm": 180.3,
        "body_fat_fraction": 0.21,
        "hr_bpm": 72,
        "sbp_mmHg": 114,
        "dbp_mmHg": 73.6,
        "respiration_rate": 12,
    }


# ============================================================
# Run ONE simulation
# ============================================================

def run_case(patient, intensity, seconds=360):

    pulse = make_engine(
        f"nb9c_intensity_{str(intensity).replace('.', '_')}"
    )

    pc = build_pulse_patient_configuration(patient)

    ok = initialize_from_patient(pulse, pc)

    if not ok:
        raise RuntimeError(
            f"Pulse failed to initialize at intensity {intensity}"
        )

    # Pulse's stabilized baseline
    before = extract_state(pulse)

    # --------------------------------------------------------
    # Exercise
    # --------------------------------------------------------

    if intensity > 0:

        exercise = SEExercise()

        exercise.set_comment(
            f"Validation exercise intensity {intensity}"
        )

        exercise.get_intensity().set_value(
            float(intensity)
        )

        pulse.process_action(exercise)

    # --------------------------------------------------------
    # Advance simulation
    # --------------------------------------------------------

    pulse.advance_time_s(seconds)

    after = extract_state(pulse)

    pulse.clear()

    return before, after


# ============================================================
# Main validation
# ============================================================

if __name__ == "__main__":

    print("=" * 80)
    print("NB9C — PULSE EXERCISE INTENSITY VALIDATION")
    print("=" * 80)

    patient = make_test_patient()

    print("\nTEST PATIENT")
    print("-" * 80)
    print(patient)

    # These are the intensities used by Pulse's own
    # ExerciseStages scenario.
    intensities = [
        0.0,
        0.0375,
        0.075,
        0.1583,
        0.3583,
    ]

    results = []

    # ========================================================
    # Run all intensities
    # ========================================================

    for intensity in intensities:

        print("\n" + "=" * 80)
        print(f"RUNNING INTENSITY = {intensity}")
        print("=" * 80)

        before, after = run_case(
            patient=patient,
            intensity=intensity,
            seconds=360,
        )

        print("\nBefore:")
        print(before)

        print("\nAfter:")
        print(after)

        # ----------------------------------------------------
        # Calculate changes
        # ----------------------------------------------------

        variables = [
            "heart_rate_bpm",
            "systolic_bp_mmHg",
            "diastolic_bp_mmHg",
            "map_mmHg",
            "cardiac_output_L_per_min",
            "oxygen_consumption_mL_per_min",
            "respiration_rate_per_min",
            "tidal_volume_L",
            "achieved_exercise_level",
            "fatigue_level",
            "total_metabolic_rate_kcal_per_day",
        ]

        row = {
            "intensity": intensity,
        }

        for variable in variables:

            before_value = before.get(variable)
            after_value = after.get(variable)

            row[f"{variable}_before"] = before_value
            row[f"{variable}_after"] = after_value

            try:
                if (
                    before_value is not None
                    and after_value is not None
                ):
                    row[f"{variable}_change"] = (
                        float(after_value)
                        - float(before_value)
                    )
                else:
                    row[f"{variable}_change"] = None

            except (TypeError, ValueError):

                row[f"{variable}_change"] = None

        results.append(row)

    # ========================================================
    # Create results table
    # ========================================================

    df = pd.DataFrame(results)

    print("\n\n")
    print("=" * 100)
    print("SUMMARY — PHYSIOLOGICAL RESPONSE TO EXERCISE INTENSITY")
    print("=" * 100)

    summary_columns = [
        "intensity",

        "heart_rate_bpm_change",
        "systolic_bp_mmHg_change",
        "diastolic_bp_mmHg_change",
        "map_mmHg_change",
        "cardiac_output_L_per_min_change",
        "oxygen_consumption_mL_per_min_change",
    ]

    print(
        df[summary_columns].to_string(
            index=False
        )
    )

    # ========================================================
    # Save complete results
    # ========================================================

    output_file = (
        "nb9c_exercise_intensity_validation_results.csv"
    )

    df.to_csv(
        output_file,
        index=False,
    )

    print("\n" + "=" * 100)
    print("VALIDATION COMPLETE")
    print("=" * 100)

    print("\nComplete results saved to:")
    print(os.path.abspath(output_file))