import streamlit as st
import pandas as pd
from ui_helpers import setup_page, hero, require_patient_selected, get_simulator, risk_band_pill

setup_page("Long-Term Simulation", "📈")
hero(
    "📈", "Long-Term Simulation",
    "This is an <b>ML counterfactual</b> — the trained model re-scored on modified feature values, "
    "using published effect sizes for each intervention. It is <b>not</b> a physiological simulation "
    "over time. For a real-time physiological response, use <b>Short-Term Simulation</b> instead.",
)

patient, cohort, source, label = require_patient_selected()
st.markdown(f"Patient: **{label}** &nbsp;·&nbsp; *{cohort} cohort*")
st.divider()

st.subheader("Choose what this patient sustains long-term")

if cohort == "lifestyle":
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='cad-card'>", unsafe_allow_html=True)
        exercise = st.checkbox("🏃 **Start regular exercise**", help=(
            "Applies a published blood-pressure reduction for sustained aerobic exercise, "
            "AND updates the model's own 'physically active' input to reflect this change — "
            "both represent the same real-world behavior, just through two different effects "
            "the model can see."
        ))
        with st.expander("What exactly does this change?"):
            st.caption(
                "• Lowers systolic/diastolic blood pressure using a published dose-response "
                "figure for sustained aerobic training (Kelley & Kelley, 2001).\n\n"
                "• Also sets this patient's 'physically active' status to Yes, since starting "
                "regular exercise is exactly what that model input measures."
            )
        weight_loss_kg = st.slider("⚖️ Weight loss (kg)", 0.0, 30.0, 0.0, step=0.5,
                                    help="Applies a published per-kg blood pressure reduction (Neter et al., 2003).")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='cad-card'>", unsafe_allow_html=True)
        quit_smoking = st.checkbox("🚭 Quit smoking", disabled=not patient.get("smoking"),
                                    help=None if patient.get("smoking") else "This patient isn't recorded as a smoker.")
        years_since_quit = st.slider("Years since quitting", 0, 20, 0) if quit_smoking else 0
        alcohol_cessation = st.checkbox("🍷 Stop alcohol", disabled=not patient.get("alcohol"),
                                         help=None if patient.get("alcohol") else "This patient isn't recorded as drinking alcohol.")
        st.markdown("</div>", unsafe_allow_html=True)

    interventions = {}
    if exercise:
        interventions["exercise"] = True
        interventions["physical_activity"] = True
    if weight_loss_kg > 0:
        interventions["weight_loss_kg"] = weight_loss_kg
    if quit_smoking:
        interventions["smoking_cessation"] = {"quit": True, "years_since_quit": years_since_quit}
    if alcohol_cessation:
        interventions["alcohol_cessation"] = True

else:
    st.markdown("<div class='cad-card'>", unsafe_allow_html=True)
    st.caption("Clinical cohort has a narrower feature set — only resting blood pressure can be modified here.")
    c1, c2 = st.columns(2)
    with c1:
        exercise = st.checkbox("🏃 Start regular exercise", help="Affects resting BP only — the clinical schema has no 'activity flag' or weight field.")
        weight_loss_kg = st.slider("⚖️ Weight loss (kg)", 0.0, 30.0, 0.0, step=0.5)
    with c2:
        apply_lipid = st.checkbox("🩸 Also apply exercise's effect on cholesterol",
                                   help="Optional, lower-confidence literature effect — off by default. See REFERENCES['exercise_lipids_optional'] in nb10.")
    st.markdown("</div>", unsafe_allow_html=True)
    interventions = {}
    if exercise:
        interventions["exercise"] = True
    if weight_loss_kg > 0:
        interventions["weight_loss_kg"] = weight_loss_kg

st.write("")
run = st.button("▶️ Run simulation", type="primary", disabled=(len(interventions) == 0), use_container_width=True)
if len(interventions) == 0:
    st.caption("Select at least one change above.")

if run:
    sim = get_simulator()
    with st.spinner("Running simulation…"):
        try:
            if cohort == "lifestyle":
                result = sim.simulate_lifestyle(patient, interventions=interventions)
            else:
                result = sim.simulate_clinical(patient, interventions=interventions, apply_optional_lipid_effect=apply_lipid)
        except Exception as e:
            st.error(f"Simulation failed: {e}")
            st.stop()

    st.divider()
    st.subheader("Result")

    baseline = result["baseline_risk"]
    projected = result["projected_risk_full_effect"]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"<div class='cad-stat'><div class='cad-stat-label'>Baseline risk</div>"
            f"<div class='cad-stat-num'>{baseline['ml_risk']:.1%}</div>"
            f"<div style='margin-top:8px'>{risk_band_pill(baseline['risk_band'])}</div></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"<div class='cad-stat'><div class='cad-stat-label'>Projected risk</div>"
            f"<div class='cad-stat-num'>{projected['ml_risk']:.1%}</div>"
            f"<div style='margin-top:8px'>{risk_band_pill(projected['risk_band'])}</div></div>",
            unsafe_allow_html=True,
        )
    with c3:
        delta_color = "#ef5768" if result["delta_ml_risk"] > 0 else "#2ecc8f"
        arrow = "↑ higher risk" if result["delta_ml_risk"] > 0 else "↓ lower risk"
        st.markdown(
            f"<div class='cad-stat'><div class='cad-stat-label'>Change</div>"
            f"<div class='cad-stat-num' style='color:{delta_color}'>{result['delta_ml_risk']:+.1%}</div>"
            f"<div style='color:#9498b8;font-size:0.85rem;margin-top:8px'>{arrow}</div></div>",
            unsafe_allow_html=True,
        )

    st.write("")
    chart_df = pd.DataFrame({"Scenario": ["Baseline", "Projected"], "Risk": [baseline["ml_risk"], projected["ml_risk"]]}).set_index("Scenario")
    st.bar_chart(chart_df)
    st.caption(
        "Compares estimated risk **before** any change (Baseline) against estimated risk **after** "
        "the changes you selected (Projected) — a shorter bar means lower estimated risk."
    )

    if result.get("projected_risk_with_time_decay"):
        td = result["projected_risk_with_time_decay"]
        st.info(
            f"⏳ **Time-adjusted estimate**: some benefits (like quitting smoking) "
            f"don't fully materialize immediately. Accounting for how long it takes: "
            f"**{td['ml_risk']:.1%}** — {td['note']}"
        )

    with st.expander("Applied intervention details"):
        st.json(result["applied_interventions"])
    with st.expander("Full raw result"):
        st.json(result)