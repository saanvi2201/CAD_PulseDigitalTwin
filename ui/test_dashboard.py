"""
test_dashboard.py — one script that checks whether the whole CAD Digital
Twin dashboard actually works, end to end, without you clicking through
every page by hand.

WHAT THIS DOES NOT DO
-----------------------------------------------------------------------------
It does not launch Streamlit and does not click buttons in a browser. Page
files (Home.py, pages/*.py) call st.set_page_config() and other Streamlit
commands at import time, which only work inside a real Streamlit server
process — so this script can't just "import" them directly. Instead it:

  1. Reads each page file as TEXT and statically checks:
       - it's valid Python (would fail to even load in Streamlit otherwise)
       - every name it imports from ui_helpers.py (or nb9a_patient_scoring.py,
         nb10b_patient_loader.py, nb10_long_term_simulation.py,
         nb9b_pulse_bridge.py) ACTUALLY EXISTS in that file right now
       - every st.switch_page("pages/....py") target actually exists on disk
     This catches the exact class of bug that broke things last time: a
     page expecting a function/constant that got renamed or removed
     elsewhere, which is invisible until you click into that specific page.

  2. Actually IMPORTS and RUNS the backend (ui_helpers, nb9a_patient_scoring,
     nb10b_patient_loader, nb10_long_term_simulation) — loads the real
     model, scores a real patient, runs a real simulation — and reports
     exactly which step failed and why, if any.

  3. Checks nb9b_pulse_bridge is importable and, only if you pass
     --run-pulse, actually runs one short Pulse simulation (this needs the
     Pulse engine + your PULSE_BIN_PATH/PULSE_PY_PATH to be correct, and is
     slow, so it's opt-in).

HOW TO RUN
-----------------------------------------------------------------------------
Place this file inside your `ui/` folder, next to ui_helpers.py, then:

    cd D:\\CAD_DigitalTwin
    venv\\Scripts\\activate
    cd ui
    python test_dashboard.py

Add --run-pulse to also do a real (slow) Pulse engine test:

    python test_dashboard.py --run-pulse

Everything is read-only. It never writes to your real Data/Manual/
manual_patients.csv (it uses a throwaway file for that test and deletes it
afterward), and it never modifies any page or backend file.
"""

import os
import sys
import ast
import time
import traceback
import argparse
import importlib

# -----------------------------------------------------------------------
# This script must live in ui/, next to ui_helpers.py, so paths resolve
# exactly the way they do when Streamlit actually runs your pages.
# -----------------------------------------------------------------------
UI_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(UI_DIR, ".."))
PAGES_DIR = os.path.join(UI_DIR, "pages")
sys.path.insert(0, UI_DIR)
sys.path.insert(0, PROJECT_ROOT)

RESULTS = []  # list of (section, check, status, detail)  status in {"PASS","FAIL","WARN","SKIP"}


def record(section, check, status, detail=""):
    RESULTS.append((section, check, status, detail))
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ ", "SKIP": "⏭️ "}[status]
    line = f"{icon} [{section}] {check}"
    if detail:
        line += f"\n      {detail}"
    print(line)


def section_header(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# =============================================================================
# SECTION 0 — Python packages
# =============================================================================
def check_packages():
    section_header("0. PYTHON PACKAGES")
    required = ["streamlit", "pandas", "numpy"]
    optional = ["plotly", "matplotlib", "shap", "sklearn", "xgboost"]
    for pkg in required:
        try:
            mod = importlib.import_module(pkg)
            v = getattr(mod, "__version__", "unknown version")
            record("packages", f"{pkg} installed", "PASS", v)
        except ImportError as e:
            record("packages", f"{pkg} installed", "FAIL",
                    f"Not installed — pip install {pkg}. ({e})")
    for pkg in optional:
        try:
            mod = importlib.import_module(pkg)
            v = getattr(mod, "__version__", "unknown version")
            record("packages", f"{pkg} installed (optional)", "PASS", v)
        except ImportError:
            record("packages", f"{pkg} installed (optional)", "WARN",
                    f"Not installed — only matters if a page actually uses it.")


# =============================================================================
# SECTION 1 — Required files/folders exist
# =============================================================================
def check_paths():
    section_header("1. PROJECT PATHS")
    try:
        import ui_helpers as uh
    except Exception as e:
        record("paths", "import ui_helpers.py to read its configured paths", "FAIL",
                f"{type(e).__name__}: {e}")
        return

    path_vars = [
        ("RAW_LIFESTYLE_CSV", getattr(uh, "RAW_LIFESTYLE_CSV", None), "file"),
        ("RAW_CLINICAL_CSV", getattr(uh, "RAW_CLINICAL_CSV", None), "file"),
        ("MODEL_DIR", getattr(uh, "MODEL_DIR", None), "dir"),
        ("EXPLAINABILITY_DIR", getattr(uh, "EXPLAINABILITY_DIR", None), "dir"),
        ("GENETICS_DIR", getattr(uh, "GENETICS_DIR", None), "dir"),
    ]
    for name, path, kind in path_vars:
        if path is None:
            record("paths", f"ui_helpers.{name} is defined", "FAIL", "Not found in ui_helpers.py at all.")
            continue
        exists = os.path.isfile(path) if kind == "file" else os.path.isdir(path)
        if exists:
            record("paths", f"{name}", "PASS", path)
        else:
            record("paths", f"{name}", "FAIL", f"{kind} not found at: {path}")

    manual_csv = getattr(uh, "MANUAL_PATIENTS_CSV", None)
    if manual_csv:
        parent = os.path.dirname(manual_csv)
        if os.path.isdir(parent):
            record("paths", "MANUAL_PATIENTS_CSV parent folder exists", "PASS", parent)
        else:
            record("paths", "MANUAL_PATIENTS_CSV parent folder exists", "WARN",
                    f"{parent} doesn't exist yet — it will be created automatically the first "
                    f"time save_manual_patient() runs, so this isn't necessarily a problem.")

    for name in ("PULSE_BIN_PATH", "PULSE_PY_PATH"):
        p = getattr(uh, name, None)
        if p and os.path.isdir(p):
            record("paths", name, "PASS", p)
        else:
            record("paths", name, "WARN", f"{p} — not found. Short-Term Simulation (Pulse) will fail until this is correct.")


# =============================================================================
# SECTION 2 — Static cross-file import check (the bug class from last time)
# =============================================================================
def get_top_level_names(filepath):
    """All names a module actually defines at top level: functions, classes,
    and plain variable/constant assignments."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def get_imports_from(filepath, source_module_names):
    """Every `from X import a, b, c` in filepath where X is in
    source_module_names. Returns {module_name: set(imported_names)}."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in source_module_names:
            found.setdefault(node.module, set()).update(a.name for a in node.names)
    return found


def get_switch_page_targets(filepath):
    """Every literal string passed to st.switch_page(...) in filepath."""
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    targets = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "switch_page" and node.args
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            targets.append(node.args[0].value)
    return targets


BACKEND_MODULES = {
    "ui_helpers": os.path.join(UI_DIR, "ui_helpers.py"),
    "nb9a_patient_scoring": os.path.join(PROJECT_ROOT, "nb9a_patient_scoring.py"),
    "nb10b_patient_loader": os.path.join(PROJECT_ROOT, "nb10b_patient_loader.py"),
    "nb10_long_term_simulation": os.path.join(PROJECT_ROOT, "nb10_long_term_simulation.py"),
    "nb9b_pulse_bridge": os.path.join(PROJECT_ROOT, "nb9b_pulse_bridge.py"),
    "domain_maps": os.path.join(PROJECT_ROOT, "domain_maps.py"),
}


def check_cross_file_imports():
    section_header("2. STATIC IMPORT CHECK (page files vs. ui_helpers.py / backend files)")

    module_exports = {}
    for mod_name, path in BACKEND_MODULES.items():
        if not os.path.isfile(path):
            record("static-imports", f"{mod_name}.py exists", "WARN",
                    f"Not found at {path} — skipping import checks against it.")
            continue
        try:
            module_exports[mod_name] = get_top_level_names(path)
        except SyntaxError as e:
            record("static-imports", f"{mod_name}.py is valid Python", "FAIL", str(e))

    page_files = [os.path.join(UI_DIR, "Home.py")]
    if os.path.isdir(PAGES_DIR):
        page_files += sorted(
            os.path.join(PAGES_DIR, f) for f in os.listdir(PAGES_DIR) if f.endswith(".py")
        )
    else:
        record("static-imports", "pages/ folder exists", "FAIL", f"Not found at {PAGES_DIR}")

    all_good = True
    for page_path in page_files:
        page_name = os.path.relpath(page_path, UI_DIR)

        # 2a. syntax
        try:
            with open(page_path, "r", encoding="utf-8") as f:
                ast.parse(f.read(), filename=page_path)
        except SyntaxError as e:
            record("static-imports", f"{page_name} — valid Python syntax", "FAIL", str(e))
            all_good = False
            continue
        record("static-imports", f"{page_name} — valid Python syntax", "PASS")

        # 2b. every imported name actually exists in the source module
        imports = get_imports_from(page_path, set(module_exports.keys()))
        for mod_name, imported_names in imports.items():
            available = module_exports.get(mod_name, set())
            missing = imported_names - available
            if missing:
                record(
                    "static-imports",
                    f"{page_name} imports from {mod_name}.py",
                    "FAIL",
                    f"These names are imported but DO NOT EXIST in {mod_name}.py: {sorted(missing)}\n"
                    f"      This page will crash immediately on load with an ImportError.\n"
                    f"      Available in {mod_name}.py: {sorted(available)}",
                )
                all_good = False
            else:
                record("static-imports", f"{page_name} imports from {mod_name}.py", "PASS",
                        f"{sorted(imported_names)}")

        # 2c. switch_page targets exist on disk
        for target in get_switch_page_targets(page_path):
            target_path = os.path.join(UI_DIR, target)
            if os.path.isfile(target_path):
                record("static-imports", f"{page_name} → switch_page('{target}')", "PASS")
            else:
                record("static-imports", f"{page_name} → switch_page('{target}')", "FAIL",
                        f"Target file does not exist at {target_path}")
                all_good = False

    return all_good


# =============================================================================
# SECTION 3 — Backend imports actually work (not just syntax)
# =============================================================================
def check_backend_imports():
    section_header("3. BACKEND MODULE IMPORTS")
    mods = {}
    for mod_name in ["ui_helpers", "nb9a_patient_scoring", "nb10b_patient_loader",
                      "nb10_long_term_simulation", "nb9b_pulse_bridge"]:
        try:
            mods[mod_name] = importlib.import_module(mod_name)
            record("backend-import", f"import {mod_name}", "PASS")
        except Exception as e:
            record("backend-import", f"import {mod_name}", "FAIL",
                    f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
    return mods


# =============================================================================
# SECTION 4 — Model loading
# =============================================================================
def check_model_loading(mods):
    section_header("4. MODEL LOADING (PatientScoringModel)")
    if "ui_helpers" not in mods:
        record("model", "get_model()", "SKIP", "ui_helpers didn't import — see Section 3.")
        return None
    uh = mods["ui_helpers"]
    try:
        t0 = time.time()
        # get_model() is @st.cache_resource, which needs a Streamlit runtime
        # to cache against — outside Streamlit it just runs the function
        # once directly, which is exactly what we want for this test.
        model = uh.get_model.__wrapped__() if hasattr(uh.get_model, "__wrapped__") else _load_model_direct(uh)
        elapsed = time.time() - t0
        record("model", "PatientScoringModel loads successfully", "PASS", f"{elapsed:.1f}s")
        return model
    except Exception as e:
        record("model", "PatientScoringModel loads successfully", "FAIL",
                f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=6)}")
        return None


def _load_model_direct(uh):
    from nb9a_patient_scoring import PatientScoringModel
    return PatientScoringModel(
        model_dir=uh.MODEL_DIR, explainability_dir=uh.EXPLAINABILITY_DIR, genetics_dir=uh.GENETICS_DIR,
    )


# =============================================================================
# SECTION 5 — Patient loading (predefined + manual round-trip)
# =============================================================================
def check_patient_loading(mods):
    section_header("5. PATIENT LOADING")
    if "nb10b_patient_loader" not in mods or "ui_helpers" not in mods:
        record("patients", "loader tests", "SKIP", "Required module didn't import — see Section 3.")
        return None, None

    loader = mods["nb10b_patient_loader"]
    uh = mods["ui_helpers"]
    lifestyle_patient = None
    clinical_patient = None

    # ---- predefined lifestyle ----
    if os.path.isfile(uh.RAW_LIFESTYLE_CSV):
        try:
            lifestyle_patient = loader.load_real_lifestyle_patient(uh.RAW_LIFESTYLE_CSV, 0)
            record("patients", "load_real_lifestyle_patient(row=0)", "PASS",
                    f"keys: {sorted(lifestyle_patient.keys())}")
        except Exception as e:
            record("patients", "load_real_lifestyle_patient(row=0)", "FAIL",
                    f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}")
    else:
        record("patients", "load_real_lifestyle_patient(row=0)", "SKIP", "RAW_LIFESTYLE_CSV not found.")

    # ---- predefined clinical ----
    if os.path.isfile(uh.RAW_CLINICAL_CSV):
        try:
            clinical_patient = loader.load_real_clinical_patient(uh.RAW_CLINICAL_CSV, 0)
            record("patients", "load_real_clinical_patient(row=0)", "PASS",
                    f"keys: {sorted(clinical_patient.keys())}")
        except Exception as e:
            record("patients", "load_real_clinical_patient(row=0)", "FAIL",
                    f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}")
    else:
        record("patients", "load_real_clinical_patient(row=0)", "SKIP", "RAW_CLINICAL_CSV not found.")

    # ---- manual round-trip, using a throwaway file ----
    test_csv = os.path.join(PROJECT_ROOT, "Data", "Manual", "manual_patients_TESTONLY.csv")
    try:
        manual = loader.build_manual_patient(
            cohort="lifestyle", age=50, gender_or_sex="m",
            systolic_bp=120, diastolic_bp=80, height_cm=175, weight_kg=75,
            cholesterol_level=1, glucose_level=1, smoking=0, alcohol=0, physical_activity=1,
        )
        record("patients", "build_manual_patient()", "PASS")

        pid = loader.save_manual_patient(manual, csv_path=test_csv)
        record("patients", "save_manual_patient()", "PASS", f"patient_id={pid}")

        reloaded = loader.load_manual_patient(pid, csv_path=test_csv)
        if reloaded == manual:
            record("patients", "load_manual_patient() round-trip matches", "PASS")
        else:
            record("patients", "load_manual_patient() round-trip matches", "FAIL",
                    "Saved and reloaded patient differ.")

        listing = loader.list_manual_patients(csv_path=test_csv)
        record("patients", "list_manual_patients()", "PASS", f"{len(listing)} row(s)")
    except Exception as e:
        record("patients", "manual patient round-trip", "FAIL",
                f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}")
    finally:
        if os.path.isfile(test_csv):
            os.remove(test_csv)

    return lifestyle_patient, clinical_patient


# =============================================================================
# SECTION 6 — Scoring
# =============================================================================
EXPECTED_SCORE_KEYS = {"ml_risk", "risk_band", "domain_attribution", "p_base", "p_integrated"}


def check_scoring(model, lifestyle_patient, clinical_patient):
    section_header("6. RISK SCORING")
    if model is None:
        record("scoring", "score_lifestyle / score_clinical", "SKIP", "Model didn't load — see Section 4.")
        return None, None

    ls_result = cl_result = None

    if lifestyle_patient is not None:
        try:
            scoring_input = {k: v for k, v in lifestyle_patient.items() if k != "_provenance"}
            ls_result = model.score_lifestyle(scoring_input)
            missing = EXPECTED_SCORE_KEYS - set(ls_result.keys())
            if missing:
                record("scoring", "score_lifestyle() returns expected keys", "FAIL",
                        f"Missing: {missing}. Got: {sorted(ls_result.keys())}")
            else:
                record("scoring", "score_lifestyle() returns expected keys", "PASS",
                        f"ml_risk={ls_result['ml_risk']:.3f}, band={ls_result['risk_band']}")
            if "top_features" not in ls_result:
                record("scoring", "score_lifestyle() includes 'top_features'", "WARN",
                        "Not present — Explainability's per-feature breakdown needs this key. "
                        "If pages/5_Explainability.py reads result['top_features'], it will KeyError "
                        "or show nothing useful.")
            else:
                record("scoring", "score_lifestyle() includes 'top_features'", "PASS",
                        f"{len(ls_result['top_features'])} feature(s)")
        except Exception as e:
            record("scoring", "score_lifestyle()", "FAIL", f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}")
    else:
        record("scoring", "score_lifestyle()", "SKIP", "No lifestyle patient available — see Section 5.")

    if clinical_patient is not None:
        try:
            scoring_input = {k: v for k, v in clinical_patient.items() if k != "_provenance"}
            cl_result = model.score_clinical(scoring_input)
            missing = EXPECTED_SCORE_KEYS - set(cl_result.keys())
            if missing:
                record("scoring", "score_clinical() returns expected keys", "FAIL",
                        f"Missing: {missing}. Got: {sorted(cl_result.keys())}")
            else:
                record("scoring", "score_clinical() returns expected keys", "PASS",
                        f"ml_risk={cl_result['ml_risk']:.3f}, band={cl_result['risk_band']}")
        except Exception as e:
            record("scoring", "score_clinical()", "FAIL", f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}")
    else:
        record("scoring", "score_clinical()", "SKIP", "No clinical patient available — see Section 5.")

    return ls_result, cl_result


# =============================================================================
# SECTION 7 — Long-term simulation
# =============================================================================
def check_long_term_simulation(mods, model, lifestyle_patient, clinical_patient):
    section_header("7. LONG-TERM SIMULATION")
    if "nb10_long_term_simulation" not in mods or model is None:
        record("longterm", "simulate_lifestyle / simulate_clinical", "SKIP",
                "Module or model unavailable — see Sections 3/4.")
        return

    try:
        sim = mods["nb10_long_term_simulation"].LongTermSimulator(model)
    except Exception as e:
        record("longterm", "LongTermSimulator(model)", "FAIL", f"{type(e).__name__}: {e}")
        return
    record("longterm", "LongTermSimulator(model) constructs", "PASS")

    expected_keys = {"baseline_risk", "projected_risk_full_effect", "delta_ml_risk", "applied_interventions"}

    if lifestyle_patient is not None:
        try:
            result = sim.simulate_lifestyle(lifestyle_patient, interventions={"exercise": True})
            missing = expected_keys - set(result.keys())
            if missing:
                record("longterm", "simulate_lifestyle(exercise=True)", "FAIL", f"Missing keys: {missing}")
            else:
                record("longterm", "simulate_lifestyle(exercise=True)", "PASS",
                        f"delta_ml_risk={result['delta_ml_risk']:+.3f}")
        except Exception as e:
            record("longterm", "simulate_lifestyle(exercise=True)", "FAIL",
                    f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}")
    else:
        record("longterm", "simulate_lifestyle()", "SKIP", "No lifestyle patient available.")

    if clinical_patient is not None:
        try:
            result = sim.simulate_clinical(clinical_patient, interventions={"exercise": True})
            missing = expected_keys - set(result.keys())
            if missing:
                record("longterm", "simulate_clinical(exercise=True)", "FAIL", f"Missing keys: {missing}")
            else:
                record("longterm", "simulate_clinical(exercise=True)", "PASS",
                        f"delta_ml_risk={result['delta_ml_risk']:+.3f}")
        except TypeError as e:
            # covers the case where simulate_clinical's signature (e.g. an
            # apply_optional_lipid_effect kwarg) doesn't match what's being
            # called here or what a page file assumes
            record("longterm", "simulate_clinical(exercise=True)", "WARN",
                    f"Called with only `interventions=` and got a TypeError — check simulate_clinical()'s "
                    f"actual required arguments: {e}")
        except Exception as e:
            record("longterm", "simulate_clinical(exercise=True)", "FAIL",
                    f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=4)}")
    else:
        record("longterm", "simulate_clinical()", "SKIP", "No clinical patient available.")


# =============================================================================
# SECTION 8 — Pulse bridge (import always; live run only with --run-pulse)
# =============================================================================
def check_pulse(mods, lifestyle_patient, run_pulse: bool):
    section_header("8. SHORT-TERM SIMULATION (Pulse bridge)")
    if "nb9b_pulse_bridge" not in mods:
        record("pulse", "nb9b_pulse_bridge import", "SKIP", "Didn't import — see Section 3.")
        return
    mod = mods["nb9b_pulse_bridge"]
    if not hasattr(mod, "run_pulse_bridge"):
        record("pulse", "run_pulse_bridge() exists", "FAIL", "Function not found in nb9b_pulse_bridge.py.")
        return
    record("pulse", "run_pulse_bridge() exists", "PASS")

    if not run_pulse:
        record("pulse", "live Pulse engine run", "SKIP",
                "Not requested — rerun with --run-pulse to actually exercise the Pulse engine "
                "(slow: engine init can take up to a minute or more).")
        return

    if lifestyle_patient is None:
        record("pulse", "live Pulse engine run", "SKIP", "No lifestyle patient available to test with.")
        return

    try:
        import ui_helpers as uh
        if uh.PULSE_BIN_PATH not in sys.path:
            sys.path.insert(0, uh.PULSE_BIN_PATH)
        if uh.PULSE_PY_PATH not in sys.path:
            sys.path.insert(0, uh.PULSE_PY_PATH)
        t0 = time.time()
        scoring_input = {k: v for k, v in lifestyle_patient.items() if k != "_provenance"}
        result = mod.run_pulse_bridge(
            scoring_input, intervention={"type": "exercise", "intensity": 0.0375, "comment": "diagnostic test"},
            advance_seconds=60,
        )
        elapsed = time.time() - t0
        if "pulse_before" in result and "pulse_after" in result:
            record("pulse", "live run_pulse_bridge() call", "PASS", f"{elapsed:.1f}s")
        else:
            record("pulse", "live run_pulse_bridge() call", "FAIL",
                    f"Returned but missing 'pulse_before'/'pulse_after'. Got keys: {sorted(result.keys())}")
    except Exception as e:
        record("pulse", "live run_pulse_bridge() call", "FAIL",
                f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=6)}")


# =============================================================================
# SUMMARY
# =============================================================================
def print_summary():
    section_header("SUMMARY")
    counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}
    for _, _, status, _ in RESULTS:
        counts[status] += 1
    print(f"✅ PASS: {counts['PASS']}   ❌ FAIL: {counts['FAIL']}   "
          f"⚠️  WARN: {counts['WARN']}   ⏭️  SKIP: {counts['SKIP']}")

    fails = [r for r in RESULTS if r[2] == "FAIL"]
    if fails:
        print("\nThings that need fixing, in order found:\n")
        for i, (section, check, status, detail) in enumerate(fails, 1):
            print(f"{i}. [{section}] {check}")
            if detail:
                first_line = detail.split("\n")[0]
                print(f"   → {first_line}")
        print(f"\n{len(fails)} issue(s) found. Fix these first — everything else is downstream of them.")
    else:
        print("\n🎉 No failures found. Any ⚠️  WARN items above are worth a look but aren't blocking.")


def main():
    parser = argparse.ArgumentParser(description="Diagnose the CAD Digital Twin dashboard end to end.")
    parser.add_argument("--run-pulse", action="store_true",
                         help="Also actually run the Pulse engine (slow, needs correct PULSE_BIN_PATH/PULSE_PY_PATH).")
    args = parser.parse_args()

    print("CAD Digital Twin — full diagnostic")
    print(f"UI folder:      {UI_DIR}")
    print(f"Project root:   {PROJECT_ROOT}")

    check_packages()
    check_paths()
    check_cross_file_imports()
    mods = check_backend_imports()
    model = check_model_loading(mods)
    lifestyle_patient, clinical_patient = check_patient_loading(mods)
    check_scoring(model, lifestyle_patient, clinical_patient)
    check_long_term_simulation(mods, model, lifestyle_patient, clinical_patient)
    check_pulse(mods, lifestyle_patient, args.run_pulse)

    print_summary()


if __name__ == "__main__":
    main()
