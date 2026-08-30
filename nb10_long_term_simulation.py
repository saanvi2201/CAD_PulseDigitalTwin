"""
nb10_long_term_simulation.py — Long-Term (Chronic) Lifestyle Intervention Simulation

FRAMING (do not lose this when writing it up)
-----------------------------------------------------------------------------
This module is the deliberate counterpart to Pulse: Pulse (NB9b) simulates
ACUTE physiology — seconds-to-minutes of hemodynamic response to an action
like exercise, using differential equations on a fixed anatomical scaffold.
It cannot and does not model chronic structural/functional adaptation
(resting bradycardia, vascular remodeling, sustained BP reduction) because
those changes are a different baseline parameter state, not something Pulse's
solver converges to by running longer.

This module instead answers a different, complementary question: "if this
patient sustained a specific lifestyle change for N weeks/months/years, what
would their risk score look like?" It does this WITHOUT touching Pulse at
all. The mechanism is:

    1. Take a published, citable population-average effect size for an
       intervention (e.g., "aerobic exercise reduces resting SBP by X mmHg").
    2. Apply that delta directly to the patient's INPUT FEATURES (systolic_bp,
       weight_kg, smoking flag, etc.) — the same features NB9a's ML models
       were trained on.
    3. Re-run the existing, already-validated score_lifestyle()/score_clinical()
       functions from nb9a_patient_scoring.py on the modified feature set.

Every number this module produces is one of exactly two things, and the
output always tells you which:
    (a) a DIRECT literature coefficient (cited, with URL, below), or
    (b) a CONSTRUCTED interpolation we built to connect two literature-cited
        endpoints (explicitly labeled "constructed" — not itself a published
        number, and weaker evidence than (a)).

Two panels, never conflated:
    Short-term (Pulse, NB9b)  -> "How this patient responds acutely, right now."
    Long-term (this module)   -> "Projected risk if this lifestyle change were
                                   sustained, based on published effect sizes."

WHAT THIS MODULE DELIBERATELY DOES NOT DO
-----------------------------------------------------------------------------
  - Does NOT shift cholesterol_level / glucose_level (the lifestyle cohort's
    CATEGORICAL 1/2/3 fields). There is no citable, defensible formula for
    "how many mmol/L of dietary change moves a patient from category 2 to
    category 1" without fabricating a threshold model. Left untouched.
  - Does NOT touch max_heart_rate, oldpeak, st_slope, or exercise_angina in
    the clinical cohort. These are stress-test-derived fields; a lifestyle
    projection has no literature-grounded way to predict them, and they are
    exactly what the SHORT-term (Pulse / real stress test) panel is for.
  - Does NOT apply a quantitative alcohol-reduction formula. Although R6
    reports blood-pressure effects by baseline drinks/day, this dataset stores
    alcohol use only as Yes/No. It cannot tell whether a person drank above
    the study threshold or by how much, so applying that dose-response would
    invent information that is not present in the patient's record.
  - Does NOT claim precision it doesn't have. The smoking-cessation TIME
    DECAY curve is explicitly a constructed linear interpolation between two
    qualitative literature findings, not a fitted/published coefficient. It
    is labeled as such everywhere it appears in the output.

=============================================================================
REFERENCES (verified via web search this session — check these yourself
before using the numbers in anything submitted for publication)
=============================================================================

[R1] Kelley GA, Kelley KS. "Aerobic Exercise and Resting Blood Pressure: A
     Meta-Analytic Review of Randomized, Controlled Trials." Preventive
     Cardiology. 2001;4(2):73-80.
     https://onlinelibrary.wiley.com/doi/10.1111/j.1520-037X.2001.00529.x
     47 RCTs, 2543 subjects. Exercise-minus-control changes:
       Hypertensive:  SBP -6 mmHg (95% CI -8 to -3), DBP -5 mmHg (CI -7 to -3)
       Normotensive:  SBP -2 mmHg (95% CI -3 to -1), DBP -1 mmHg (CI -2 to -1)
     CONFIDENCE: HIGH. Large, classic, widely-replicated meta-analysis; the
     hypertensive/normotensive split and rough magnitude is corroborated by
     Whelton et al. 2002 (Annals of Internal Medicine, pooled all-comers
     -3.84/-2.58 mmHg) and Cornelissen & Smart 2013 (hypertensive-only
     range 6.0-12.3 mmHg SBP), both found in the same search session.
     Trials pooled here ran roughly 8-52 weeks of program duration — treat
     this delta as "after a sustained moderate-intensity aerobic program of
     at least ~8-12 weeks," not an instantaneous effect.

[R2] Neter JE, Stam BE, Kok FJ, Grobbee DE, Geleijnse JM. "Influence of
     Weight Reduction on Blood Pressure: A Meta-Analysis of Randomized
     Controlled Trials." Hypertension. 2003;42(5):878-884.
     https://www.ahajournals.org/doi/10.1161/01.hyp.0000094221.86888.ae
     25 RCTs, 4874 subjects. Per kilogram of weight lost:
       SBP -1.05 mmHg (95% CI -1.43 to -0.66)
       DBP -0.92 mmHg (95% CI -1.28 to -0.55)
     CONFIDENCE: HIGH. Large, well-powered, dose-response (per-kg) design —
     this is the one intervention here that is inherently continuous/dosed
     rather than a single before/after snapshot, so it needs no time-course
     assumption at all: give it a kg figure, get a mmHg figure.

[R3] Critchley JA, Capewell S. "Smoking cessation for the secondary
     prevention of coronary heart disease." Cochrane Database Syst Rev.
     2004;(1):CD003041. PMID 14974003.
     https://pubmed.ncbi.nlm.nih.gov/14974003/
     20 cohort studies, patients with DIAGNOSED CHD, >=2 yr follow-up.
     Pooled RR for mortality in quitters vs continuing smokers: 0.64
     (95% CI 0.58-0.71), i.e. ~36% relative risk reduction. Also RR 0.68 for
     non-fatal MI.
     SCOPE LIMIT (important): this is a SECONDARY prevention estimate —
     patients who already have CHD. Applying its magnitude to a primary-
     prevention screening patient (no diagnosed CAD) is an extrapolation
     beyond the studied population. Flagged in the code output.

[R4] "Cardiovascular Effects of Smoking and Smoking Cessation: A 2024
     Update." PMC11843939.
     https://pmc.ncbi.nlm.nih.gov/articles/PMC11843939/
     Narrative synthesis of multiple cohorts: cardiovascular mortality risk
     declines progressively with sustained cessation and becomes comparable
     to never-smokers only after roughly 10-15 years of abstinence.
     Also: Duncan MS et al., JAMA 2019 (Framingham Heart Study) found CVD
     risk significantly lower within 5 years of cessation vs. continuing
     smokers among heavy smokers, but still elevated vs. never-smokers
     beyond 5 years.
     CONFIDENCE: qualitative pattern is well-supported (risk falls, falls
     faster early, takes a decade-plus to fully normalize) but there is no
     single agreed numeric decay curve across studies. See DECAY MODEL note
     below — the curve used here is CONSTRUCTED, not fitted to these papers.

[R5] (OPTIONAL, OFF BY DEFAULT, LOWER CONFIDENCE) "The effects of exercise
     on blood lipids and lipoproteins: a meta-analysis of studies." Med Sci
     Sports Exerc. 1983;15(5):393-402. PMID 6645868.
     https://pubmed.ncbi.nlm.nih.gov/6645868/
     Pooled: total cholesterol -10 mg/dL, LDL -5.1 mg/dL, HDL +1.2 mg/dL
     (NOT significant).
     CONFIDENCE: LOW/MODERATE — heterogeneous across the literature. A more
     recent meta-analysis restricted to adults 50+ (Kelley GA et al., PMC
     2447857) found smaller, though still significant, changes: TC -3.3
     mg/dL, LDL -3.9 mg/dL, HDL +2.5 mg/dL. Given this spread, this
     intervention effect is implemented but OFF by default and only affects
     the clinical cohort's continuous `cholesterol` field (the lifestyle
     cohort's cholesterol_level is categorical and is intentionally not
     touched — see module docstring above).

[R6] Roerecke M et al. "Effect of a reduction in alcohol consumption on blood
     pressure: a systematic review and meta-analysis." Lancet Public Health.
     2017;2(2):e108-e120. PMID 29253389.
     https://pubmed.ncbi.nlm.nih.gov/29253389/
     In people drinking >2 drinks/day, reducing intake was associated with
     lower BP; the largest reported effect was among people drinking >=6
     drinks/day who reduced intake by about 50% (SBP -5.50, DBP -3.97 mmHg).

ALCOHOL / PHYSICAL_ACTIVITY note: these are binary flags in the lifestyle
cohort's training data (alcohol, physical_activity). R6 is valid evidence
that alcohol reduction can lower BP in people drinking above 2 drinks/day,
but this app does not record drinks/day or the amount of reduction. Therefore
the simulator deliberately does not apply R6's numerical effect; it only
changes the binary alcohol input when the user selects stopping alcohol.
That is a model what-if, not an alcohol dose-response prediction.

DECAY MODEL — smoking cessation time course (CONSTRUCTED, read carefully)
-----------------------------------------------------------------------------
There is no single published formula giving "fraction of smoking-related
excess CAD risk removed at year t since quitting" for a general population.
What IS published (R3, R4) is a qualitative shape: benefit accrues starting
early, meaningfully within ~5 years, and risk approaches (but per Duncan et
al. does not fully equal) never-smoker risk only by roughly 10-15 years.

To turn that qualitative shape into a usable number, this module applies a
LINEAR interpolation from 0% recovered at t=0 to 100% recovered at t=15
years. This is our construction, calibrated only to match the "~15 years"
anchor point in R4 — it is explicitly NOT a fitted or published decay curve,
and a true clinical decay curve is very unlikely to be linear (early years
probably recover risk faster than late years, per the RR pattern in R3/R4).
Treat any single-year output of this curve as illustrative, not a number to
put in a table without this caveat attached. It is returned in every result
dict tagged "constructed_approximation": True so it can never be silently
mistaken for a cited coefficient downstream.

Edit log: 28/08/26 — initial version.
"""

import os
import sys
import copy
import json

# =============================================================================
# Import the already-verified NB9a scoring model (no changes made to it)
# =============================================================================

from nb9a_patient_scoring import PatientScoringModel


# =============================================================================
# CITATION REGISTRY — kept in code (not just docstring) so results can carry
# their own provenance. Do not edit numbers here without re-checking the URL.
# =============================================================================

REFERENCES = {
    "exercise_bp": {
        "citation": "Kelley GA, Kelley KS. Aerobic Exercise and Resting Blood "
                     "Pressure: A Meta-Analytic Review of Randomized, "
                     "Controlled Trials. Preventive Cardiology. 2001;4(2):73-80.",
        "url": "https://onlinelibrary.wiley.com/doi/10.1111/j.1520-037X.2001.00529.x",
        "confidence": "high",
    },
    "weight_loss_bp": {
        "citation": "Neter JE, Stam BE, Kok FJ, Grobbee DE, Geleijnse JM. "
                     "Influence of Weight Reduction on Blood Pressure: A "
                     "Meta-Analysis of Randomized Controlled Trials. "
                     "Hypertension. 2003;42(5):878-884.",
        "url": "https://www.ahajournals.org/doi/10.1161/01.hyp.0000094221.86888.ae",
        "confidence": "high",
    },
    "smoking_cessation_rr": {
        "citation": "Critchley JA, Capewell S. Smoking cessation for the "
                     "secondary prevention of coronary heart disease. "
                     "Cochrane Database Syst Rev. 2004;(1):CD003041. "
                     "PMID 14974003.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/14974003/",
        "confidence": "supporting context only; not consumed by a formula; secondary-prevention population",
    },
    "smoking_cessation_timecourse": {
        "citation": "Cardiovascular Effects of Smoking and Smoking Cessation: "
                     "A 2024 Update. PMC11843939. (10-15 year normalization "
                     "finding; also cites Duncan MS et al., JAMA 2019, "
                     "Framingham Heart Study, for the 5-year partial-benefit "
                     "finding.)",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11843939/",
        "confidence": "qualitative pattern only — see DECAY MODEL note in module docstring",
    },
    "exercise_lipids_optional": {
        "citation": "The effects of exercise on blood lipids and lipoproteins: "
                     "a meta-analysis of studies. Med Sci Sports Exerc. "
                     "1983;15(5):393-402. PMID 6645868.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/6645868/",
        "confidence": "low/moderate — heterogeneous across literature, see docstring",
    },
    "alcohol_reduction_bp_context": {
        "citation": "Roerecke M et al. Effect of a reduction in alcohol consumption on blood pressure: "
                     "a systematic review and meta-analysis. Lancet Public Health. 2017;2(2):e108-e120. "
                     "PMID 29253389.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/29253389/",
        "confidence": "high for the studied dose groups; not applied because this app lacks drinks/day data",
    },
}


# =============================================================================
# Intervention effect functions — each one returns (delta, provenance_dict)
# =============================================================================

def exercise_bp_delta(baseline_sbp: float, baseline_dbp: float) -> dict:
    """R1 (Kelley & Kelley 2001). Branches on whether the patient's baseline
    crosses the classic 140/90 hypertensive threshold used BY THAT PAPER
    (note: newer ACC/AHA 2017 guidelines use 130/80 — we use 140/90 here
    specifically because that's the threshold R1's own subgroup split used;
    mixing guideline vintages would misapply the cited number)."""
    is_hypertensive = (baseline_sbp >= 140) or (baseline_dbp >= 90)
    if is_hypertensive:
        d_sbp, d_dbp = -6.0, -5.0
    else:
        d_sbp, d_dbp = -2.0, -1.0
    return {
        "d_sbp": d_sbp,
        "d_dbp": d_dbp,
        "subgroup": "hypertensive (>=140/90)" if is_hypertensive else "normotensive",
        "reference": REFERENCES["exercise_bp"],
        "constructed_approximation": False,
        "assumed_duration": "sustained moderate-intensity aerobic program, ~8-12+ weeks",
    }


def weight_loss_bp_delta(kg_lost: float) -> dict:
    """R2 (Neter et al. 2003). Linear, dose-response — no time-course
    assumption needed, it's a direct per-kg coefficient."""
    if kg_lost < 0:
        raise ValueError("kg_lost must be >= 0 (this function models weight LOSS).")
    d_sbp = -1.05 * kg_lost
    d_dbp = -0.92 * kg_lost
    return {
        "d_sbp": d_sbp,
        "d_dbp": d_dbp,
        "kg_lost": kg_lost,
        "reference": REFERENCES["weight_loss_bp"],
        "constructed_approximation": False,
    }


def smoking_cessation_decay_fraction(years_since_quit: float) -> dict:
    """CONSTRUCTED linear interpolation, 0 at t=0 -> 1.0 at t=15 years.
    See module docstring 'DECAY MODEL' section — this is NOT a published
    coefficient, only the t=15 anchor is literature-grounded (R4)."""
    if years_since_quit < 0:
        raise ValueError("years_since_quit must be >= 0.")
    fraction = min(1.0, years_since_quit / 15.0)
    return {
        "fraction_of_benefit_realized": fraction,
        "years_since_quit": years_since_quit,
        "reference": REFERENCES["smoking_cessation_timecourse"],
        "constructed_approximation": True,
        "note": "Linear interpolation constructed by us to connect published "
                "qualitative findings (meaningful benefit within ~5y, near-full "
                "normalization by ~10-15y). Not itself a fitted/published curve.",
    }


def exercise_lipid_delta_clinical() -> dict:
    """R5 (OPTIONAL, off by default). Only applies to the clinical cohort's
    continuous `cholesterol` field (mg/dL)."""
    return {
        "d_total_cholesterol_mgdl": -10.0,
        "reference": REFERENCES["exercise_lipids_optional"],
        "constructed_approximation": False,
        "note": "Low/moderate confidence — see docstring. A newer 50+-adults "
                "meta-analysis found a smaller effect (-3.3 mg/dL). Treat this "
                "as an illustrative range, not a precise value.",
    }


# =============================================================================
# Bounds sanity-checks (mirrors the physiological bounds NB1/NB9a already
# enforce, so we fail loudly here with a clear message BEFORE handing an
# implausible row to build_lifestyle_features/build_clinical_features, which
# would otherwise raise a more generic error deeper in the stack)
# =============================================================================

_SBP_BOUNDS = (70, 250)
_DBP_BOUNDS = (40, 150)


def _clamp_check_bp(sbp, dbp, context: str):
    if not (_SBP_BOUNDS[0] <= sbp <= _SBP_BOUNDS[1]):
        raise ValueError(
            f"[{context}] Projected systolic_bp={sbp:.1f} falls outside the "
            f"physiologically plausible range {_SBP_BOUNDS} that the trained "
            f"models have support for. The intervention as specified is too "
            f"large / not realistic for this starting point."
        )
    if not (_DBP_BOUNDS[0] <= dbp <= _DBP_BOUNDS[1]):
        raise ValueError(
            f"[{context}] Projected diastolic_bp={dbp:.1f} falls outside the "
            f"physiologically plausible range {_DBP_BOUNDS}."
        )
    if dbp >= sbp:
        raise ValueError(
            f"[{context}] Projected diastolic_bp ({dbp:.1f}) >= systolic_bp "
            f"({sbp:.1f}) is physiologically impossible."
        )


# =============================================================================
# LongTermSimulator — orchestrates: apply interventions to a copy of the raw
# patient dict -> re-score with the existing NB9a model -> report before/after
# =============================================================================

class LongTermSimulator:
    def __init__(self, model: PatientScoringModel):
        self.model = model

    # -------------------------------------------------------------------
    # Lifestyle cohort
    # -------------------------------------------------------------------
    def simulate_lifestyle(self, raw_patient: dict, interventions: dict) -> dict:
        """
        raw_patient: dict matching build_lifestyle_features' expected raw
            input (age, gender, height_cm, weight_kg, systolic_bp/ap_hi,
            diastolic_bp/ap_lo, cholesterol_level, glucose_level, smoking,
            alcohol, physical_activity).
        interventions: dict, any subset of:
            {
              "exercise": True,
              "weight_loss_kg": 5.0,
              "smoking_cessation": {"quit": True, "years_since_quit": 5},
              "alcohol_cessation": True,
              "physical_activity": True,   # flip flag to 1 directly
            }
        """
        baseline_raw = dict(raw_patient)
        modified_raw = dict(raw_patient)
        applied = []

        # normalize field names the same way build_lifestyle_features does,
        # so we're editing the field that actually gets used
        if "ap_hi" in modified_raw and "systolic_bp" not in modified_raw:
            modified_raw["systolic_bp"] = modified_raw["ap_hi"]
        if "ap_lo" in modified_raw and "diastolic_bp" not in modified_raw:
            modified_raw["diastolic_bp"] = modified_raw["ap_lo"]

        cur_sbp = float(modified_raw["systolic_bp"])
        cur_dbp = float(modified_raw["diastolic_bp"])

        if interventions.get("exercise"):
            eff = exercise_bp_delta(cur_sbp, cur_dbp)
            cur_sbp += eff["d_sbp"]
            cur_dbp += eff["d_dbp"]
            applied.append({"intervention": "exercise", **eff})

        if interventions.get("weight_loss_kg"):
            kg = float(interventions["weight_loss_kg"])
            eff = weight_loss_bp_delta(kg)
            cur_sbp += eff["d_sbp"]
            cur_dbp += eff["d_dbp"]
            new_weight = float(modified_raw["weight_kg"]) - kg
            if new_weight <= 0:
                raise ValueError(
                    f"weight_loss_kg={kg} exceeds the patient's current "
                    f"weight_kg={modified_raw['weight_kg']}."
                )
            modified_raw["weight_kg"] = new_weight
            applied.append({"intervention": "weight_loss", **eff})

        _clamp_check_bp(cur_sbp, cur_dbp, context="lifestyle cohort, post-intervention")
        modified_raw["systolic_bp"] = cur_sbp
        modified_raw["diastolic_bp"] = cur_dbp
        modified_raw.pop("ap_hi", None)
        modified_raw.pop("ap_lo", None)

        smoking_decay_info = None
        if interventions.get("smoking_cessation", {}).get("quit"):
            years = interventions["smoking_cessation"].get("years_since_quit", 0)
            modified_raw["smoking"] = 0  # immediate flag flip (the model's learned effect)
            smoking_decay_info = smoking_cessation_decay_fraction(years)
            applied.append({
                "intervention": "smoking_cessation_flag",
                "note": "Binary smoking flag set to 0 — this is the model's "
                        "learned smoker-vs-nonsmoker differential, i.e. the "
                        "'fully realized' endpoint. See 'projected_risk_with_time_decay' "
                        "in the result for a time-adjusted estimate.",
                "constructed_approximation": False,
            })

        if interventions.get("alcohol_cessation"):
            modified_raw["alcohol"] = 0
            applied.append({
                "intervention": "alcohol_cessation_flag",
                "reference": REFERENCES["alcohol_reduction_bp_context"],
                "note": "Direct binary flag flip only. The alcohol study is not "
                        "numerically applied because the record has no drinks/day "
                        "or amount-reduced data. See ALCOHOL note in module docstring.",
                "constructed_approximation": False,
            })

        if interventions.get("physical_activity"):
            modified_raw["physical_activity"] = 1
            applied.append({
                "intervention": "physical_activity_flag",
                "note": "Direct binary flag flip (the trained feature itself).",
                "constructed_approximation": False,
            })

        baseline_result = self.model.score_lifestyle(baseline_raw)
        modified_result = self.model.score_lifestyle(modified_raw)

        result = {
            "cohort": "lifestyle",
            "baseline_raw": baseline_raw,
            "modified_raw": modified_raw,
            "applied_interventions": applied,
            "baseline_risk": baseline_result,
            "projected_risk_full_effect": modified_result,
            "delta_ml_risk": modified_result["ml_risk"] - baseline_result["ml_risk"],
            "modelling_assumptions": [
                "Effects from separately studied interventions are added together. "
                "Their combined effect has not been directly validated for this individual and may be smaller.",
                "This is a model re-score after changing selected inputs, not a clinical forecast or treatment recommendation.",
            ],
        }

        if smoking_decay_info is not None:
            frac = smoking_decay_info["fraction_of_benefit_realized"]
            full_delta = modified_result["ml_risk"] - baseline_result["ml_risk"]
            time_adjusted_risk = baseline_result["ml_risk"] + frac * full_delta
            result["smoking_time_decay"] = smoking_decay_info
            result["projected_risk_with_time_decay"] = {
                "ml_risk": time_adjusted_risk,
                "risk_band": self.model.__class__ and _band_lookup(time_adjusted_risk),
                "note": "Interpolated between baseline_risk and "
                        "projected_risk_full_effect using the CONSTRUCTED decay "
                        "fraction above. Not a direct model output.",
            }

        return result

    # -------------------------------------------------------------------
    # Clinical cohort
    # -------------------------------------------------------------------
    def simulate_clinical(self, raw_patient: dict, interventions: dict,
                           apply_optional_lipid_effect: bool = False) -> dict:
        """
        raw_patient: dict matching build_clinical_features' expected raw
            input (age, sex, chest_pain_type, resting_bp, cholesterol,
            fasting_blood_sugar, resting_ecg, max_heart_rate, exercise_angina,
            oldpeak, st_slope).
        interventions: dict, any subset of:
            {
              "exercise": True,             # affects resting_bp only
              "weight_loss_kg": 5.0,         # affects resting_bp only (no
                                              #   weight field exists in the
                                              #   clinical model's inputs)
              "smoking_cessation": {"quit": True, "years_since_quit": 5},
                                              # NOTE: clinical cohort has no
                                              #   smoking field in this schema
                                              #   — see note below.
            }
        apply_optional_lipid_effect: if True, applies R5 to `cholesterol`.
            OFF by default — see REFERENCES['exercise_lipids_optional'].
        """
        baseline_raw = dict(raw_patient)
        modified_raw = dict(raw_patient)
        applied = []

        cur_sbp = float(modified_raw["resting_bp"])
        # clinical schema (per nb9a build_clinical_features) carries only one
        # resting_bp value (systolic). There's no diastolic field to adjust
        # here, so only the SBP half of R1/R2 is applied to this cohort.

        if interventions.get("exercise"):
            eff = exercise_bp_delta(cur_sbp, baseline_dbp=80)  # dbp unknown in
            # this schema; 80 used only to decide the hypertensive/normotensive
            # branch (a reasonable population-typical dbp), NOT stored anywhere.
            cur_sbp += eff["d_sbp"]
            applied.append({"intervention": "exercise", **eff,
                             "note": "Clinical schema has no diastolic_bp field; "
                                     "only the SBP delta is applied. Subgroup "
                                     "branch used an assumed typical DBP=80 "
                                     "purely to pick hypertensive vs normotensive."})

        if interventions.get("weight_loss_kg"):
            kg = float(interventions["weight_loss_kg"])
            eff = weight_loss_bp_delta(kg)
            cur_sbp += eff["d_sbp"]
            applied.append({"intervention": "weight_loss", **eff,
                             "note": "Clinical schema has no weight_kg field to "
                                     "update; only the resulting resting_bp "
                                     "delta is applied."})

        if not (_SBP_BOUNDS[0] <= cur_sbp <= _SBP_BOUNDS[1]):
            raise ValueError(
                f"Projected resting_bp={cur_sbp:.1f} falls outside the "
                f"physiologically plausible range {_SBP_BOUNDS}."
            )
        modified_raw["resting_bp"] = cur_sbp

        if interventions.get("smoking_cessation", {}).get("quit"):
            applied.append({
                "intervention": "smoking_cessation",
                "note": "NOT APPLIED — the clinical cohort's feature schema "
                        "(per build_clinical_features / NB2) does not include "
                        "a smoking field, so there is no input to modify here. "
                        "Use the lifestyle cohort for a smoking-cessation "
                        "projection.",
                "skipped": True,
            })

        if apply_optional_lipid_effect:
            eff = exercise_lipid_delta_clinical()
            modified_raw["cholesterol"] = max(
                100.0, float(modified_raw["cholesterol"]) + eff["d_total_cholesterol_mgdl"]
            )
            applied.append({"intervention": "exercise_lipid_effect_optional", **eff})

        baseline_result = self.model.score_clinical(baseline_raw)
        modified_result = self.model.score_clinical(modified_raw)

        return {
            "cohort": "clinical",
            "baseline_raw": baseline_raw,
            "modified_raw": modified_raw,
            "applied_interventions": applied,
            "baseline_risk": baseline_result,
            "projected_risk_full_effect": modified_result,
            "delta_ml_risk": modified_result["ml_risk"] - baseline_result["ml_risk"],
            "modelling_assumptions": [
                "Effects from separately studied interventions are added together. "
                "Their combined effect has not been directly validated for this individual and may be smaller.",
                "A DBP of 80 mmHg is used only to select the exercise-study subgroup because this cohort has no DBP field.",
                "This is a model re-score after changing selected inputs, not a clinical forecast or treatment recommendation.",
            ],
        }


def _band_lookup(p):
    from nb9a_patient_scoring import assign_band
    return assign_band(p)


# =============================================================================
# EXAMPLE / SMOKE TEST — mirrors nb9e's test patient so this is directly
# runnable against the same real model artifacts.
# =============================================================================

if __name__ == "__main__":
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

    MODEL_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Models")
    EXPLAINABILITY_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Explainability")
    GENETICS_DIR = os.path.join(PROJECT_ROOT, "Outputs", "Genetics")

    print("=" * 80)
    print("NB10 — LONG-TERM (LITERATURE-GROUNDED) INTERVENTION SIMULATION")
    print("=" * 80)

    model = PatientScoringModel(
        model_dir=MODEL_DIR,
        explainability_dir=EXPLAINABILITY_DIR,
        genetics_dir=GENETICS_DIR,
    )
    sim = LongTermSimulator(model)

    lifestyle_patient = {
        "age": 45,
        "gender": "m",
        "height_cm": 178,
        "weight_kg": 92,          # deliberately overweight for a visible demo
        "ap_hi": 148,             # deliberately hypertensive for a visible demo
        "ap_lo": 94,
        "cholesterol_level": 2,
        "glucose_level": 1,
        "smoking": 1,
        "alcohol": 0,
        "physical_activity": 0,
    }

    print("\n" + "-" * 80)
    print("LIFESTYLE COHORT — exercise + weight loss + smoking cessation")
    print("-" * 80)

    ls_result = sim.simulate_lifestyle(
        lifestyle_patient,
        interventions={
            "exercise": True,
            "weight_loss_kg": 6.0,
            "smoking_cessation": {"quit": True, "years_since_quit": 5},
            "physical_activity": True,
        },
    )
    print(json.dumps(ls_result, indent=2, default=str))

    clinical_patient = {
        "age": 52,
        "sex": 1,
        "chest_pain_type": 1,
        "resting_bp": 150,
        "cholesterol": 240,
        "fasting_blood_sugar": 0,
        "resting_ecg": 0,
        "max_heart_rate": 150,
        "exercise_angina": 0,
        "oldpeak": 0.0,
        "st_slope": 1,
    }

    print("\n" + "-" * 80)
    print("CLINICAL COHORT — exercise + weight loss (+ optional lipid effect)")
    print("-" * 80)

    cl_result = sim.simulate_clinical(
        clinical_patient,
        interventions={"exercise": True, "weight_loss_kg": 6.0},
        apply_optional_lipid_effect=True,
    )
    print(json.dumps(cl_result, indent=2, default=str))

    out_dir = os.path.join(PROJECT_ROOT, "validation")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "nb10_long_term_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"lifestyle": ls_result, "clinical": cl_result}, f, indent=2, default=str)

    print("\n" + "=" * 80)
    print("NB10 COMPLETE — saved to:", out_path)
    print("=" * 80)
