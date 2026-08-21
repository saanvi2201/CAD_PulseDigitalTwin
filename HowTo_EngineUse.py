# Distributed under the Apache License, Version 2.0.
# See accompanying NOTICE file for details.

import sys
import logging
from enum import Enum
from pulse.cdm.engine import eSerializationFormat, SEDataRequestManager, SEDataRequest
from pulse.cdm.engine import IEventHandler, SEEventChange, ILoggerForward, eEvent

from pulse.cdm.patient import eSex, SEPatient, SEPatientConfiguration
from pulse.cdm.patient_actions import SEExercise
from pulse.engine.PulseEngine import PulseEngine, version, hash
from pulse.cdm.scalars import ElectricPotentialUnit, FrequencyUnit, LengthUnit, MassUnit, MassPerVolumeUnit, \
                              PressureUnit, TemperatureUnit, TimeUnit, VolumeUnit, VolumePerTimeUnit

from pulse.cdm.io.patient import serialize_patient_from_file
from pulse.cdm.io.environment import serialize_environmental_conditions_from_file

class eStartType(Enum):
    State = 0
    Stabilize_PatientFile = 1
    Stabilize_PatientObject = 2

class local_event_handler(IEventHandler):
    def handle_event(self, change: SEEventChange):
        # Listen for specific event states you are interested in
        if change.event == eEvent.StartOfInhale and change.active:
            print(change)

class local_log_fowrwad(ILoggerForward):
    def __init__(self):
        super().__init__()
        defaultLevel = logging.INFO
        self.logger = logging.getLogger()
        self.logger.setLevel(defaultLevel)
        formatStr = '%(asctime)s %(levelname)s %(message)s'
        formatter = logging.Formatter(formatStr)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def forward_debug(self, msg: str):
        self.logger.debug(msg)
        print(msg)
    def forward_info(self, msg: str):
        self.logger.info(msg)
        print(msg)
    def forward_warning(self, msg: str):
        self.logger.warning(msg)
        print(msg)
    def forward_error(self, msg: str):
        self.logger.error(msg)
        print(msg)
    def forward_fatal(self, msg: str):
        self.logger.fatal(msg)
        print(msg)

def HowTo_UseEngine():
    print("Using Pulse Version "+version()+"-"+hash())

    pulse = PulseEngine()

    # Let's print out events from the engine
    pulse.set_event_handler(local_event_handler())

    #  Logging manipulation:
    #  Passing the log_forward object to PulseEngine will allow you to control the logging of the engine.
    #  A pre-existing class has been used here,
    #  which forwards the logging to the Python console via the logging package.
    # This is the recommended approach to logging
    pulse.set_log_listener(local_log_fowrwad())

    # You can have pulse make a log file for you,
    # Pulse will only write a log if you pass a filename
    pulse.set_log_filename("./test_results/howto/HowTo_EngineUse.py.log")

    # You can also have Pulse write to the console (std::cout)
    # By default this is off
    pulse.log_to_console(True)

    # By default, NOTHING is written to file/log/pulled to python
    # You must explictly do one or more of the above to get log messages somewhere

    # Data Requests are used to get access to the hundreds of parameters available in Pulse
    # To learn more about Data Requests please look at the data request section here:
    # https://pulse.kitware.com/_scenario_file.html
    data_requests = [
        SEDataRequest.create_physiology_request("HeartRate", unit=FrequencyUnit.Per_min),
        SEDataRequest.create_physiology_request("ArterialPressure",  unit=PressureUnit.mmHg),
        SEDataRequest.create_physiology_request("MeanArterialPressure",  unit=PressureUnit.mmHg),
        SEDataRequest.create_physiology_request("SystolicArterialPressure",  unit=PressureUnit.mmHg),
        SEDataRequest.create_physiology_request("DiastolicArterialPressure", unit=PressureUnit.mmHg),
        SEDataRequest.create_physiology_request("OxygenSaturation"),
        SEDataRequest.create_physiology_request("EndTidalCarbonDioxidePressure",  unit=PressureUnit.mmHg),
        SEDataRequest.create_physiology_request("RespirationRate",  unit=FrequencyUnit.Per_min),
        SEDataRequest.create_physiology_request("SkinTemperature",  unit=TemperatureUnit.C),
        SEDataRequest.create_physiology_request("CardiacOutput", unit=VolumePerTimeUnit.L_Per_min),
        SEDataRequest.create_physiology_request("BloodVolume",  unit=VolumeUnit.mL),
        SEDataRequest.create_gas_compartment_request("LeftLungPulmonary", "Volume",  unit=VolumeUnit.mL),
        SEDataRequest.create_gas_compartment_request("RightLungPulmonary", "Volume",  unit=VolumeUnit.L), # Unit difference is OK!
        SEDataRequest.create_gas_compartment_substance_request("Carina", "CarbonDioxide", "PartialPressure",  unit=PressureUnit.mmHg),
        SEDataRequest.create_liquid_compartment_request("Aorta", "Pressure",  unit=PressureUnit.mmHg),
        SEDataRequest.create_liquid_compartment_substance_request("Aorta", "Oxygen", "PartialPressure",  unit=PressureUnit.mmHg),
        SEDataRequest.create_ecg_request("Lead3ElectricPotential",  unit=ElectricPotentialUnit.mV),
        SEDataRequest.create_substance_request("Oxygen", "AlveolarTransfer", VolumePerTimeUnit.mL_Per_s),
        SEDataRequest.create_substance_request("CarbonDioxide", "AlveolarTransfer", VolumePerTimeUnit.mL_Per_s),
    ]
    data_req_mgr = SEDataRequestManager(data_requests)
    # NOTE: If No data requests are being provided, Pulse will return the default vitals data
    # In addition to getting this data back via this API
    # You can have Pulse write the data you have requested to a CSV file
    data_req_mgr.set_results_filename("./test_results/howto/HowTo_EngineUse.py.csv")

    # There are several ways to initialize an engine to a patient
    start_type = eStartType.State
    if start_type is eStartType.State: # The engine is ready instantaneously
        if not pulse.serialize_from_file("./states/StandardMale@0s.json", data_req_mgr):
            print("Unable to load initial state file")
            return
        # Stabilization will require the engine to run for several minutes
        # to get to a homeostatic state based on your patients properties
    elif start_type is eStartType.Stabilize_PatientFile or \
         start_type is eStartType.Stabilize_PatientObject:
        pc = SEPatientConfiguration()
        # Add a patient definition to our patient configuration
        if start_type is eStartType.Stabilize_PatientFile:
            # We can point to a patient file on disk
            pc.set_patient_file("./patients/Soldier.json")
        elif start_type is eStartType.Stabilize_PatientObject:
            # We can create our own patient
            p = pc.get_patient()
            # You only need to set sex and all other properties will be computed
            # per https://pulse.kitware.com/_patient_methodology.html
            # Let's  load up a file from disk (You don't have to start with a file)
            serialize_patient_from_file("./patients/Soldier.json", p)
            # Now let's modify a few properties
            p.set_name("Wenye")
            p.get_age().set_value(22,TimeUnit.yr)
            p.get_height().set_value(72, LengthUnit.inch)
            p.get_weight().set_value(180, MassUnit.lb)
            p.get_heart_rate_baseline().set_value(72, FrequencyUnit.Per_min)
            p.get_systolic_arterial_pressure_baseline().set_value(117, PressureUnit.mmHg)
            p.get_diastolic_arterial_pressure_baseline().set_value(72, PressureUnit.mmHg)
            p.get_respiration_rate_baseline().set_value(12, FrequencyUnit.Per_min)
        # Let's add a condition to our stabilization
        # This is optional, you do not need any conditions
        # But if you do, you can add as many as you want like this
        env = pc.get_conditions().get_initial_environmental_conditions()
        # Let's  load up a file from disk (You don't have to start with a file)
        serialize_environmental_conditions_from_file("./environments/ExerciseEnvironment.json",
                                                        env.get_environmental_conditions())
        # Now let's modify a few properties
        env.get_environmental_conditions().get_air_density().set_value(1.225, MassPerVolumeUnit.kg_Per_m3)
        env.get_environmental_conditions().get_ambient_temperature().set_value(33, TemperatureUnit.C)
        env.get_environmental_conditions().get_respiration_ambient_temperature().set_value(33, TemperatureUnit.C)

        # By default, pulse will look for data files in the working directory of your program "./"
        # You can change that in your patient configuration
        pc.set_data_root_dir("./")

        # Initialize the engine with our configuration
        # Optionally you can provide a data_dir root where Pulse will look for required data files
        if not pulse.initialize_engine(pc, data_req_mgr):
            print("Unable to load stabilize engine")
            return

    # You can get the initial patient at any time
    # But it will not change, so once is good
    # All values will be set to what the engine stabilized to
    initialPatient = SEPatient();
    pulse.get_initial_patient(initialPatient);
    print("Sex: " + str(initialPatient.get_sex()));
    print("Age: " + str(initialPatient.get_age()));
    print("Height: " + str(initialPatient.get_height()));
    print("Weight: " + str(initialPatient.get_weight()));

    # Get some data from the engine
    # The results array contains a value for each of the data requests made above
    # The order of the array is in the same order as the data requests array is
    # NOTE that the results array also contains the simulation time at results[0]
    # So the length is Number of Data Requests + 1
    # Think of this array as starting at index 1, and in the same order as above
    results = pulse.pull_data()
    data_req_mgr.to_console(results)

    # Perform an action
    exercise = SEExercise()
    exercise.set_comment("Start some star jumps")
    exercise.get_intensity().set_value(0.06)
    pulse.process_action(exercise)

    # Advance some time and print out the vitals
    pulse.advance_time_s(30)
    results = pulse.pull_data()
    data_req_mgr.to_console(results)
    # Perform an action

    # Let's see what events are active
    # This is on demand
    # If you want a callback to notify you when an event becomes active
    # Then create an event handler
    active_events = pulse.pull_active_events()
    # This is a map of event to duration (in seconds)
    for event, duration_s in active_events.items():
        print(event + " has been active for " + str(duration_s) + "s")

    exercise.set_comment("Stop star jumps")
    exercise.get_intensity().set_value(0)
    pulse.process_action(exercise)
    # Advance some time and print out the vitals
    pulse.advance_time_s(45)
    results = pulse.pull_data()
    data_req_mgr.to_console(results)

    # When we are done with the engine,
    # we can clear the engine to release any files it's been writing to
    pulse.clear()

HowTo_UseEngine()

