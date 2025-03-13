"""
Module: FieldProbe.py
Description: This module implements serial commands and a serial communication interface
             for interacting with an ETS Lindgren HI6006 field probe. It defines several
             command classes for reading probe data (identity, battery, temperature, and
             composite field measurements) as well as simulation and communication classes.
Author: Bryce Kowalczyk
Date: 2025-09-01
"""

import time
import serial
from serial import SerialException, serialutil
import threading
import queue
import random
from abc import ABC, abstractmethod
from PyQt5.QtCore import QObject, pyqtSignal

    
class SerialCommand(ABC):
    
    """
    Abstract base class representing a generic serial command.
    
    Attributes:
        ERRORS (list): List of error messages corresponding to error codes.
        command (bytes): Command to be sent to the device.
        blocksize (int): Expected size of the response block.
        signal (int): Associated signal value for the command.
    """
    
    ERRORS = [
        'Unknown Error',
        'Communication Error',
        'Buffer Full Error',
        'Invalid Command',
        'Invalid Parameter',
        'Hardware Error',
        'Parity Error',
        'Probe Off',
        'Invalid Command',
        'Battery Fail'
    ]
    
    def __init__(self, command: bytes, blocksize: int, signal: int) -> None:
        """
        Initialize a SerialCommand instance.
        
        Args:
            command (bytes): The command to send.
            blocksize (int): Expected size of the response.
            signal (int): Signal identifier associated with the command.
        """
        self.command = command
        self.blocksize = blocksize
        self.signal = signal
    
    def checkForError(self, response: bytes) -> tuple[bool, str]:
        """
        Check the response for errors.
        
        Args:
            response (bytes): The raw response from the device.
        
        Returns:
            tuple: A tuple containing a boolean indicating if an error was found,
            and a message describing the error or the response.
        """
        message = response.decode().strip().strip(':')
        if message.startswith('E'):
            self.signal = 6
            return True, self.ERRORS[message[1]]
        if message.endswith('F'):
            self.signal = 6
            return True, self.ERRORS[9]
        return False, message
    
    @abstractmethod
    def parse(self, response: str) -> None:
        """
        Abstract method to parse the response from the device.
        
        Args:
            response (str): The response string to parse.
        
        Raises:
            NotImplementedError: This method should be overridden by subclasses.
        """
        pass
            

class TemperatureCommand(SerialCommand):
    """
    Command to request temperature data from the field probe.
    
    Attributes:
        temperature (float): Parsed temperature value.
    """
    def __init__(self) -> None:
        """
        Initialize a TemperatureCommand instance.
        """
        super().__init__(command=b'TF', blocksize=8, signal=4)
        self.temperature = 0.0
    
    def parse(self, response: str) -> float:
        """
        Parse the response to extract the temperature.
        
        Args:
            response (str): The response string starting with 'T' followed by the temperature value.
        
        Returns:
            float: The parsed temperature.
        """
        self.temperature = float(response.strip('T'))
        return self.temperature

class BatteryCommand(SerialCommand):
    """
    Command to request battery status from the field probe.
    
    Attributes:
        percentage (int): Battery percentage.
    """
    def __init__(self) -> None:
        """
        Initialize a BatteryCommand instance.
        """
        super().__init__(command=b'BP', blocksize=6, signal=3)
        self.percentage = 100
    
    def parse(self, response: str) -> int:
        """
        Parse the response to extract the battery percentage.
        
        Args:
            response (str): The response string containing the battery percentage in hexadecimal.
        
        Returns:
            int: The battery percentage.
        """
        self.percentage = int(response[1:3], 16)
        return self.percentage
    
class IdentityCommand(SerialCommand):
    """
    Command to request identity information from the field probe.
    
    Attributes:
        model (str): Model number of the probe.
        revision (str): Firmware revision.
        serial_no (str): Serial number of the probe.
        calibration (str): Calibration date.
    """
    
    def __init__(self) -> None:
        """
        Initialize an IdentityCommand instance.
        """
        super().__init__(command=b'I', blocksize=34, signal=2)
        self.model: str = 'HI-6006'
        self.firmware: str = ''
        self.serialNo: str = ''
        self.calibrationDate: str = ''
        
    def parse(self, response: str) -> tuple[str, str, str, str]:
        """
        Parse the identity response.
        
        Args:
            response (str): The response string starting with 'I' followed by identity data.
        
        Returns:
            tuple: A tuple containing the model, revision, serial number, and calibration date.
        """
        response_str = response.strip('I')
        self.model = f'HI-{response_str[0:4]}'
        self.revision = response_str[4:14]
        self.serial_no = response_str[14:22]
        self.calibration = response_str[22:30]
        return self.model, self.revision, self.serial_no, self.calibration
    
class CompositeDataCommand(SerialCommand):
    """
    Command to request composite field data from the probe.
    
    Attributes:
        composite (float): Composite field measurement.
        x (float): X component of the field.
        y (float): Y component of the field.
        z (float): Z component of the field.
    """

    def __init__(self) -> None:
        """
        Initialize a CompositeDataCommand instance.
        """
        super().__init__(command=b'D5', blocksize=24, signal=1)
        self.composite = 0.0
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        
    def parse(self, response: str) -> tuple[int, int, int, int]:
        """
        Parse the composite data response.
        
        Args:
            response (str): The response string with composite field data.
        
        Returns:
            tuple: A tuple containing the x, y, z, and composite field values.
        """
        response_str = response.strip(':DN')
        self.x = float(response_str[0:5])
        self.y = float(response_str[5:10])
        self.z = float(response_str[10:15])
        self.composite = float(response_str[15:20])
        return self.x, self.y, self.z, self.composite

class FieldProbe(QObject):
    """
    Simulation class for a field probe that emits signals for various measurements.
    
    Signals:
        fieldIntensityReceived: Emitted with composite and component field strengths.
        identityReceived: Emitted with identity details.
        batteryReceived: Emitted with battery percentage.
        temperatureReceived: Emitted with temperature value.
        serialConnectionError: Emitted when a serial connection error occurs.
        fieldProbeError: Emitted when an error occurs reading the probe.
    """
    
    fieldIntensityReceived = pyqtSignal(float, float, float, float)
    identityReceived = pyqtSignal(str, str, str, str)
    batteryReceived = pyqtSignal(int)
    temperatureReceived = pyqtSignal(float) 
    serialConnectionError = pyqtSignal(str)
    fieldProbeError = pyqtSignal(str)
    
    def __init__(self) -> None:
        """
        Initialize a FieldProbe instance.
        """
        super().__init__()
        self.serial = None
        self.is_running = False
        self.battery_level = 100
        self.battery_fail = False
        self.info_interval = 2.0
        
    def start(self):
        """
        Start the field probe simulation.
        """
        self.is_running = True
        self.initializeProbe()
        
    def stop(self):
        """
        Stop the field probe simulation.
        """
        self.is_running = False
    
    def initializeProbe(self):
        """
        Initialize the probe by emitting an identity signal.
        """
        self.identityReceived.emit('6006', '', '', '')
            
    def getBatteryPercentage(self):
        """
        Simulate retrieving the battery percentage and emit the corresponding signal.
        """
        self.batteryReceived.emit(random.randrange(0, 100))
        
    def getTemperature(self):
        """
        Simulate retrieving the temperature and emit the corresponding signal.
        """
        self.temperatureReceived.emit(random.randrange(40, 110))
        
    def getFieldStrengthMeasurement(self):
        """
        Simulate retrieving field strength measurements and emit the corresponding signal.
        """
        self.fieldIntensityReceived.emit(
            random.randrange(-10, 5),
            random.randrange(-10, 5),
            random.randrange(-10, 5),
            random.randrange(-10, 5)
        )
        
    def readWriteProbe(self):
        """
        Placeholder method for reading from and writing to the probe.
        """
        pass

class ETSLindgrenHI6006(QObject):
    """
    Class to manage the ETS Lindgren HI6006 field probe via serial communication.
    
    Signals:
        fieldIntensityReceived: Emitted with composite and component field strengths.
        identityReceived: Emitted with identity details.
        batteryReceived: Emitted with battery percentage.
        temperatureReceived: Emitted with temperature value.
        serialConnectionError: Emitted when a serial connection error occurs.
        fieldProbeError: Emitted when an error occurs while reading the probe.
    """
    
    fieldIntensityReceived = pyqtSignal(float, float, float, float)
    identityReceived = pyqtSignal(str, str, str, str)
    batteryReceived = pyqtSignal(int)
    temperatureReceived = pyqtSignal(float) 
    serialConnectionError = pyqtSignal(str)
    fieldProbeError = pyqtSignal(str)
    
    def __init__(self, serial_port: str = 'COM7'):
        """
        Initialize an ETSLindgrenHI6006 instance.
        
        Args:
            serial_port (str): The serial port to use (default is 'COM7').
        """
        super().__init__()
        self.serial_port = serial_port
        self.serial = None
        self.is_running = False
        self.battery_level = 100
        self.battery_fail = False
        self.command_queue = queue.Queue()
        self.info_interval = 2.0
        self.data_interval = 0.005
        self.composite_field = 0.0
        self.x_component = 0.0
        self.y_component = 0.0
        self.z_component = 0.0
        self.probe_thread = None
        self.stop_probe_event = threading.Event()
        self.reading_field = False
    
    def commandToSignal(self, command: SerialCommand) -> pyqtSignal:
        """
        Map a SerialCommand to its corresponding PyQt signal.
        
        Args:
            command (SerialCommand): The command instance.
        
        Returns:
            pyqtSignal: The associated signal for the command.
        """
        if type(command) == IdentityCommand:
            return self.identityReceived
        elif type(command) == BatteryCommand:
            return self.batteryReceived
        elif type(command) == TemperatureCommand:
            return self.temperatureReceived
        elif type(command) == CompositeDataCommand:
            return self.fieldIntensityReceived
        else:
            return self.fieldProbeError
    
    def start(self):
        """
        Start the probe by opening the serial connection and launching the probe thread.
        """
        self.is_running = True
        try:
            self.serial = serial.Serial(self.serial_port, baudrate=9600, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, stopbits=1, timeout=5)
            self.probe_thread = threading.Thread(target=self.readWriteProbe)
            self.probe_thread.start()
            self.initializeProbe()
            print('Probe Thread Started')
        except ValueError as e:
            self.is_running = False
            self.serialConnectionError.emit(str(e))
        except SerialException as e:
            self.is_running = False
            self.serialConnectionError.emit(str(e))
            print(str(e))
        except FileNotFoundError as e:
            self.is_running = False
            self.serialConnectionError.emit(str(e))
            print(str(e))
        except serialutil.SerialException as e:
            self.is_running = False
            self.serialConnectionError.emit(str(e))
            print(str(e))
        except:
            self.is_running = False
            self.serialConnectionError.emit('Unknown Error')
            print('Unknown Error')
        
    def stop(self):
        """
        Stop the probe, terminate the probe thread, and close the serial connection.
        """
        self.is_running = False
        self.stop_probe_event.set()
        if self.probe_thread is not None:
            if self.probe_thread.is_alive():
                self.probe_thread.join()
        if self.serial and self.serial.is_open:
            self.serial.close()
        
    def initializeProbe(self):
        """
        Initialize the probe by queuing an IdentityCommand.
        """
        self.command_queue.put(IdentityCommand())
        
    def getBatteryPercentage(self):
        """
        Queue a BatteryCommand to retrieve the battery percentage.
        """
        self.command_queue.put(BatteryCommand())
        
    def getTemperature(self):
        """
        Queue a TemperatureCommand to retrieve the temperature.
        """
        self.command_queue.put(TemperatureCommand())
    
    def getFieldStrengthMeasurement(self):
        """
        Queue a CompositeDataCommand to retrieve field strength measurements.
        """
        self.command_queue.put(CompositeDataCommand())
        
    def readCurrentField(self):
        """
        Get the current field measurements.
        
        Returns:
            tuple: A tuple containing the composite field, x, y, and z components.
        """
        return self.composite_field, self.x_component, self.y_component, self.z_component
    
    def readWriteProbe(self):
        """
        Main loop for reading from and writing to the probe.
        Processes the command queue and emits appropriate signals based on the responses.
        """
        last_info_update = time.time()
        last_data_update = time.time()
        while not self.stop_probe_event.is_set() and self.is_running:
            if time.time() - last_data_update >= self.data_interval:
                self.getFieldStrengthMeasurement()
                last_data_update = time.time()
            if time.time() - last_info_update >= self.info_interval:
                self.getBatteryPercentage()
                self.getTemperature()
                last_info_update = time.time()
            if not self.command_queue.empty() and not self.reading_field:
                serial_command: SerialCommand = self.command_queue.get()
                try:
                    self.serial.write(serial_command.command)
                    response = self.serial.read(serial_command.blocksize)
                except:
                    self.serialConnectionError.emit('Serial Communication Error')
                    break
                error, message = serial_command.checkForError(response)
                if error:
                    self.fieldProbeError.emit(message)
                else:
                    if type(serial_command) == IdentityCommand:
                        try:
                            model, revision, serial, calibration = serial_command.parse(message)
                            self.identityReceived.emit(model, revision, serial, calibration)
                        except:
                            self.fieldProbeError.emit(f'Error Reading Probe Identity: {message}')
                    elif type(serial_command) == CompositeDataCommand:
                        try:
                            # Keep reading field for UI Updates
                            x, y, z, composite = serial_command.parse(message)
                            self.x_component = x
                            self.y_component = y
                            self.z_component = z
                            self.composite_field = composite
                        except:
                            self.fieldProbeError.emit(f'Error Reading Field Intensity: {message}')
                    elif type(serial_command) == BatteryCommand:
                        try:
                            percentage = serial_command.parse(message)
                            #print(f'Read Battery Level: {percentage}')
                            self.batteryReceived.emit(percentage)
                        except:
                            self.fieldProbeError.emit(f'Error Reading Battery Level: {message}')
                    elif type(serial_command) == TemperatureCommand:
                        try:
                            temperature = serial_command.parse(message)
                            #print(f'Read Battery Level: {temperature}')
                            self.temperatureReceived.emit(temperature)
                        except:
                            self.fieldProbeError.emit(f'Error Reading Temperature: {message}')
                    else:
                        self.fieldProbeError.emit('Unknown Command & Response')
                    
                    