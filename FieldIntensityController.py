from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from qt_material import apply_stylesheet

from MainWindow import Ui_MainWindow
from SignalGenerator import AgilentN5181A, Time, Modulation, Frequency, SignalGenerator
from FieldProbe import ETSLindgrenHI6006, FieldProbe
from LivePlot import FrequencyPlot, PowerPlot

import os
import sys
import math
import time

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
        self.desired_field = 1.0
        self.current_field = 0.0
    
    def setGains(self, Kp: float, Ki: float, Kd: float):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
    
    def setTargetValue(self, setpoint: float):
        print(f"Desired field set to: {setpoint}")
        self.desired_field = setpoint
        
    def getTargetValue(self) -> float:
        return self.desired_field
    
    def calculate(self, current_field: float) -> float:
        error = self.desired_field - current_field
        self.integral += error
        derivative = error - self.prev_error
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)
        self.prev_error = error
        #print(f"Current Field: {current_field}, Error: {error}, Integral: {self.integral}, Derivative: {derivative}, Output: {output}")
        return output
    
    def clear(self):
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
        self.signalGenerator = AgilentN5181A()
        #self.signalGenerator = SignalGenerator()
        self.signalGenerator.instrumentDetected.connect(self.on_sigGen_instrumentDetected)
        self.signalGenerator.instrumentConnected.connect(self.on_sigGen_instrumentConnected)
        self.signalGenerator.frequencySet.connect(self.on_sigGen_frequencySet)
        self.signalGenerator.powerSet.connect(self.on_sigGen_powerSet)
        self.signalGenerator.error.connect(self.on_sigGen_error)
        self.signalGenerator.rfOutSet.connect(self.on_sigGen_rfOutSet)
        self.signalGenerator.sweepFinished.connect(self.on_sigGen_sweepFinished)
        self.signalGenerator.sweepStatus.connect(self.on_sigGen_sweepStatus)
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
        self.desiredFieldIntensity = 1.0
        self.xfieldIntensity = 0.0
        self.yfieldIntensity = 0.0
        self.zfieldIntensity = 0.0
        self.currentOutputPower = -10.0
        self.currentOutputFrequency = 100.0
        self.equipmentLimits = EquipmentLimits(0.1, 6000.0, 15.0)
        self.sweepStartTime = time.time()
        self.powerStartTime = time.time()
        
        
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
        self.pidController = PIDController(0.5, 1.0, 0.1)
        
        # Initiate Plots
        self.plot_widget = QWidget(self)
        self.frequency_plot_widget = FrequencyPlot(self.plot_widget, width=4, height=3, dpi=100)
        self.gridLayout_frequencyPlot.addWidget(self.frequency_plot_widget)
        
        self.power_plot_widget = QWidget(self)
        self.field_plot = PowerPlot(self.power_plot_widget, width=4, height=3, dpi=100)
        self.gridLayout_powerPlot.addWidget(self.field_plot)

        self.doubleSpinBox_sweepTerm.setValue(0.01)
        self.spinBox_startFreq.setValue(100.0)
        self.spinBox_stopFreq.setValue(1000.0)
        
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
        self.field_plot.rescale_plot(0.0, self.signalGenerator.getSweepTime(), 0.0, (self.pidController.getTargetValue() * 2.0))
    
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
            self.reset_sweep_plot_view()
            
    def on_spinBox_stopFreq_valueChanged(self, freq: float):
        valid = self.applyFrequencyLimits(float(freq))
        if valid:
            self.signalGenerator.setStopFrequency(float(freq))
            self.reset_sweep_plot_view()

    def on_spinBox_dwell_valueChanged(self, time: float):
        self.signalGenerator.setStepDwell(float(time), self.comboBox_dwellUnit.currentText())
        self.reset_sweep_plot_view()
            
    def on_comboBox_dwellUnit_activated(self):
        # Capture Spec Floor
        if self.comboBox_dwellUnit.currentText() == Time.Millisecond.value:
            if self.spinBox_dwell.value() < 0.00105:
                self.spinBox_dwell.setValue(0.00105)

    def on_spinBox_sweepTerm_valueChanged(self, term: float):
        print("Sweep Term: " + str(term))
        self.signalGenerator.setSweepTerm(float(term))
        self.reset_sweep_plot_view()
    
    def reset_sweep_plot_view(self):
        self.frequency_plot_widget.init_plot(0.0, self.signalGenerator.getSweepTime(), self.signalGenerator.getStartFrequency(), self.signalGenerator.getStopFrequency())
        self.field_plot.rescale_plot(0.0, self.signalGenerator.getSweepTime(), 0.0, (self.pidController.getTargetValue() * 2.0))
    
    def on_pushButton_startSweep_pressed(self):
        self.sweepStartTime = time.time()
        self.sweepOn = True
        self.signalGenerator.setRFOut(True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)  # Update every 100 ms
        self.toggleSweepUI(enabled=False)
        self.pushButton_pauseSweep.setEnabled(True)
        self.progressBar_freqSweep.setHidden(False)
        self.signalGenerator.startFrequencySweep()
        
    def on_pushButton_pauseSweep_pressed(self):
        self.signalGenerator.stopFrequencySweep()
        self.toggleSweepUI(enabled=True)
                
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
            self.pushButton_modulationOn.setEnabled(False)
            return
        self.label_validSettings.setText('Valid Settings')
        self.label_validSettings.setStyleSheet('color: green')
        self.pushButton_modulationOn.setEnabled(True)
        self.signalGenerator.setAMFrequency(freq)
        
    def pushButton_modulationState_pressed(self):
        sender = self.sender()
        on = sender == self.pushButton_modulationOn
        self.signalGenerator.setModulationState(on)
        
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

    @pyqtSlot(float, float, float, float)
    def on_fieldProbe_fieldIntensityReceived(self, x: float, y: float, z: float, composite: float):
        self.measuredFieldIntensity = composite
        self.updateFieldStrengthUI(x, y, z, composite)
        if self.outputOn:
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
        self.measuredFieldIntensity = composite
        self.xfieldIntensity = x
        self.yfieldIntensity = y
        self.zfieldIntensity = z
        
    def update_field_data_plot(self):
        self.field_plot.update_plot(time.time() - self.powerStartTime, setpoint = self.pidController.getTargetValue(), composite=self.measuredFieldIntensity, x=self.xfieldIntensity, y=self.yfieldIntensity, z=self.zfieldIntensity)
    
    def on_fieldProbe_batteryReceived(self, level: int):
        self.label_chargeLevel.setText(f'{str(level)} %')
        
    def on_fieldProbe_temperatureReceived(self, temp: float):
        self.label_temperature.setText(f'{str(temp)} °F')
    
    def on_fieldProbe_fieldProbeError(self, message: str):
        self.displayAlert(message)
        
    def on_fieldProbe_serialConnectionError(self, message: str):
        self.displayAlert(message)
    
    def on_sigGen_rfOutSet(self, on: bool):
        if on:
            self.outputOn = True
            self.pushButton_rfOn.setEnabled(False)
            self.pushButton_rfOff.setEnabled(True)
            pixmap = QPixmap('broadcast-on.png')
            scaledPixmap = pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            self.label_rfOutState.setPixmap(scaledPixmap)
            self.powerStartTime = time.time()
            self.field_timer = QTimer(self)
            self.field_timer.timeout.connect(self.update_field_data_plot)
            self.field_timer.start(100)  # Update every 100 ms
        else:
            self.outputOn = False
            self.pushButton_rfOn.setEnabled(True)
            self.pushButton_rfOff.setEnabled(False)
            pixmap = QPixmap('broadcast-off.png')
            scaledPixmap = pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
            self.label_rfOutState.setPixmap(scaledPixmap)
            self.field_timer.stop()
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
        pixmap = QPixmap('AgilentN5181A.png')
        scaledPixmap = pixmap.scaled(275, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_sigGen.setPixmap(scaledPixmap)
        # Initialize sig gen to match UI
        self.signalGenerator.setRFOut(False)
        self.signalGenerator.setModulationState(False)
        self.signalGenerator.setFrequency(100.0)
        self.signalGenerator.setPower(-10.0)
        
    def on_sigGen_frequencySet(self, frequency: float):
        frequency /= 1000000.0
        self.currentOutputFrequency = frequency
        self.lcdNumber_freqOut.display(round(frequency, 9))
        
    def update_data(self):
        t = time.time() - self.sweepStartTime
        print("Elapsed Time: " + str(t))
        self.frequency_plot_widget.update_plot(time.time() - self.sweepStartTime, self.currentOutputFrequency)
    
    def on_sigGen_powerSet(self, power: float):
        self.currentOutputPower = power
        self.lcdNumber_powerOut.display(power)
    
    def on_sigGen_sweepFinished(self):
        self.sweepRunning = False
        self.signalGenerator.setRFOut(False)
        self.toggleSweepUI(enabled=True)
        self.pushButton_startSweep.setEnabled(True)
        self.progressBar_freqSweep.setHidden(True)
        self.signalGenerator.stopFrequencySweep()
        
    def on_sigGen_sweepStatus(self, percent: float):
        self.lcdNumber_sweepProgress.display(percent)
        self.progressBar_freqSweep.setValue(int(percent))
        
    def on_sigGen_modStateSet(self, on: bool):
        self.pushButton_modulationOn.setEnabled(not on)
        self.pushButton_modulationOff.setEnabled(on)
        self.modulationOn = on
    
    def on_sigGen_modFrequencySet(self, modType: int, frequency: float):
        self.spinBox_modFreq.disconnect(self.spinBox_modFreq_valueChanged)
        self.spinBox_modFreq.setValue(frequency)
        self.spinBox_modFreq.valueChanged.connect(self.spinBox_modFreq_valueChanged)
    
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
        self.displayAlert(message)
    
    def disableSweepButtons(self, state: bool):
        self.freqStopBox.setDisabled(state)
        self.stepDwellBox.setDisabled(state)
        self.stepCountBox.setDisabled(state)
    
    def disableModButtons(self, state: bool):
        self.amDepthBox.setDisabled(state)
        self.amFreqBox.setDisabled(state)
    
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
            
    def calculateSweepStepCount(self, start: float, stop: float, term: float) -> int:
        freq_log = math.log(stop / start)
        term_log = math.log(1.0 + term)
        return int(math.ceil(freq_log / term_log))
    
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