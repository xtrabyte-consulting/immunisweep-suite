import time
import socketscpi
import threading
import queue
import ping3
from PyQt5.QtCore import QObject, pyqtSignal
from enum import Enum

class Modulation(Enum):
    AM = 1
    FM = 2
    PM = 3
    OFF = 0
    
class SCPI(Enum):
    On = 'ON'
    Off = 'OFF'
    MHz = 'MHz'
    kHz = 'kHz'
    dBm = 'dBm'
    Linear = 'LIN'
    Exponential = 'EXP'
    Internal = 'INT'
    External = 'EXT'
    AC = 'AC'
    DC = 'DC'
    RFOut = ':OUTP:STAT'
    Identity = '*IDN'
    Frequency = ':FREQ'
    Power = ':POW'
    AMState = ':AM:STAT'
    AMType = ':AM:TYPE'
    AMMode = ':AM:MODE'
    AMDepthStep = ':AM:DEPT:STEP'
    AMSource = ':AM:SOUR'
    AMCoupling = ':AM:EXT:COUP'
    AMFreq = ':AM:INT:FREQ'
    AMFreqStep = ':AM:INT:FREQ:STEP'
    AMLinDepth = ':AM:DEPT:LIN'
    AMExpDepth = ':AM:DEPT:EXP'
    FMState = ':FM:STAT'
    FMSource = ':FM:SOUR'
    FMCoupling = ':FM:EXT:COUP'
    FMFreq = ':FM:INT:FREQ' 
    FMStep = ':FM:INT:FREQ:STEP'
    PMState = ':PM:STAT'
    PMSource = ':PM:SOUR'
    PMBand = ':PM:BAND|BWID'
    PMCoupling = ':PM:EXT:COUP'
    PMFreq = ':PM:INT:FREQ'
    PMStep = ':PM:INT:FREQ:STEP'
    ModulationState = ':OUTP:MOD:STAT'
    OperationComplete = '*OPC?'
    Empty = ''
    Exit = 'Exit'

class AgilentN5181A(QObject):
    instrumentConnected = pyqtSignal(str)
    instrumentDetected = pyqtSignal(bool)
    error = pyqtSignal(str)
    modTypeSet = pyqtSignal(int, bool)
    modStateSet = pyqtSignal(bool)
    frequencySet = pyqtSignal(float)
    powerSet = pyqtSignal(float)
    amDepthSet = pyqtSignal(float)
    rfOutSet = pyqtSignal(bool)
    sweepFinished = pyqtSignal()
    
    def __init__(self, ip_address: str = '192.168.100.79',  port: int = 5024):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.instrument = None
        self.is_running = False
        self.power = 0.0
        self.frequency = 0.0
        self.commandQueue = queue.Queue()
        self.write_thread = None
        self.runSweep = False
        self.commandLock = threading.Lock()
    
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

    def stop(self):
        self.is_running = False
        self.commandQueue.put((SCPI.Exit, f'{SCPI.RFOut.value} {SCPI.Off.value}'))
        if self.write_thread:
            self.write_thread.join()
        
    def connect(self):
        self.is_running = True
        try:
            self.instrument = socketscpi.SocketInstrument(self.ip_address)
            self.instrumentConnected.emit(self.instrument.instId)
            print(f'Connected To: {self.instrument.instId}')
            self.write_thread = threading.Thread(target=self.writeSCPI)
            self.write_thread.start()
        except socketscpi.SockInstError as e:
            self.error.emit(str(e))
            print(f'Error on connect: {str(e)}')
            self.is_running = False
    
    def initInstrument(self):
        self.commandQueue.put((SCPI.Identity, ''))
        
    def setFrequency(self, freq: float):
        suffix = SCPI.MHz.value
        if freq > 6000.0:
            freq = 6000.0
        if freq < 1:
            if freq < 0.1:
                freq = 0.1
            suffix = SCPI.kHz.value
        self.commandQueue.put((SCPI.Frequency, f'{SCPI.Frequency.value} {str(freq)} {suffix}'))
        
    def setPower(self, pow: int):
        self.commandQueue.put((SCPI.Power, f'{SCPI.Power.value} {str(pow)} {SCPI.dBm.value}'))
    
    def setModulationType(self, mod):
        if mod == Modulation.AM:
            self.commandQueue.put((SCPI.PMState, f'{SCPI.PMState.value} {SCPI.Off.value}'))
            self.commandQueue.put((SCPI.FMState, f'{SCPI.FMState.value} {SCPI.Off.value}'))
            self.commandQueue.put((SCPI.AMState, f'{SCPI.AMState.value} {SCPI.On.value}'))
        elif mod == Modulation.FM:
            self.commandQueue.put((SCPI.PMState, f'{SCPI.PMState.value} {SCPI.Off.value}'))
            self.commandQueue.put((SCPI.AMState, f'{SCPI.AMState.value} {SCPI.Off.value}'))
            self.commandQueue.put((SCPI.FMState, f'{SCPI.FMState.value} {SCPI.On.value}'))
        elif mod == Modulation.PM:
            self.commandQueue.put((SCPI.FMState, f'{SCPI.FMState.value} {SCPI.Off.value}'))
            self.commandQueue.put((SCPI.AMState, f'{SCPI.AMState.value} {SCPI.Off.value}'))
            self.commandQueue.put((SCPI.PMState, f'{SCPI.PMState.value} {SCPI.On.value}'))
    
    # TODO: Ranges, coupling, normal/deep/high
    def setModulationState(self, on: bool):
        self.commandQueue.put((SCPI.ModulationState, f'{SCPI.ModulationState.value} {SCPI.On.value if on else SCPI.Off.value}'))
    
    def setAMSource(self, internal: bool):
        self.commandQueue.put((SCPI.AMSource, f'{SCPI.AMSource.value} {SCPI.Internal.value if internal else SCPI.External.value}'))
    
    def setAMCoupling(self, dc: bool):
        self.commandQueue.put((SCPI.AMCoupling, f'{SCPI.AMCoupling.value} {SCPI.DC.value if dc else SCPI.AC.value}'))
     
    def setAMType(self, linear: bool):
        self.commandQueue.put((SCPI.AMType, f'{SCPI.AMType.value} {SCPI.Linear.value if linear else SCPI.Exponential.value}'))
    
    def setAMLinearDepth(self, percent: float):
        self.commandQueue.put((SCPI.AMLinDepth, f'{SCPI.AMLinDepth.value} {str(percent)}'))
        
    def setAMExpDepth(self, depth: float):
        self.commandQueue.put((SCPI.AMExpDepth, f'{SCPI.AMExpDepth.value} {str(depth)}'))
        
    def setAMFrequency(self, freq: float):
        # Range: 0.1 -> 20 MHz
        if freq > 20000:
            freq = 20000
        elif freq < 0.0001:
            freq = 0.0001
        self.commandQueue.put((SCPI.AMFreq, f'{SCPI.AMFreq.value} {str(freq)} {SCPI.kHz.value}'))
        
    def setAMState(self, on: bool):
        self.commandQueue.put((SCPI.AMState, f'{SCPI.AMState.value} {SCPI.On.value if on else SCPI.Off.value}'))
        
    def setFMState(self, on: bool):
        self.commandQueue.put((SCPI.FMState, f'{SCPI.FMState.value} {SCPI.On.value if on else SCPI.Off.value}'))
    
    def setFMSource(self, internal: bool):
        self.commandQueue.put((SCPI.FMSource, f'{SCPI.FMSource.value} {SCPI.Internal.value if internal else SCPI.External.value}'))
 
    def setFMFrequency(self, freq: float, unit: str = SCPI.kHz.value):
        # Range: 0.1 Hz -> 2MHz
        self.commandQueue.put((SCPI.FMFreq, f'{SCPI.FMFreq.value} {str(freq)} {unit}'))
        
    def setFMStep(self, step: float):
        # Range: 0.5Hz - 1e6 Hz
        self.commandQueue.put((SCPI.FMStep, f'{SCPI.FMFreq.value} {str(step)}'))
    
    def setFMCoupling(self, dc: bool):
        self.commandQueue.put((SCPI.FMCoupling, f'{SCPI.FMCoupling.value} {SCPI.DC.value if dc else SCPI.AC.value}'))
        
    def setPMState(self, on: bool):
        self.commandQueue.put((SCPI.PMState, f'{SCPI.PMState.value} {SCPI.On.value if on else SCPI.Off.value}'))
    
    def setPMSource(self, internal: bool):
        self.commandQueue.put((SCPI.PMSource, f'{SCPI.PMSource.value} {SCPI.Internal.value if internal else SCPI.External.value}'))
 
    def setPMFrequency(self, freq: float, unit: str = SCPI.kHz.value):
        # Range: 0.1 Hz -> 2MHz
        self.commandQueue.put((SCPI.PMFreq, f'{SCPI.PMFreq.value} {str(freq)} {unit}'))
        
    def setPMStep(self, step: float):
        # Range: 0.5Hz - 1e6 Hz
        self.commandQueue.put((SCPI.PMStep, f'{SCPI.PMFreq.value} {str(step)}'))
    
    def setPMCoupling(self, dc: bool):
        self.commandQueue.put((SCPI.PMCoupling, f'{SCPI.PMCoupling.value} {SCPI.DC.value if dc else SCPI.AC.value}'))    
    
    def setPMBandwidth(self, normal: bool):
        self.deleteLater
    
    def setRFOut(self, on: bool):
        self.clearQueue()
        self.commandQueue.put((SCPI.RFOut, f'{SCPI.RFOut.value} {SCPI.On.value if on else SCPI.Off.value}'))
        
    def clearQueue(self):
        self.clearing = True
        while self.commandQueue.qsize() is not 0:
            self.commandQueue.get()

    def clearErrors(self):
        try:
            self.instrument.err_check()
        except socketscpi.SockInstError as e:
            print(e)
            #self.error_occured.emit(e)

    def startFrequencySweep(self, start: int, stop: int, steps: int, dwell: int, exp: bool):
        dwell *= 0.001
        if exp:
            self.sweepThread = threading.Thread(target=self.sweepExponential, args=(start, stop, steps, dwell))
        else:
            self.sweepThread = threading.Thread(target=self.sweepLinear, args=(start, stop, steps, dwell))
        self.runSweep = True
        self.sweepThread.start()
        
    def stopFrequencySweep(self):
        self.runSweep = False
        self.sweepThread.join()

    def sweepLinear(self, start, stop, steps, dwell):
        traversal = stop - start
        step = traversal / steps
        current = start
        while current <= stop and self.runSweep:
            self.setFrequency(current)
            current += step
            time.sleep(dwell)
        self.sweepFinished.emit()
        
    def sweepExponential(self, start, stop, steps, dwell):
        ratio = pow((stop / start), 1 / (steps - 1))
        current = start
        while current <= stop and self.runSweep:
            self.setFrequency(current)
            current *= ratio
            time.sleep(dwell)
        self.sweepFinished.emit()
    
    def writeSCPI(self):
        while self.is_running:
            # This will block until a command is availible
            if self.clearing:
                self.commandQueue.join()
            else:
                command = self.commandQueue.get()
                commandType = command[0]
                commandValue = command[1]
                if commandType == SCPI.Exit:
                    print('Exiting write thread')
                    break
                        
                self.instrument.write(commandValue)
                complete = self.instrument.query(SCPI.OperationComplete.value)
                
                state = self.instrument.query(f'{commandType.value}?')
                
                if commandType == SCPI.Identity: 
                    self.instrumentConnected.emit(state)
                elif commandType == SCPI.RFOut:
                    self.rfOutSet.emit(state == '1')
                elif commandType == SCPI.Power:
                    self.powerSet.emit(float(state))
                elif commandType == SCPI.Frequency:
                    self.frequencySet.emit(float(state))
                elif commandType == SCPI.ModulationState:
                    self.modStateSet.emit(state == '1')
                elif commandType == SCPI.AmpModState:
                    self.modTypeSet(Modulation.AM.value, state == '1')
                elif commandType == SCPI.AmpModDepth:
                    self.amDepthSet(float(state))
                elif commandType == SCPI.FreqModState:
                    self.modTypeSet(Modulation.FM.value, state == '1')
                elif commandType == SCPI.PhaseModState:
                    self.modTypeSet(Modulation.PM.value, state == '1')
                
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