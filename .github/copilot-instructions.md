# CAD Digital Twin / Pulse-BioGears project guidance

This repository is a cardiovascular CAD digital-twin project with a current focus on the Pulse/BioGears physiology subsystem. Keep changes tightly scoped to the active workflow and do not rewrite working simulation logic just to make it “cleaner.”

## Current Pulse workflow
The active Pulse/BioGears files are:
- HowTo_EngineUse.py
- HowTo_Exercise.py
- HowTo_CardiovascularModification.py
- nb9b_pulse_bridge.py
- nb9b_pulse_bridge_2.py
- nb9_diag.py
- Soldier.json

These files define the current workflow for initializing the Pulse engine, building a patient, requesting physiology data, applying exercise or cardiovascular modifications, and reading outputs.

## Experimental, legacy, or non-runtime files
Treat these as secondary or non-authoritative unless a task explicitly targets them:
- nb9a_patient_scoring.py: ML/risk-scoring path, not the direct Pulse runtime.
- Notebooks/old/: historical notebook revisions and duplicate experiments.
- Outputs/: generated artifacts, pickles, logs, plots, CSVs.
- test_results/: execution logs/results for debugging and validation.
- app.py: lightweight UI prototype; not part of core simulation workflow.
- Data/Raw and Data/Processed: datasets; not source code and may be large or restricted.

## How the Pulse workflow is executed
The Pulse engine is run through the established bridge pattern:
1. Add the local Pulse Python install to the Python path.
2. Load the patient template from Soldier.json.
3. Construct an SEPatientConfiguration / SEPatient and set required values.
4. Set the data root directory for Pulse data files.
5. Create SEDataRequestManager and requested physiology outputs.
6. Initialize the engine with initialize_engine(...).
7. Pull results via pull_data().
8. Apply actions such as SEExercise or SECardiovascularMechanicsModification.
9. Advance time and collect post-intervention values.

Do not invent a new execution pattern when the existing workflow already works. Trace the current implementation before changing behavior.

## Dependencies and constraints
Important dependencies include:
- Pulse/PyPulse engine modules (pulse.engine.PulseEngine, pulse.cdm.*)
- Python scientific stack: numpy, pandas, scikit-learn, scipy, matplotlib, shap, streamlit

Important constraints:
- Do not introduce hard-coded absolute Windows paths such as D:\pulse-engine\... or D:\CAD_DigitalTwin\...
- Do not rewrite working simulation logic unnecessarily; prefer minimal, necessary fixes.
- Before modifying code, trace the existing workflow and dependencies; identify the exact function, data flow, and API contract affected.
- Keep changes minimal and explain why each change is necessary.
- Never delete or overwrite data without explicit permission.
- Do not commit local virtual environments, generated outputs, logs, or large datasets unless the task specifically requires it.

## Data and output handling
Treat generated directories as runtime artifacts, not source code:
- Outputs/
- test_results/
- Data/Raw/
- Data/Processed/
- venv/

Large biomedical datasets and generated files should not be assumed safe to overwrite or delete. Preserve them unless the user explicitly requests cleanup or regeneration.

## Scope expectations for Copilot
- Prefer small, targeted edits.
- Explain the reason for each code change in terms of the existing Pulse workflow.
- If a fix depends on a local Pulse installation, use environment-based configuration rather than machine-specific paths.
- If a file is legacy/experimental, do not treat it as the authoritative implementation for the current Pulse subsystem.
- Preserve established working behavior and simulation semantics unless the task explicitly requires a change.
