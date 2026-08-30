import streamlit as st
import pandas as pd
import random
from ui_helpers import (
    setup_page, hero, RAW_LIFESTYLE_CSV, RAW_CLINICAL_CSV, MANUAL_PATIENTS_CSV, get_model,
    go_browse_cohort,
)

setup_page("Summary", "📊")
hero("📊", "Patient Population", "An overview of every patient this system knows about — where they "
     "came from, and a quick look at how risk is distributed across a sample of them.")

c1, c2, c3 = st.columns(3)
try:
    n_lifestyle = len(pd.read_csv(RAW_LIFESTYLE_CSV))
except FileNotFoundError:
    n_lifestyle = 0
try:
    n_clinical = len(pd.read_csv(RAW_CLINICAL_CSV))
except FileNotFoundError:
    n_clinical = 0
try:
    n_manual = len(pd.read_csv(MANUAL_PATIENTS_CSV))
except FileNotFoundError:
    n_manual = 0

cards = [
    (c1, "Predefined — Lifestyle", n_lifestyle, "from Cardio_Data.csv", "lifestyle"),
    (c2, "Predefined — Clinical", n_clinical, "from df_clinical_test_raw.csv", "clinical"),
    (c3, "Manually entered", n_manual, "from Data/Manual/manual_patients.csv", None),
]

for col, title, val, sub, cohort_key in cards:
    with col:
        st.markdown(
            f"<div class='cad-stat'>"
            f"<div class='cad-stat-num'>{val:,}</div>"
            f"<div class='cad-stat-label'>{title}</div>"
            f"<div class='cad-stat-tag'>{sub}</div></div>",
            unsafe_allow_html=True,
        )
        if cohort_key:
            if st.button(
                f"Browse {cohort_key} patients →",
                key=f"browse_{cohort_key}",
                type="primary",
                use_container_width=True,
            ):
                go_browse_cohort(cohort_key)
        else:
            if st.button("Manage manual patients →", key="manage_manual", type="primary", use_container_width=True):
                st.switch_page("pages/7_Manual_Patients.py")

st.divider()
st.subheader("Risk overview for a sample of patients")
st.markdown(
    "<div class='cad-card'>"
    "Scoring a patient (including the explainability breakdown) takes real computation, so checking "
    "all 70,000+ patients at once isn't practical here. Instead, pick a cohort and a sample size below — "
    "this pulls that many patients at random and shows you the spread of risk across them. A bigger "
    "sample gives a more reliable picture, but takes longer to run."
    "</div>",
    unsafe_allow_html=True,
)

cohort_for_sample = st.radio(
    "Which cohort?", ["lifestyle", "clinical"], horizontal=True,
    format_func=lambda c: "🏃 Lifestyle" if c == "lifestyle" else "🏥 Clinical",
)
sample_n = st.slider("How many patients to check", 5, 200, 30, step=5)

if st.button("▶️ Calculate risk overview", type="primary"):
    from nb10b_patient_loader import load_real_lifestyle_patient, load_real_clinical_patient

    model = get_model()
    csv_path = RAW_LIFESTYLE_CSV if cohort_for_sample == "lifestyle" else RAW_CLINICAL_CSV
    try:
        n_rows = len(pd.read_csv(csv_path))
    except FileNotFoundError:
        st.error(f"Could not find {csv_path}")
        st.stop()

    sample_indices = random.sample(range(n_rows), min(sample_n, n_rows))
    bands, risks, errors = [], [], 0
    progress = st.progress(0.0, text="Checking patients…")
    for i, idx in enumerate(sample_indices):
        try:
            if cohort_for_sample == "lifestyle":
                p = load_real_lifestyle_patient(csv_path, idx)
                r = model.score_lifestyle({k: v for k, v in p.items() if k != "_provenance"})
            else:
                p = load_real_clinical_patient(csv_path, idx)
                r = model.score_clinical({k: v for k, v in p.items() if k != "_provenance"})
            bands.append(r["risk_band"])
            risks.append(r["ml_risk"])
        except Exception:
            errors += 1
        progress.progress((i + 1) / len(sample_indices), text=f"Checking patients… ({i+1}/{len(sample_indices)})")
    progress.empty()

    if errors:
        st.caption(f"{errors} patient(s) skipped due to data issues (e.g. missing values).")

    if risks:
        st.markdown(f"#### Out of {len(risks)} patients checked")
        band_counts = pd.Series(bands).value_counts().reindex(["Low", "Moderate", "High", "Very High"]).fillna(0)
        c1, c2 = st.columns(2)
        with c1:
            st.bar_chart(band_counts)
            st.caption("How many sampled patients fall into each risk category.")
        with c2:
            st.markdown(
                f"<div class='cad-stat'><div class='cad-stat-num'>{sum(risks)/len(risks):.1%}</div>"
                f"<div class='cad-stat-label'>Average estimated risk</div></div>",
                unsafe_allow_html=True,
            )
            st.table(band_counts.rename("Number of patients").astype(int))
    else:
        st.warning("No patients could be scored from this sample.")

st.divider()
st.subheader("Manually entered patients")
from nb10b_patient_loader import list_manual_patients
manual_df = list_manual_patients(csv_path=MANUAL_PATIENTS_CSV)
if manual_df.empty:
    st.info("None saved yet — add one from **Select Patient → Manually Entered Patient**.")
else:
    st.dataframe(manual_df, use_container_width=True)
    if st.button("🧾 Open Manual Patients", type="primary"):
        st.switch_page("pages/7_Manual_Patients.py")
