import typing
import socketscpi
import threading
import ping3
from PyQt5.QtCore import QObject, pyqtSignal

class SignalGenerator(QObject):
    instrument_connected = pyqtSignal(str)
    instrument_detected = pyqtSignal(bool)
    error_occured = pyqtSignal(str)
    current_power = pyqtSignal(float)
    current_frequency = pyqtSignal(float)
    
    def __init__(self, ip_address: str = '192.168.1.7',  port: int = 23):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.sig_gen = None
        self.is_running = False
        self.power = 0.0
        self.frequency = 0.0
        self.new_command = False
        self.commands: list[str] = []
    
    def detect(self):
        self.deleteLater 
        
    def connect(self):
        self.is_running = True
        try:
            self.sig_gen = socketscpi.SocketInstrument(self.ip_address, port=self.port, timeout=5)
            self.instrument_connected.emit(self.sig_gen.instId)
            print(self.sig_gen.instId)
            self.write_thread = threading.Thread(target=self.writeSCPI)
            self.write_thread.start()
        except socketscpi.SockInstError as e:
            self.error_occured.emit(str(e))
            self.is_running = False
    
    def initInstrument(self):
        self.commands = ['*rst']
        self.new_command = True
        
    def setFreqSweep(self, start: str, stop: str):
        self.commands.clear()
        self.commands.append[f':FREQ:STAR {start};STOP {stop}']
        self.commands.append[':FREQ:MODE LIST']
        self.commands.append[':FREQ:SPAN 100 MHz']
        self.new_command = True
        #self.commands.append[f':FREQ:STOP {stop}']
    
    def setDwell(self, dwell):
        self.commands.append[':FREQ:SPAN 100 MHz']
        # :SWE:DWELL
        # :LIST:TRIG:SOUR IMM
        # :SWE:GEN: STEP
        # :SWE:POIN <number of teps>
        # :SWE:SPAC LIN|LOG

    # WE USING FASTTT
    def setFast(self, freq: int, power: int):
        self.commands.append(f':FAST:FP {freq}, {power}')


    def setPower(self, power: int):
        self.commands.append[f':POW {str(power)}DBM']
        self.commands.append[f':POW :STAR']
        self.new_command = True
    
    def writeSCPI(self):
        while self.is_running:
            if self.new_command:
                for command in self.commands:
                    self.sig_gen.write(command)
                    self.commands.remove(command)
                done = self.sig_gen.query('*OPC?')
                print(str(done))
                self.new_command = False
                
    def check_static_ip(self):
        while self.ping_started:
            try:
                response_time = ping3.ping(self.target_ip, timeout = 0.5)
                if response_time is not None and response_time:
                    if response_time:
                        self.network_online.emit(True)
                else:
                    if (self.count == 0):
                        self.network_online.emit(False)
                    else:
                        self.count -= 1
            except Exception as e:
                if (self.count == 0):
                        self.error_occured.emit(f'Network error occurred: {str(e)}')
                else:
                    self.count -= 1