import streamlit as st

from ui_helpers import setup_page, hero


setup_page("Project Overview", "ℹ️")
hero(
    "ℹ️",
    "About this CAD Digital Twin",
    "A transparent guide to what the app shows, how it works, and where its results should not be over-interpreted.",
)

st.subheader("What this project is trying to do")
st.markdown(
    """
    This project is an educational decision-support prototype for exploring coronary artery disease (CAD) risk information.
    It brings together patient data, trained machine-learning models, explainability, and carefully limited what-if scenarios.
    The goal is to help users understand how recorded factors are associated with the model's estimate — not to diagnose CAD or replace a clinician.
    """
)

st.subheader("How the app works")
st.markdown(
    """
    1. **Patient data** — The app uses either a predefined record or a manually entered record, from one of two cohorts with different available fields.
    2. **Risk estimate** — A trained machine-learning model produces an estimated CAD-risk score from that cohort's inputs.
    3. **Explainability** — The app shows which recorded inputs most influenced that model estimate for this patient. These are associations inside the model, not proof of cause and effect.
    4. **Long-term what-if simulation** — Selected lifestyle changes alter only the relevant model inputs, using published population-average evidence where available, and the model is scored again.
    5. **Short-term simulation** — The separate Pulse engine models an acute exercise response over minutes. It does not model long-term adaptation.
    """
)

st.subheader("Potential impact")
st.markdown(
    """
    The interface can make a complex risk model easier to inspect: users can see the difference between a current model estimate,
    the factors that influenced it, and a clearly labelled hypothetical scenario. It may support learning, discussion, and research
    prototyping around prevention. Any real clinical decision still needs appropriately validated tools, clinical judgement, and the patient's full history.
    """
)

st.subheader("Important limitations")
st.error("This app is not a diagnostic device, medical advice, or a treatment planner. Do not use it alone to make healthcare decisions.")

limitations = [
    ("Model estimates are not individual outcomes", "A percentage shown here is the output of a model trained on historical data. It is not a diagnosis, a guaranteed future outcome, or a personal probability with clinical calibration."),
    ("The data may not represent every person", "The underlying cohorts, feature definitions, and missing fields limit who the models can represent. Results may be less reliable for people unlike the training populations."),
    ("Explanations show association, not cause", "A factor can push this model's estimate up or down without causing CAD. The explanation is about the model's reasoning for this record."),
    ("Long-term scenarios combine population averages", "Exercise and weight-loss effects come from separate studies and are added together here. Their combined effect for one person may be smaller, different, or absent."),
    ("Smoking recovery is illustrative", "The time-adjusted smoking result uses a constructed 0–15 year interpolation informed by published timelines; it is not a validated patient-level recovery equation. The supporting Cochrane evidence is from people with established CHD, so extending it to screening patients is uncertain."),
    ("Alcohol intake is incomplete", "The lifestyle data record alcohol only as Yes/No, not drinks per day. Although research finds BP benefits from reducing heavier drinking, this app cannot safely apply that dose-response and only changes the binary model input."),
    ("Some inputs cannot be projected", "The app deliberately does not guess changes to categorical cholesterol/glucose fields or clinical stress-test features when there is no defensible formula to do so."),
    ("Clinical-cohort BP assumption", "That cohort has systolic resting BP but no diastolic BP. When exercise is selected, 80 mmHg is used only to choose the study subgroup; results near the study's 90 mmHg boundary are especially assumption-sensitive."),
    ("Short- and long-term views answer different questions", "Pulse models an acute physiological response, while the long-term page re-scores changed inputs. Neither view demonstrates that a change will happen for a particular person."),
]

for heading, text in limitations:
    with st.expander(heading):
        st.write(text)

st.subheader("Evidence used in the long-term page")
st.markdown(
    """
    The long-term simulation cites its evidence beside each intervention and stores the same references with the result.
    Its primary blood-pressure inputs are aerobic-exercise and weight-loss meta-analyses. The alcohol study is shown as context only,
    because the data lack the dose information needed to apply it. See the intervention details after running a scenario for the exact evidence and assumptions used.
    """
)
