import time
import socketscpi
import threading
import ping3
from PyQt5.QtCore import QObject, pyqtSignal

class AgilentN5181A(QObject):
    instrument_connected = pyqtSignal(str)
    instrument_detected = pyqtSignal(bool)
    error_occured = pyqtSignal(str)
    current_power = pyqtSignal(float)
    current_frequency = pyqtSignal(float)
    
    def __init__(self, ip_address: str = '192.168.80.79',  port: int = 5024):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.sig_gen = None
        self.is_running = False
        self.power = 0.0
        self.frequency = 0.0
        self.new_command = False
        self.write_command: str = ':OUT:STAT OFF'
        self.read_command: str = '*IDN?'
    
    def detect(self):
        self.ping_started = True
        self.ping_thread = threading.Thread(target=self.check_static_ip)
        self.count = 4
        self.ping_thread.start()
        
    def retryDetection(self):
        self.count = 4
    
    def stopDetection(self):
        self.ping_started = False
        self.ping_thread.join()
        
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
        self.write_command = '*IDN?'
        self.read_command = '*IDN?'
        self.new_command = True
        
    def setFrequency(self, freq: int):
        self.write_command = f':FREQ {str(freq)} MHz'
        self.read_command = ':FREQ?'
        self.new_command = True
        
    def setPower(self, pow: int):
        self.write_command = f':POW {str(pow)} dBm'
        self.read_command = ':POW?'
        self.new_command = True
        
    def setAmpModOn(self, state: bool):
        self.write_command = f':OUTP:MOD:STAT {"ON" if state else "OFF"}'
        #TODO: ':AM:STAT ON' & 'OUTP:MOD:TYPE AM'
        self.read_command = 'OUTP:MOD:STAT?'
        self.new_command = True
        
    def setAmpModDepth(self, depth: int):
        self.write_command = f':AM:DEPT:LIN {str(depth)}'
        self.read_command = ':AM:STAT?'
        self.new_command = True
    
        # :SWE:DWELL
        # :LIST:TRIG:SOUR IMM
        # :SWE:GEN: STEP
        # :SWE:POIN <number of teps>
        # :SWE:SPAC LIN|LOG
        
    def startFrequencySweep(self, start: int, stop: int, steps: int, dwell: int):
        self.sweepThread = threading.Thread(target=self.sweepFrequency, args=(start, stop, steps, dwell))
        self.sweepThread.start()

    def sweepFrequency(self, start, stop, steps, dwell):
        traversal = start - stop
        step = traversal / steps
        dwell *= 0.001
        current = start
        while current <= stop:
            self.setFrequency(current)
            current += step
            time.sleep(dwell)
    
    def writeSCPI(self):
        while self.is_running:
            if self.new_command:
                self.sig_gen.write(self.write_command)
                done = self.sig_gen.query('*OPC?')
                print(str(done))
                state = self.sig_gen.query(self.read_command)
                if self.write_command[:4] == ':FRE':
                    self.current_frequency.emit(float(state))
                elif self.write_command[:4] == ':POW':
                    self.current_power.emit(float(state))
                elif self.write_command[:4] == '*IDN':
                    self.instrument_connected.emit(state)
                self.new_command = False
                
    def check_static_ip(self):
        while self.ping_started:
            try:
                response_time = ping3.ping(self.ip_address, timeout = 0.5)
                if response_time is not None and response_time:
                    if response_time:
                        self.instrument_detected.emit(True)
                else:
                    if (self.count == 0):
                        self.instrument_detected.emit(False)
                    else:
                        self.count -= 1
            except Exception as e:
                if (self.count == 0):
                        self.error_occured.emit(f'Network error occurred: {str(e)}')
                else:
                    self.count -= 1