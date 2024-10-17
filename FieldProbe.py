import time
import serial
from serial import SerialException, SerialTimeoutException, serialutil
import threading
import queue
import random
from abc import ABC, abstractmethod
from PyQt5.QtCore import QObject, pyqtSignal

    
class SerialCommand(ABC):
    
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
        self.command = command
        self.blocksize = blocksize
        self.signal = signal
    
    def checkForError(self, response: bytes) -> tuple[bool, str]:
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
        pass
            

class TemperatureCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'TF', blocksize=8, signal=4)
        self.temperature = 0.0
    
    def parse(self, response: str) -> float:
        self.temperature = float(response.strip('T'))
        return self.temperature

class BatteryCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'BP', blocksize=6, signal=3)
        self.percentage = 100
    
    def parse(self, response: str) -> int:
        self.percentage = int(response[1:3], 16)
        return self.percentage
    
class IdentityCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'I', blocksize=34, signal=2)
        self.model: str = 'HI-6006'
        self.firmware: str
        self.serialNo: str
        self.calibrationDate: str
        
    def parse(self, response: str) -> tuple[str, str, str, str]:
        response_str = response.strip('I')
        self.model = f'HI-{response_str[0:4]}'
        self.revision = response_str[4:14]
        self.serial_no = response_str[14:22]
        self.calibration = response_str[22:30]
        return self.model, self.revision, self.serial_no, self.calibration
    
class CompositeDataCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'D5', blocksize=24, signal=1)
        self.composite = 0.0
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        
    def parse(self, response: str) -> tuple[int, int, int, int]:
        response_str = response.strip(':DN')
        self.x = float(response_str[0:5])
        self.y = float(response_str[5:10])
        self.z = float(response_str[10:15])
        self.composite = float(response_str[15:20])
        return self.x, self.y, self.z, self.composite

class FieldProbe(QObject):
    fieldIntensityReceived = pyqtSignal(float, float, float, float)
    identityReceived = pyqtSignal(str, str, str, str)
    batteryReceived = pyqtSignal(int)
    temperatureReceived = pyqtSignal(float) 
    serialConnectionError = pyqtSignal(str)
    fieldProbeError = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.serial = None
        self.is_running = False
        self.battery_level = 100
        self.battery_fail = False
        self.info_interval = 2.0
        
    def start(self):
        self.is_running = True
        self.initializeProbe()
        
    def stop(self):
        self.is_running = False
    
    def initializeProbe(self):
        self.identityReceived.emit('6006', '', '', '')
            
    def getBatteryPercentage(self):
        self.batteryReceived.emit(random.randrange(0, 100))
        
    def getTemperature(self):
        self.temperatureReceived.emit(random.randrange(40, 110))
        
    def getFieldStrengthMeasurement(self):
        self.fieldIntensityReceived.emit(random.randrange(-10, 5), random.randrange(-10, 5), random.randrange(-10, 5), random.randrange(-10, 5))
        
    def readWriteProbe(self):
        pass

class ETSLindgrenHI6006(QObject):
    fieldIntensityReceived = pyqtSignal(float, float, float, float)
    identityReceived = pyqtSignal(str, str, str, str)
    batteryReceived = pyqtSignal(int)
    temperatureReceived = pyqtSignal(float) 
    serialConnectionError = pyqtSignal(str)
    fieldProbeError = pyqtSignal(str)
    
    def __init__(self, serial_port: str = 'COM5'):
        super().__init__()
        self.serial_port = serial_port
        self.serial = None
        self.is_running = False
        self.battery_level = 100
        self.battery_fail = False
        self.command_queue = queue.Queue()
        self.info_interval = 2.0
        self.data_interval = 0.01
        self.composite_field = 0.0
        self.x_component = 0.0
        self.y_component = 0.0
        self.z_component = 0.0
        self.stop_probe_event = threading.Event()
        self.reading_field = False
    
    def commandToSignal(self, command: SerialCommand) -> pyqtSignal:
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
        self.is_running = False
        self.stop_probe_event.set()
        if self.probe_thread is not None:
            if self.probe_thread.is_alive():
                self.probe_thread.join()
        if self.serial and self.serial.is_open:
            self.serial.close()
        
    def initializeProbe(self):
        self.command_queue.put(IdentityCommand())
        
    def getBatteryPercentage(self):
        self.command_queue.put(BatteryCommand())
        
    def getTemperature(self):
        self.command_queue.put(TemperatureCommand())
    
    def getFieldStrengthMeasurement(self):
        self.command_queue.put(CompositeDataCommand())
        
    def readCurrentField(self):
        return self.composite_field, self.x_component, self.y_component, self.z_component
    
    def readWriteProbe(self):
        last_info_update = time.time()
        last_data_update = time.time()
        alerted = 0
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
                            #print(f'Read Field Level: {composite}')
                            self.x_component = x
                            self.y_component = y
                            self.z_component = z
                            self.composite_field = composite
                            self.fieldIntensityReceived.emit(composite, x, y, z)
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
                    
                    