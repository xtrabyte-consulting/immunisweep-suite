import serial
from serial import SerialException, SerialTimeoutException, serialutil
import threading
import queue
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
        print(f'Temp: {self.temperature}')
        return self.temperature

class BatteryCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'BP', blocksize=5, signal=3)
        self.percentage = 100
    
    def parse(self, response: str) -> int:
        self.percentage = int(response.strip('BN'))
        print(f'Battery: {self.percentage}')
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
        self.x = float(response_str[10:15])
        self.composite = float(response_str[15:20])
        return self.x, self.y, self.z, self.composite

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
        self.command_queue = queue.Queue
        self.info_interval = 10
        self.stop_probe_event = threading.Event()
        self.stop_info_update = threading.Event()
    
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
            self.initiaizeProbe()
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
            running = False
            self.serialConnectionError.emit(str(e))
            print(str(e))
        
    def stop(self):
        self.is_running = False
        self.stop_probe_event.set()
        self.probe_thread.join()
        if self.serial and self.serial.is_open:
            self.serial.close()
        
    def initiaizeProbe(self):
        self.command_queue.put(IdentityCommand())
        
    def beginBatTempUpdates(self):
        self.tempBatThread = threading.Thread(target=self.updateProbeStatus)
        self.tempBatThread.start()
        
    def endBatTempUpdates(self):
        self.stop_info_update.set()
        self.tempBatThread.join() 
        
    def setUpdateInterval(self, interval: int):
        self.probeStatusInterval = interval if interval > 5 else 5
        
    def updateProbeStatus(self):
        while not self.stop_info_update.is_set():
            self.command_queue.put(BatteryCommand())
            self.command_queue.put(TemperatureCommand())
            self.stop_info_update.wait(self.probeStatusInterval)
        
    def getBatteryPercentage(self):
        self.command_queue.put(BatteryCommand())
        
    def getTemperature(self):
        self.command_queue.put(TemperatureCommand())
    
    def getFieldStrengthMeasurement(self):
        self.command_queue.put(CompositeDataCommand())
    
    def readWriteProbe(self):
        while not self.stop_probe_event.is_set():
            serial_command: SerialCommand = self.command_queue.get()
            self.serial.write(serial_command.command)
            response = self.serial.read(serial_command.blocksize)
            error, message = serial_command.checkForError(response)
            if error:
                self.fieldProbeError.emit(message)
            else:
                self.commandToSignal(serial_command).emit(serial_command.parse(message))
                    
                    