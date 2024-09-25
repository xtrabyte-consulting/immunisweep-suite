from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from qt_material import apply_stylesheet

from MainWindow import Ui_MainWindow
from SignalGenerator import AgilentN5181A, Time, Modulation, Frequency, SignalGenerator
from FieldProbe import ETSLindgrenHI6006, FieldProbe
from Plots import PowerPlot

import os
import sys

import signal
from PyQt5.QtCore import QResource

CURRENT_DIR = os.path.curdir

try:
    # Include in try/except block if you're also targeting Mac/Linux
    from PyQt5.QtWinExtras import QtWin
    myappid = 'something.else' #'com.learnpyqt.minute-apps.paint'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)    
except ImportError:
    pass

class PIDController():
    
    def __init__(self, Kp, Ki, Kd):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_error = 0.0
        self.integral = 0.0
        self.desired_value = 0.0
        self.measured_value = 0.0
        
    def setMeasuredValue(self, actual: float):
        self.measured_value = actual
    
    def setTargetValue(self, setpoint: float):
        self.desired_value = setpoint
        
    def calculate(self) -> float:
        return self.calculate(self.desired_value, self.measured_value)
        
    def calculate(self, current_field: float) -> float:
        return self.calculate(self.desired_value, current_field)
        
    def calculate(self, desired_field: float, current_field: float) -> float:
        error = desired_field - current_field
        self.integral += error
        derivative = error - self.prev_error

        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative

        self.prev_error = error

        return output
    
    def clear(self):
        self.desired_value = 0.0
        self.measured_value = 0.0
        self.prev_error = 0.0
        self.integral = 0.0

class EquipmentLimits():
    
    def __init__(self, min_freq: float, max_freq: float, max_power: float):
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.max_power = max_power
        
    def setMinFrequency(self, freq: float):
        self.min_freq = freq
            
    def setMaxFrequency(self, freq: float):
        self.max_freq = freq
            
    def setMaxPower(self, power: float):
        self.max_power = power

class MainWindow(QMainWindow, Ui_MainWindow):
    
    sweepOn = False
    modulationOn = False
    rfOutOn = False
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('XtraByte Field Controller')
        
        # Field Probe Signal -> Slot Connections
        self.fieldProbe = ETSLindgrenHI6006()
        #self.fieldProbe = FieldProbe()
        self.fieldProbe.fieldIntensityReceived.connect(self.on_fieldProbe_fieldIntensityReceived)
        self.fieldProbe.identityReceived.connect(self.on_fieldProbe_identityReceived)
        self.fieldProbe.batteryReceived.connect(self.on_fieldProbe_batteryReceived)
        self.fieldProbe.temperatureReceived.connect(self.on_fieldProbe_temperatureReceived)
        self.fieldProbe.serialConnectionError.connect(self.on_fieldProbe_serialConnectionError)
        self.fieldProbe.fieldProbeError.connect(self.on_fieldProbe_fieldProbeError)
        
        # Signal Generator Signal -> Slot Connections
        self.signalGenerator = AgilentN5181A('192.168.100.79', 5024)
        #self.signalGenerator = SignalGenerator()
        self.signalGenerator.instrumentDetected.connect(self.on_sigGen_instrumentDetected)
        self.signalGenerator.instrumentConnected.connect(self.on_sigGen_instrumentConnected)
        self.signalGenerator.frequencySet.connect(self.on_sigGen_frequencySet)
        self.signalGenerator.powerSet.connect(self.on_sigGen_powerSet)
        self.signalGenerator.error.connect(self.on_sigGen_error)
        self.signalGenerator.rfOutSet.connect(self.on_sigGen_rfOutSet)
        self.signalGenerator.sweepFinished.connect(self.on_sigGen_sweepFinished)
        self.signalGenerator.sweepStatus.connect(self.on_sigGen_sweepStatus)
        self.signalGenerator.modModeSet.connect(self.on_sigGen_modModeSet)
        self.signalGenerator.modCouplingSet.connect(self.on_sigGen_modCouplingSet)
        self.signalGenerator.modSourceSet.connect(self.on_sigGen_modSourceSet)
        self.signalGenerator.modStateSet.connect(self.on_sigGen_modStateSet)
        self.signalGenerator.modFreqSet.connect(self.on_sigGen_modFrequencySet)
        self.signalGenerator.amTypeSet.connect(self.on_sigGen_amTypeSet)
        self.signalGenerator.modSubStateSet.connect(self.on_sigGen_modSubStateSet)
        self.signalGenerator.modDepthSet.connect(self.on_sigGen_modDepthSet)
        
        # Initialize State
        self.sweepRunning = False
        self.outputOn = False
        self.modulationOn = False
        self.measuredFieldIntensity = 0.0
        self.desiredFieldIntensity = 0.0
        self.currentOutputPower = 0.0
        self.currentOutputFrequency = 30.0
        self.equipmentLimits = EquipmentLimits(0.1, 6000.0, 10.0)
        
        
        ### UI Input and Control Signal -> Slot Connections
        # Device detection
        self.pushButton_detectSigGen.pressed.connect(self.on_pushButton_detectSigGen_pressed)
        self.pushButton_detectFieldProbe.pressed.connect(self.on_pushButton_detectFieldProbe_pressed)
        
        # Output Power/State Control
        self.spinBox_targetStrength.setRange(0, 10)
        self.spinBox_targetStrength.valueChanged.connect(self.on_spinBox_targetStrength_valueChanged)
        self.pushButton_rfOn.pressed.connect(self.on_pushButton_rfState_pressed)
        self.pushButton_rfOff.pressed.connect(self.on_pushButton_rfState_pressed)
        
        # Output Frequency Control

        self.spinBox_startFreq.valueChanged[float].connect(self.on_spinBox_startFreq_valueChanged)
        self.spinBox_stopFreq.valueChanged[float].connect(self.on_spinBox_stopFreq_valueChanged)
        self.spinBox_dwell.valueChanged.connect(self.on_spinBox_dwell_valueChanged)
        self.comboBox_dwellUnit.activated.connect(self.on_comboBox_dwellUnit_activated)
        self.doubleSpinBox_sweepTerm.valueChanged.connect(self.on_spinBox_sweepTerm_valueChanged)
        self.pushButton_startSweep.pressed.connect(self.on_pushButton_startSweep_pressed)
        self.pushButton_pauseSweep.pressed.connect(self.on_pushButton_pauseSweep_pressed)
        
        # Output Modulation Control
        self.spinBox_modDepth.valueChanged[float].connect(self.spinBox_modDepth_valueChanged)
        self.spinBox_modFreq.valueChanged.connect(self.spinBox_modFreq_valueChanged)
        self.pushButton_modulationOff.pressed.connect(self.pushButton_modulationState_pressed)
        self.pushButton_modulationOn.pressed.connect(self.pushButton_modulationState_pressed)
        
        # Amplifier and Antenna Selections
        self.comboBox_amplifier.currentIndexChanged[str].connect(self.on_comboBox_amplifier_activated)
        self.comboBox_antenna.currentIndexChanged[str].connect(self.on_comboBox_antenna_activated)
        
        # Closed-Loop Power Control
        self.pidController = PIDController(1.0, 1.0, 0.5)
        
        # Initiate Plots
        self.intensityPlot = PowerPlot()
        self.graphicsView_powerAndField.setScene(self.intensityPlot)
        self.frequencyPlot = PowerPlot(title="Frequency", labels={'left': "Frequency (dBm)", 'bottom': 'Time (sec)'})
        self.graphicsView_frequencySweep.setScene(self.frequencyPlot)
        
        # Other UI Setup
        self.pushButton_pauseSweep.setEnabled(False)
        pixmap = QPixmap('broadcast-off.png')
        scaledPixmap = pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_rfOutState.setPixmap(scaledPixmap)
        # self.label_rfOutState.setText('RF Off') TODO: Add RF State Label
        pixmap = QPixmap('thermometer.png')
        scaledPixmap = pixmap.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_temperatureTitle.setPixmap(scaledPixmap)
        pixmap = QPixmap('battery.png')
        scaledPixmap = pixmap.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_chargeTitle.setPixmap(scaledPixmap)
        self.progressBar_freqSweep.setValue(0)
        self.progressBar_freqSweep.setHidden(True)
        
        self.startDeviceDetection()
        
    def startDeviceDetection(self):
        self.alerted = False
        self.signalGenerator.detect()
        self.fieldProbe.start()
        
    def on_pushButton_detectSigGen_pressed(self):
        self.signalGenerator.detect()
        
    def on_pushButton_detectFieldProbe_pressed(self):
        self.fieldProbe.start()
        
    def on_comboBox_amplifier_activated(self, amplifier: str):
        print(f"Amplifier Selected: {amplifier}")
        if amplifier == 'AR 25A250AMB':
            self.equipmentLimits.setMaxPower(0.0)
            self.equipmentLimits.setMinFrequency(1.0)
            self.equipmentLimits.setMaxFrequency(300.0)
            self.label_amplifierStats.setText('Min Freq: 1 MHz\nMax Freq: 300 MHz\nPower In: 0 dBm')
        elif amplifier == 'IFI SMX25':
            self.equipmentLimits.setMaxPower(0.0)
            self.equipmentLimits.setMinFrequency(300.0)
            self.equipmentLimits.setMaxFrequency(1000.0)
            self.label_amplifierStats.setText('Min Freq: 300 MHz\nMax Freq: 1000 MHz\nPower In: 0 dBm')
        elif amplifier == 'IFI S3110':
            self.equipmentLimits.setMaxPower(0.0)
            self.equipmentLimits.setMinFrequency(800.0)
            self.equipmentLimits.setMaxFrequency(3000.0)
            self.label_amplifierStats.setText('Min Freq: 800 MHz\nMax Freq: 3000 MHz\nPower In: 0 dBm')
        elif amplifier == 'MC ZVE8G':
            self.equipmentLimits.setMaxPower(0.0)
            self.equipmentLimits.setMinFrequency(2000.0)
            self.equipmentLimits.setMaxFrequency(8000.0)
            self.label_amplifierStats.setText('Min Freq: 2000 MHz\nMax Freq: 8000 MHz\nPower In: 0 dBm')
            
    def on_comboBox_antenna_activated(self, antenna: str):
        print(f"Antenna Selected: {antenna}")
        if antenna == 'ETS 3143B':
            self.equipmentLimits.setMinFrequency(30.0)
            self.equipmentLimits.setMaxFrequency(3000.0)
            self.label_antennaStats.setText('Min Freq: 30 MHz\nMax Freq: 3000 MHz')
        elif antenna == 'EMCO 3155':
            self.equipmentLimits.setMinFrequency(1000.0)
            self.equipmentLimits.setMaxFrequency(18000.0)
            self.label_antennaStats.setText('Min Freq: 1 GHz\nMax Freq: 18 GHz')
                
    def on_spinBox_targetStrength_valueChanged(self, target):
        print(f"Spin box value changed: {target}")
        self.pidController.setTargetValue(float(target))
    
    def on_pushButton_rfState_pressed(self):
        sender = self.sender()
        if sender == self.pushButton_rfOff:
            self.signalGenerator.setRFOut(False)
        elif sender == self.pushButton_rfOn:
            self.signalGenerator.setRFOut(True)
    
    def on_connectFieldProbeButton_pressed(self):
        self.fieldProbe.start()

    def on_connectSigGenButton_pressed(self):
        self.signalGenerator.retryDetection()
        
    def on_radioButton_sweepType_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_linSweep:
                self.toggleSweepUI(enabled=True)
                self.sweepOn = True
                self.signalGenerator.setSweepType(False)
            elif sender == self.radioButton_logSweep:
                # TODO: Logic to get sig gen to calculate steps with 1% jump spec
                self.toggleSweepUI(enabled=True)
                self.sweepOn = True
                self.signalGenerator.setSweepType(True)
            elif sender == self.radioButton_sweepOff:
                self.toggleSweepUI(enabled=False)
                self.sweepOn = False
                
    def toggleSweepUI(self, enabled: bool):
        self.spinBox_startFreq.setEnabled(enabled)
        self.spinBox_stopFreq.setEnabled(enabled)
        self.spinBox_dwell.setEnabled(enabled)
        self.pushButton_startSweep.setEnabled(enabled)
    
    def applyFrequencyLimits(self, freq: float) -> bool:
        print(f"Frequency: {freq}, Type: {type(freq)}, ")
        if freq < self.equipmentLimits.min_freq:
            self.label_validSettings.setText('Invalid Setting: Frequency Too Low')
            self.label_validSettings.setStyleSheet('color: red')
            self.pushButton_startSweep.setEnabled(False)
            self.pushButton_rfOn.setEnabled(False)
            valid = False
        elif freq > self.equipmentLimits.max_freq:
            self.label_validSettings.setText('Invalid Setting: Frequency Too High')
            self.label_validSettings.setStyleSheet('color: red')
            self.pushButton_startSweep.setEnabled(False)
            self.pushButton_rfOn.setEnabled(False)
            valid = False
        else:
            self.label_validSettings.setText('Valid Settings')
            self.label_validSettings.setStyleSheet('color: green')
            self.pushButton_startSweep.setEnabled(True)
            self.pushButton_rfOn.setEnabled(True)
            valid = True
        return valid
                
    def on_spinBox_startFreq_valueChanged(self, freq: float):
        print(f"Spin box value changed: Types: {type(freq)}")
        valid = self.applyFrequencyLimits(float(freq))
        if valid:
            self.signalGenerator.setStartFrequency(float(freq))
            
        
    def on_spinBox_stopFreq_valueChanged(self, freq: float):
        valid = self.applyFrequencyLimits(float(freq))
        if valid:
            self.signalGenerator.setStopFrequency(float(freq))

    def on_spinBox_dwell_valueChanged(self, time: float):
        self.signalGenerator.setStepDwell(float(time), self.comboBox_dwellUnit.currentText())
            
    def on_comboBox_dwellUnit_activated(self):
        # Capture Spec Floor
        if self.comboBox_dwellUnit.currentText() == Time.Millisecond.value:
            if self.spinBox_dwell.value() < 0.00105:
                self.spinBox_dwell.setValue(0.00105)

    def on_spinBox_sweepTerm_valueChanged(self, term: float):
        print("Sweep Term: " + str(term))
        self.signalGenerator.setSweepTerm(float(term))
    
    def on_pushButton_startSweep_pressed(self):
        self.sweepOn = True
        self.signalGenerator.setRFOut(True)
        self.fieldProbe.setFieldUpdates(False)
        self.fieldProbe.setUpdateInterval(2.0)
        self.fieldProbe.getFieldStrengthMeasurement()
        self.toggleSweepUI(enabled=False)
        self.pushButton_pauseSweep.setEnabled(True)
        self.progressBar_freqSweep.setHidden(False)
        
    def on_pushButton_pauseSweep_pressed(self):
        self.fieldProbe.setFieldUpdates(True)
        self.fieldProbe.setUpdateInterval(0.5)
        self.signalGenerator.stopFrequencySweep()
        
    def on_radioButton_modType_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            self.radioButton_amState.disconnect()
            self.radioButton_fmState.disconnect()
            self.radioButton_pmState.disconnect()
            if sender == self.radioButton_amState:
                self.modulationType = Modulation.AM
                self.signalGenerator.setModulationType(Modulation.AM)
                self.toggleModControlTypeUI(Modulation.AM)
            elif sender == self.radioButton_fmState:
                self.modulationType = Modulation.FM
                self.signalGenerator.setModulationType(Modulation.FM)
                self.toggleModControlTypeUI(Modulation.FM)
            elif sender == self.radioButton_pmState:
                self.modulationType = Modulation.PM
                self.signalGenerator.setModulationType(Modulation.PM)
                self.toggleModControlTypeUI(Modulation.PM)
            self.radioButton_amState.toggled.connect(self.on_radioButton_modType_toggled)
            self.radioButton_fmState.toggled.connect(self.on_radioButton_modType_toggled)
            self.radioButton_pmState.toggled.connect(self.on_radioButton_modType_toggled)
                
    def on_radioButton_source_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_intSource:
                self.toggleModSourceUI(internal=True)
                self.setCurrentModSource(internal=True)
            elif sender == self.radioButton_extSource:
                self.toggleModSourceUI(internal=False)
                self.setCurrentModSource(internal=False)
                
    def on_radioButton_coupling_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_acCoupling:
                if self.modulationType == Modulation.AM and self.radioButton_intSource.isChecked():
                    self.signalGenerator.setAMType(True)
                    self.comboBox_depthDevUnit.setCurrentText('%')
                else:
                    self.setCurrentModCoupling(False)
            elif sender == self.radioButton_acdcCoupling:
                if self.modulationType == Modulation.AM and self.radioButton_intSource.isChecked():
                    self.signalGenerator.setAMType(False)
                    self.comboBox_depthDevUnit.setCurrentText('dBm')
                else:
                    self.setCurrentModCoupling(True)
                
    def on_radioButton_modMode_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_basicMode:
                self.setCurrentModMode(True)
            elif sender == self.radioButton_deepHighMode:
                self.setCurrentModMode(False)
                
    def spinBox_modDepth_valueChanged(self, percent: float):
        self.signalGenerator.setAMLinearDepth(float(percent))
    
    def applyModFrequencyUnits(self, freq: float, unit: str) -> (float, str):
        if unit == Frequency.Hz.value:
            if freq < 0.1:
                freq = 0.1
            elif freq > 1000.0:
                freq /= 1000.0
                unit = Frequency.kHz.value
        elif unit == Frequency.kHz.value:
            if freq > 10000.0:
                freq /= 1000.0
                unit = Frequency.MHz.value
            elif freq < 0.1:
                freq *= 1000.0
                unit = Frequency.Hz.value
        elif unit == Frequency.MHz.value:
            if freq > 20.0:
                freq = 20.0
            elif freq < 0.1:
                freq *= 1000.0
                unit = Frequency.kHz.value
        else:
            freq = 1.0
            unit = Frequency.kHz.value
        return float(freq), str(unit)
    
    def spinBox_modFreq_valueChanged(self, freq: float):
        if freq > 20000.0 or freq < 0.0001:
            self.label_validSettings.setText('Invalid AM Frequency Setting')
            self.label_validSettings.setStyleSheet('color: red')
            return
        self.label_validSettings.setText('Valid Settings')
        self.label_validSettings.setStyleSheet('color: green')
        self.signalGenerator.setAMFrequency(freq)
        
    def pushButton_modulationState_pressed(self):
        sender = self.sender()
        on = sender == self.pushButton_modulationOn
        self.signalGenerator.setModulationState(on)
        #TODO: Move To Signal
        self.pushButton_modulationOff.setEnabled(on)
        self.pushButton_modulationOn.setEnabled(not on)
        
    def setCurrentModMode(self, normal: bool):
        if self.modulationType == Modulation.AM:
            self.signalGenerator.setAMMode(normal)
        elif self.modulationType == Modulation.PM:
            self.signalGenerator.setPMBandwidth(normal)

    def setCurrentModCoupling(self, dc: bool):
        # TODO: Refactor into SignalGenerator Class
        if self.modulationType == Modulation.AM:
            self.signalGenerator.setAMCoupling(dc)
        elif self.modulationType == Modulation.FM:
            self.signalGenerator.setFMCoupling(dc)
        elif self.modulationType == Modulation.PM:
            self.signalGenerator.setPMCoupling(dc)
    
    def setCurrentModSource(self, internal: bool):
        # TODO: Refactor into SignalGenerator Class
        if self.modulationType == Modulation.AM:
            self.signalGenerator.setAMSource(internal)
        elif self.modulationType == Modulation.FM:
            self.signalGenerator.setFMSource(internal)
        elif self.modulationType == Modulation.PM:
            self.signalGenerator.setPMSource(internal)
    
    def toggleModSourceUI(self, internal: bool):
        self.radioButton_deepHighMode.setEnabled(internal)
        self.radioButton_basicMode.setEnabled(internal)
        self.spinBox_depthDev.setEnabled(internal)
        self.comboBox_depthDevUnit.setEnabled(internal)
        self.spinBox_modFreq.setEnabled(internal)
        self.comboBox_modFreqUnit.setEnabled(internal)
        if internal:
            if self.modulationType == Modulation.AM:
                self.label_couplingTypeTitle.setText('AM Type')
                self.radioButton_acCoupling.setText('Linear')
                self.radioButton_acCoupling.setEnabled(True)
                self.radioButton_acCoupling.setChecked(True)
                self.radioButton_acdcCoupling.setText('Exponential')
                self.radioButton_acdcCoupling.setEnabled(True)
            else:
                self.label_couplingTypeTitle.setText('Exteneral Coupling')
                self.radioButton_acCoupling.setText('AC Only')
                self.radioButton_acCoupling.setEnabled(False)
                self.radioButton_acdcCoupling.setText('AC/DC')
                self.radioButton_acdcCoupling.setEnabled(False)
        else:
            self.label_couplingTypeTitle.setText('Exteneral Coupling')
            self.radioButton_acCoupling.setText('AC Only')
            self.radioButton_acCoupling.setEnabled(True)
            self.radioButton_acdcCoupling.setText('AC/DC')
            self.radioButton_acdcCoupling.setEnabled(True)
        
    def toggleModControlTypeUI(self, modType: Modulation):
        self.radioButton_intSource.setChecked(True)
        if modType == Modulation.AM:
            self.label_couplingTypeTitle.setText('Mode')
            self.radioButton_acCoupling.setText('Linear')
            self.radioButton_acCoupling.setEnabled(True)
            self.radioButton_acCoupling.setChecked(True)
            self.radioButton_acdcCoupling.setText('Exp')
            self.radioButton_acdcCoupling.setEnabled(True)
            self.label_ampmMode.setText('Am Type')
            self.radioButton_deepHighMode.setHidden(False)
            self.radioButton_deepHighMode.setText('Deep')
            self.radioButton_basicMode.setEnabled(True)
            self.radioButton_deepHighMode.setEnabled(True)
            self.radioButton_basicMode.setChecked(True)
            self.label_amDepthFPMDev.setText('Depth')
            self.comboBox_depthDevUnit.clear()
            self.comboBox_depthDevUnit.addItems(['%', 'dBm'])
            self.comboBox_depthDevUnit.setCurrentText('%')
        elif modType == Modulation.FM:
            self.radioButton_deepHighMode.setText('High')
            self.label_amDepthFPMDev.setText('Deviation')
            self.label_couplingTypeTitle.setText('Mode')
            self.radioButton_acCoupling.setText('AC Only')
            self.radioButton_acdcCoupling.setText('AC/DC')
            self.radioButton_acCoupling.setEnabled(False)
            self.radioButton_acdcCoupling.setEnabled(False)
            self.comboBox_depthDevUnit.clear()
            self.comboBox_depthDevUnit.addItems([Frequency.Hz.value, Frequency.kHz.value, Frequency.MHz.value])
            self.comboBox_depthDevUnit.setCurrentText(Frequency.kHz.value)
            self.label_ampmMode.setText('Coupling')
            #self.radioButton_deepHighMode.setHidden(True)
            self.radioButton_basicMode.setEnabled(False)
            self.radioButton_deepHighMode.setEnabled(False)
        elif modType == Modulation.PM:
            self.label_amDepthFPMDev.setText('Deviation')
            self.label_couplingTypeTitle.setText('Mode')
            self.radioButton_acCoupling.setText('AC Only')
            self.radioButton_acdcCoupling.setText('AC/DC')
            self.radioButton_acCoupling.setEnabled(False)
            self.radioButton_acdcCoupling.setEnabled(False)
            self.comboBox_depthDevUnit.clear()
            self.comboBox_depthDevUnit.addItems(['Rad', 'Deg'])
            self.comboBox_depthDevUnit.setCurrentText('Deg')
            self.label_ampmMode.setText('Coupling')
            self.radioButton_deepHighMode.setText('High')
            self.radioButton_deepHighMode.setHidden(False)
            self.radioButton_basicMode.setEnabled(True)
            self.radioButton_basicMode.setChecked(True)
            self.radioButton_deepHighMode.setEnabled(True)       
        
    def displayAlert(self, text):
        self.alert = QMessageBox()
        self.alert.setText(text)
        self.alert.exec()
    
    @pyqtSlot(str, str, str, str)
    def on_fieldProbe_identityReceived(self, model: str, revision: str, serial: str, calibration: str):
        self.pushButton_detectFieldProbe.hide()
        pixmap = QPixmap('HI-6006.png')
        scaledPixmap = pixmap.scaled(275, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_fieldProbe.setPixmap(scaledPixmap)
        self.label_fieldProbeName.setText('ETS Lindgren ' + model + ' Serial: ' + serial)
        self.fieldProbe.getFieldStrengthMeasurement()
        self.fieldProbe.beginBatTempUpdates(0.5)

    @pyqtSlot(float, float, float, float)
    def on_fieldProbe_fieldIntensityReceived(self, x: float, y: float, z: float, composite: float):
        self.measuredFieldIntensity = composite
        self.updateFieldStrengthUI(x, y, z, composite)
        if self.sweepOn or self.outputOn:
            output = self.pidController.calculate(composite)
            #print("PID Out: " + str(output))
            if output > self.equipmentLimits.max_power:
                output = self.equipmentLimits.max_power
                self.label_validSettings.setText('Attempted Invalid Power Setting')
                self.label_validSettings.setStyleSheet('color: red')
            else:
                self.label_validSettings.setText('Valid Settings')
                self.label_validSettings.setStyleSheet('color: green')
            if output < -110:
                output = -110
            self.signalGenerator.setPower(output)
    
    def updateFieldStrengthUI(self, x: float, y: float, z: float, composite: float):
        self.lcdNumber_avgStrength.display(composite)
        self.lcdNumber_xMag.display(x)
        self.lcdNumber_yMag.display(y)
        self.lcdNumber_zMag.display(z)
        # TODO: Plot on different lines
        self.intensityPlot.plotData(QTime.currentTime(), composite)
        self.intensityPlot.plotData(QTime.currentTime(), x)
        self.intensityPlot.plotData(QTime.currentTime(), y)
        self.intensityPlot.plotData(QTime.currentTime(), z)
    
    def on_fieldProbe_batteryReceived(self, level: int):
        print(f"Probe Charge Level: {str(level)}")
        self.label_chargeLevel.setText(f'{str(level)} %')
        
    def on_fieldProbe_temperatureReceived(self, temp: float):
        print(f"Probe Temp Receievd: {str(temp)}")
        self.label_temperature.setText(f'{str(temp)} °F')
    
    def on_fieldProbe_fieldProbeError(self, message: str):
        print(f"Probe Error: {message}")
        self.displayAlert(message)
        
    def on_fieldProbe_serialConnectionError(self, message: str):
        print(f"Serial Error: {message}")
        self.displayAlert(message)
    
    def on_sigGen_rfOutSet(self, on: bool):
        if on:
            print('RF On')
            self.pushButton_rfOn.setEnabled(False)
            self.pushButton_rfOff.setEnabled(True)
            pixmap = QPixmap('broadcast-on.png')
            scaledPixmap = pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            self.label_rfOutState.setPixmap(scaledPixmap)
            self.rfOutOn = True
            self.outputOn = True
            if self.sweepOn:
                self.signalGenerator.startFrequencySweep()
                self.sweepRunning = True
        else:
            print("RF Off")
            self.pushButton_rfOn.setEnabled(True)
            self.pushButton_rfOff.setEnabled(False)
            pixmap = QPixmap('broadcast-off.png')
            scaledPixmap = pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            self.label_rfOutState.setPixmap(scaledPixmap)
            self.rfOutOn = False
            self.outputOn = False
            if self.sweepOn and self.sweepRunning:
                self.signalGenerator.stopFrequencySweep()
                self.sweepRunning = False
        self.pidController.clear()
    
    def on_sigGen_instrumentDetected(self, detected: bool):
        if detected:
            self.signalGenerator.stopDetection()
            self.signalGenerator.connect()
        else:
            self.signalGenerator.retryDetection()
            if not self.alerted:
                self.displayAlert("Signal Generator Disconnected. Please connect via LAN.")
                self.alerted = True        
    
    def on_sigGen_instrumentConnected(self, message: str):
        self.pushButton_detectSigGen.hide()
        identity = message.split(',')
        company = identity[0]
        model = identity[1]
        serial = identity[2]
        self.label_sigGenName.setText(company + ' ' + model + ' Serial: ' + serial)
        #self.label_sigGenName.setText(''.join(message.split(',')))
        pixmap = QPixmap('AgilentN5181A.png')
        scaledPixmap = pixmap.scaled(275, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_sigGen.setPixmap(scaledPixmap)
        
    def on_sigGen_frequencySet(self, frequency: float):
        frequency /= 1000000.0
        self.frequencyPlot.plotData(QTime.currentTime(), frequency)
        self.lcdNumber_freqOut.display(round(frequency, 9))
    
    def on_sigGen_powerSet(self, power: float):
        self.currentOutputPower = power
        self.lcdNumber_powerOut.display(power)
        self.intensityPlot.plotData(QTime.currentTime(), power)
        self.fieldProbe.getFieldStrengthMeasurement()
    
    def on_sigGen_sweepFinished(self):
        self.sweepRunning = False
        self.signalGenerator.setRFOut(False)
        self.fieldProbe.setFieldUpdates(True)
        self.fieldProbe.setUpdateInterval(0.5)
        self.toggleSweepUI(enabled=True)
        self.pushButton_startSweep.setEnabled(True)
        self.progressBar_freqSweep.setHidden(True)
        
    def on_sigGen_sweepStatus(self, percent: float):
        self.lcdNumber_sweepProgress.display(percent)
        self.progressBar_freqSweep.setValue(int(percent))
        
    def on_sigGen_modStateSet(self, on: bool):
        self.pushButton_modulationOn.setEnabled(not on)
        self.pushButton_modulationOff.setEnabled(on)
        self.modulationOn = on
        
    def on_sigGen_modModeSet(self, modType: int, state: bool):
        '''Feedback is the same for all modulation modes'''
        pass
    
    @pyqtSlot(int, bool)            
    def on_sigGen_modCouplingSet(self, modType: int, state: bool):
        if modType == Modulation.AM.value:
            self.label_modulationType.setText('Amplitude Modulation')
            if state:
                self.label_modulationCoupling.setText('External AC')
            else:
                self.label_modulationCoupling.setText('External AC/DC')
        elif modType == Modulation.FM.value:
            self.label_modulationType.setText('Frequency Modulation')
            if state:
                self.label_modulationCoupling.setText('External AC')
            else:
                self.label_modulationCoupling.setText('External AC/DC')
        elif modType == Modulation.PM.value:
            self.label_modulationType.setText('Phase Modulation')
            if state:
                self.label_modulationCoupling.setText('External AC')
            else:
                self.ç.setText('External AC/DC')
                
    @pyqtSlot(int, bool)
    def on_sigGen_modSourceSet(self, modType: int, state: bool):
        if modType == self.modulationType.value:
            if state:
                self.label_modulationCoupling.setText('Internal')
                self.label_modulationState.setHidden(False)
            else:
                self.label_modulationCoupling.setText('External AC')
                self.label_modulationState.setHidden(True)
    
    def on_sigGen_modFrequencySet(self, modType: int, frequency: float):
        self.spinBox_modFreq.disconnect(self.spinBox_modFreq_valueChanged)
        self.spinBox_modFreq.setValue(frequency)
        self.spinBox_modFreq.valueChanged.connect(self.spinBox_modFreq_valueChanged)
            
    def on_sigGen_modSubStateSet(self, modType: int, state: bool):
        if state:
            if self.modulationOn:
                self.label_modulationState.setText('On')
            if modType == Modulation.AM.value:
                self.label_modulationType.setText('Amplitude Modulation')
                self.modulationType = Modulation.AM
            elif modType == Modulation.FM.value:
                self.label_modulationType.setText('Frequency Modulation')
                self.modulationType = Modulation.FM
            elif modType == Modulation.PM.value:
                self.label_modulationType.setText('Phase Modulation')
                self.modulationType = Modulation.PM
                
    def on_sigGen_modDepthSet(self, depth: float):
        self.spinBox_modDepth.disconnect(self.spinBox_modDepth_valueChanged)
        self.spinBox_modDepth.setValue(depth)
        self.spinBox_modDepth.valueChanged.connect(self.spinBox_modDepth_valueChanged)
        
    def on_sigGen_amTypeSet(self, linear: bool):
        if linear:
            self.label_modUnit.setText('%')
        else:
            self.label_modUnit.setText('dBm')
        
    def on_sigGen_error(self, message: str):
        print(message)
        self.displayAlert(message)
    
    def disableSweepButtons(self, state: bool):
        self.freqStopBox.setDisabled(state)
        self.stepDwellBox.setDisabled(state)
        self.stepCountBox.setDisabled(state)
    
    def disableModButtons(self, state: bool):
        self.amDepthBox.setDisabled(state)
        self.amFreqBox.setDisabled(state)
    
    def on_linearSweepButton_toggled(self):
        if self.linearSweepButton.isChecked():
            self.sweepOn = True
            self.disableSweepButtons(False)
        else:
            self.sweepOn = False
            self.disableSweepButtons(True)
            
    def on_expSweepButton_toggled(self):
        if self.expSweepButton.isChecked():
            self.sweepOn = True
            self.disableSweepButtons(False)
        else:
            self.sweepOn = False
            self.disableSweepButtons(True)
    
    def on_sweepOffButton_toggled(self):
        if self.sweepOffButton.isChecked():
            self.sweepOn = False
            self.disableSweepButtons(True)
        else:
            self.sweepOn = True
            self.disableSweepButtons(False)
        
    def on_ampModButton_toggled(self):
        if self.ampModButton.isChecked():
            self.modulationOn = True
            self.disableModButtons(False)
            self.signalGenerator.setModulationType(True)
        else:
            self.modulationOn = False
            self.disableModButtons(True)
            self.signalGenerator.setModulationState(False)
            
    def on_phaseModButton_toggled(self):
        if self.phaseModButton.isChecked():
            self.modulationOn = True
            self.disableModButtons(False)
            self.signalGenerator.setModulationType(False)
        else:
            self.modulationOn = False
            self.disableModButtons(True)
            self.signalGenerator.setModulationState(False)
            
    def on_modOffButton_toggled(self):
        if self.modOffButton.isChecked():
            self.modulationOn = False
            self.disableModButtons(True)
            self.signalGenerator.setModulationState(False)
        else:
            self.modulationOn = True
            self.disableModButtons(False)
            self.signalGenerator.setModulationState(True)
            
    def closeEvent(self, event):
        self.fieldProbe.stop()
        self.signalGenerator.stop()
        del self.fieldProbe
        del self.signalGenerator
        QApplication.quit()
        sys.exit()

        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    #app.setWindowIcon(QtGui.QIcon(':/icons/field_controller.ico'))
    window = MainWindow()
    
    apply_stylesheet(app, theme='dark_cyan.xml')
    window.show()
    #app.aboutToQuit(window.killThreads())
    signal.signal(signal.SIGINT, window.closeEvent)
    sys.exit(app.exec_())