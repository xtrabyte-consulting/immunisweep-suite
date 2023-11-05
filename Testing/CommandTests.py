from SignalGenerator import AgilentN5181A, Frequency, Modulation
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal


class CommandTest(QObject):
    
    def __init__(self, ipAdress = '192.168.100.79'):
        super(CommandTest, self).__init__()
        self.ipAdress = ipAdress
        self.agilent = AgilentN5181A(self.ipAdress, 5024)
        self.agilent.instrumentDetected.connect(self.on_intrumentDetected)
        self.agilent.instrumentConnected.connect(self.on_instrumentConnected)
        self.agilent.error.connect(self.on_error)
        self.agilent.modModeSet.connect(self.on_mod_mode_set)
        self.agilent.modStateSet.connect(self.on_mod_state_set)
        self.agilent.modSubStateSet.connect(self.on_mod_substate_set)
        self.agilent.modSourceSet.connect(self.on_mod_source_set)
        self.agilent.modFreqSet.connect(self.on_mod_freq_set)
        self.agilent.modCouplingSet.connect(self.on_mod_coupling_set)
        self.agilent.amTypeSet.connect(self.on_am_type_set)
        self.agilent.modDepthSet.connect(self.on_am_depth_set)
        self.agilent.frequencySet.connect(self.on_frequency_set)
        self.agilent.powerSet.connect(self.on_power_set)
        self.agilent.rfOutSet.connect(self.on_rf_out_set)
        self.agilent.sweepFinished.connect(self.on_sweep_finished)
        print('Testing is set up. Connecting...')
        self.agilent.connect()
        
    def resetIpAddress(self, address):
        self.ipAdress = address
        self.agilent = AgilentN5181A(self.ipAdress, 5024)
        self.agilent.detect()
    
    @pyqtSlot(bool)    
    def on_intrumentDetected(self, detected: bool):
        if detected:
            print("Instrument detected. Setting up communication...")
            self.agilent.stopDetection()
            self.agilent.connect()
        else:
            self.agilent.retryDetection()
            print(f"Instrument not found at: {self.ipAdress}. Retrying...")
    
    @pyqtSlot(str)
    def on_instrumentConnected(self, deviceID: str):
        print(f'Successfully set up communication with: {deviceID}')
        print(f'Running Test Sequence...')

        self.agilent.setRFOut(False)
        self.agilent.setFrequency(250, Frequency.MHz.value)
        self.agilent.setPower(-77)
        
        # Testing amplitude modulation settings
        self.agilent.setModulationType(Modulation.AM)
        self.agilent.setAMSource(True)
        self.agilent.setAMMode(True)
        self.agilent.setAMFrequency(2.0)
        self.agilent.setAMType(False)
        self.agilent.setAMExpDepth(-0.5)
        self.agilent.setAMType(True)
        self.agilent.setAMLinearDepth(50.0)
        self.agilent.setModulationState(True)
        self.agilent.setModulationState(False)
        self.agilent.setAMMode(False)
        self.agilent.setAMSource(False)
        self.agilent.setAMCoupling(True)
        self.agilent.setAMCoupling(False)
        
        # Testing Frequency Modulation Settings
        self.agilent.setModulationType(Modulation.FM)
        self.agilent.setFMSource(True)
        self.agilent.setFMFrequency(0.9, Frequency.MHz.value)
        self.agilent.setModulationState(True)
        self.agilent.setModulationState(False)
        self.agilent.setFMSource(False)
        self.agilent.setFMCoupling(True)
        self.agilent.setFMCoupling(False)
        
        # Testing Phase Modulation Settings
        self.agilent.setModulationType(Modulation.PM)
        self.agilent.setPMSource(True)
        self.agilent.setPMFrequency(400, Frequency.kHz.value)
        self.agilent.setPMBandwidth(True)
        self.agilent.setModulationState(True)
        self.agilent.setModulationState(False)
        self.agilent.setPMBandwidth(False)
        self.agilent.setPMSource(False)
        self.agilent.setPMCoupling(True)
        self.agilent.setPMCoupling(False)
    
    @pyqtSlot(str)
    def on_error(self, error_message: str):
        print(f"Error: {error_message}")

    @pyqtSlot(int, bool)
    def on_mod_mode_set(self, mod_type, state):
        print(f"Modulation {mod_type} mode set to deep/high: {state}")

    @pyqtSlot(bool)
    def on_mod_state_set(self, state):
        print(f"Modulation state set to {state}")

    @pyqtSlot(int, bool)
    def on_mod_substate_set(self, mod_type, state):
        print(f"Modulation {mod_type} state set to {state}")

    @pyqtSlot(int, bool)
    def on_mod_source_set(self, mod_type, source):
        print(f"Modulation {mod_type} source set to {source}")

    @pyqtSlot(int, float)
    def on_mod_freq_set(self, mod_type, freq):
        print(f"Modulation {mod_type} frequency set to {freq}")

    @pyqtSlot(int, bool)
    def on_mod_coupling_set(self, mod_type, state):
        print(f"Modulation {mod_type} coupling set to {state}")

    @pyqtSlot(bool)
    def on_am_type_set(self, am_type):
        print(f"AM type set to {'Linear' if am_type else 'Exponential'}")

    @pyqtSlot(float)
    def on_am_depth_set(self, depth):
        print(f"AM depth set to {depth}")

    @pyqtSlot(float)
    def on_frequency_set(self, freq):
        print(f"Frequency set to {freq}")

    @pyqtSlot(float)
    def on_power_set(self, power):
        print(f"Power set to {power}")

    @pyqtSlot(bool)
    def on_rf_out_set(self, state):
        print(f"RF Out set to {state}")

    @pyqtSlot()
    def on_sweep_finished(self):
        print("Sweep finished")        
        

if __name__ == '__main__':
    test = CommandTest()