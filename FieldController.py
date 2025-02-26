from PyQt5.QtCore import QObject, QTimer, QThread, pyqtSignal, pyqtSlot
from FieldProbe import ETSLindgrenHI6006
from SignalGenerator import AgilentN5181A, Frequency, Time
from PID import PIDController as PID
from time import sleep
import math
import os
from datetime import datetime

class FieldController(QObject):
    
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
        super().__init__()
        self.signal_generator = signal_generator
        self.field_probe = field_probe
        self.use_stepper = False
        if pid_controller is None:
            self.pid_controller = PID(0.1, 0.01, 0.01)
            self.use_stepper = True
            
        # Initialize the field controller parameters
        self.is_sweeping = False
        self.last_step = False
        self.high_field_detected = False
        self.sweeping_missed = False
        self.missed_frequencies = []
        self.target_field = 1.0
        self.threshold = 1.5
        self.base_power = -30
        self.current_power = -30
        self.start_freq = 1000.0
        self.current_freq = 1000.0
        self.stop_freq = 2000.0
        self.dwell_time_ms = 500
        self.sweep_term = 0.01
        self.current_field_level = 0.0
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        
        # Ensure the MyApp directory exists and set up logging
        self.log_file_path = self.setup_logging_directory()
        
    def setup_logging_directory(self) -> str:
        '''Create a directory for logging data and return the path.'''
        # Get the user's Documents directory
        documents_dir = os.path.expanduser("~/Documents")
        log_dir = os.path.join(documents_dir, "ImmuniSweepLogs")

        # Ensure the MyApp directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a log file path with the current date and time
        log_file = os.path.join(log_dir, f"log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
        
        return log_file
    
    def log_warning(self, frequency: float, warning: str):
        '''Log data to a file.'''
        self.missed_frequencies.append(frequency)
        with open(self.log_file_path, "a") as log_file:
            log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - High Field Detected Warning: {warning}\n")
            
    def start_sweep(self):
        """Start the frequency sweep with the specified range, dwell and step term."""
        self.is_sweeping = True
        self.last_step = False
        self.sweeping_missed = False
        self.missed_frequencies = []
        self.current_freq = self.start_freq
        # Set the signal generator to low power to start
        self.signal_generator.setPower(self.base_power)
        self.signal_generator.setRFOut(True)
        self.signal_generator.setModulationState(True)
        sleep(1.0) # Wait for power to stabilize
        print(f"Starting sweep from {self.start_freq} to {self.stop_freq} with a step term of {self.sweep_term}")
        self.step_sweep()

    def sweep_missed_frequencies(self):
        '''Sweep the missed frequencies again.'''
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
        """Step through the frequency sweep range."""
        
        # Check if the sweep is still active
        if self.current_freq <= self.stop_freq and self.is_sweeping:
            
            # Reset signal generator to low power
            self.signal_generator.setPower(self.base_power)
            # Set the signal generator frequency
            self.signal_generator.setFrequency(self.current_freq, Frequency.MHz.value)
            print(f"Current Frequency: {self.current_freq}, Current Power: {self.current_power}")
            sleep(0.1) # Wait for power to stabilize, field to reach steady state
            
            # Emit the signal to update the UI with the new frequency
            #self.current_freq = round(self.signal_generator.getFrequency(), 2)
            self.frequencyUpdated.emit(self.current_freq)
            self.sweepStatus.emit(self.log_percentage(self.current_freq, self.start_freq, self.stop_freq))

            print(f"Adjusting power to target level at {self.current_freq} MHz")
            # Perform closed-loop control to adjust the power
            self.adjust_power_to_target_level()
            
            
            self.powerUpdated.emit(self.current_power)
            self.fieldUpdated.emit(self.current_field_level, self.current_x, self.current_y, self.current_z)
            
            print(f"Sleeping for {self.dwell_time_ms} milliseconds")
            self.startDwell.emit(self.dwell_time_ms)
            
            

            # Move to the next frequency step
            if self.sweeping_missed:
                if len(self.missed_frequencies) == 0:
                    print("Missed frequencies swept again")
                    self.is_sweeping = False
                    return
                self.current_freq = self.missed_frequencies[0]
                self.missed_frequencies.pop(0)
            else:
                self.current_freq = self.current_freq + (self.current_freq * self.sweep_term)
                print("Power adjusted. Moving to next frequency step: ", self.current_freq)
                if self.current_freq >= self.stop_freq:
                    print("End of sweep range reached: Last step")
                    self.current_freq = self.stop_freq
                    self.last_step = True
                if self.last_step:
                    print("Last step reached")
                    self.is_sweeping = False
        else:
            
            # Sweep is complete
            print("Sweep Completed")
            self.sweepCompleted.emit(self.missed_frequencies)
            self.is_sweeping = False
            self.signal_generator.setRFOut(False)
            self.signal_generator.setModulationState(False)
            self.frequencyUpdated.emit(self.current_freq)
            self.sweepStatus.emit(100.0)
            
    def stop_sweep(self):
        """Stop the frequency sweep and all timers."""
        print("Stopping sweep")
        self.is_sweeping = False
        self.high_field_detected = False
        #self.adjust_timer.stop()
        #self.sweep_timer.stop()
        self.signal_generator.setRFOut(False)
        self.signal_generator.setModulationState(False)
        self.signal_generator.setPower(self.base_power)
        if not self.use_stepper:
            self.pid_controller.clear()
            
    def setTargetField(self, target_field: float):
        self.target_field = target_field
        if not self.use_stepper:
            self.pid_controller.setTargetValue(target_field)
            
    def getTargetField(self) -> float:
        return self.target_field
            
    def setStartFrequency(self, start_freq: float):
        print(f"Setting start frequency to: {start_freq}")
        self.start_freq = start_freq
        
    def getStartFrequency(self) -> float:
        return self.start_freq
        
    def setStopFrequency(self, stop_freq: float):
        self.stop_freq = stop_freq
        
    def getStopFrequency(self) -> float:
        return self.stop_freq
        
    def setDwellTime(self, dwell_time: float, unit: str):
        print(f"Setting dwell time to: {dwell_time} {unit}")
        if unit == Time.Microsecond.value:
            dwell_time *= 0.001
        elif unit == Time.Second.value:
            dwell_time *= 1000
        self.dwell_time_ms = int(dwell_time)
        print(f"Dwell time set to: {self.dwell_time_ms} ms")
        
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
        return (self.dwell_time_ms / 1000) * self.getStepCount() * 1.1 # Assume 10% overhead for settling time
    
        
    def adjust_power_to_target_level(self):
        """Adjust the power level based on probe readings to return to target field level."""
        power_limit_exceeded = False
        while True:
            # Get the current field level from the field probe
            sleep(0.005)
            # Call a direct blocking method to get the true field strength right now
            current_field_level, x, y, z = self.field_probe.readCurrentField()
            self.current_field_level = current_field_level
            self.current_x = x
            self.current_y = y
            self.current_z = z
            
            print(f"Current Field Level: {current_field_level} V/m")
            
            if (current_field_level > self.target_field) and (current_field_level < (self.target_field * self.threshold)):
                print(f"Field level within threshold: {current_field_level}")
                break
            
            # Check if the field level is too high. If so, emit a signal to notify the user
            if current_field_level > (self.target_field * 2.0):
                warning_message = f'Field level exceeded 2x target level: {current_field_level} V/m \n At frequency: {self.current_freq} MHz \n And power: {self.current_power} dBm'
                self.log_warning(self.current_freq, warning_message)
                break
            
            # Get the current power level from the signal generator
            self.current_power = self.signal_generator.getPower()
            
            if not self.use_stepper:
                pid_output = self.pid_controller.calculate(current_field_level)
                self.signal_generator.setPower(pid_output + self.current_power)
            else:
                # Adjust the power level based on the current field level
                if current_field_level < self.target_field:
                    self.current_power += 0.1
                elif current_field_level > (self.target_field * self.threshold):
                    self.current_power -= 1
                print(f"Setting power to: {self.current_power}")
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
                        self.current_power = self.signal_generator.setPower(self.current_power)
                        # Move to the next frequency step
                        break
                self.current_power = self.signal_generator.setPower(self.current_power)
                print(f"Power set to: {self.current_power}")