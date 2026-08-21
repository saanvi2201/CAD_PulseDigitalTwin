# Distributed under the Apache License, Version 2.0.
# See accompanying NOTICE file for details.

from pulse.cdm.engine import eSerializationFormat
from pulse.cdm.patient_actions import SEExercise
from pulse.engine.PulseEngine import PulseEngine

def HowTo_Exercise():
    pulse = PulseEngine()
    pulse.set_log_filename("./test_results/howto/HowTo_Exercise.py.log")
    pulse.log_to_console(True)

    # NOTE: No data requests are being provided, so Pulse will return the default vitals data
    if not pulse.serialize_from_file("./states/Soldier@0s.json", None):
        print("Unable to load initial state file")
        return

    # Get default data at time 0s from the engine
    results = pulse.pull_data()
    pulse.print_results()

    # Perform an action
    exercise = SEExercise()
    exercise.set_comment("Start some star jumps")
    exercise.get_intensity().set_value(0.06)
    pulse.process_action(exercise)

    # Advance some time and print out the vitals
    pulse.advance_time_s(30)
    results = pulse.pull_data()
    pulse.print_results()

    # For this example, you will see an increase in heart rate

HowTo_Exercise()