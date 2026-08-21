# Distributed under the Apache License, Version 2.0.
# See accompanying NOTICE file for details.

from pulse.cdm.engine import eSerializationFormat
from pulse.cdm.patient_actions import SECardiovascularMechanicsModification
from pulse.engine.PulseEngine import PulseEngine

def HowTo_CardiovascularModification():
    pulse = PulseEngine()
    pulse.set_log_filename("./test_results/howto/HowTo_CardiovascularModification.py.log")
    pulse.log_to_console(True)

    # NOTE: No data requests are being provided, so Pulse will return the default vitals data
    if not pulse.serialize_from_file("./states/Soldier@0s.json", None):
        print("Unable to load initial state file")
        return

    # Get some data from the engine
    results = pulse.pull_data()
    pulse.print_results()

    # Advance some time and print out the vitals
    pulse.advance_time_s(30)
    results = pulse.pull_data()
    pulse.print_results()

    cvMod = SECardiovascularMechanicsModification()
    cvMod.get_modifiers().get_heart_rate_multiplier().set_value(1.05)

    # By default, the engine will run a stabilization stage to get to a new homeostatis based on the provided modifiers
    # You can listen to the Stabilization event to see when the stabilization stage ends (and starts)
    # If you are slowly modifying the system with your own logic, and don't want the stabilization stage to run
    # set the incremental flag to true, and the engine apply this action and not run a stabilization stage

    pulse.process_action(cvMod)

    # Advance some time and print out the vitals
    pulse.advance_time_s(30)
    results = pulse.pull_data()
    pulse.print_results()

HowTo_CardiovascularModification()

