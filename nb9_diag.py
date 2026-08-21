"""
nb9b_diagnostic.py -- 4-condition controlled comparison
CVD Digital Twin Project | CAD_DT_Final

Runs, in order:
  1. Soldier via serialize_from_file("./states/Soldier@0s.json")  -- pre-baked
     state, no stabilization computed at all. Reference floor.
  2. Soldier via SEPatientConfiguration + initialize_engine(), ZERO overrides
     beyond the one required field (sex) -- isolates whether stabilization
     itself is the problem.
  3. Custom patient (age/sex/height/weight only, NO BP override) via
     stabilization -- isolates whether the BP-baseline override specifically
     is what's causing the crash.
  4. Custom patient WITH BP override (120/80) via stabilization -- reproduces
     your original crashing run for direct comparison.

Every condition runs the SAME exercise intensity (0.06) for the SAME 30s,
and pulls the SAME variables, so the printed table is a clean apples-to-apples
comparison.

Path fix vs the previous version: HowTo_EngineUse.py uses set_data_root_dir("./")
and serialize_patient_from_file("./patients/Soldier.json", p) -- both RELATIVE.
That only resolves correctly if the process's cwd is the directory containing
states/ patients/ environments/, which you already confirmed is
D:\\pulse-engine\\build\\install\\bin (that's where the official HowTo_Exercise.py
ran successfully). So this script chdir's there itself before any Pulse call,
instead of guessing an absolute data-root path.
"""

import os
import sys

# ── Paths -- adjust ONLY if your install differs from what you've confirmed ──
PULSE_PYTHON_PATH = r"D:\pulse-engine\build\install\python"
PULSE_BIN_DIR      = r"D:\pulse-engine\build\install\bin"     # confirmed via your successful HowTo_Exercise.py run
LOG_DIR             = r"D:\CAD_DigitalTwin\test_results\nb9b_diagnostic"  # absolute, so it doesn't move when we chdir

sys.path.insert(0, PULSE_PYTHON_PATH)
os.makedirs(LOG_DIR, exist_ok=True)

# Pulse resolves "./states/...", "./patients/..." relative to cwd -- match
# the directory the confirmed-working official example was run from.
os.chdir(PULSE_BIN_DIR)

from pulse.engine.PulseEngine import PulseEngine, version, hash
from pulse.cdm.engine import SEDataRequestManager, SEDataRequest
from pulse.cdm.patient import eSex, SEPatient, SEPatientConfiguration
from pulse.cdm.patient_actions import SEExercise
from pulse.cdm.scalars import (
    FrequencyUnit, PressureUnit, VolumePerTimeUnit, VolumeUnit, TimeUnit, LengthUnit, MassUnit,
)
from pulse.cdm.io.patient import serialize_patient_from_file

print("Using Pulse Version " + version() + "-" + hash())
print(f"Running from cwd: {os.getcwd()}")


# ============================================================================
# Data requests -- [CONFIRMED], BloodVolume added per HowTo_EngineUse.py
# ============================================================================

data_requests = [
    SEDataRequest.create_physiology_request("HeartRate", unit=FrequencyUnit.Per_min),
    SEDataRequest.create_physiology_request("SystolicArterialPressure", unit=PressureUnit.mmHg),
    SEDataRequest.create_physiology_request("DiastolicArterialPressure", unit=PressureUnit.mmHg),
    SEDataRequest.create_physiology_request("MeanArterialPressure", unit=PressureUnit.mmHg),
    SEDataRequest.create_physiology_request("CardiacOutput", unit=VolumePerTimeUnit.L_Per_min),
    SEDataRequest.create_physiology_request("BloodVolume", unit=VolumeUnit.mL),
]

RESULT_INDEX = {
    'heart_rate'     : 1,
    'systolic_bp'    : 2,
    'diastolic_bp'   : 3,
    'map'            : 4,
    'cardiac_output' : 5,
    'blood_volume'   : 6,
}


def new_data_manager(tag: str) -> "SEDataRequestManager":
    # Fresh manager per condition so each condition's CSV is separate/inspectable.
    dm = SEDataRequestManager(data_requests)
    dm.set_results_filename(os.path.join(LOG_DIR, f"{tag}_results.csv"))
    return dm


def extract_state(pulse: "PulseEngine") -> dict:
    results = pulse.pull_data()
    return {
        'heart_rate_bpm'          : results[RESULT_INDEX['heart_rate']],
        'systolic_bp_mmHg'        : results[RESULT_INDEX['systolic_bp']],
        'diastolic_bp_mmHg'       : results[RESULT_INDEX['diastolic_bp']],
        'map_mmHg'                : results[RESULT_INDEX['map']],
        'cardiac_output_L_per_min': results[RESULT_INDEX['cardiac_output']],
        'blood_volume_mL'         : results[RESULT_INDEX['blood_volume']],
    }


# ============================================================================
# Patient builder -- age/height/weight/sbp/dbp now all OPTIONAL overrides on
# top of the Soldier.json template. Only sex is required (Soldier.json has no
# sex field per HowTo_EngineUse.py's comment: "You only need to set sex").
# ============================================================================

def build_patient_configuration(sex='m', age=None, height_cm=None, weight_kg=None,
                                 systolic_bp=None, diastolic_bp=None) -> "SEPatientConfiguration":
    pc = SEPatientConfiguration()
    p = pc.get_patient()  # [CONFIRMED] get_patient(), not set_patient()

    # [CONFIRMED] relative path, matches HowTo_EngineUse.py exactly, now that
    # cwd == PULSE_BIN_DIR
    serialize_patient_from_file("./patients/Soldier.json", p)

    p.set_name("DigitalTwinPatient")
    sex_value = eSex.Male if sex in ('m', 'M', 'male', 'Male', 1, '1') else eSex.Female
    p.set_sex(sex_value)  # required -- not in Soldier.json

    if age is not None:
        p.get_age().set_value(age, TimeUnit.yr)
    if height_cm is not None:
        p.get_height().set_value(height_cm, LengthUnit.cm)
    if weight_kg is not None:
        p.get_weight().set_value(weight_kg, MassUnit.kg)
    if systolic_bp is not None:
        p.get_systolic_arterial_pressure_baseline().set_value(systolic_bp, PressureUnit.mmHg)
    if diastolic_bp is not None:
        p.get_diastolic_arterial_pressure_baseline().set_value(diastolic_bp, PressureUnit.mmHg)

    pc.set_data_root_dir("./")  # [CONFIRMED] relative, exact match to HowTo_EngineUse.py
    return pc


def apply_exercise(pulse: "PulseEngine", intensity: float, comment: str = "Exercise"):
    action = SEExercise()
    action.set_comment(comment)
    action.get_intensity().set_value(intensity)
    pulse.process_action(action)


# ============================================================================
# Condition runners
# ============================================================================

def run_condition_state_file(tag: str, exercise_intensity: float, advance_seconds: float) -> dict:
    """Condition 1: pre-baked stabilized state, no stabilization computed."""
    dm = new_data_manager(tag)
    pulse = PulseEngine()
    pulse.set_log_filename(os.path.join(LOG_DIR, f"{tag}.log"))
    pulse.log_to_console(True)
    try:
        # [CONFIRMED] serialize_from_file accepts a data_req_mgr -- shown in
        # HowTo_EngineUse.py's State branch (StandardMale@0s.json + data_req_mgr)
        if not pulse.serialize_from_file("./states/Soldier@0s.json", dm):
            raise RuntimeError("serialize_from_file failed to load Soldier@0s.json")

        before = extract_state(pulse)
        apply_exercise(pulse, exercise_intensity)
        pulse.advance_time_s(advance_seconds)
        after = extract_state(pulse)
        return {'condition': tag, 'before': before, 'after': after}
    finally:
        pulse.clear()


def run_condition_stabilized(tag: str, patient_kwargs: dict,
                              exercise_intensity: float, advance_seconds: float) -> dict:
    """Conditions 2/3/4: full SEPatientConfiguration -> initialize_engine path."""
    dm = new_data_manager(tag)
    pulse = PulseEngine()
    pulse.set_log_filename(os.path.join(LOG_DIR, f"{tag}.log"))
    pulse.log_to_console(True)
    try:
        pc = build_patient_configuration(**patient_kwargs)
        ok = pulse.initialize_engine(pc, dm)  # [CONFIRMED] positional
        if not ok:
            raise RuntimeError(
                f"initialize_engine() returned False for condition '{tag}'. "
                f"Check {os.path.join(LOG_DIR, tag + '.log')} for the Pulse-side reason."
            )

        before = extract_state(pulse)
        apply_exercise(pulse, exercise_intensity)
        pulse.advance_time_s(advance_seconds)
        after = extract_state(pulse)
        return {'condition': tag, 'before': before, 'after': after}
    finally:
        pulse.clear()


# ============================================================================
# Run all 4 conditions
# ============================================================================

if __name__ == "__main__":
    EXERCISE_INTENSITY = 0.06
    ADVANCE_SECONDS = 30
    results = []

    print("\n" + "=" * 70)
    print("  CONDITION 1: Soldier via state file (reference floor, no stabilization)")
    print("=" * 70)
    try:
        results.append(run_condition_state_file(
            "cond1_soldier_state_file", EXERCISE_INTENSITY, ADVANCE_SECONDS))
        print(results[-1])
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        results.append({'condition': 'cond1_soldier_state_file', 'before': None, 'after': None, 'error': str(e)})

    print("\n" + "=" * 70)
    print("  CONDITION 2: Soldier via stabilization pathway, zero overrides")
    print("=" * 70)
    try:
        results.append(run_condition_stabilized(
            "cond2_soldier_stabilized_zero_override",
            {'sex': 'm'},
            EXERCISE_INTENSITY, ADVANCE_SECONDS))
        print(results[-1])
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        results.append({'condition': 'cond2_soldier_stabilized_zero_override', 'before': None, 'after': None, 'error': str(e)})

    print("\n" + "=" * 70)
    print("  CONDITION 3: Custom patient, stabilization, NO BP override")
    print("=" * 70)
    try:
        results.append(run_condition_stabilized(
            "cond3_custom_no_bp_override",
            {'sex': 'm', 'age': 45, 'height_cm': 178, 'weight_kg': 82},
            EXERCISE_INTENSITY, ADVANCE_SECONDS))
        print(results[-1])
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        results.append({'condition': 'cond3_custom_no_bp_override', 'before': None, 'after': None, 'error': str(e)})

    print("\n" + "=" * 70)
    print("  CONDITION 4: Custom patient, stabilization, WITH BP override (120/80)")
    print("=" * 70)
    try:
        results.append(run_condition_stabilized(
            "cond4_custom_with_bp_override",
            {'sex': 'm', 'age': 45, 'height_cm': 178, 'weight_kg': 82,
             'systolic_bp': 120, 'diastolic_bp': 80},
            EXERCISE_INTENSITY, ADVANCE_SECONDS))
        print(results[-1])
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
        results.append({'condition': 'cond4_custom_with_bp_override', 'before': None, 'after': None, 'error': str(e)})

    # ── Comparison table ──────────────────────────────────────────────────────
    print("\n\n" + "=" * 100)
    print("  COMPARISON TABLE  (exercise intensity = 0.06, advance = 30s)")
    print("=" * 100)
    header = f"{'Condition':<42}{'HR before->after':<20}{'SBP before->after':<22}{'DBP before->after':<22}{'MAP before->after'}"
    print(header)
    print("-" * 100)
    for r in results:
        if r.get('before') is None:
            print(f"{r['condition']:<42}FAILED: {r.get('error', '')}")
            continue
        b, a = r['before'], r['after']
        hr  = f"{b['heart_rate_bpm']:.1f} -> {a['heart_rate_bpm']:.1f}"
        sbp = f"{b['systolic_bp_mmHg']:.1f} -> {a['systolic_bp_mmHg']:.1f}"
        dbp = f"{b['diastolic_bp_mmHg']:.1f} -> {a['diastolic_bp_mmHg']:.1f}"
        map_ = f"{b['map_mmHg']:.1f} -> {a['map_mmHg']:.1f}"
        print(f"{r['condition']:<42}{hr:<20}{sbp:<22}{dbp:<22}{map_}")

    print("\nHow to read this:")
    print("  If condition 2 already shows the BP crash -> the problem is the")
    print("    stabilization pathway itself, not your custom demographics.")
    print("  If condition 2 looks normal but condition 3 crashes -> something")
    print("    about custom age/height/weight (not BP) triggers it.")
    print("  If condition 3 looks normal but condition 4 crashes -> the BP")
    print("    baseline override specifically is the cause (the inconsistent-")
    print("    override hypothesis).")
    print("  Condition 1 is your reference floor -- compare its exercise response")
    print("    shape (not exact numbers) against whichever condition matches your")
    print("    real use case.")