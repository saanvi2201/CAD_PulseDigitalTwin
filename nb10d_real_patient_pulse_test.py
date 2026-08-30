import os
import json
import sys

# Make Pulse's Python bindings available
sys.path.insert(0, r"D:\pulse-engine\build\install\bin")
sys.path.insert(0, r"D:\pulse-engine\build\install\python")


from nb10b_patient_loader import load_real_lifestyle_patient
from nb9b_pulse_bridge import run_pulse_bridge


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

RAW_CARDIO_CSV = os.path.join(
    PROJECT_ROOT, "Data", "Raw", "Cardio_Data.csv"
)


def main():

    print("=" * 80)
    print("REAL PATIENT → PULSE SHORT-TERM TEST")
    print("=" * 80)

    # ------------------------------------------------------------
    # 1. Load an ACTUAL patient from our predefined raw dataset.
    # ------------------------------------------------------------
    patient = load_real_lifestyle_patient(
        raw_csv_path=RAW_CARDIO_CSV,
        row_index=0,
    )

    print("\nREAL PATIENT LOADED:")
    print(json.dumps(patient, indent=2))

    # ------------------------------------------------------------
    # 2. Send the SAME patient to Pulse.
    #
    # Exercise intensity = 0.0375
    # Advance simulation by 360 seconds = 6 minutes
    # ------------------------------------------------------------
    result = run_pulse_bridge(
        patient,
        intervention={
            "type": "exercise",
            "intensity": 0.0375,
            "comment": "Short-term exercise test"
        },
        advance_seconds=360,
    )

    # ------------------------------------------------------------
    # 3. Display Pulse's physiological response.
    # ------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PULSE RESULT")
    print("=" * 80)

    print("\nBEFORE EXERCISE:")
    print(json.dumps(result["pulse_before"], indent=2))

    print("\nAFTER EXERCISE:")
    print(json.dumps(result["pulse_after"], indent=2))

    print("\n" + "=" * 80)
    print("REAL PATIENT → PULSE TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()