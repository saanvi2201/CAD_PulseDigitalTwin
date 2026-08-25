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
# Import working bridge
# ============================================================

from nb9b_pulse_bridge import (
    build_pulse_patient_configuration,
    make_engine,
    initialize_from_patient,
    extract_state,
    apply_exercise,
    stop_exercise,
)

# ============================================================
# StandardMale-like patient
# ============================================================

PATIENT = {
    "name": "StandardMaleStagedValidation",
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
# Official ExerciseStages protocol
#
# From Pulse's ExerciseStages.json:
#
# 30 s rest
# 0.0375 for 6 min
# stop for 2 min
# 0.075 for 6 min
# stop for 2 min
# 0.1583 for 6 min
# stop for 2 min
# 0.3583 for 6 min
# stop for 5 min
# ============================================================

STAGES = [
    (0.0375, 360),
    (0.0750, 360),
    (0.1583, 360),
    (0.3583, 360),
]

RECOVERY_SECONDS = 120
FINAL_RECOVERY_SECONDS = 300


def snapshot(pulse, label, intensity):
    state = extract_state(pulse)

    row = {
        "label": label,
        "intensity": intensity,
    }

    row.update(state)

    return row


def run_staged_protocol():

    print("=" * 80)
    print("NB9D — STAGED EXERCISE VALIDATION")
    print("=" * 80)

    print("\nPatient:")
    print(PATIENT)

    pulse = make_engine("nb9d_staged_validation")

    pc = build_pulse_patient_configuration(PATIENT)

    ok = initialize_from_patient(pulse, pc)

    if not ok:
        raise RuntimeError("Pulse failed to initialize.")

    results = []

    # --------------------------------------------------------
    # Initial stabilized baseline
    # --------------------------------------------------------

    results.append(
        snapshot(
            pulse,
            "baseline",
            0.0
        )
    )

    # --------------------------------------------------------
    # Official scenario starts with 30 s before exercise
    # --------------------------------------------------------

    print("\n30 s pre-exercise rest...")
    pulse.advance_time_s(30)

    results.append(
        snapshot(
            pulse,
            "pre_exercise",
            0.0
        )
    )

    # --------------------------------------------------------
    # Exercise stages
    # --------------------------------------------------------

    for i, (intensity, duration) in enumerate(STAGES, start=1):

        print("\n" + "=" * 80)
        print(
            f"STAGE {i}: intensity={intensity}, "
            f"duration={duration}s"
        )
        print("=" * 80)

        action = apply_exercise(
            pulse,
            intensity,
            comment=f"NB9D Stage {i}"
        )

        results.append(
            snapshot(
                pulse,
                f"stage_{i}_start",
                intensity
            )
        )

        pulse.advance_time_s(duration)

        results.append(
            snapshot(
                pulse,
                f"stage_{i}_end",
                intensity
            )
        )

        # ----------------------------------------------------
        # Stop exercise
        # ----------------------------------------------------

        print(f"Stopping stage {i}...")

        stop_exercise(
            pulse,
            action
        )

        results.append(
            snapshot(
                pulse,
                f"stage_{i}_stopped",
                0.0
            )
        )

        # ----------------------------------------------------
        # Recovery between stages
        # ----------------------------------------------------

        if i < len(STAGES):

            print(
                f"{RECOVERY_SECONDS}s recovery..."
            )

            pulse.advance_time_s(
                RECOVERY_SECONDS
            )

            results.append(
                snapshot(
                    pulse,
                    f"recovery_after_stage_{i}",
                    0.0
                )
            )

    # --------------------------------------------------------
    # Final recovery
    # --------------------------------------------------------

    print(
        f"\nFinal recovery: "
        f"{FINAL_RECOVERY_SECONDS}s..."
    )

    pulse.advance_time_s(
        FINAL_RECOVERY_SECONDS
    )

    results.append(
        snapshot(
            pulse,
            "final_recovery",
            0.0
        )
    )

    pulse.clear()

    return pd.DataFrame(results)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    df = run_staged_protocol()

    print("\n")
    print("=" * 100)
    print("STAGED PROTOCOL RESULTS")
    print("=" * 100)

    useful = [
        "label",
        "intensity",
        "heart_rate_bpm",
        "systolic_bp_mmHg",
        "diastolic_bp_mmHg",
        "map_mmHg",
        "cardiac_output_L_per_min",
    ]

    available = [
        c for c in useful
        if c in df.columns
    ]

    print(
        df[available].to_string(index=False)
    )

    output_file = (
        "nb9d_staged_validation_results.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    print("\nResults saved to:")
    print(os.path.abspath(output_file))