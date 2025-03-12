#!/usr/bin/env python3
"""
Field Controller Module
=========================
This module defines the FieldController class, which manages a frequency sweep
for field measurements using a signal generator and field probe. The controller
performs a closed-loop adjustment of power to achieve a target field level,
handles missed frequencies, logs warnings, and emits signals to update the UI.

Dependencies:
    - PyQt5 for signals and QObject.
    - External modules: ETSLindgrenHI6006 (FieldProbe), AgilentN5181A (SignalGenerator),
    - Frequency and Time enums, and a PID controller.
"""

from PyQt5.QtCore import QObject, pyqtSignal
from FieldProbe import ETSLindgrenHI6006
from SignalGenerator import AgilentN5181A, Frequency, Time
from PID import PIDController as PID
from time import sleep
import math
import os
from datetime import datetime

class FieldController(QObject):
    """
    FieldController manages the frequency sweep process, adjusts power levels based on
    field measurements, logs warnings, and emits UI update signals.
    """
    
    # Signals for UI updates
    frequencyUpdated = pyqtSignal(float)
    powerUpdated = pyqtSignal(float)
    fieldUpdated = pyqtSignal(float, float, float, float)
    sweepCompleted = pyqtSignal(list)
    sweepStatus = pyqtSignal(float)
    highFieldDetected = pyqtSignal(str)
    powerLimitExceeded = pyqtSignal(str)
    missedFieldWarning = pyqtSignal(str)
    startDwell = pyqtSignal(int)
    
    def __init__(self, signal_generator: AgilentN5181A, field_probe: ETSLindgrenHI6006, pid_controller: PID | None):
        """
        Initialize the FieldController with the given signal generator, field probe, and PID controller.
        If no PID controller is provided, a default controller is created and the 'stepper' mode is used.

        Parameters:
            signal_generator (AgilentN5181A): The signal generator instance.
            field_probe (ETSLindgrenHI6006): The field probe instance.
            pid_controller (PID or None): Optional PID controller for closed-loop control.
        """
        super().__init__()
        self.signal_generator = signal_generator
        self.field_probe = field_probe
        self.use_stepper = False
        if pid_controller is None:
            self.pid_controller = PID(0.1, 0.01, 0.01)
            self.use_stepper = True
        else:
            self.pid_controller = pid_controller
            
        # Sweep control flags and parameters
        self.is_sweeping = False
        self.last_step = False
        self.high_field_detected = False
        self.sweeping_missed = False
        self.missed_frequencies = []
        
        # Field and power control parameters
        self.target_field = 1.0     # Target field level in V/m
        self.threshold = 1.5        # Threshold for field level
        self.base_power = -30       # Base power level in dBm
        self.current_power = -30    # Current power level in dBm
        self.start_freq = 1000.0    # Start frequency in MHz
        self.current_freq = 1000.0  # Current frequency in MHz
        self.stop_freq = 2000.0     # Stop frequency in MHz
        self.dwell_time_ms = 500    # Dwell time in milliseconds
        self.sweep_term = 0.01      # Sweep term for frequency steps
        
        # Initial field probe parameters
        self.current_field_level = 0.0
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        
        # Set up logging
        self.log_file_path = self.setup_logging_directory()
        
    def setup_logging_directory(self) -> str:
        """
        Create and return the logging directory path with a log file for current session.

        Returns:
            str: The full file path to the newly created log file.
        """
        documents_dir = os.path.expanduser("~/Documents")
        log_dir = os.path.join(documents_dir, "ImmuniSweepLogs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
        return log_file
    
    def log_warning(self, frequency: float, warning: str):
        """
        Log a warning message to the log file and record the missed frequency.

        Parameters:
            frequency (float): The frequency at which the warning occurred.
            warning (str): The warning message detailing the issue.
        """
        self.missed_frequencies.append(frequency)
        with open(self.log_file_path, "a") as log_file:
            log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - High Field Detected Warning: {warning}\n")
            
    def start_sweep(self):
        """
        Initiate the frequency sweep process. Resets sweep parameters, sets initial signal generator state,
        and begins stepping through the sweep.
        """
        self.is_sweeping = True
        self.last_step = False
        self.sweeping_missed = False
        self.missed_frequencies = []
        self.current_freq = self.start_freq
        
        # Initialize the signal generator to base power and enable RF output and modulation
        self.signal_generator.setPower(self.base_power)
        self.signal_generator.setRFOut(True)
        self.signal_generator.setModulationState(True)
        sleep(1.0) # Allow power to stabilize
        print(f"Starting sweep from {self.start_freq} to {self.stop_freq} with a step term of {self.sweep_term}")
        self.step_sweep()

    def sweep_missed_frequencies(self):
        """
        Re-sweep through frequencies that were missed in the previous sweep.
        Resets sweep parameters based on the missed frequencies list.
        """
        if not self.missed_frequencies:
            return
        
        self.is_sweeping = True
        self.last_step = False
        self.sweeping_missed = True
        self.start_freq = self.missed_frequencies[0]
        self.stop_freq = self.missed_frequencies[-1]
        self.current_freq = self.missed_frequencies[0]
        self.missed_frequencies.pop(0)
        
        self.signal_generator.setPower(self.base_power)
        self.signal_generator.setRFOut(True)
        self.signal_generator.setModulationState(True)
        sleep(0.5) # Wait for power to stabilize
        print(f"Sweeping back through from {self.start_freq} to {self.stop_freq} with a step term of {self.sweep_term}")
        self.step_sweep()

    def step_sweep(self):
        """
        Perform one step of the frequency sweep:
            - Update the signal generator frequency and power.
            - Emit UI update signals.
            - Adjust power to reach the target field level.
            - Advance to the next frequency or end the sweep if completed.
        """
        if self.current_freq <= self.stop_freq and self.is_sweeping:
            # Set frequency and reset power to base level
            self.signal_generator.setPower(self.base_power)
            self.signal_generator.setFrequency(self.current_freq, Frequency.MHz.value)
            print(f"Current Frequency: {self.current_freq}, Current Power: {self.current_power}")
            sleep(0.1) # Allow stabilization
            
            # Emit UI updates for frequency and sweep progress
            self.frequencyUpdated.emit(self.current_freq)
            self.sweepStatus.emit(self.log_percentage(self.current_freq, self.start_freq, self.stop_freq))

            # Adjust power to approach the target field level
            print(f"Adjusting power to target level at {self.current_freq} MHz")
            self.adjust_power_to_target_level()
            
            # Emit UI updates for power and field measurements
            self.powerUpdated.emit(self.current_power)
            self.fieldUpdated.emit(self.current_field_level, self.current_x, self.current_y, self.current_z)
            
            # Emit dwell time signal for UI to wait before next step
            print(f"Sleeping for {self.dwell_time_ms} milliseconds")
            self.startDwell.emit(self.dwell_time_ms)
            
            # Determine next frequency step based on sweep mode
            if self.sweeping_missed:
                if not self.missed_frequencies:
                    print("Completed re-sweeping missed frequencies")
                    self.is_sweeping = False
                    return
                self.current_freq = self.missed_frequencies.pop(0)
            else:
                self.current_freq = self.current_freq + (self.current_freq * self.sweep_term)
                print("Power adjusted. Moving to next frequency step: ", self.current_freq)
                if self.current_freq >= self.stop_freq:
                    print("End of sweep range reached: Last step")
                    self.current_freq = self.stop_freq
                    self.last_step = True
                if self.last_step:
                    print("Last step reached; stopping sweep")
                    self.is_sweeping = False
        else:
            # Sweep completed: disable outputs and emit final signals
            print("Sweep Completed")
            self.sweepCompleted.emit(self.missed_frequencies)
            self.is_sweeping = False
            self.signal_generator.setRFOut(False)
            self.signal_generator.setModulationState(False)
            self.frequencyUpdated.emit(self.current_freq)
            self.sweepStatus.emit(100.0)
            
    def stop_sweep(self):
        """
        Immediately stop the frequency sweep and reset signal generator outputs.
        Also clears PID controller data if applicable.
        """
        print("Stopping sweep")
        self.is_sweeping = False
        self.high_field_detected = False
        self.signal_generator.setRFOut(False)
        self.signal_generator.setModulationState(False)
        self.signal_generator.setPower(self.base_power)
        if not self.use_stepper:
            self.pid_controller.clear()
            
    def setTargetField(self, target_field: float):
        """
        Set the target field level for the sweep and update the PID controller if in use.

        Parameters:
            target_field (float): The desired target field level (V/m).
        """
        self.target_field = target_field
        if not self.use_stepper:
            self.pid_controller.setTargetValue(target_field)
            
    def getTargetField(self) -> float:
        """
        Retrieve the target field level.

        Returns:
            float: The target field level (V/m).
        """
        return self.target_field
            
    def setStartFrequency(self, start_freq: float):
        """
        Set the starting frequency for the sweep.

        Parameters:
            start_freq (float): The starting frequency (MHz).
        """
        print(f"Setting start frequency to: {start_freq}")
        self.start_freq = start_freq
        
    def getStartFrequency(self) -> float:
        """
        Retrieve the starting frequency of the sweep.

        Returns:
            float: The starting frequency (MHz).
        """
        return self.start_freq
        
    def setStopFrequency(self, stop_freq: float):
        """
        Set the stop frequency for the sweep.

        Parameters:
            stop_freq (float): The stop frequency (MHz).
        """
        self.stop_freq = stop_freq
        
    def getStopFrequency(self) -> float:
        """
        Retrieve the stop frequency of the sweep.

        Returns:
            float: The stop frequency (MHz).
        """
        return self.stop_freq
        
    def setDwellTime(self, dwell_time: float, unit: str):
        """
        Set the dwell time for each frequency step in the sweep.

        Parameters:
            dwell_time (float): The dwell time value.
            unit (str): The time unit (e.g., Microsecond, Second). The dwell time will be converted to milliseconds.
        """
        print(f"Setting dwell time to: {dwell_time} {unit}")
        if unit == Time.Microsecond.value:
            dwell_time *= 0.001
        elif unit == Time.Second.value:
            dwell_time *= 1000
        self.dwell_time_ms = int(dwell_time)
        print(f"Dwell time set to: {self.dwell_time_ms} ms")
        
    def setSweepTerm(self, sweep_term: float):
        """
        Set the relative step term used to calculate the next frequency in the sweep.

        Parameters:
            sweep_term (float): The relative increase factor for each frequency step.
        """
        self.sweep_term = sweep_term
        
    def log_percentage(self, curr_val, min_val, max_val):
        """
        Calculate the percentage completion of the sweep using a logarithmic scale.

        Parameters:
            curr_val (float): The current frequency value.
            min_val (float): The starting frequency.
            max_val (float): The ending frequency.

        Returns:
            float: The normalized percentage (0 to 100) of the sweep.
        """
        normalized_curr = (math.log(curr_val) - math.log(min_val)) / (math.log(max_val) - math.log(min_val))
        return normalized_curr * 100
    
    def getStepCount(self) -> int:
        """
        Calculate the total number of steps in the sweep based on the start/stop frequencies and sweep term.

        Returns:
            int: The total number of frequency steps.
        """
        steps = math.log(self.stop_freq / self.start_freq) / math.log(1.0 + self.sweep_term)
        step_count = int(math.ceil(steps))
        return step_count
    
    def getSweepTime(self) -> float:
        """
        Estimate the total sweep time, including a 10% overhead for settling time.

        Returns:
            float: The total estimated sweep time in seconds.
        """
        return (self.dwell_time_ms / 1000) * self.getStepCount() * 1.1 # Assume 10% overhead for settling time
    
        
    def adjust_power_to_target_level(self):
        """
        Adjust the signal generator's power output using a closed-loop control until the measured field
        reaches the target field level within an acceptable threshold. In stepper mode, the adjustment
        is made incrementally. If the field level exceeds twice the target or if the power limit is exceeded,
        a warning is logged and the sweep is aborted.
        """
        power_limit_exceeded = False
        while True:
            sleep(0.005) # Small delay for stabilization (play with this value)
            # Blocking call to read the current field level and vector components
            current_field_level, x, y, z = self.field_probe.readCurrentField()
            self.current_field_level = current_field_level
            self.current_x = x
            self.current_y = y
            self.current_z = z
            
            print(f"Current Field Level: {current_field_level} V/m")
            
            # Check if field level is within acceptable threshold
            if (current_field_level > self.target_field) and (current_field_level < (self.target_field * self.threshold)):
                print(f"Field level within threshold: {current_field_level}")
                break
            
            # If field level is excessively high, log warning and break out
            if current_field_level > (self.target_field * 2.0):
                warning_message = f'Field level exceeded 2x target level: {current_field_level} V/m \n At frequency: {self.current_freq} MHz \n And power: {self.current_power} dBm'
                self.log_warning(self.current_freq, warning_message)
                break
            
            # Update current power from signal generator
            self.current_power = self.signal_generator.getPower()
            
            if not self.use_stepper:
                # Use PID controller to calculate adjustment
                pid_output = self.pid_controller.calculate(current_field_level)
                self.signal_generator.setPower(pid_output + self.current_power)
            else:
                # Stepper mode: incrementally adjust power
                if current_field_level < self.target_field:
                    self.current_power += 0.1
                elif current_field_level > (self.target_field * self.threshold):
                    self.current_power -= 1
                    
                print(f"Setting power to: {self.current_power}")
                
                # Check for power limit and potential hardware issues
                if self.current_power > 10.0:
                    if current_field_level <= 0.5:
                        if not power_limit_exceeded:
                            power_limit_exceeded = True
                            warning_message = f'Power limit exceeded: {self.current_power} dBm at frequency: {self.current_freq} MHz and field level: {current_field_level} V/m. \nAborting sweep. Please check hardware connection.'
                            self.powerLimitExceeded.emit(warning_message)
                        self.current_power = self.base_power
                        self.current_power = self.signal_generator.setPower(self.current_power)
                        self.stop_sweep()
                        break
                    else:
                        warning_message = f'Field level below target level: {current_field_level} V/m, \n at frequency: {self.current_freq} MHz, \n and power: {self.current_power} dBm'
                        self.log_warning(self.current_freq, warning_message)
                        self.current_power = self.base_power
                        self.signal_generator.setPower(self.current_power)
                        # Move to the next frequency step
                        break
                # Update power setting and log the change
                self.current_power = self.signal_generator.setPower(self.current_power)
                print(f"Power set to: {self.current_power}")