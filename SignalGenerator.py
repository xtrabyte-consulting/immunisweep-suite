import time
import socketscpi
import socket
import threading
import queue
import ping3
import math
from PyQt5.QtCore import QObject, pyqtSignal
from enum import Enum

class Modulation(Enum):
    AM = 1
    FM = 2
    PM = 3
    OFF = 0
    
class Sweep(Enum):
    OFF = 0
    LINEAR = 1
    EXPONENTIAL = 2
    
class Frequency(Enum):
    Hz = 'Hz'
    kHz = 'kHz'
    MHz = 'MHz'
    GHz = 'GHz'
    
class Time(Enum):
    Microsecond = 'μs'
    Millisecond = 'ms'
    Second = 'sec'
    
class SCPI(Enum):
    On = 'ON'
    Off = 'OFF'
    dBm = 'dBm'
    Normal = 'NORM'
    Deep = 'DEEP'
    High = 'HIGH'
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

class SignalGenerator(QObject):
    instrumentConnected = pyqtSignal(str)
    instrumentDetected = pyqtSignal(bool)
    error = pyqtSignal(str)
    modModeSet = pyqtSignal(int, bool)
    modStateSet = pyqtSignal(bool)
    modSourceSet = pyqtSignal(bool)
    modSubStateSet = pyqtSignal(int, bool)
    modSourceSet = pyqtSignal(int, bool)
    modFreqSet = pyqtSignal(int, float)
    modCouplingSet = pyqtSignal(int, bool)
    amTypeSet = pyqtSignal(bool)
    modDepthSet = pyqtSignal(float)
    frequencySet = pyqtSignal(float)
    powerSet = pyqtSignal(float)
    rfOutSet = pyqtSignal(bool)
    sweepFinished = pyqtSignal()
    sweepStatus = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.instrument = None
        self.is_running = False
        self.power = 0.0
        self.frequency = 0.0
        self.runSweep = False
        self.sweepType = Sweep.OFF
        self.startFrequency = 100
        self.stopFrequency = 6000
        self.stepDwell = 0.1
        self.stepCount = 100
        self.clearing = False
        self.detected = False
        
    def detect(self):
        self.instrumentDetected.emit(True)
        self.detected = True
        
    def retryDetection(self):
        pass
    
    def stopDetection(self):
        pass
    
    def stop(self):
        self.is_running = False
        
    def connect(self):
        self.instrumentConnected.emit('Agilent N5181A')
        self.is_running = True
        self.clearing = False
        
    def initInstrument(self):
        self.instrumentConnected.emit('Agilent N5181A')
        
    def setFrequency(self, freq: float):
        self.frequencySet.emit(freq)
        
    def setFrequency(self, freq: float, unit: str):
        self.frequencySet.emit(freq)
        
    def setPower(self, pow: float):
        self.powerSet.emit(pow)
        
    def setModulationType(self, mod):
        if mod == Modulation.AM:
            self.modSubStateSet.emit(Modulation.AM.value, True)
            self.modSubStateSet.emit(Modulation.FM.value, False)
            self.modSubStateSet.emit(Modulation.PM.value, False)
        elif mod == Modulation.FM:
            self.modSubStateSet.emit(Modulation.AM.value, False)
            self.modSubStateSet.emit(Modulation.FM.value, True)
            self.modSubStateSet.emit(Modulation.PM.value, False)
        elif mod == Modulation.PM:
            self.modSubStateSet.emit(Modulation.AM.value, False)
            self.modSubStateSet.emit(Modulation.FM.value, False)
            self.modSubStateSet.emit(Modulation.PM.value, True)
            
    def setModulationState(self, on: bool):
        self.modStateSet.emit(on)
        
    def setAMSource(self, internal: bool):
        self.modSourceSet.emit(Modulation.AM.value, internal)
        
    def setAMMode(self, normal: bool):
        self.modModeSet.emit(Modulation.AM.value, normal)
        
    def setAMCoupling(self, dc: bool):
        self.modCouplingSet.emit(Modulation.AM.value, dc)
        
    def setAMType(self, linear: bool):
        self.amTypeSet.emit(linear)
        
    def setAMLinearDepth(self, percent: float):
        self.modDepthSet.emit(percent)
        
    def setAMExpDepth(self, depth: float):
        self.modDepthSet.emit(depth)
        
    def setAMFrequency(self, freq: float):
        self.modFreqSet.emit(Modulation.AM.value, freq)
        
    def setAMState(self, on: bool):
        self.modSubStateSet.emit(Modulation.AM.value, on)
        
    def setFMState(self, on: bool):
        self.modSubStateSet.emit(Modulation.FM.value, on)
        
    def setFMSource(self, internal: bool):
        self.modSourceSet.emit(Modulation.FM.value, internal)
        
    def setFMFrequency(self, freq: float, unit: str = Frequency.kHz.value):
        self.modFreqSet.emit(Modulation.FM.value, freq)
        
    def setFMStep(self, step: float):
        pass
    
    def setFMCoupling(self, dc: bool):
        self.modCouplingSet.emit(Modulation.FM.value, dc)
        
    def setPMState(self, on: bool):
        self.modSubStateSet.emit(Modulation.PM.value, on)
        
    def setPMSource(self, internal: bool):
        self.modSourceSet.emit(Modulation.PM.value, internal)
        
    def setPMFrequency(self, freq: float, unit: str = Frequency.kHz.value):
        self.modFreqSet.emit(Modulation.PM.value, freq)
        
    def setPMStep(self, step: float):
        pass
    
    def setPMCoupling(self, dc: bool):
        self.modCouplingSet.emit(Modulation.PM.value, dc)
        
    def setPMBandwidth(self, normal: bool):
        self.modModeSet.emit(Modulation.PM.value, normal)
        
    def setRFOut(self, on: bool):
        self.rfOutSet.emit(on)
        
    def clearQueue(self):
        pass
    
    def clearErrors(self):
        pass
    
    def setSweepType(self, exp: bool):
        if exp:
            self.sweepType = Sweep.EXPONENTIAL
        else:
            self.sweepType = Sweep.LINEAR
            
    def setStartFrequency(self, freq: float):
        self.startFrequency = freq
        
    def setStopFrequency(self, freq: float):
        self.stopFrequency = freq
        
    def setStepDwell(self, dwell: float, unit: str):
        if unit == Time.Microsecond.value:
            dwell *= 0.000001
        elif unit == Time.Millisecond.value:
            dwell *= 0.001
        self.stepDwell = dwell
        
    def setStepCount(self, count: int):
        self.stepCount = count
        
    def startFrequencySweep(self):
        self.startFrequencySweep(self.startFrequency, self.stopFrequency, self.stepCount, self.stepDwell, self.sweepType == Sweep.EXPONENTIAL)
        
    def startFrequencySweep(self, start: float, stop: float, steps: int, dwell: float, exp: bool):
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
            self.sweepStatus.emit((current - start) / (stop - start) * 100)
            time.sleep(dwell)
        self.sweepFinished.emit()
        
    def log_percentage(curr_val, min_val, max_val):
        normalized_curr = (math.log(curr_val) - math.log(min_val)) / (math.log(max_val) - math.log(min_val))
        return normalized_curr * 100
    
    def sweepExponential(self, start, stop, steps, dwell):
        ratio = pow((stop / start), 1 / (steps - 1))
        current = start
        while current <= stop and self.runSweep:
            self.setFrequency(current)
            current *= ratio
            self.sweepStatus.emit(self.log_percentage(current, start, stop))
            time.sleep(dwell)
        self.sweepFinished.emit()
    

class AgilentN5181A(QObject):
    instrumentConnected = pyqtSignal(str)
    instrumentDetected = pyqtSignal(bool)
    error = pyqtSignal(str)
    modModeSet = pyqtSignal(int, bool)
    modStateSet = pyqtSignal(bool)
    modSourceSet = pyqtSignal(bool)
    modSubStateSet = pyqtSignal(int, bool)
    modSourceSet = pyqtSignal(int, bool)
    modFreqSet = pyqtSignal(int, float)
    modCouplingSet = pyqtSignal(int, bool)
    amTypeSet = pyqtSignal(bool)
    modDepthSet = pyqtSignal(float)
    frequencySet = pyqtSignal(float)
    powerSet = pyqtSignal(float)
    rfOutSet = pyqtSignal(bool)
    sweepFinished = pyqtSignal()
    sweepStatus = pyqtSignal(float)
    
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
        self.sweepType = Sweep.OFF
        self.startFrequency = 100.0
        self.stopFrequency = 6000.0
        self.stepDwell = 0.5
        self.stepCount = 100
        self.clearing = False
        self.detected = False
        self.sweepTerm = 0.01
    
    def detect(self):
        print('Detecting.')
        self.ping_started = True
        self.ping_thread = threading.Thread(target=self.check_static_ip)
        self.count = 4
        print('Starting ping thread.')
        self.ping_thread.start()
        
    def retryDetection(self):
        self.count = 4
        self.ping_started = True
    
    def stopDetection(self):
        self.ping_started = False
        self.ping_thread.join()

    def stop(self):
        self.commandQueue.put((SCPI.Exit, f'{SCPI.RFOut.value} {SCPI.Off.value}'))
        self.is_running = False
        self.ping_started = False
        if self.ping_thread is not None and self.ping_thread.is_alive():
            self.ping_thread.join()
        if self.write_thread is not None and self.write_thread.is_alive():
            self.write_thread.join()
        
    def connect(self):
        try:
            self.instrument = socketscpi.SocketInstrument(self.ip_address)
            self.instrumentConnected.emit(self.instrument.instId)
            #print(f'Connected To: {self.instrument.instId}')
            self.write_thread = threading.Thread(target=self.writeSCPI)
            self.is_running = True
            self.clearing = False
            self.write_thread.start()
        except socketscpi.SockInstError as e:
            self.error.emit(str(e))
            print(f'Error on connect: {str(e)}')
            self.is_running = False
        except socket.timeout as e:
            self.error.emit(str(e))
            print(f'Socket Error: {str(e)}')
        except ConnectionRefusedError as e:
            self.error.emit(str(e))
            print(f'Error on connect: {str(e)}')
            self.is_running = False
        except:
            self.error.emit('Unknown Error')
            print('Unknown Error')
            self.is_running = False
    
    def initInstrument(self):
        self.commandQueue.put((SCPI.Identity, ''))
    
    #def setFrequency(self, freq: float):
        # Assume MHz
    #    self.setFrequency(self, freq, Frequency.MHz.value)
        
    def setFrequency(self, freq: float, unit: str):
        if unit == Frequency.GHz.value:
            if freq > 6.0:
                freq = 6.0
            if freq < 0.000000001:
                freq = 0.000000001
        if unit == Frequency.MHz.value:
            if freq > 6000.0:
                freq = 6000.0
            if freq < 0.1:
                    freq = 0.1
        if unit == Frequency.kHz.value:
            if freq > 6000000.0:
                freq = 6000000.0
            if freq < 100.0:
                freq = 100.0
        self.commandQueue.put((SCPI.Frequency, f'{SCPI.Frequency.value} {str(freq)} {unit}'))
        
    def setPower(self, pow: float):
        #print(f'Setting Power: {str(pow)}')
        if pow > 9.9:
            pow = 9.9
            self.error.emit("Power above amplifier maximum input. Setting to 9.9 dBm")
        self.commandQueue.put((SCPI.Power, f'{SCPI.Power.value} {str(round(pow, 3))} {SCPI.dBm.value}'))
    
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
        
    def setAMMode(self, normal: bool):
        self.commandQueue.put((SCPI.AMSource, f'{SCPI.AMMode.value} {SCPI.Normal.value if normal else SCPI.Deep.value}'))
    
    def setAMCoupling(self, dc: bool):
        self.commandQueue.put((SCPI.AMCoupling, f'{SCPI.AMCoupling.value} {SCPI.DC.value if dc else SCPI.AC.value}'))

    def setAMType(self, linear: bool):
        self.commandQueue.put((SCPI.AMType, f'{SCPI.AMType.value} {SCPI.Linear.value if linear else SCPI.Exponential.value}'))
    
    def setAMLinearDepth(self, percent: float):
        self.commandQueue.put((SCPI.AMLinDepth, f'{SCPI.AMLinDepth.value} {str(percent)}'))
        
    def setAMExpDepth(self, depth: float):
        self.commandQueue.put((SCPI.AMExpDepth, f'{SCPI.AMExpDepth.value} {str(depth)}'))
        
    def setAMFrequency(self, freq: float, unit: str):
        # Range: 0.1 -> 20 MHz
        if freq > 20000:
            freq = 20000
        if freq < 0.0001:
            freq = 0.0001
        self.commandQueue.put((SCPI.AMFreq, f'{SCPI.AMFreq.value} {str(freq)} {Frequency.kHz.value}'))
        
    def setAMState(self, on: bool):
        self.commandQueue.put((SCPI.AMState, f'{SCPI.AMState.value} {SCPI.On.value if on else SCPI.Off.value}'))
        
    def setFMState(self, on: bool):
        self.commandQueue.put((SCPI.FMState, f'{SCPI.FMState.value} {SCPI.On.value if on else SCPI.Off.value}'))
    
    def setFMSource(self, internal: bool):
        self.commandQueue.put((SCPI.FMSource, f'{SCPI.FMSource.value} {SCPI.Internal.value if internal else SCPI.External.value}'))

    def setFMFrequency(self, freq: float, unit: str = Frequency.kHz.value):
        # Range: 0.1 Hz -> 2MHz
        if unit == Frequency.MHz.value:
            if freq > 20:
                freq = 20
        elif unit == Frequency.Hz.value:
            if freq < 0.1:
                freq = 0.1
        elif unit == Frequency.kHz.value:
            if freq > 20000.0:
                freq = 20000.0
        else:
            unit = Frequency.kHz.value
            freq = 1
        self.commandQueue.put((SCPI.FMFreq, f'{SCPI.FMFreq.value} {str(freq)} {unit}'))
        
    def setFMStep(self, step: float):
        # Range: 0.5Hz - 1e6 Hz
        self.commandQueue.put((SCPI.FMStep, f'{SCPI.FMStep.value} {str(step)}'))
    
    def setFMCoupling(self, dc: bool):
        self.commandQueue.put((SCPI.FMCoupling, f'{SCPI.FMCoupling.value} {SCPI.DC.value if dc else SCPI.AC.value}'))
        
    def setPMState(self, on: bool):
        self.commandQueue.put((SCPI.PMState, f'{SCPI.PMState.value} {SCPI.On.value if on else SCPI.Off.value}'))
    
    def setPMSource(self, internal: bool):
        self.commandQueue.put((SCPI.PMSource, f'{SCPI.PMSource.value} {SCPI.Internal.value if internal else SCPI.External.value}'))
 
    def setPMFrequency(self, freq: float, unit: str = Frequency.kHz.value):
        # Range: 0.1 Hz -> 2MHz
        if unit == Frequency.MHz.value:
            if freq > 20:
                freq = 20
        elif unit == Frequency.Hz.value:
            if freq < 0.1:
                freq = 0.1
        else:
            unit = Frequency.kHz.value
            freq = 1
        self.commandQueue.put((SCPI.PMFreq, f'{SCPI.PMFreq.value} {str(freq)} {unit}'))
        
    def setPMStep(self, step: float):
        # Range: 0.5Hz - 1e6 Hz
        self.commandQueue.put((SCPI.PMStep, f'{SCPI.PMFreq.value} {str(step)}'))
    
    def setPMCoupling(self, dc: bool):
        self.commandQueue.put((SCPI.PMCoupling, f'{SCPI.PMCoupling.value} {SCPI.DC.value if dc else SCPI.AC.value}'))    
    
    def setPMBandwidth(self, normal: bool):
        self.commandQueue.put((SCPI.PMBand, f'{SCPI.PMBand.value} {SCPI.Normal.value if normal else SCPI.High.value}'))
    
    def setRFOut(self, on: bool):
        #self.clearQueue()
        self.commandQueue.put((SCPI.RFOut, f'{SCPI.RFOut.value} {SCPI.On.value if on else SCPI.Off.value}'))
        
    def clearQueue(self):
        self.clearing = True
        while self.commandQueue.qsize() != 0:
            self.commandQueue.get()

    def clearErrors(self):
        try:
            self.instrument.err_check()
        except socketscpi.SockInstError as e:
            print(e)
            #self.error_occured.emit(e)

    def setSweepType(self, exp: bool):
        if exp:
            self.sweepType = Sweep.EXPONENTIAL
        else:
            self.sweepType = Sweep.LINEAR
            
    def setStartFrequency(self, freq: float):
        # Convert to kHz
        self.startFrequency = freq * 1000
        
    def getStartFrequency(self) -> float:
        # Convert back to MHz
        return self.startFrequency / 1000 
        
    def setStopFrequency(self, freq: float):
        # Convert to kHz
        self.stopFrequency = freq * 1000
        
    def getStopFrequency(self) -> float:
        # Convert back to MHz
        return self.stopFrequency / 1000
    
    def getDefaultLogarithmicStepCount(self) -> int:
        steps = math.log(self.stopFrequency / self.startFrequency) / math.log(1.01)
        print(f'StartFreq: {self.startFrequency}, StopFreq: {self.stopFrequency}, steps: {steps}')
        self.stepCount = int(steps)
        return self.stepCount
    
    def setStepDwell(self, dwell: float, unit: str):
        # Convert to Sec
        if unit == Time.Microsecond.value:
            dwell *= 0.000001
        elif unit == Time.Millisecond.value:
            dwell *= 0.001
        self.stepDwell = dwell
        
    def setSweepTerm(self, term: float):
        self.sweepTerm = term
    
    def getStepCount(self) -> int:
        steps = math.log(self.stopFrequency / self.startFrequency) / math.log(1.0 + self.sweepTerm)
        self.stepCount = int(math.ceil(steps))
        return self.stepCount
    
    def getSweepTime(self) -> float:
        return self.stepDwell * self.getStepCount()
    
    def startFrequencySweep(self):
        self.sweepThread = threading.Thread(target=self.sweepExponential, args=(self.startFrequency, self.stopFrequency, self.sweepTerm, self.stepDwell))
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
            self.setFrequency(current, Frequency.kHz.value)
            current += step
            self.sweepStatus.emit((current - start) / (stop - start) * 100)
            time.sleep(dwell)
        self.sweepFinished.emit()
    

    def log_percentage(self, curr_val, min_val, max_val):
        normalized_curr = (math.log(curr_val) - math.log(min_val)) / (math.log(max_val) - math.log(min_val))
        return normalized_curr * 100
    
    def sweepExponential(self, start, stop, term, dwell):
        current = start
        print(f'Start: {start}, Ratio: {term}, Stop: {stop}')
        while current <= stop and self.runSweep:
            self.setFrequency(current, Frequency.kHz.value)
            current = current + (current * term)
            self.sweepStatus.emit(self.log_percentage(current, start, stop))
            time.sleep(dwell)
        self.sweepFinished.emit()
    
    def writeSCPI(self):
        print("Starting SCPI comms loop...")
        while self.is_running:
            # This will block until a command is availible
            if self.clearing:
                print("Blocking Loop until command Queue is empty.")
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
                #if complete:
                state = self.instrument.query(f'{commandType.value}?')
                if commandType == SCPI.Identity: 
                    self.instrumentConnected.emit(state)
                elif commandType == SCPI.RFOut:
                    self.rfOutSet.emit(bool(int(state)))
                elif commandType == SCPI.Power:
                    self.powerSet.emit(float(state))
                elif commandType == SCPI.Frequency:
                    self.frequencySet.emit(float(state))
                elif commandType == SCPI.ModulationState:
                    self.modStateSet.emit(bool(int(state)))
                elif commandType == SCPI.AMState:
                    self.modSubStateSet.emit(Modulation.AM.value, bool(int(state)))
                elif commandType == SCPI.AMType:
                    self.amTypeSet.emit(SCPI.Linear.value == state)
                elif commandType == SCPI.AMMode:
                    self.modModeSet.emit(Modulation.AM.value, SCPI.Normal.value == state)
                elif commandType == SCPI.AMSource:
                    self.modSourceSet.emit(Modulation.AM.value, SCPI.Internal.value == state)
                elif commandType == SCPI.AMLinDepth:
                    self.modDepthSet.emit(float(state))
                elif commandType == SCPI.AMExpDepth:
                    self.modDepthSet.emit(float(state))
                elif commandType == SCPI.AMCoupling:
                    self.modCouplingSet.emit(Modulation.AM.value, state == SCPI.AC.value)
                elif commandType == SCPI.AMFreq:
                    self.modFreqSet.emit(Modulation.AM.value, float(state))
                elif commandType == SCPI.FMState:
                    self.modSubStateSet.emit(Modulation.FM.value, bool(int(state)))
                elif commandType == SCPI.FMSource:
                    self.modSourceSet.emit(Modulation.FM.value, SCPI.Internal.value == state)
                elif commandType == SCPI.FMCoupling:
                    self.modCouplingSet(Modulation.FM.value, state == SCPI.AC.value)
                elif commandType == SCPI.FMFreq:
                    self.modFreqSet.emit(Modulation.FM.value, float(state))
                elif commandType == SCPI.PMState:
                    self.modSubStateSet.emit(Modulation.PM.value, bool(int(state)))
                elif commandType == SCPI.PMBand:
                    self.modModeSet.emit(Modulation.PM.value, SCPI.Normal.value == state)
                elif commandType == SCPI.PMSource:
                    self.modSourceSet.emit(Modulation.PM.value, SCPI.Internal.value == state)
                elif commandType == SCPI.PMCoupling:
                    self.modCouplingSet.emit(Modulation.PM.value, SCPI.AC.value == state)
                elif commandType == SCPI.PMFreq:
                    self.modFreqSet.emit(Modulation.PM.value, float(state))
    
                
    def check_static_ip(self):
        responded = False
        while self.ping_started and not responded:
            print('Ping started.')
            try:
                print('Pinging...')
                response_time = ping3.ping(self.ip_address, timeout = 0.5)
                print(f'Response: {str(response_time)}')
                if response_time is not None and response_time:
                    if response_time:
                        self.instrumentDetected.emit(True)
                        self.detected = True
                        responded = True
                    else:
                        print(str(response_time))
                else:
                    if (self.count == 0):
                        self.instrumentDetected.emit(False)
                    else:
                        self.count -= 1
            except Exception as e:
                print(f'Network Error {str(e)}')
                if (self.count == 0):
                        self.error.emit(f'Network error occurred: {str(e)}')
                else:
                    self.count -= 1