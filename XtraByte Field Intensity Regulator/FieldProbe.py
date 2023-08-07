import serial
from serial import SerialException, SerialTimeoutException
import threading
from PyQt5.QtCore import QObject, pyqtSignal

class ETSLindgrenHI6006(QObject):
    fieldIntensityReceived = pyqtSignal(float, float, float, float)
    identityReceived = pyqtSignal(str, str, str)
    batteryReceived = pyqtSignal(int)
    temperatureReceived = pyqtSignal(float) 
    serialConnectionError = pyqtSignal(str)
    fieldProbeError = pyqtSignal(str)
    
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
                    
                    