import streamlit as st
import pandas as pd
from ui_helpers import setup_page, hero, require_patient_selected, get_simulator, risk_band_pill

setup_page("Long-Term Simulation", "📈")
hero(
    "📈", "Long-Term Simulation",
    "A what-if view: the model is scored again after selected inputs are changed, using published population-average evidence where available. "
    "It is not a personal clinical forecast or a simulation of the body changing day by day.",
)

st.warning(
    "**Read this before using a result:** This is an educational, model-based scenario — not medical advice. "
    "When more than one change is selected, separately studied average effects are added together, so the combined result may overstate a real individual's benefit. "
    "See **Project Overview** in the sidebar for all limitations."
)

patient, cohort, source, label = require_patient_selected()
st.markdown(f"Patient: **{label}** &nbsp;·&nbsp; *{cohort} cohort*")
st.divider()

st.subheader("Choose what this patient sustains long-term")

if cohort == "lifestyle":
    c1, c2 = st.columns(2)
    with c1:
        exercise = st.checkbox("🏃 **Start regular exercise**", help=(
            "Applies a published blood-pressure reduction for sustained aerobic exercise, "
            "AND updates the model's own 'physically active' input to reflect this change — "
            "both represent the same real-world behavior, just through two different effects "
            "the model can see."
        ))
        with st.expander("What exactly does this change?"):
            st.markdown(
                "This assumes the patient sustains regular aerobic exercise for weeks to months. "
                "The simulation lowers resting blood pressure and changes the model's "
                "**Physically active** input to Yes. It does not simulate one workout or "
                "guarantee an individual clinical outcome.\n\n"
                "**Evidence used:** Kelley & Kelley (2001), a meta-analysis of 47 randomized "
                "trials, reported lower resting blood pressure after aerobic exercise; the "
                "implemented effect is larger for participants with baseline BP at or above 140/90. "
                "[Read the study](https://onlinelibrary.wiley.com/doi/10.1111/j.1520-037X.2001.00529.x)."
            )
        weight_loss_kg = st.slider("⚖️ Weight loss (kg)", 0.0, 30.0, 0.0, step=0.5,
                                    help="Applies a published per-kg blood pressure reduction (Neter et al., 2003).")
        with st.expander("What exactly does weight loss change?"):
            st.markdown(
                "This reduces the patient's weight by the selected amount, recalculates BMI, and "
                "lowers systolic/diastolic blood pressure. The change is modelled as a sustained "
                "weight loss, not a short-term fluctuation.\n\n"
                "**Evidence used:** Neter et al. (2003), a meta-analysis of 25 randomized trials, "
                "estimated average BP reductions of about **1.05 mmHg systolic** and **0.92 mmHg "
                "diastolic per kg** lost. [Read the study](https://www.ahajournals.org/doi/10.1161/01.hyp.0000094221.86888.ae)."
            )
    with c2:
        quit_smoking = st.checkbox("🚭 Quit smoking", disabled=not patient.get("smoking"),
                                    help=None if patient.get("smoking") else "This patient isn't recorded as a smoker.")
        years_since_quit = st.slider("Years since quitting", 0, 20, 0) if quit_smoking else 0
        with st.expander("What exactly does quitting smoking change?"):
            st.markdown(
                "The model changes the patient's smoking input from Yes to No. The full-effect "
                "result shows the model's smoker-versus-non-smoker difference; the time-adjusted "
                "result applies an **illustrative, constructed** recovery curve based on years since quitting. "
                "It is not a patient-specific clinical prediction.\n\n"
                "**Evidence used:** smoking cessation is associated with lower cardiovascular risk, "
                "with benefit accumulating over time. The model uses a 0–15 year linear approximation "
                "because no single published patient-level recovery equation applies here. "
                "[Read the review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11843939/) and "
                "[the Cochrane review](https://pubmed.ncbi.nlm.nih.gov/14974003/)."
            )
        alcohol_cessation = st.checkbox("🍷 Stop alcohol", disabled=not patient.get("alcohol"),
                                         help=None if patient.get("alcohol") else "This patient isn't recorded as drinking alcohol.")
        with st.expander("What exactly does stopping alcohol change?"):
            st.markdown(
                "The model changes the dataset's alcohol-use input from Yes to No. Because this "
                "dataset records alcohol use only as a Yes/No field—not amount, frequency, or prior "
                "intake—the simulation does **not** invent a precise blood-pressure or risk reduction.\n\n"
                "**Evidence context:** reducing alcohol can lower blood pressure, especially for people "
                "who drink more heavily, but the effect depends on baseline intake. "
                "[Roerecke et al. (2017) systematic review and meta-analysis](https://pubmed.ncbi.nlm.nih.gov/29253389/)."
            )

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
        with st.expander("What exactly does regular exercise change?"):
            st.markdown(
                "This lowers the resting blood-pressure field used by the clinical model. The clinical "
                "dataset has no physical-activity field, so it does not change an activity status.\n\n"
                "**Evidence used:** sustained aerobic exercise reduced resting BP in a meta-analysis of "
                "randomized trials. [Kelley & Kelley (2001)](https://onlinelibrary.wiley.com/doi/10.1111/j.1520-037X.2001.00529.x)."
            )
        weight_loss_kg = st.slider("⚖️ Weight loss (kg)", 0.0, 30.0, 0.0, step=0.5)
        with st.expander("What exactly does weight loss change?"):
            st.markdown(
                "This applies a per-kilogram resting-BP reduction. The clinical dataset has no weight "
                "or BMI input, so the simulation does not alter those fields.\n\n"
                "**Evidence used:** Neter et al. (2003) estimated average reductions of about 1.05 mmHg "
                "systolic and 0.92 mmHg diastolic per kg lost. "
                "[Read the study](https://www.ahajournals.org/doi/10.1161/01.hyp.0000094221.86888.ae)."
            )
    with c2:
        apply_lipid = st.checkbox("🩸 Also apply exercise's effect on cholesterol",
                                   help="Optional, lower-confidence literature effect — off by default. See REFERENCES['exercise_lipids_optional'] in nb10.")
        with st.expander("What exactly does the optional cholesterol change?"):
            st.markdown(
                "When selected with regular exercise, this applies a small average reduction to the "
                "clinical cohort's cholesterol field. It is off by default because published results vary "
                "across studies and it should not be treated as a guaranteed individual effect.\n\n"
                "**Evidence used:** a meta-analysis found modest average lipid changes with exercise. "
                "[Read the study](https://pubmed.ncbi.nlm.nih.gov/6645868/)."
            )
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
    bar_col, line_col = st.columns(2)
    with bar_col:
        st.markdown("**Risk comparison**")
        st.bar_chart(chart_df, color="#6c9bfb")
    with line_col:
        st.markdown("**Risk projection**")
        st.line_chart(chart_df, color="#4cd98f")
    st.caption(
        "Compares estimated risk **before** any change (Baseline) against estimated risk **after** "
        "the changes you selected (Projected) — a shorter bar and a downward line mean lower estimated risk. "
        "The line connects the two scenario estimates; it is not a day-by-day clinical forecast."
    )

    if result.get("projected_risk_with_time_decay"):
        td = result["projected_risk_with_time_decay"]
        st.info(
            f"⏳ **Time-adjusted estimate**: some benefits (like quitting smoking) "
            f"don't fully materialize immediately. Accounting for how long it takes: "
            f"**{td['ml_risk']:.1%}** — {td['note']}"
        )

    with st.expander("Key assumptions and limitations for this result", expanded=True):
        for assumption in result.get("modelling_assumptions", []):
            st.markdown(f"- {assumption}")
        st.markdown(
            "- The displayed risk is a re-scored model output, not a diagnosis or a prediction that this patient will experience an outcome."
        )

    with st.expander("Applied intervention details"):
        st.json(result["applied_interventions"])
    with st.expander("Full raw result"):
        st.json(result)
