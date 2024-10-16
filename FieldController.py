from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from FieldProbe import ETSLindgrenHI6006
from SignalGenerator import AgilentN5181A, Frequency, Time
from PID import PIDController as PID
from time import sleep
import math
from typing import Optional

class FieldController(QObject):
    
    # Signals for UI updates
    frequencyUpdated = pyqtSignal(float)
    powerUpdated = pyqtSignal(float)
    fieldUpdated = pyqtSignal(float, float, float, float)
    sweepCompleted = pyqtSignal()
    sweepStatus = pyqtSignal(float)
    highFieldDetected = pyqtSignal()
    
    def __init__(self, signal_generator: AgilentN5181A, field_probe: ETSLindgrenHI6006, pid_controller: PID | None):
        super().__init__()
        self.signal_generator = signal_generator
        self.field_probe = field_probe
        self.use_stepper = False
        if pid_controller is None:
            self.pid_controller = PID(0.1, 0.01, 0.01)
            self.use_stepper = True
        self.is_sweeping = False
        self.target_field = 1.0
        self.threshold = 1.5
        self.base_power = -10
        self.start_freq = 100.0
        self.stop_freq = 1000.0
        self.dwell_time = 0.5
        self.sweep_term = 0.01
        
    def setTargetField(self, target_field: float):
        self.target_field = target_field
        if not self.use_stepper:
            self.pid_controller.setTargetValue(target_field)
            
    def getTargetField(self) -> float:
        return self.target_field
            
    def setStartFrequency(self, start_freq: float):
        self.start_freq = start_freq
        
    def getStartFrequency(self) -> float:
        return self.start_freq
        
    def setStopFrequency(self, stop_freq: float):
        self.stop_freq = stop_freq
        
    def getStopFrequency(self) -> float:
        return self.stop_freq
        
    def setDwellTime(self, dwell_time: float, unit: str):
        if unit == Time.Microsecond.value:
            dwell_time *= 0.000001
        elif unit == Time.Millisecond.value:
            dwell_time *= 0.001
        self.dwell_time = dwell_time
        
    def setSweepTerm(self, sweep_term: float):
        self.sweep_term = sweep_term
        
    def log_percentage(self, curr_val, min_val, max_val):
        normalized_curr = (math.log(curr_val) - math.log(min_val)) / (math.log(max_val) - math.log(min_val))
        return normalized_curr * 100
    
    def getStepCount(self) -> int:
        steps = math.log(self.stop_freq / self.start_freq) / math.log(1.0 + self.sweep_term)
        step_count = int(math.ceil(steps))
        return step_count
    
    def getSweepTime(self) -> float:
        return self.dwell_time * self.getStepCount()
            
    @pyqtSlot(float, float, float, float)
    def start_sweep(self):
        """Start the frequency sweep with the specified range, dwell and step term."""
        self.is_sweeping = True
        current_freq = self.start_freq
        # Set the signal generator to low power to start
        self.signal_generator.setPower(self.base_power)
        self.signal_generator.setRFOut(True)
        print(f"Starting sweep from {self.start_freq} to {self.stop_freq} with a step term of {self.sweep_term}")

        while current_freq <= self.stop_freq and self.is_sweeping:
            print(f"Current Frequency: {current_freq}")
            # Set the signal generator frequency
            self.signal_generator.setFrequency(current_freq, Frequency.MHz.value)
            self.sweepStatus.emit(self.log_percentage(current_freq, self.start_freq, self.stop_freq))

            # Emit the signal to update the UI with the new frequency
            self.frequencyUpdated.emit(current_freq)

            print(f"Adjusting power to target level at {current_freq} MHz")
            # Perform closed-loop control to adjust the power
            self.adjust_power_to_target_level()
            
            print(f"Sleeping for {self.dwell_time} seconds")
            sleep(self.dwell_time)
            
            print("Power adjusted. Moving to next frequency step.")
            # Reset signal generator to low power
            self.signal_generator.setPower(self.base_power)

            # Move to the next frequency step
            current_freq = current_freq + (current_freq * self.sweep_term)

        # Emit the sweep completed signal
        self.sweepCompleted.emit()
        
    def adjust_power_to_target_level(self):
        """Adjust the power level based on probe readings to return to target field level."""
        while True:
            # Get the current field level from the field probe
            sleep(0.01)
            # Call a direct blocking method to get the true field strength right now
            current_field_level, x, y, z = self.field_probe.readCurrentField()
            
            print(f"Current Field Level: {current_field_level} V/m")
            # Emit signal to update the UI with the field level
            self.fieldUpdated.emit(current_field_level, x, y, z)
            
            # Check if the field level is too high. If so, stop the sweep
            # shut off the RF output and emit a signal to notify the user
            if current_field_level > (self.target_field * 2.0):
                self.highFieldDetected.emit()
                self.signal_generator.setPower(self.base_power)
                self.signal_generator.setRFOut(False)
                self.is_sweeping = False
                break
            
            if (current_field_level > self.target_field) and (current_field_level < (self.target_field * self.threshold)):
                print(f"Field level within threshold: {current_field_level}")
                current_field_level, x, y, z = self.field_probe.readCurrentField()
                self.fieldUpdated.emit(current_field_level, x, y, z)
                break
            
            current_power = self.signal_generator.getPower()
            
            if self.use_stepper:
                print("Using stepper control")
                # Adjust the power level based on the current field level
                if current_field_level < self.target_field:
                    current_power += 0.1
                elif current_field_level > (self.target_field * self.threshold):
                    current_power -= 1
                print(f"Setting power to: {current_power}")
                current_power = self.signal_generator.setPower(current_power)
                print(f"Power set to: {current_power}")
            else:
                pid_output = self.pid_controller.calculate(current_field_level)
                self.signal_generator.setPower(pid_output + current_power)
            self.powerUpdated.emit(current_power)
            
    def stop_sweep(self):
        """Stop the frequency sweep."""
        self.is_sweeping = False
        self.signal_generator.setRFOut(False)
        if not self.use_stepper:
            self.pid_controller.clear()