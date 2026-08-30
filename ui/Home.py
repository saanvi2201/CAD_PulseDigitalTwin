import streamlit as st
from ui_helpers import setup_page, hero, get_selected_patient, cohort_field_summary, risk_band_pill, fmt_age

setup_page("Home", "🫀")
hero("🫀", "Coronary Artery Disease Digital Twin",
     "Genomically-informed CAD risk prediction and what-if simulation — walking through one patient at a time.")

steps = [
    ("🔎", "Select Patient", "Choose a patient from the predefined dataset, or enter one manually.", "pages/1_Select_Patient.py"),
    ("🗂️", "Patient Dashboard", "See their profile and current ML-estimated CAD risk, with a plain-language reason.", "pages/2_Patient_Dashboard.py"),
    ("📈", "Long-Term Simulation", "A what-if ML counterfactual — how would risk change with exercise, weight loss, quitting smoking, etc.", "pages/3_Long_Term_Simulation.py"),
    ("🫁", "Short-Term Simulation", "A real physiological simulation (Pulse engine) of an acute exercise bout: heart rate / BP / cardiac output response.", "pages/4_Short_Term_Simulation.py"),
    ("🔬", "Explainability", "Which specific factors — genetic, clinical, lifestyle — are driving this patient's risk, and by how much.", "pages/5_Explainability.py"),
    ("📊", "Summary", "Browse and click into every patient this system knows about, predefined or manually entered.", "pages/6_Summary.py"),
]

st.markdown(
    """
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #141726; border: 1px solid #262b45; border-radius: 16px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] .stButton button {
        width: 100%; background: transparent; border: 1px solid #262b45;
        border-radius: 10px; color: #dfe1f0; margin-top: 8px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] .stButton button:hover {
        background: #191d31; border-color: #6c7dfb; color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(3)
for i, (icon, name, desc, page_path) in enumerate(steps):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(
                f"<div style='padding:4px 6px'>"
                f"<div style='font-size:1.7rem'>{icon}</div>"
                f"<div style='font-weight:700;margin:6px 0 4px 0;font-size:1.05rem'>{i+1}. {name}</div>"
                f"<div style='color:#9498b8;font-size:0.9rem;min-height:70px;line-height:1.45'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button("Open →", key=f"home_card_{i}", use_container_width=True):
                st.switch_page(page_path)

st.divider()

patient, cohort, source, label = get_selected_patient()
if patient is None:
    st.markdown(
        "<div class='cad-card' style='text-align:center;padding:2rem'>"
        "<div style='font-size:1.8rem'>👋</div>"
        "<div style='font-weight:700;margin:6px 0'>No patient selected yet</div>"
        "<div style='color:#9498b8'>Start on <b>Select Patient</b> to begin.</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("🔎 Go to Select Patient", type="primary"):
        st.switch_page("pages/1_Select_Patient.py")
else:
    badge_color = "#3b6fd6" if source == "predefined" else "#2ea86f"
    badge_text = "Predefined Dataset" if source == "predefined" else "Manual Entry"
    st.markdown(
        f"<div class='cad-card'>"
        f"<div style='font-weight:700;font-size:1.1rem;margin-bottom:6px'>Currently selected: {label}</div>"
        f"<span class='source-badge' style='background:{badge_color}'>{badge_text}</span>"
        f"&nbsp;&nbsp;<span style='color:#9498b8'>{cohort} cohort</span></div>",
        unsafe_allow_html=True,
    )
    with st.expander("Quick profile view", expanded=True):
        st.table(cohort_field_summary(patient, cohort))
    c1, c2 = st.columns(2)
    if c1.button("🗂️ Go to Patient Dashboard", type="primary", use_container_width=True):
        st.switch_page("pages/2_Patient_Dashboard.py")
    if c2.button("🔎 Choose a different patient", use_container_width=True):
        st.switch_page("pages/1_Select_Patient.py")