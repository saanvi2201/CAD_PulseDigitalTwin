import streamlit as st
from ui_helpers import (
    setup_page, hero, require_patient_selected, cohort_field_summary, risk_band_pill,
    get_model, backend_available, friendly_feature_name,
)

setup_page("Patient Dashboard", "🗂️")

patient, cohort, source, label = require_patient_selected()

badge_color = "#3b6fd6" if source == "predefined" else "#2ea86f"
badge_text = "Predefined Dataset" if source == "predefined" else "Manual Entry"
hero(
    "🗂️", label,
    f"<span class='source-badge' style='background:{badge_color}'>{badge_text}</span>"
    f"&nbsp;&nbsp;<span style='color:#9498b8'>{cohort} cohort</span>",
)

left, right = st.columns([1, 1])

with left:
    st.subheader("Patient profile")
    st.markdown("<div class='cad-card'>", unsafe_allow_html=True)
    fields = cohort_field_summary(patient, cohort)   # already returns whole-number age
    st.table(fields)
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.subheader("Current model-estimated risk")

    ok, msg = backend_available()
    if not ok:
        st.error(msg)
    else:
        with st.spinner("Scoring patient…"):
            model = get_model()
            scoring_input = {k: v for k, v in patient.items() if k != "_provenance"}
            result = model.score_lifestyle(scoring_input) if cohort == "lifestyle" else model.score_clinical(scoring_input)

        st.markdown(
            f"<div class='cad-card' style='text-align:center'>"
            f"<div style='font-size:2.6rem;font-weight:800;font-family:Manrope,sans-serif'>{result['ml_risk']:.1%}</div>"
            f"<div style='color:#9498b8;margin-bottom:12px'>Calibrated CAD risk</div>"
            f"{risk_band_pill(result['risk_band'])}"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.caption(
            f"Base model probability: {result['p_base']:.1%}  ·  "
            f"PRS-integrated: {result['p_integrated']:.1%}  ·  "
            f"After calibration: {result['ml_risk']:.1%}"
        )

        domain_pct = result["domain_attribution"]
        top_domain = max(domain_pct, key=domain_pct.get)
        top_feats = result.get("top_features", [])
        top_feat_in_domain = next((f for f in top_feats if f["domain"] == top_domain), top_feats[0] if top_feats else None)

        st.markdown("#### Why this number?")
        why_text = (
            f"For **{label}**, the model estimates a **{result['ml_risk']:.1%}** CAD risk from the "
            "available profile. This is an estimate to support discussion and follow-up, not a diagnosis.\n\n"
            f"**{top_domain.capitalize()}** factors account for the largest share of the model's explanation "
            f"(**{domain_pct[top_domain]:.0f}%** of its attributed risk signal)."
        )
        if top_feat_in_domain:
            fname = friendly_feature_name(top_feat_in_domain["feature"])
            direction = top_feat_in_domain["direction"]
            why_text += (
                f" Within that group, **{fname}** has the strongest model contribution for this "
                f"patient and is associated with a model estimate that **{direction} risk**."
            )
        # Do not place Markdown inside an HTML card: Streamlit will then show
        # the literal ** markers instead of rendering emphasis.
        with st.container(border=True):
            st.markdown(why_text)
            st.caption(
                "These percentages describe the model's explanation, not the percentage of risk caused by a factor."
            )
        st.caption("See the **Explainability** page for the full feature-by-feature breakdown.")

        if result.get("_unmatched_features"):
            st.caption(f"⚠️ Unmatched SHAP features folded into 'clinical': {result['_unmatched_features']}")

st.divider()
c1, c2, c3 = st.columns(3)
if c1.button("📈 Long-Term Simulation", use_container_width=True):
    st.switch_page("pages/3_Long_Term_Simulation.py")
if c2.button("🫁 Short-Term Simulation", use_container_width=True):
    st.switch_page("pages/4_Short_Term_Simulation.py")
if c3.button("🔬 Full Explainability", use_container_width=True):
    st.switch_page("pages/5_Explainability.py")
