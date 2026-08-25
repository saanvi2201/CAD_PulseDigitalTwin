"""
NB9b -- Pulse Physiology Bridge  (REWRITTEN against confirmed local APIs)
Build-order Step 6 | CVD Digital Twin Project | CAD_DT_Final

Every Pulse call below is either:
  [CONFIRMED]  -- taken directly from HowTo_EngineUse.py / HowTo_Exercise.py /
                  HowTo_CardiovascularModification.py / Soldier.json, which you
                  attached from your actual REL_4_3_2 install, or
  [OPEN]       -- a genuine open question that is NOT an API-naming question
                  (e.g. which physiological multiplier represents "quit smoking"),
                  clearly marked and left for you to decide, not guessed.

Nothing below is written against general Pulse familiarity anymore -- if a call
isn't in your HowTo files, it isn't used.

--------------------------------------------------------------------------
CHANGELOG vs the previous version -- read this before running
--------------------------------------------------------------------------
1. Logging is now wired up (set_log_filename + log_to_console(True)) BEFORE
   anything else happens. Previously nothing was logged, so the earlier
   'initialize_engine() returns False' failure gave you no reason why. Run
   this version and read test_results/nb9b/nb9b.log (or the console) --
   Pulse will tell you exactly what it rejected.

2. build_pulse_patient() now seeds from a template file (Soldier.json) via
   serialize_patient_from_file() BEFORE overriding age/sex/height/weight,
   exactly like HowTo_EngineUse.py's Stabilize_PatientObject branch. This is
   the most likely fix for the False return -- a patient built from scratch
   with only 4 properties set is missing BodyFatFraction and baseline
   HR/RR, which Pulse's stabilization needs.

3. pc.set_data_root_dir(...) is now called, matching every reference example.
   YOU must point PULSE_DATA_ROOT_DIR at the correct folder for your install
   -- I don't know your directory layout, so this is a placeholder you need
   to fix, not a guess I'm making on your behalf. See the comment at that
   line for how to find the right folder.

4. SESmokingCessation is REMOVED -- it does not exist in any of your
   reference files and I will not fabricate a class name. Lifestyle-level
   interventions now use the confirmed SECardiovascularMechanicsModification
   mechanism instead (see Section 5) -- but the specific multiplier/value
   that should represent "quit smoking" is left as an open modeling
   decision for you, not invented by me.

5. MeanArterialPressure and the results[0]=SimTime indexing are now marked
   CONFIRMED, not inferred -- both are directly demonstrated in
   HowTo_EngineUse.py.
--------------------------------------------------------------------------
"""

import os
import sys

# ── Update this for your machine ──────────────────────────────────────────────
PULSE_INSTALL_PATH = r"D:\pulse-engine\build\install\python"
sys.path.insert(0, PULSE_INSTALL_PATH)

# ── PULSE_DATA_ROOT_DIR — REQUIRED, NOT A GUESS YOU CAN SKIP ──────────────────
# Every reference example calls pc.set_data_root_dir(...) before
# initialize_engine(). This must point at the folder Pulse resolves its
# relative paths against ("./states/...", "./patients/...", "./environments/...").
# Look inside your D:\pulse-engine\build\install tree for whichever folder
# directly CONTAINS "states", "patients", and "environments" subfolders
# (commonly the same folder the HowTo_*.py scripts are meant to be run from,
# or a sibling "data"/"bin" folder) and put that path here.
PULSE_DATA_ROOT_DIR = r"D:\pulse-engine\build\install\bin"  # <-- VERIFY THIS

# Same reasoning for the patient template -- this must resolve to an actual
# Soldier.json (or another baseline patient file) under PULSE_DATA_ROOT_DIR.
PATIENT_TEMPLATE_RELATIVE_PATH = r"D:\pulse-engine\build\install\bin\patients\Soldier.json"  # <-- VERIFY THIS

LOG_DIR = "./test_results/nb9b/"
os.makedirs(LOG_DIR, exist_ok=True)

# ── Imports — all confirmed present together in HowTo_EngineUse.py ───────────
from pulse.engine.PulseEngine import PulseEngine, version, hash
from pulse.cdm.engine import SEDataRequestManager, SEDataRequest
from pulse.cdm.patient import eSex, SEPatient, SEPatientConfiguration
from pulse.cdm.patient_actions import SEExercise, SECardiovascularMechanicsModification
from pulse.cdm.scalars import (
    FrequencyUnit, PressureUnit, VolumePerTimeUnit, TimeUnit, LengthUnit, MassUnit,
)
from pulse.cdm.io.patient import serialize_patient_from_file

print("Using Pulse Version " + version() + "-" + hash())


# ============================================================================
# Section 1 — Data Requests                                        [CONFIRMED]
# Exact pattern + names from HowTo_EngineUse.py, including MeanArterialPressure
# which is explicitly in that file's data_requests list.
# ============================================================================

data_requests = [
    SEDataRequest.create_physiology_request("HeartRate", unit=FrequencyUnit.Per_min),
    SEDataRequest.create_physiology_request("SystolicArterialPressure", unit=PressureUnit.mmHg),
    SEDataRequest.create_physiology_request("DiastolicArterialPressure", unit=PressureUnit.mmHg),
    SEDataRequest.create_physiology_request("MeanArterialPressure", unit=PressureUnit.mmHg),
    SEDataRequest.create_physiology_request("CardiacOutput", unit=VolumePerTimeUnit.L_Per_min),
]

# CONFIRMED by HowTo_EngineUse.py's own comment:
#   "the results array also contains the simulation time at results[0] ...
#    think of this array as starting at index 1, in the same order as above"
RESULT_INDEX = {
    'heart_rate'     : 1,
    'systolic_bp'    : 2,
    'diastolic_bp'   : 3,
    'map'            : 4,
    'cardiac_output' : 5,
}

data_manager = SEDataRequestManager(data_requests)
data_manager.set_results_filename(os.path.join(LOG_DIR, "nb9b_results.csv"))
print(f"{len(data_requests)} data requests declared")


# ============================================================================
# Section 2 — Build a Pulse Patient From Raw Demographics
# Seeds from a template file first (CONFIRMED pattern from HowTo_EngineUse.py
# / Soldier.json), then overrides only the fields our raw_patient dict supplies.
# This is the fix for BodyFatFraction / baseline HR / baseline RR being unset.
# ============================================================================

# Same field-alias handling as NB9a's build_lifestyle_features(), so the SAME
# raw_patient dict can feed both NB9a's scoring and this Pulse bridge.
_ALIASES = {
    'height': 'height_cm', 'weight': 'weight_kg',
    'ap_hi': 'systolic_bp', 'ap_lo': 'diastolic_bp',
}

def _normalize_raw_patient(raw_patient: dict) -> dict:
    r = dict(raw_patient)
    for old, new in _ALIASES.items():
        if old in r and new not in r:
            r[new] = r.pop(old)
    return r


def build_pulse_patient_configuration(raw_patient: dict) -> "SEPatientConfiguration":
    """
    [CONFIRMED mechanism] Mirrors HowTo_EngineUse.py's Stabilize_PatientObject
    branch exactly:
        pc = SEPatientConfiguration()
        p = pc.get_patient()                      # get_patient(), NOT set_patient()
        serialize_patient_from_file(template, p)   # seed required baseline fields
        p.set_name(...); p.get_age().set_value(...); ...  # override what we know
        pc.set_data_root_dir(...)
    """
    r = _normalize_raw_patient(raw_patient)

    age    = r.get('age')
    sex_raw = r.get('sex', r.get('gender'))
    height = r.get('height_cm')
    weight = r.get('weight_kg')
    sbp    = r.get('systolic_bp')
    dbp    = r.get('diastolic_bp')

    missing = [n for n, v in [('age', age), ('sex', sex_raw)] if v is None]
    if missing:
        raise ValueError(f"Missing required field(s): {missing}")

    pc = SEPatientConfiguration()
    p = pc.get_patient()  # [CONFIRMED] get_patient(), matches the reversed
                           # isinstance() workaround you already identified

    # [CONFIRMED] seed from template BEFORE overriding, exactly like
    # HowTo_EngineUse.py: "Let's load up a file from disk ... Now let's
    # modify a few properties"
    serialize_patient_from_file(PATIENT_TEMPLATE_RELATIVE_PATH, p)

    p.set_name("DigitalTwinPatient")

    sex_value = eSex.Male if sex_raw in ('m', 'M', 'male', 'Male', 1, '1') else eSex.Female
    p.set_sex(sex_value)                                          # [CONFIRMED]
    p.get_age().set_value(age, TimeUnit.yr)                       # [CONFIRMED]

    if height is not None:
        # LengthUnit.cm: [OPEN, low risk] not literally shown in your files
        # (they use LengthUnit.inch) but a standard unit on the same enum --
        # if this throws AttributeError, convert cm -> inch yourself and use
        # LengthUnit.inch instead, which IS confirmed.
        p.get_height().set_value(height, LengthUnit.cm)
    if weight is not None:
        p.get_weight().set_value(weight, MassUnit.kg)             # [CONFIRMED unit]

    # [CONFIRMED] baseline vitals setters, from HowTo_EngineUse.py
    if sbp is not None:
        p.get_systolic_arterial_pressure_baseline().set_value(sbp, PressureUnit.mmHg)
    if dbp is not None:
        p.get_diastolic_arterial_pressure_baseline().set_value(dbp, PressureUnit.mmHg)

    # [CONFIRMED] every reference example sets this before initialize_engine
    pc.set_data_root_dir(PULSE_DATA_ROOT_DIR)

    return pc


print("build_pulse_patient_configuration() defined")


# ============================================================================
# Section 3 — Engine Setup, Init, Baseline Extraction              [CONFIRMED]
# ============================================================================

def make_engine(log_name: str) -> "PulseEngine":
    pulse = PulseEngine()
    # [CONFIRMED] — must call at least one of these or Pulse logs nowhere,
    # per HowTo_EngineUse.py's own comment. This is what was missing before
    # and is why the earlier False return gave you no diagnostic info.
    pulse.set_log_filename(os.path.join(LOG_DIR, f"{log_name}.log"))
    pulse.log_to_console(True)
    return pulse


def initialize_from_patient(pulse: "PulseEngine", pc: "SEPatientConfiguration") -> bool:
    # [CONFIRMED] positional args, exact call from HowTo_EngineUse.py
    return pulse.initialize_engine(pc, data_manager)


def extract_state(pulse: "PulseEngine") -> dict:
    # [CONFIRMED] pull_data() + index access, HowTo_EngineUse.py pattern
    results = pulse.pull_data()
    return {
        'heart_rate_bpm'          : results[RESULT_INDEX['heart_rate']],
        'systolic_bp_mmHg'        : results[RESULT_INDEX['systolic_bp']],
        'diastolic_bp_mmHg'       : results[RESULT_INDEX['diastolic_bp']],
        'map_mmHg'                : results[RESULT_INDEX['map']],
        'cardiac_output_L_per_min': results[RESULT_INDEX['cardiac_output']],
    }


def debug_print_initial_patient(pulse: "PulseEngine") -> None:
    # [CONFIRMED] optional sanity check -- lets you visually confirm Pulse
    # actually stabilized to the demographics you asked for.
    initial_patient = SEPatient()
    pulse.get_initial_patient(initial_patient)
    print("  Stabilized patient — Sex:", initial_patient.get_sex())
    print("  Stabilized patient — Age:", initial_patient.get_age())
    print("  Stabilized patient — Height:", initial_patient.get_height())
    print("  Stabilized patient — Weight:", initial_patient.get_weight())


print("make_engine() / initialize_from_patient() / extract_state() defined")


# ============================================================================
# Section 4 — Exercise Intervention                                [CONFIRMED]
# Exact pattern from HowTo_Exercise.py: set_comment + get_intensity().set_value
# (no unit — 0..1 fraction), process_action(). Reuse the SAME action object to
# stop, exactly as HowTo_EngineUse.py does (set intensity back to 0).
# ============================================================================

def apply_exercise(pulse: "PulseEngine", intensity: float, comment: str = "") -> "SEExercise":
    action = SEExercise()
    action.set_comment(comment)
    action.get_intensity().set_value(intensity)
    pulse.process_action(action)
    return action  # keep the reference so you can reuse it to stop the exercise


def stop_exercise(pulse: "PulseEngine", action: "SEExercise") -> None:
    action.set_comment("Stop")
    action.get_intensity().set_value(0)
    pulse.process_action(action)


# ============================================================================
# Section 5 — Cardiovascular Modification (lifestyle-level intervention)
#                                                          [CONFIRMED mechanism,
#                                                           OPEN modeling value]
# HowTo_CardiovascularModification.py confirms this class and this exact
# setter for heart_rate_multiplier:
#     cvMod = SECardiovascularMechanicsModification()
#     cvMod.get_modifiers().get_heart_rate_multiplier().set_value(1.05)
#     pulse.process_action(cvMod)
#
# By default this triggers Pulse's own re-stabilization to a new homeostasis
# -- which is actually a good physiological fit for a persistent lifestyle
# change (vs. SEExercise, which is a transient action).
#
# WHAT I HAVE NOT DONE: I have not picked a multiplier or value to represent
# "quit smoking." That is a physiological modeling decision -- it needs a
# citation or a defensible rationale (e.g. literature on smoking's acute/
# chronic effect on heart rate or vascular resistance), not an invented
# number from me. get_modifiers() likely exposes other multipliers besides
# heart_rate (e.g. resistance/compliance terms) by the same naming pattern,
# but ONLY heart_rate_multiplier is confirmed in your reference files. Run:
#     print([m for m in dir(cvMod.get_modifiers()) if m.startswith('get_')])
# on your machine to see the full confirmed list for your installed version
# before using anything beyond heart_rate_multiplier.
# ============================================================================

def apply_cardiovascular_modification(pulse: "PulseEngine", heart_rate_multiplier: float):
    """
    [CONFIRMED mechanism] Applies a persistent CV modification and lets Pulse
    re-stabilize. heart_rate_multiplier: e.g. 1.05 = +5% baseline HR (this
    exact value, 1.05, is the literal example in HowTo_CardiovascularModification.py
    -- it is NOT a claim about what quitting smoking does; pick your own
    value with a justification before using this for anything you'll report).
    """
    cv_mod = SECardiovascularMechanicsModification()
    cv_mod.get_modifiers().get_heart_rate_multiplier().set_value(heart_rate_multiplier)
    pulse.process_action(cv_mod)
    return cv_mod


print("apply_exercise() / stop_exercise() / apply_cardiovascular_modification() defined")


# ============================================================================
# Section 6 — Combined Bridge Function
# ============================================================================

def run_pulse_bridge(raw_patient: dict,
                      intervention: dict = None,
                      advance_seconds: float = 30) -> dict:
    """
    intervention examples:
      {'type': 'exercise', 'intensity': 0.6}
      {'type': 'cardiovascular_modification', 'heart_rate_multiplier': 1.05}
      None  -> baseline only, no intervention
    """
    pulse = make_engine("run_pulse_bridge")
    try:
        pc = build_pulse_patient_configuration(raw_patient)
        ok = initialize_from_patient(pulse, pc)
        if not ok:
            raise RuntimeError(
                "initialize_engine() returned False. Check "
                f"{LOG_DIR}run_pulse_bridge.log (and the console, since "
                "log_to_console(True) is set) for the actual Pulse-side reason "
                "-- likely a bad PULSE_DATA_ROOT_DIR or PATIENT_TEMPLATE_RELATIVE_PATH."
            )

        print("Patient initialized")
        debug_print_initial_patient(pulse)

        pulse_before = extract_state(pulse)
        print(f"  Baseline: {pulse_before}")

        if intervention is not None:
            itype = intervention.get('type')
            if itype == 'exercise':
                apply_exercise(pulse, intervention.get('intensity', 0.5),
                                comment=intervention.get('comment', 'Exercise'))
            elif itype == 'cardiovascular_modification':
                if 'heart_rate_multiplier' not in intervention:
                    raise ValueError(
                        "cardiovascular_modification requires 'heart_rate_multiplier' "
                        "-- see Section 5 comments; this value is a modeling decision, "
                        "not something this function will default for you."
                    )
                apply_cardiovascular_modification(pulse, intervention['heart_rate_multiplier'])
            else:
                raise ValueError(
                    f"Unknown intervention type: {itype!r} "
                    "(expected 'exercise' or 'cardiovascular_modification')"
                )

        pulse.advance_time_s(advance_seconds)  # [CONFIRMED]
        pulse_after = extract_state(pulse)
        print(f"  After {advance_seconds}s + {intervention}: {pulse_after}")

        return {
            'pulse_before': pulse_before,
            'pulse_after': pulse_after,
            'intervention_applied': intervention,
            'advance_seconds': advance_seconds,
        }
    finally:
        pulse.clear()  # [CONFIRMED]


print("run_pulse_bridge() defined")


# ============================================================================
# Section 7 — Test
# ============================================================================

if __name__ == "__main__":
    test_patient = {
        'age': 45, 'gender': 'm', 'height_cm': 178, 'weight_kg': 82,
        'systolic_bp': 120, 'diastolic_bp': 80,
    }

    print("=" * 60)
    print("  SECTION 7a: baseline only (run this first, alone)")
    print("=" * 60)
    try:
        baseline_only = run_pulse_bridge(test_patient, intervention=None, advance_seconds=10)
        print("\n[BASELINE TEST COMPLETE]")
        print(baseline_only)
        print("\nSanity check -- expected resting ranges:")
        print("  heart_rate_bpm : 60-100")
        print("  systolic_bp    : 90-140")
        print("  diastolic_bp   : 60-90")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nFailed at: {type(e).__name__}: {e}")
        print(f"Check {LOG_DIR}run_pulse_bridge.log for the Pulse-side reason.")
        print("Most likely causes, in order: PULSE_DATA_ROOT_DIR wrong, "
              "PATIENT_TEMPLATE_RELATIVE_PATH wrong, LengthUnit.cm not valid "
              "(try LengthUnit.inch with a converted value instead).")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  SECTION 7b: exercise intervention (only run after 7a passes)")
    print("=" * 60)
    exercise_result = run_pulse_bridge(
        test_patient, intervention={'type': 'exercise', 'intensity': 0.0375}, advance_seconds=360
    )
    print(exercise_result)
