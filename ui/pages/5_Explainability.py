import streamlit as st
import pandas as pd
import altair as alt

from ui_helpers import (
    setup_page, hero, require_patient_selected, get_model, risk_band_pill, domain_dot,
    friendly_feature_name, DOMAIN_COLOR,
)

setup_page("Explainability", "🔬")
hero(
    "🔬", "Why This Risk Number?",
    "A breakdown of which factors are driving this patient's estimated risk — first in plain "
    "language, then in as much technical detail as you want.",
)

patient, cohort, source, label = require_patient_selected()
st.markdown(f"Patient: **{label}** &nbsp;·&nbsp; *{cohort} cohort*")

model = get_model()
scoring_input = {k: v for k, v in patient.items() if k != "_provenance"}
with st.spinner("Computing explanation…"):
    result = model.score_lifestyle(scoring_input) if cohort == "lifestyle" else model.score_clinical(scoring_input)

st.markdown(
    f"<div class='cad-card' style='text-align:center'>"
    f"<div style='font-size:1.8rem;font-weight:800'>{result['ml_risk']:.1%}</div>"
    f"<div style='color:#9498b8;margin-bottom:8px'>Current estimated risk</div>"
    f"{risk_band_pill(result['risk_band'])}</div>",
    unsafe_allow_html=True,
)

domain_pct = result["domain_attribution"]
top_features = result.get("top_features", [])


# =============================================================================
# GROUP ONE-HOT CATEGORICAL FEATURES FOR DISPLAY (unchanged logic, only
# affects how SHAP features are shown, not the underlying calculation)
# =============================================================================
def prepare_display_features(top_features):
    grouped = []
    categorical_groups = {"cholesterol_level_": "Cholesterol", "glucose_level_": "Glucose"}
    already_grouped = set()
    for feature in top_features:
        original_name = feature["feature"]
        if original_name in already_grouped:
            continue
        matched_group = next(((p, d) for p, d in categorical_groups.items() if original_name.startswith(p)), None)
        if matched_group is None:
            grouped.append({
                "feature": original_name, "display_name": friendly_feature_name(original_name),
                "shap_value": float(feature["shap_value"]),
                "direction": feature.get("direction", "increases" if feature["shap_value"] > 0 else "decreases"),
                "domain": feature["domain"],
            })
            continue
        prefix, display_name = matched_group
        related = [f for f in top_features if f["feature"].startswith(prefix)]
        combined_shap = sum(float(f["shap_value"]) for f in related)
        for f in related:
            already_grouped.add(f["feature"])
        direction = "increases" if combined_shap > 0 else ("decreases" if combined_shap < 0 else "has little effect on")
        grouped.append({"feature": prefix.rstrip("_"), "display_name": display_name, "shap_value": combined_shap,
                         "direction": direction, "domain": related[0]["domain"]})
    return grouped


display_features = prepare_display_features(top_features) if top_features else []


def feature_value_text(feature: dict) -> str:
    """Describe the recorded input in everyday language without implying causation."""
    feature_key = feature["feature"]
    value = patient.get(feature_key)
    if value is None and feature_key in {"cholesterol_level", "glucose_level"}:
        value = patient.get(feature_key)
    if value is None:
        return "This is based on the information recorded for this patient."
    if feature_key in {"smoking", "alcohol", "physical_activity"}:
        return f"Recorded here as: **{'Yes' if value else 'No'}**."
    return f"Recorded value: **{value}**."


def feature_explanation(feature: dict, contribution_pct: float) -> str:
    """Short, plain-language explanation of a model contribution."""
    if feature["shap_value"] > 0:
        direction = "pushed the model's estimate higher"
    elif feature["shap_value"] < 0:
        direction = "pushed the model's estimate lower"
    else:
        direction = "made almost no difference to the model's estimate"
    influence = "a relatively large" if contribution_pct >= 20 else "a smaller"
    return (
        f"For this patient, **{feature['display_name']}** {direction}. "
        f"It accounts for about **{contribution_pct:.1f}%** of the factors shown on this page, "
        f"which makes it {influence} influence on this model result. "
        f"{feature_value_text(feature)}"
        " This does not mean it caused an outcome or that changing it will change risk by the same amount."
    )


# =============================================================================
# PLAIN-LANGUAGE SUMMARY — written for a patient, not a data scientist.
# No "SHAP", no "attribution magnitude", no raw coefficients here — those
# live in the technical expander further down for anyone who wants them.
# =============================================================================
st.divider()
st.subheader("In plain terms")

if not display_features:
    st.info("Not enough detail is available to explain this patient's result.")
else:
    domain_df = pd.DataFrame({"Domain": list(domain_pct.keys()), "Contribution (%)": list(domain_pct.values())}) \
        .sort_values("Contribution (%)", ascending=False).reset_index(drop=True)
    top_domain = domain_df.iloc[0]["Domain"]
    top_domain_pct = domain_df.iloc[0]["Contribution (%)"]

    domain_plain = {
        "clinical": "clinical measurements (like blood pressure, cholesterol, and heart-test results)",
        "lifestyle": "everyday lifestyle factors (like smoking, activity, weight, and diet-related measurements)",
        "genetic": "genetic background",
    }

    domain_feats = sorted([f for f in display_features if f["domain"] == top_domain],
                          key=lambda f: abs(f["shap_value"]), reverse=True)
    increasing = [f for f in domain_feats if f["shap_value"] > 0]
    decreasing = [f for f in domain_feats if f["shap_value"] < 0]

    sentences = []
    sentences.append(
        f"For **{label}**, the model estimates a **{result['ml_risk']:.1%}** risk level. "
        "This is a model estimate based on the information available for this patient; it is not a diagnosis."
    )
    sentences.append(
        f"The largest share of the explanation comes from **{domain_plain.get(top_domain, top_domain)}** "
        f"(**{top_domain_pct:.0f}%** of the model's explained risk signal)."
    )

    if increasing:
        names = ", ".join(f"**{f['display_name']}**" for f in increasing[:2])
        sentences.append(f"The factors most associated with a higher estimate are {names}.")
    if decreasing:
        names = ", ".join(f"**{f['display_name']}**" for f in decreasing[:2])
        sentences.append(f"The factors most associated with a lower estimate are {names}.")

    if len(domain_df) > 1:
        second = domain_df.iloc[1]
        if second["Contribution (%)"] >= 15:
            sentences.append(
                f"**{domain_plain.get(second['Domain'], second['Domain']).capitalize()}** also plays a "
                f"meaningful role, at about **{second['Contribution (%)']:.0f}%**."
            )

    # Markdown must be rendered outside an HTML string; Streamlit does not
    # parse **bold** or *emphasis* inside the contents of an HTML div.
    with st.container(border=True):
        for sentence in sentences:
            st.markdown(sentence)

    if "genetic" in domain_pct:
        st.markdown(
            f"<div class='cad-card' style='background:#141726;font-size:0.92rem;color:#c7cbe0'>"
            f"🧬 The genetic portion of this score (about {domain_pct['genetic']:.0f}%) is <b>not</b> a "
            f"personal genetic test result for this patient. It's a small, fixed adjustment based on "
            f"general population genetic risk patterns for this ancestry group — the same adjustment "
            f"is applied to every patient, regardless of their individual genetics.</div>",
            unsafe_allow_html=True,
        )


# =============================================================================
# DOMAIN BREAKDOWN (chart)
# =============================================================================
st.divider()
st.subheader("Breakdown by domain")
domain_df = pd.DataFrame({"Domain": list(domain_pct.keys()), "Contribution (%)": list(domain_pct.values())}) \
    .sort_values("Contribution (%)", ascending=False)

chart_type = st.radio(
    "Chart type",
    ["Bar chart", "Pie chart"],
    horizontal=True,
    label_visibility="collapsed",
)

# Use the same colours in the chart and in the text legend.
domain_order = domain_df["Domain"].tolist()
domain_colors = [DOMAIN_COLOR.get(domain, "#888888") for domain in domain_order]

c1, c2 = st.columns([1, 1])
with c1:
    if chart_type == "Pie chart":
        chart = alt.Chart(domain_df).mark_arc(innerRadius=55).encode(
            theta=alt.Theta("Contribution (%):Q", stack=True),
            color=alt.Color(
                "Domain:N",
                scale=alt.Scale(domain=domain_order, range=domain_colors),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Domain:N", title="Domain"),
                alt.Tooltip("Contribution (%):Q", title="Contribution", format=".1f"),
            ],
        ).properties(height=300)
    else:
        chart = alt.Chart(domain_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("Domain:N", sort=domain_order, title=None),
            y=alt.Y("Contribution (%):Q", title="Contribution (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color(
                "Domain:N",
                scale=alt.Scale(domain=domain_order, range=domain_colors),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Domain:N", title="Domain"),
                alt.Tooltip("Contribution (%):Q", title="Contribution", format=".1f"),
            ],
        ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)
    st.caption("Share of the patient's total explained risk signal coming from each domain.")
with c2:
    for _, row in domain_df.iterrows():
        st.markdown(f"{domain_dot(row['Domain'])}<b>{row['Domain'].capitalize()}</b> — {row['Contribution (%)']:.1f}%",
                    unsafe_allow_html=True)


# =============================================================================
# FEATURE-LEVEL DETAIL (technical) — kept as an expander/section for anyone
# who wants the underlying numbers, separated from the plain summary above.
# =============================================================================
st.divider()
st.subheader("How each recorded factor affected this result")
st.caption("🔺 made the model estimate higher · 🔻 made it lower. The number and percentage compare factors within this explanation; they are not changes in the patient's risk percentage.")

if not display_features:
    st.info("No feature-level detail is available for this patient.")
else:
    total_displayed_shap = sum(abs(float(f["shap_value"])) for f in display_features) or 1.0
    max_abs = max(abs(f["shap_value"]) for f in display_features) or 1.0
    domains_present = sorted(set(f["domain"] for f in display_features), key=lambda d: -domain_pct.get(d, 0))
    cols = st.columns(len(domains_present))

    for col, dom in zip(cols, domains_present):
        with col:
            st.markdown(f"{domain_dot(dom)}**{dom.capitalize()}**", unsafe_allow_html=True)
            feats_in_domain = sorted([f for f in display_features if f["domain"] == dom],
                                      key=lambda f: abs(f["shap_value"]), reverse=True)
            for f in feats_in_domain:
                val = f["shap_value"]
                arrow = "🔺" if val > 0 else ("🔻" if val < 0 else "•")
                bar_pct = min(abs(val) / max_abs * 100, 100)
                contribution_pct = abs(val) / total_displayed_shap * 100
                bar_color = "#ef5768" if val > 0 else "#2ecc8f"
                st.markdown(
                    f"<div class='feat-row'><span>{arrow} {f['display_name']}</span>"
                    f"<span style='font-weight:700;font-size:0.88rem'>{val:+.4f} "
                    f"<span style='color:#9498b8;font-weight:500'>({contribution_pct:.1f}%)</span></span></div>"
                    f"<div class='feat-bar-bg' style='margin-bottom:12px'>"
                    f"<div class='feat-bar-fill' style='width:{bar_pct:.0f}%;background:{bar_color}'></div></div>",
                    unsafe_allow_html=True,
                )
                with st.expander(f"What does {f['display_name']} mean here?"):
                    st.markdown(feature_explanation(f, contribution_pct))

if result.get("_unmatched_features"):
    st.warning(f"These features didn't match either domain map and were folded into 'clinical' by default: "
               f"{result['_unmatched_features']}. Check domain_maps.py if this is unintentional.")

with st.expander("Explainer method used"):
    st.write(result["_explainer_used"])
