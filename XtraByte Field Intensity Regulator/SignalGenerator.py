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
    ampModDepthReceived = pyqtSignal(float)
    rfOutStateReceived = pyqtSignal(bool)
    sweepFinished = pyqtSignal()
    
    def __init__(self, ip_address: str = '192.168.100.79',  port: int = 5024):
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
        self.connected = False
        self.ping_thread.start()
        
    def retryDetection(self):
        self.count = 4
    
    def stopDetection(self):
        self.ping_started = False
        self.ping_thread.join()
        
    def connect(self):
        self.is_running = True
        try:
            self.sig_gen = socketscpi.SocketInstrument(self.ip_address)
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
        
    def setFrequency(self, freq: float):
        suffix = 'MHz'
        if freq > 6000.0:
            freq = 6000.0
        if freq < 1:
            if freq < 0.1:
                freq = 0.1
            suffix = 'kHz'
        self.write_command = f':FREQ {str(freq)} {suffix}'
        self.read_command = ':FREQ?'
        self.new_command = True
        
    def setPower(self, pow: int):
        self.write_command = f':POW {str(pow)} dBm'
        self.read_command = ':POW?'
        self.new_command = True
        
    def setModulationType(self, am: bool):
        self.write_command = f':OUTP:MOD:TYPE {"AM" if am else "PM"}'
        #TODO: 'OUTP:MOD:STAT ON'
        self.read_command = ':OUTP:MOD:STAT?'
        self.new_command = True
        
    def setModulationState(self, on: bool):
        self.write_command = f':AM:STAT {"ON" if on else "OFF"}'
        self.read_command = ':AM:STAT?'
        self.new_command = True
        
    def setAmpModDepth(self, depth: float):
        self.write_command = f':AM:DEPT:LIN {str(depth)}'
        self.read_command = ':AM:STAT?'
        self.new_command = True
    
    def setRFOut(self, on: bool):
        self.write_command = f':OUTP:STAT {"ON" if on else "OFF"}'
        self.read_command = ':OUTP:STAT?'
        self.new_command = True
        # :SWE:DWELL
        # :LIST:TRIG:SOUR IMM
        # :SWE:GEN: STEP
        # :SWE:POIN <number of teps>
        # :SWE:SPAC LIN|LOG

    def clearErrors(self):
        try:
            self.sig_gen.err_check()
        except socketscpi.SockInstError as e:
            print(e)
            #self.error_occured.emit(e)

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
        self.sweepFinished.emit()
    
    def writeSCPI(self):
        while self.is_running:
            if self.new_command:
                self.sig_gen.write(self.write_command)
                done = self.sig_gen.query('*OPC?')
                print(str(done))
                state = self.sig_gen.query(self.read_command)
                self.new_command = False
                if self.write_command[:4] == ':FRE':
                    self.current_frequency.emit(float(state))
                elif self.write_command[:4] == ':POW':
                    self.current_power.emit(float(state))
                elif self.write_command[:4] == '*IDN':
                    self.instrument_connected.emit(state)
                elif self.write_command[:9] == ':OUTP:MOD':
                    self.setModulationState(True)
                elif self.write_command[:4] == ':AM:':
                    self.ampModDepthReceived.emit(float(state))
                elif self.write_command[:10] == ':OUTP:STAT':
                    self.rfOutStateReceived.emit(True if state == '1' else False)
                
    def check_static_ip(self):
        while self.ping_started:
            if not self.connected:
                try:
                    response_time = ping3.ping(self.ip_address, timeout = 0.5)
                    if response_time is not None and response_time:
                        if response_time:
                            self.instrument_detected.emit(True)
                            self.connected = True
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