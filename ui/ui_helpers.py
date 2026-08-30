"""
ui_helpers.py — shared config, design system, cached backend loading, and
utility functions used across every page of the app.
"""

import os
import sys
import streamlit as st
import pandas as pd

# -----------------------------------------------------------------------
# PROJECT PATHS — EDIT THESE to match your actual folder layout.
# -----------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

RAW_LIFESTYLE_CSV = os.path.join(PROJECT_ROOT, "Data", "Raw", "Cardio_Data.csv")
RAW_CLINICAL_CSV = os.path.join(PROJECT_ROOT, "Outputs", "Clinical", "df_clinical_test_raw.csv")

MODEL_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Models")
EXPLAINABILITY_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Explainability")
GENETICS_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Genetics")

MANUAL_PATIENTS_CSV = os.path.join(PROJECT_ROOT, "Data", "Manual", "manual_patients.csv")

PULSE_BIN_PATH = r"D:\pulse-engine\build\install\bin"
PULSE_PY_PATH = r"D:\pulse-engine\build\install\python"

NAV_PAGES = [
    ("Home.py", "🏠", "Home"),
    ("pages/1_Select_Patient.py", "🔎", "Select Patient"),
    ("pages/2_Patient_Dashboard.py", "🗂️", "Patient Dashboard"),
    ("pages/3_Long_Term_Simulation.py", "📈", "Long-Term Simulation"),
    ("pages/4_Short_Term_Simulation.py", "🫁", "Short-Term Simulation"),
    ("pages/5_Explainability.py", "🔬", "Explainability"),
    ("pages/6_Summary.py", "📊", "Summary"),
]


# =============================================================================
# THEME / STYLING
# =============================================================================
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
h1, h2, h3, .cad-hero-title { font-family: 'Manrope', 'Inter', sans-serif; letter-spacing: -0.01em; }

:root {
    --bg: #0c0e16;
    --bg-panel: #141726;
    --bg-panel-2: #191d31;
    --border: #262b45;
    --text: #eef0fb;
    --text-dim: #9498b8;
    --accent: #6c7dfb;
    --accent-2: #a06cfb;
    --good: #2ecc8f;
    --warn: #f4b740;
    --bad: #ef5768;
}

[data-testid="stAppViewContainer"], .main { background: var(--bg); }
[data-testid="stHeader"] { background: rgba(12,14,22,0.0); }

/* Hide Streamlit's default auto-generated multipage nav links */
[data-testid="stSidebarNav"] { display: none; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #10121c 0%, #0c0e16 100%);
    border-right: 1px solid var(--border);
}
/* Streamlit places every sidebar item in a vertical layout wrapper. Keep its
   default gap compact so the navigation reads as one coherent menu. */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.35rem !important;
}
.cad-brand {
    display: flex; align-items: center; gap: 10px;
    padding: 4px 2px 18px 2px; margin-bottom: 10px;
    border-bottom: 1px solid var(--border);
}
.cad-brand-mark {
    width: 34px; height: 34px; border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem; flex-shrink: 0;
}
.cad-brand-text { font-family: 'Manrope', sans-serif; font-weight: 800; font-size: 1.02rem; color: var(--text); line-height: 1.1; }
.cad-brand-sub { font-size: 0.7rem; color: var(--text-dim); font-weight: 500; }

section[data-testid="stSidebar"] .stButton button {
    width: 100%; text-align: left;
    background: transparent; color: var(--text-dim);
    border: 1px solid transparent; border-radius: 10px;
    padding: 0.55rem 0.8rem; font-size: 0.92rem; font-weight: 500;
    margin-bottom: 3px; transition: all 0.15s ease;
}
section[data-testid="stSidebar"] .stButton button:hover {
    background: var(--bg-panel-2); border-color: var(--border); color: var(--text);
}
section[data-testid="stSidebar"] [class*="st-key-nav_active_"] button {
    background: linear-gradient(90deg, rgba(108,125,251,0.18), rgba(160,108,251,0.06));
    border-color: rgba(108,125,251,0.4); color: var(--text) !important; font-weight: 700 !important;
}

/* Page hero header */
.cad-hero {
    background: linear-gradient(120deg, rgba(108,125,251,0.14), rgba(160,108,251,0.05));
    border: 1px solid var(--border); border-radius: 18px;
    padding: 1.4rem 1.7rem; margin-bottom: 1.4rem;
}
.cad-hero-title { font-size: 1.65rem; font-weight: 800; color: var(--text); margin: 0 0 4px 0; }
.cad-hero-sub { color: var(--text-dim); font-size: 0.96rem; line-height: 1.5; margin: 0; }

/* Generic card */
.cad-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.15rem 1.35rem;
    margin-bottom: 0.9rem;
}
.cad-card-tight { padding: 0.85rem 1.05rem; }
.cad-card-hover:hover { border-color: rgba(108,125,251,0.45); }

/* Stat card */
.cad-stat {
    background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px;
    padding: 1.3rem 1.1rem; text-align: center;
}
.cad-stat-num { font-family: 'Manrope', sans-serif; font-size: 2.1rem; font-weight: 800; color: var(--text); line-height: 1.05; }
.cad-stat-label { color: var(--text-dim); font-size: 0.88rem; margin-top: 4px; font-weight: 500; }
.cad-stat-tag { font-size: 0.74rem; color: #6a6f8f; margin-top: 6px; }

/* Risk band pill */
.risk-pill {
    display: inline-block; padding: 7px 20px; border-radius: 999px;
    font-weight: 700; font-size: 1.0rem; color: white; letter-spacing: 0.01em;
}
/* Source badge */
.source-badge { display: inline-block; padding: 4px 13px; border-radius: 999px; font-size: 0.82rem; font-weight: 700; color: white; }

/* Feature contribution row */
.feat-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; }
.feat-bar-bg { background: #21243280; border-radius: 6px; height: 8px; width: 100%; margin-top: 4px; overflow: hidden; }
.feat-bar-fill { height: 100%; border-radius: 6px; }

/* Buttons */
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    border: none; font-weight: 700;
}
.stButton > button[kind="primary"]:hover { filter: brightness(1.08); }

hr { border-color: var(--border) !important; }
[data-testid="stMetricValue"] { color: var(--text); }
</style>
"""


def setup_page(title: str, icon: str, layout: str = "wide"):
    st.set_page_config(page_title=f"{title} — CAD Digital Twin", page_icon=icon, layout=layout)
    st.markdown(_CSS, unsafe_allow_html=True)
    render_sidebar_nav(active_title=title)


def hero(icon: str, title: str, subtitle: str):
    """Consistent page header banner — use instead of a bare st.title()."""
    st.markdown(
        f"<div class='cad-hero'>"
        f"<div class='cad-hero-title'>{icon} {title}</div>"
        f"<div class='cad-hero-sub'>{subtitle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_sidebar_nav(active_title: str = None):
    with st.sidebar:
        st.markdown(
            "<div class='cad-brand'>"
            "<div class='cad-brand-mark'>🫀</div>"
            "<div><div class='cad-brand-text'>CAD Digital Twin</div>"
            "<div class='cad-brand-sub'>Genomic risk & what-if simulation</div></div>"
            "</div>",
            unsafe_allow_html=True,
        )
        patient, cohort, source, label = get_selected_patient()
        if patient is not None:
            badge_color = "#3b6fd6" if source == "predefined" else "#2ea86f"
            st.markdown(
                f"<div class='cad-card cad-card-tight' style='margin-bottom:14px'>"
                f"<span class='source-badge' style='background:{badge_color}'>"
                f"{'Predefined' if source == 'predefined' else 'Manual'}</span>"
                f"<div style='margin-top:7px;font-size:0.88rem;color:#c7cbe0;font-weight:600'>{label}</div>"
                f"<div style='font-size:0.76rem;color:#6a6f8f'>{cohort} cohort</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        for path, icon, name in NAV_PAGES:
            is_active = (active_title == name)
            button_key = f"nav_active_{path}" if is_active else f"nav_{path}"
            if st.button(f"{icon}  {name}", key=button_key, use_container_width=True):
                st.switch_page(path)
        st.markdown("---")
        st.caption("Genomically-informed CAD risk digital twin")


# =============================================================================
# CACHED MODEL LOADING
# =============================================================================
@st.cache_resource(show_spinner="Loading trained model artifacts (first load only)…")
def get_model():
    from nb9a_patient_scoring import PatientScoringModel
    return PatientScoringModel(
        model_dir=MODEL_DIR, explainability_dir=EXPLAINABILITY_DIR, genetics_dir=GENETICS_DIR,
    )


@st.cache_resource(show_spinner=False)
def get_simulator():
    from nb10_long_term_simulation import LongTermSimulator
    return LongTermSimulator(get_model())


def backend_available() -> tuple[bool, str]:
    missing = []
    for label, path in [
        ("Models dir", MODEL_DIR), ("Explainability dir", EXPLAINABILITY_DIR), ("Genetics dir", GENETICS_DIR),
    ]:
        if not os.path.isdir(path):
            missing.append(f"{label} not found at: {path}")
    return (len(missing) == 0), "  \n".join(missing)


# =============================================================================
# SESSION STATE
# =============================================================================
def set_selected_patient(patient: dict, cohort: str, source: str, label: str):
    st.session_state["selected_patient"] = patient
    st.session_state["selected_cohort"] = cohort
    st.session_state["selected_source"] = source
    st.session_state["selected_label"] = label


def get_selected_patient():
    return (
        st.session_state.get("selected_patient"),
        st.session_state.get("selected_cohort"),
        st.session_state.get("selected_source"),
        st.session_state.get("selected_label"),
    )


def require_patient_selected():
    patient, cohort, source, label = get_selected_patient()
    if patient is None:
        st.markdown(
            "<div class='cad-card' style='text-align:center;padding:2.5rem'>"
            "<div style='font-size:2rem'>🔎</div>"
            "<div style='font-weight:700;font-size:1.1rem;margin:8px 0 4px 0'>No patient selected yet</div>"
            "<div style='color:#9498b8;margin-bottom:16px'>Choose a patient from the predefined dataset, or enter one manually, to continue.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("🔎 Go to Select Patient", type="primary"):
            st.switch_page("pages/1_Select_Patient.py")
        st.stop()
    return patient, cohort, source, label


# =============================================================================
# NAVIGATE-WITH-CONTEXT helpers (used by the Summary page's clickable cards)
# =============================================================================
def go_browse_cohort(cohort: str):
    """Set a one-shot prefill flag and jump to Select Patient with that
    cohort's tab/filter pre-selected. Select Patient reads and clears this
    flag on load."""
    st.session_state["prefill_cohort"] = cohort
    st.switch_page("pages/1_Select_Patient.py")


def consume_prefill_cohort(default: str = "lifestyle") -> str:
    val = st.session_state.pop("prefill_cohort", None)
    return val if val in ("lifestyle", "clinical") else default


# =============================================================================
# Formatting / explanation helpers
# =============================================================================
RISK_BAND_COLOR = {"Low": "#2ecc8f", "Moderate": "#f4b740", "High": "#f2884a", "Very High": "#ef5768"}
DOMAIN_COLOR = {"clinical": "#6c9bfb", "lifestyle": "#4cd98f", "genetic": "#c98cf7"}

COHORT_EXPLAINER = {
    "lifestyle": (
        "**Lifestyle cohort** — sourced from a large general-population survey "
        "(~70,000 people). Captures everyday lifestyle/metabolic factors: age, "
        "gender, height/weight, blood pressure, cholesterol & glucose category, "
        "smoking, alcohol, physical activity. Good for modeling day-to-day "
        "lifestyle what-ifs (exercise, weight loss, quitting smoking)."
    ),
    "clinical": (
        "**Clinical cohort** — sourced from a smaller hospital/clinical dataset "
        "(~900 patients). Captures clinical exam/test findings: chest pain type, "
        "resting ECG, exercise-induced angina, ST slope, max heart rate, "
        "oldpeak. Good for modeling more clinically-detailed risk profiles."
    ),
}


def fmt_age(age) -> str:
    """Whole-number display for age, everywhere in the UI. The underlying
    value stays a float (some source rows have decimal ages, e.g.
    60.03835616) — only how it's SHOWN is rounded. Never round the value
    that gets passed back into scoring/simulation."""
    try:
        return str(int(round(float(age))))
    except (TypeError, ValueError):
        return str(age)


def risk_band_pill(band: str) -> str:
    color = RISK_BAND_COLOR.get(band, "#666")
    return f"<span class='risk-pill' style='background:{color}'>{band}</span>"


def domain_dot(domain: str) -> str:
    color = DOMAIN_COLOR.get(domain, "#888")
    return f"<span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:{color};margin-right:6px'></span>"


FRIENDLY_FEATURE_NAMES = {
    "age": "Age", "gender": "Gender", "bmi": "Body Mass Index (BMI)",
    "systolic_bp": "Systolic blood pressure", "diastolic_bp": "Diastolic blood pressure",
    "smoking": "Smoking", "alcohol": "Alcohol use", "physical_activity": "Physical activity",
    "cholesterol_level_1": "Normal cholesterol", "cholesterol_level_2": "Above-normal cholesterol",
    "cholesterol_level_3": "High cholesterol", "glucose_level_1": "Normal glucose",
    "glucose_level_2": "Above-normal glucose", "glucose_level_3": "High glucose",
    "sex": "Sex", "chest_pain_type": "Chest pain type", "resting_bp": "Resting blood pressure",
    "cholesterol": "Cholesterol (mg/dl)", "fasting_blood_sugar": "Fasting blood sugar > 120 mg/dl",
    "resting_ecg": "Resting ECG result", "max_heart_rate": "Maximum heart rate achieved",
    "exercise_angina": "Exercise-induced angina", "oldpeak": "ST depression (oldpeak)",
    "st_slope": "ST segment slope",
}


def friendly_feature_name(feat: str) -> str:
    return FRIENDLY_FEATURE_NAMES.get(feat, feat.replace("_", " ").capitalize())


def cohort_field_summary(patient: dict, cohort: str) -> dict:
    if cohort == "lifestyle":
        h = patient.get("height_cm")
        w = patient.get("weight_kg")
        bmi = round(w / ((h / 100) ** 2), 1) if h and w else None
        return {
            "Age": fmt_age(patient.get("age")),
            "Gender": "Male" if patient.get("gender") == "m" else "Female",
            "Height (cm)": h,
            "Weight (kg)": w,
            "BMI": bmi,
            "Systolic BP": patient.get("systolic_bp"),
            "Diastolic BP": patient.get("diastolic_bp"),
            "Cholesterol level (1-3)": patient.get("cholesterol_level"),
            "Glucose level (1-3)": patient.get("glucose_level"),
            "Smoking": "Yes" if patient.get("smoking") else "No",
            "Alcohol": "Yes" if patient.get("alcohol") else "No",
            "Physically active": "Yes" if patient.get("physical_activity") else "No",
        }
    else:
        return {
            "Age": fmt_age(patient.get("age")),
            "Sex": "Male" if patient.get("sex") == 1 else "Female",
            "Chest pain type": patient.get("chest_pain_type"),
            "Resting BP": patient.get("resting_bp"),
            "Cholesterol (mg/dl)": patient.get("cholesterol"),
            "Fasting blood sugar > 120": "Yes" if patient.get("fasting_blood_sugar") else "No",
            "Resting ECG": patient.get("resting_ecg"),
            "Max heart rate": patient.get("max_heart_rate"),
            "Exercise angina": "Yes" if patient.get("exercise_angina") else "No",
            "Oldpeak": patient.get("oldpeak"),
            "ST slope": patient.get("st_slope"),
        }
