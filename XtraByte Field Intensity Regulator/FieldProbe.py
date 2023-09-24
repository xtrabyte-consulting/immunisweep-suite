import serial
from serial import SerialException, SerialTimeoutException
import threading
import queue
import time
from dataclasses import dataclass
from abc import ABC, abstractmethod
from PyQt5.QtCore import QObject, pyqtSignal

    
class SerialCommand(ABC):
    def __init__(self, command: bytes, blocksize: int) -> None:
        self.command = command
        self.blocksize = blocksize
    
    @abstractmethod
    def parse(self, response: bytes) -> None:
        pass    
 
class TemperatureCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'TF', blocksize=8)
        self.temperature = 0.0
    
    def parse(self, response: bytes) -> tuple[int, float]:
        self.temperature = float(response.decode().strip().strip(':T'))
        print(f'Temp: {self.temperature}')
        return 4, self.temperature
        self.temperatureReceived.emit(self.temperature)

class BatteryCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'BP', blocksize=5)
        self.percentage = 100
    
    def parse(self, response: bytes) -> tuple[int, int]:
        self.percentage = int(response.decode().strip(':BNF').strip())
        print(f'Battery: {self.percentage}')
        return 3, self.percentage
    
class IdentityCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'I', blocksize=34)
        self.model: str = 'HI-6006'
        self.firmware: str
        self.serialNo: str
        self.calibrationDate: str
        
    def parse(self, response: bytes) -> tuple[int, str, str, str, str]:
        response_str = response.decode().strip()
        self.model = response_str[2:6]
        self.revision = response_str[6:16]
        self.serial_no = response_str[16:24]
        self.calibration = response_str[24:32]
        return 2, self.model, self.revision, self.serial_no, self.calibration
    
class CompositeDataCommand(SerialCommand):
    def __init__(self) -> None:
        super().__init__(command=b'D5', blocksize=24)
        self.composite = 0.0
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        
    def parse(self, response: bytes) -> tuple[int, int, int, int, int]:
        response_str = response.decode().strip(':DNF')
        self.x = float(response_str[0:5])
        self.y = float(response_str[5:10])
        self.x = float(response_str[10:15])
        self.composite = float(response_str[15:20])
        return 1, self.x, self.y, self.z, self.composite

class ETSLindgrenHI6006(QObject):
    fieldIntensityReceived = pyqtSignal(float, float, float, float)
    identityReceived = pyqtSignal(str, str, str, str)
    batteryReceived = pyqtSignal(int)
    temperatureReceived = pyqtSignal(float) 
    serialConnectionError = pyqtSignal(str)
    fieldProbeError = pyqtSignal(str)
    SignalToCommandMap = dict
    {
        1: fieldIntensityReceived,
        2: identityReceived,
        3: batteryReceived,
        4: temperatureReceived,
        5: serialConnectionError,
        6: fieldProbeError
    }
    
    def __init__(self, serial_port: str = 'COM5'):
        super().__init__()
        self.serial_port = serial_port
        self.serial = None
        self.is_running = False
        self.read_received = False
        self.firstCommand = True
        self.command: str = None
        self.battery_level: int = 100
        self.battery_flag: bool = False
        self.blockSize = 35
        self.commandQueue = queue.Queue
        self.probeStatusInterval = 10
    
    def start(self):
        self.is_running = True
        try:
            self.serial = serial.Serial(self.serial_port, baudrate=9600, bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD, stopbits=1, timeout=5)
        except ValueError as e:
            self.is_running = False
            self.serialConnectionError.emit(str(e))
        except SerialException as e:
            self.is_running = False
            self.serialConnectionError.emit(str(e))
            print(str(e))
        self.read_thread = threading.Thread(target=self.readSerial)
        self.write_thread = threading.Thread(target=self.writeSerial)
        self.read_thread.start()
        self.write_thread.start()
        self.commandInit()
        
    def stop(self):
        self.is_running = False
        self.write_thread.join()
        self.read_thread.join()
        if self.serial and self.serial.is_open:
            self.serial.close()
        
    def initiaizeProbe(self):
        self.commandQueue.put(IdentityCommand())
        
    def beginBatTempUpdates(self):
        self.tempBatThread = threading.Thread(target=self.updateProbeStatus)
        self.tempBatThread.start()
        
    def setUpdateInterval(self, interval: int):
        self.probeStatusInterval = interval
        
    def updateProbeStatus(self):
        while self.probeStatusInterval > 0:
            self.commandQueue.put(BatteryCommand())
            self.commandQueue.put(TemperatureCommand())
            time.sleep(self.probeStatusInterval)
        
    def commandInit(self):
        self.blockSize = 34
        self.command = b'I'
        self.read_received = True
        
    def getBatteryPercentage(self):
        
        self.command = b'BP'
        self.read_received = True
        
    def getTemperature(self):
        self.command = b'TF'
        self.read_received = True
    
    def getEField(self):
        self.blockSize = 24
        self.command = b'D5'
        self.read_received = True

    def writeSerial(self):
        while self.is_running:
            if self.read_received:
                self.serial.write(self.command)
                self.read_received = False
    
    def probeProbe(self):
        while self.is_running:
            command: ProbeCommand = self.commandQueue.get()
            self.serial.write(command.word)
            response = self.serial.read(command.blocksize).decode().strip().strip()
    
    def readSerial(self):
        while self.is_running:
            if self.serial.in_waiting > 0:
                response = self.serial.read(self.blockSize).decode().strip()
                print(f"Probe Response{response}")
                if response.startswith(':D'):
                    x_component = float(response[2:7])
                    y_component = float(response[7:12])
                    z_component = float(response[12:17])
                    composite = float(response[17:22])
                    #print(f"X: {x_component}, Y: {y_component}, Z: {z_component}, Comp: {composite}")
                    self.fieldIntensityReceived.emit(x_component, y_component, z_component, composite)
                elif response.startswith(':I'):
                    model = response[2:6]
                    revision = response[6:16]
                    serial_no = response[16:24]
                    #calibration = response[24:32]
                    #self.battery_flag = response[32] == 'F'
                    print(model, revision, serial_no)
                    self.identityReceived.emit(model, revision, serial_no)
                elif response.startswith(':B'):
                    self.battery_level = int(response[2:4], 16)
                    self.battery_flag = response[4] == 'F'
                    print(f'Batt: {self.battery_flag}')
                    self.batteryReceived.emit(self.battery_level)
                elif response.startswith(':T'):
                    temperature = float(response[2:6])
                    print(f'Temp: {temperature}')
                    self.temperatureReceived.emit(temperature)
                elif response.startswith(':E'):
                    e = int(response[2])
                    if e == 1:
                        s = "Communication Error"
                    elif e == 2:
                        s = "Buffer Full Error"
                    elif e == 3:
                        s = "Invalid Command"
                    elif e == 4:
                        s = "Invalid Parameter"
                    elif e == 5:
                        s = "Hardware Error"
                    elif e == 6:
                        s = "Parity Error"
                    elif e == 7:
                        s = "Probe Off"
                    elif e == 9:
                        s = "Invalid Command"
                    else:
                        s = "Unknown Error"
                    self.fieldProbeError.emit(s)
                self.read_received = True
                if self.battery_flag:
                    self.fieldProbeError.emit("Battery below safe operting level.")
                    
                    