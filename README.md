# CAD Digital Twin / Pulse-BioGears

This repository is focused on the Pulse/BioGears physiology subsystem for a cardiovascular CAD digital-twin workflow.

## What the current Pulse work does
At a high level, the current workflow initializes the Pulse engine, loads a baseline patient template, requests physiology outputs, applies interventions such as exercise or cardiovascular modifications, advances time, and reads the resulting patient/physiology values.

## Canonical entry point
The main repository workflow is centered on:
- nb9b_pulse_bridge.py

This is the current bridge script intended to run the Pulse/BioGears simulation flow.

## Supporting files
The working Pulse flow is grounded in the following reference files:
- HowTo_EngineUse.py
- HowTo_Exercise.py
- HowTo_CardiovascularModification.py
- Soldier.json

These files define the confirmed engine setup, patient configuration, exercise action, and cardiovascular modification patterns used by the current bridge.

## Diagnostic vs normal flow
- nb9_diag.py is a diagnostic/debugging script used to isolate issues in the Pulse initialization/stabilization path.
- It is not the normal entry point for the repository workflow.

## Older duplicate version
- nb9b_pulse_bridge_2.py is an older or duplicate local version and is not part of the canonical repository workflow.

## External dependency
The Pulse/BioGears installation itself is an external dependency and is not included in this repository.

The current bridge script contains machine-specific Pulse installation paths that may need to be updated on another developer's machine before it runs successfully.

## Repository hygiene
Large datasets, generated outputs, local test results, and the local Python virtual environment are intentionally excluded from GitHub.

This repository is intended to let another team member pick up and continue the Pulse/BioGears work with the current bridge and reference materials.

## Current status
This repository is currently set up as a collaboration starting point for continuing the Pulse/BioGears workflow, with the canonical bridge in nb9b_pulse_bridge.py and supporting reference files in the project root.
