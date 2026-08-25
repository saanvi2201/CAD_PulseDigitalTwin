import streamlit as st

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="CAD Digital Twin",
    page_icon="❤️",
    layout="wide"
)

# -----------------------------
# Title
# -----------------------------
st.title("❤️ CAD Digital Twin")
st.write("Version 0.1 - Basic Cardiovascular Digital Twin")

# -----------------------------
# Patient Inputs
# -----------------------------
st.header("Patient Information")

col1, col2 = st.columns(2)

with col1:

    age = st.slider(
        "Age",
        18,
        90,
        50
    )

    sex = st.selectbox(
        "Sex",
        ["Male", "Female"]
    )

    height = st.slider(
        "Height (cm)",
        140,
        210,
        170
    )

    weight = st.slider(
        "Weight (kg)",
        40,
        180,
        75
    )

with col2:

    sbp = st.slider(
        "Systolic Blood Pressure (mmHg)",
        80,
        220,
        120
    )

    dbp = st.slider(
        "Diastolic Blood Pressure (mmHg)",
        40,
        150,
        80
    )

    apob = st.slider(
        "ApoB (mg/dL)",
        40,
        200,
        90
    )

    hscrp = st.slider(
        "hs-CRP (mg/L)",
        0.0,
        10.0,
        1.0
    )

    prs = st.slider(
        "PRS Percentile",
        0,
        100,
        50
    )

# -----------------------------
# Simulation Button
# -----------------------------
if st.button("🚀 Simulate"):

    # -------------------------
    # Basic Calculations
    # -------------------------

    bmi = weight / ((height / 100) ** 2)

    map_value = dbp + (sbp - dbp) / 3

    heart_rate = 72

    if sbp > 140:
        heart_rate += 6

    if prs > 80:
        heart_rate += 4

    if apob > 120:
        heart_rate += 3

    cardiac_output = 5.2

    if bmi > 30:
        cardiac_output -= 0.4

    if apob > 120:
        cardiac_output -= 0.3

    # -------------------------
    # Simple CAD Risk Score
    # -------------------------

    risk = (
        prs * 0.4
        + (apob / 200) * 30
        + (hscrp / 10) * 20
        + (sbp / 220) * 10
    )

    risk = min(risk, 100)

    # -------------------------
    # Results
    # -------------------------

    st.header("Simulation Results")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "❤️ Heart Rate",
        f"{heart_rate:.0f} bpm"
    )

    c2.metric(
        "🩸 Mean Arterial Pressure",
        f"{map_value:.1f} mmHg"
    )

    c3.metric(
        "❤️ Cardiac Output",
        f"{cardiac_output:.2f} L/min"
    )

    c4.metric(
        "⚠️ CAD Risk",
        f"{risk:.1f}%"
    )

    # -------------------------
    # Interpretation
    # -------------------------

    st.subheader("Clinical Interpretation")

    if risk < 30:
        st.success("🟢 Low Cardiovascular Risk")

    elif risk < 60:
        st.warning("🟡 Moderate Cardiovascular Risk")

    else:
        st.error("🔴 High Cardiovascular Risk")

    # -------------------------
    # Patient Summary
    # -------------------------

    st.subheader("Patient Summary")

    st.write(f"**Age:** {age} years")
    st.write(f"**Sex:** {sex}")
    st.write(f"**BMI:** {bmi:.1f}")
    st.write(f"**Blood Pressure:** {sbp}/{dbp} mmHg")
    st.write(f"**ApoB:** {apob} mg/dL")
    st.write(f"**hs-CRP:** {hscrp:.1f} mg/L")
    st.write(f"**PRS Percentile:** {prs}")