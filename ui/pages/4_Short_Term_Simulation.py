import streamlit as st
import pandas as pd
from ui_helpers import setup_page, require_patient_selected, PULSE_BIN_PATH, PULSE_PY_PATH

setup_page("Short-Term Simulation", "🫁")
st.title("🫁 Short-Term Simulation (Pulse Physiology Engine)")
st.markdown(
    "<div class='cad-card'>This runs a real physiological simulation "
    "(Pulse/BioGears) of an acute exercise bout for THIS patient's demographics "
    "— heart rate, blood pressure, MAP, and cardiac output response. These are "
    "<b>simulated physiological outputs</b>, not clinical predictions, and are "
    "separate from the ML risk score.</div>",
    unsafe_allow_html=True,
)

patient, cohort, source, label = require_patient_selected()
st.markdown(f"Patient: **{label}** ({cohort} cohort)")

# Exercise simulation is only supported for patients whose resting blood
# pressure is at or below the configured safe threshold. Check this before
# creating/running the Pulse job so the engine is never started for an
# ineligible patient.
MAX_SHORT_TERM_SYSTOLIC_BP = 120
MAX_SHORT_TERM_DIASTOLIC_BP = 80


def _as_number(value):
    """Return a numeric value when possible; otherwise return None."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


systolic_bp = _as_number(patient.get("systolic_bp", patient.get("ap_hi")))
diastolic_bp = _as_number(patient.get("diastolic_bp", patient.get("ap_lo")))

eligibility_error = None
if systolic_bp is None or diastolic_bp is None:
    eligibility_error = (
        "Short-term simulation cannot be run because this patient does not have "
        "both systolic and diastolic blood-pressure values."
    )
elif systolic_bp > MAX_SHORT_TERM_SYSTOLIC_BP or diastolic_bp > MAX_SHORT_TERM_DIASTOLIC_BP:
    eligibility_error = (
        "Short-term simulation cannot be run for this patient: resting blood pressure "
        f"is {systolic_bp:g}/{diastolic_bp:g} mmHg. Exercise simulation is limited to "
        f"patients at or below {MAX_SHORT_TERM_SYSTOLIC_BP}/{MAX_SHORT_TERM_DIASTOLIC_BP} mmHg."
    )

if eligibility_error:
    st.error(f"🚫 {eligibility_error}")
else:
    st.success(
        f"✓ Patient is eligible for short-term simulation "
        f"({systolic_bp:g}/{diastolic_bp:g} mmHg)."
    )

st.divider()
st.subheader("Exercise parameters")
c1, c2 = st.columns(2)
with c1:
    intensity = st.slider("Exercise intensity (Pulse's 0.0–1.0 scale)", 0.0, 1.0, 0.0375, step=0.0125)
    st.caption("0.0 = no exertion, 1.0 = maximum effort. 0.0375 ≈ light activity, used in earlier test runs.")
with c2:
    duration_s = st.slider("Duration (seconds)", 30, 1800, 360, step=30)
    st.caption(f"= {duration_s // 60} min {duration_s % 60} sec of simulated time.")

run = st.button(
    "▶️ Run Pulse simulation",
    type="primary",
    disabled=eligibility_error is not None,
    help=eligibility_error,
)

if run:
    import sys
    if PULSE_BIN_PATH not in sys.path:
        sys.path.insert(0, PULSE_BIN_PATH)
    if PULSE_PY_PATH not in sys.path:
        sys.path.insert(0, PULSE_PY_PATH)

    scoring_input = {k: v for k, v in patient.items() if k != "_provenance"}

    # ---- Step-by-step status so the user never wonders "is this stuck?" ----
    # Pulse's own internal stages (build config, initialize/stabilize, apply
    # exercise, advance time) aren't individually reported back by
    # run_pulse_bridge() as separate callbacks, so we show the STAGES we
    # know are happening in order, and only mark each "done" once the
    # single blocking call actually returns.
    status = st.status("Starting Pulse simulation…", expanded=True)
    status.write("① Building patient configuration from selected patient's demographics…")
    status.write("② Initializing Pulse engine and stabilizing to this patient's baseline "
                  "(this is usually the slowest step — can take from several seconds up to "
                  "a minute or more)…")
    status.write(f"③ Applying exercise (intensity={intensity}) and advancing {duration_s}s of simulated time…")
    status.write("_(These steps run as one call into the engine — the log lines above show "
                  "what's happening inside it; this box will update once it returns.)_")

    try:
        from nb9b_pulse_bridge import run_pulse_bridge
        result = run_pulse_bridge(
            scoring_input,
            intervention={"type": "exercise", "intensity": intensity, "comment": "UI exercise test"},
            advance_seconds=duration_s,
        )
        status.update(label="✅ Pulse simulation complete", state="complete", expanded=False)
    except Exception as e:
        status.update(label="❌ Pulse simulation failed", state="error", expanded=True)
        st.error(
            f"Pulse simulation failed: {e}\n\n"
            "Common causes: wrong PULSE_BIN_PATH/PULSE_PY_PATH in ui_helpers.py, "
            "or initialize_engine() returning False — check the Pulse log for detail."
        )
        st.stop()

    st.divider()
    st.subheader("Result: before vs after")
    st.caption(
        "Each panel below is one physiological measurement, shown on its OWN scale "
        "(heart rate, blood pressure, and cardiac output use very different units — "
        "plotting them together on one chart made the comparison meaningless, so "
        "they're now separated)."
    )

    before, after = result["pulse_before"], result["pulse_after"]
    metrics = [
        ("Heart rate", "heart_rate_bpm", "bpm", "How fast the heart is beating."),
        ("Systolic BP", "systolic_bp_mmHg", "mmHg", "Pressure in arteries during a heartbeat."),
        ("Diastolic BP", "diastolic_bp_mmHg", "mmHg", "Pressure in arteries between heartbeats."),
        ("MAP", "map_mmHg", "mmHg", "Mean arterial pressure — average pressure over one cardiac cycle."),
        ("Cardiac output", "cardiac_output_L_per_min", "L/min", "Volume of blood the heart pumps per minute."),
    ]

    # ---- Individual before/after mini-charts, one metric per column, each
    # with its own axis, so units never get mixed. ----
    cols = st.columns(len(metrics))
    for col, (name, key, unit, explanation) in zip(cols, metrics):
        b, a = before[key], after[key]
        delta = a - b
        pct = (delta / b * 100) if b else 0
        with col:
            st.markdown(f"**{name}**")
            st.caption(explanation)
            mini_df = pd.DataFrame({"": [b, a]}, index=["Before", "After"])
            st.bar_chart(mini_df, height=180)
            delta_color = "#C62828" if delta > 0 else "#2E7D32"
            st.markdown(
                f"<div style='text-align:center'>"
                f"<span style='font-size:1.3rem;font-weight:700'>{a:.1f} {unit}</span><br>"
                f"<span style='color:{delta_color}'>{delta:+.1f} ({pct:+.1f}%)</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("Before / After comparison table")
    table_rows = []
    for name, key, unit, _ in metrics:
        b, a = before[key], after[key]
        delta = a - b
        pct = (delta / b * 100) if b else 0
        table_rows.append({
            "Measurement": f"{name} ({unit})",
            "Before": round(b, 1),
            "After": round(a, 1),
            "Change": f"{delta:+.1f}",
            "% Change": f"{pct:+.1f}%",
        })
    comparison_df = pd.DataFrame(table_rows).set_index("Measurement")
    st.dataframe(comparison_df, use_container_width=True)

    with st.expander("Full raw result"):
        st.json(result)
