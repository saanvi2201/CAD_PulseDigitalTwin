"""Browse, inspect, load, and safely delete manually entered patients."""

import streamlit as st
import pandas as pd

from ui_helpers import (
    MANUAL_PATIENTS_CSV,
    cohort_field_summary,
    get_selected_patient,
    set_selected_patient,
    setup_page,
)
from nb10b_patient_loader import (
    list_manual_patients,
    load_manual_patient,
)


def delete_manual_patient_record(patient_id: str) -> None:
    """Delete one manual-record row without relying on a cached backend import."""
    records = pd.read_csv(MANUAL_PATIENTS_CSV)
    if patient_id not in set(records["patient_id"]):
        raise KeyError(f"Manual patient {patient_id!r} was not found.")
    records.loc[records["patient_id"] != patient_id].to_csv(MANUAL_PATIENTS_CSV, index=False)


setup_page("Manual Patients", "🧾")
st.title("🧾 Manual Patients")
st.markdown(
    "<div class='cad-card'>Review patients entered in this app. Manual patients are stored "
    "separately from the predefined datasets. Choose a patient to inspect their full profile, "
    "load them into the dashboard, or permanently delete that manual record.</div>",
    unsafe_allow_html=True,
)

listing = list_manual_patients(csv_path=MANUAL_PATIENTS_CSV)
if listing.empty:
    st.info("No manually entered patients have been saved yet.")
    if st.button("➕ Enter a patient", type="primary"):
        st.switch_page("pages/1_Select_Patient.py")
    st.stop()

st.subheader("Saved manual patients")
st.dataframe(listing, use_container_width=True, hide_index=True)

patient_id = st.selectbox("Patient to inspect", listing["patient_id"].tolist())
record = listing.loc[listing["patient_id"] == patient_id].iloc[0]
patient = load_manual_patient(patient_id, csv_path=MANUAL_PATIENTS_CSV)
cohort = record["cohort"]

st.subheader(f"Details: {patient_id}")
left, right = st.columns([2, 1])
with left:
    st.table(cohort_field_summary(patient, cohort))
with right:
    st.markdown("**Record information**")
    st.write(f"Cohort: {cohort.capitalize()}")
    st.write(f"Saved: {record['timestamp_utc']}")
    st.write(f"Patient ID: `{patient_id}`")

with st.expander("Raw stored record"):
    st.json(patient)

c1, c2 = st.columns(2)
with c1:
    if st.button("🗂️ Load in Patient Dashboard", type="primary", use_container_width=True):
        set_selected_patient(
            patient,
            cohort=cohort,
            source="manual",
            label=f"Manual patient {patient_id}",
        )
        st.switch_page("pages/2_Patient_Dashboard.py")

with c2:
    confirm_delete = st.checkbox(
        f"I understand this permanently deletes {patient_id}",
        key=f"confirm_delete_{patient_id}",
    )
    if st.button("🗑️ Delete this manual patient", disabled=not confirm_delete, use_container_width=True):
        delete_manual_patient_record(patient_id)
        selected_patient, _, selected_source, selected_label = get_selected_patient()
        if selected_source == "manual" and selected_label == f"Manual patient {patient_id}":
            for key in ("selected_patient", "selected_cohort", "selected_source", "selected_label"):
                st.session_state.pop(key, None)
        st.success(f"Deleted manual patient {patient_id}.")
        st.rerun()
