from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from PyQt5 import QtGui, QtWidgets, QtCore

from PyQt5.QtGui import QPainter, QBitmap, QPolygon, QPen, QBrush, QColor
from PyQt5.QtCore import Qt

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

from MainWindow import Ui_MainWindow
from SignalGenerator import AgilentN5181A, Time, Modulation, Frequency
from FieldProbe import ETSLindgrenHI6006
from Plots import PowerPlot

import os
import sys

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

class MainWindow(QMainWindow, Ui_MainWindow):
    
    sweepOn = True
    modulationOn = False
    rfOutOn = False
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('XtraByte Field Controller')
        
        # Field Probe Signal -> Slot Connections
        self.fieldProbe = ETSLindgrenHI6006('COM5')
        self.fieldProbe.fieldIntensityReceived.connect(self.on_fieldProbe_fieldIntensityReceived)
        self.fieldProbe.identityReceived.connect(self.on_fieldProbe_identityReceived)
        self.fieldProbe.batteryReceived.connect(self.on_fieldProbe_batteryReceived)
        self.fieldProbe.temperatureReceived.connect(self.on_fieldProbe_temperatureReceived)
        self.fieldProbe.serialConnectionError.connect(self.on_fieldProbe_serialConnectionError)
        self.fieldProbe.fieldProbeError.connect(self.on_fieldProbe_fieldProbeError)
        
        # Signal Generator Signal -> Slot Connections
        self.signalGenerator = AgilentN5181A('192.168.100.79', 5024)
        self.signalGenerator.instrumentDetected.connect(self.on_sigGen_instrumentDetected)
        self.signalGenerator.instrumentConnected.connect(self.on_sigGen_instrumentConnected)
        self.signalGenerator.frequencySet.connect(self.on_sigGen_frequencySet)
        self.signalGenerator.powerSet.connect(self.on_sigGen_powerSet)
        self.signalGenerator.error.connect(self.on_sigGen_error)
        self.signalGenerator.rfOutSet.connect(self.on_sigGen_rfOutSet)
        self.signalGenerator.sweepFinished.connect(self.on_sigGen_sweepFinished)
        
        ### UI Input and Control Signal -> Slot Connections
        # Device detection
        self.pushButton_detectSigGen.pressed.connect(self.on_pushButton_detectSigGen_pressed)
        self.pushButton_detectFieldProbe.pressed.connect(self.on_pushButton_detectFieldProbe_pressed)
        
        # Output Power/State Control
        self.powerControlButtonGroup = QButtonGroup()
        self.powerControlButtonGroup.addButton(self.radioButton_pidControl)
        self.powerControlButtonGroup.addButton(self.radioButton_staticPower)
        self.radioButton_pidControl.toggled.connect(self.on_radioButton_powerControl_toggled)
        self.radioButton_staticPower.toggled.connect(self.on_radioButton_powerControl_toggled)
        self.spinBox_targetStrength.valueChanged.connect(self.on_spinBox_targetStrength_valueChanged)
        self.pushButton_rfOn.pressed.connect(self.on_pushButton_rfState_pressed)
        self.pushButton_rfOff.pressed.connect(self.on_pushButton_rfState_pressed)
        
        # Output Frequency Control
        self.freqSweepGroup = QButtonGroup()
        self.freqSweepGroup.addButton(self.radioButton_sweepOff)
        self.freqSweepGroup.addButton(self.radioButton_logSweep)
        self.freqSweepGroup.addButton(self.radioButton_linSweep)
        self.radioButton_linSweep.toggled.connect(self.on_radioButton_sweepType_toggled)
        self.radioButton_logSweep.toggled.connect(self.on_radioButton_sweepType_toggled)
        self.radioButton_sweepOff.toggled.connect(self.on_radioButton_sweepType_toggled)
        self.spinBox_startFreq.valueChanged.connect(self.on_spinBox_startFreq_valueChanged)
        self.comboBox_startFreqUnit.activated.connect(self.on_comboBox_startFreqUnit_activated)
        self.spinBox_stopFreq.valueChanged.connect(self.on_spinBox_stopFreq_valueChanged)
        self.comboBox_stopFreqUnit.activated.connect(self.on_comboBox_stopFreqUnit_activated)
        self.spinBox_dwell.valueChanged.connect(self.on_spinBox_dwell_valueChanged)
        self.comboBox_dwellUnit.activated.connect(self.on_comboBox_dwellUnit_activated)
        self.spinBox_stepCount.valueChanged.connect(self.on_spinBox_stepCount_valueChanged)
        self.pushButton_startSweep.pressed.connect(self.on_pushButton_startSweep_pressed)
        self.pushButton_pauseSweep.pressed.connect(self.on_pushButton_pauseSweep_pressed)
        
        # Output Modulation Control
        self.modGroup = QButtonGroup()
        self.modGroup.addButton(self.radioButton_amState) 
        self.modGroup.addButton(self.radioButton_fmState)
        self.modGroup.addButton(self.radioButton_pmState)
        self.radioButton_amState.toggled.connect(self.on_radioButton_modType_toggled)
        self.radioButton_fmState.toggled.connect(self.on_radioButton_modType_toggled)
        self.radioButton_pmState.toggled.connect(self.on_radioButton_modType_toggled)
        self.sourceGroup = QButtonGroup()
        self.sourceGroup.addButton(self.radioButton_intSource)
        self.sourceGroup.addButton(self.radioButton_extSource)
        self.radioButton_intSource.toggled.connect(self.on_radioButton_source_toggled)
        self.radioButton_extSource.toggled.connect(self.on_radioButton_source_toggled)
        self.couplingGroup = QButtonGroup()
        self.couplingGroup.addButton(self.radioButton_acCoupling)
        self.couplingGroup.addButton(self.radioButton_acdcCoupling)
        self.radioButton_acCoupling.toggled.connect(self.on_radioButton_coupling_toggled)
        self.radioButton_acdcCoupling.toggled.connect(self.on_radioButton_coupling_toggled)
        self.modeGroup = QButtonGroup()
        self.modeGroup.addButton(self.radioButton_basicMode)
        self.modeGroup.addButton(self.radioButton_deepHighMode) #TODO: Change Deep/High Text
        self.radioButton_basicMode.toggled.connect(self.on_radioButton_modMode_toggled)
        self.radioButton_deepHighMode.toggled.connect(self.on_radioButton_modMode_toggled)
        self.spinBox_depthDev.valueChanged.connect(self.spinBox_depthDev_valueChanged)
        self.comboBox_depthDevUnit.activated.connect(self.comboBox_depthDevUnit_activated)
        self.spinBox_modFreq.valueChanged.connect(self.spinBox_modFreq_valueChanged)
        self.comboBox_modFreqUnit.activated.connect(self.comboBox_modFreqUnit_activated)
        self.pushButton_modulationOff.pressed.connect(self.pushButton_modulationState_pressed)
        self.pushButton_modulationOn.pressed.connect(self.pushButton_modulationState_pressed)
        
        # Closed-Loop Power Control
        self.pidController = PIDController(1.0, 1.0, 0.5)
        
        # Initiate Plots
        self.intensityPlot = PowerPlot()
        self.topGraphicsView.setScene(self.intensityPlot)
        self.frequencyPlot = PowerPlot(title="Frquency", labels={'left': "Frquency (dBm)", 'bottom': 'Time (sec)'})
        self.bottomGraphicsView.setScene(self.frequencyPlot)
        
        # Initialize State
        self.powerControl = True
        self.sweepRunning = False
        self.ouputOn = False
        self.modulationOn = False
        self.modulationType = Modulation.AM
        self.internalModulation = True
        self.measuredFiedldIntensity = 0.0
        self.desiredFieldIntensity = 0.0
        self.currentOutputPower = 0.0
        
        self.startDeviceDetection()
        
    def startDeviceDetection(self):
        self.alerted = False
        self.signalGenerator.detect()
        self.fieldProbe.start()
    
    def killThreads(self):
        self.fieldProbe.stop()
        #self.signalGenerator.stopDetection()
        self.signalGenerator.stop()
        
    def on_pushButton_detectSigGen_pressed(self):
        self.signalGenerator.detect()
        
    def on_pushButton_detectFieldProbe_pressed(self):
        self.fieldProbe.start()
        
    def on_radioButton_powerControl_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_pidControl:
                self.powerControl = True
                self.label_desiredFieldTitle.setText("Target RMS Field Strength")
                self.label_strengthUnit.setText("V/m")
                self.spinBox_targetStrength.setValue(self.measuredFieldIntensity)
                self.desiredFieldIntensity = self.measuredFieldIntensity
                self.pidController.clear()
                self.pidController.setMeasuredValue(self.measuredFieldIntensity)
                self.pidController.setTargetValue(self.desiredFieldIntensity)
            elif sender == self.radioButton_staticPower:
                self.powerControl = False
                self.label_desiredFieldTitle.setText("Output Power")
                self.label_strengthUnit.setText("dBm")
                self.spinBox_targetStrength.setValue(self.currentOutputPower)
                self.pidController.clear()
                
    def on_spinBox_targetStrength_valueChanged(self, target):
        if self.powerControl:
            self.pidController.setTargetValue(float(target))
        else:
            self.signalGenerator.setPower(float(target))
        
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
        if enabled:
            self.label_startFreq.setText('Start Frequency')
        else:
            self.label_startFreq.setText('Frequency')
        self.spinBox_stopFreq.setEnabled(enabled)
        self.spinBox_dwell.setEnabled(enabled)
        self.comboBox_stopFreqUnit.setEnabled(enabled)
        self.comboBox_dwellUnit.setEnabled(enabled)
        self.spinBox_stepCount.setEnabled(enabled)
        self.pushButton_startSweep.setEnabled(enabled)
                
    def on_spinBox_startFreq_valueChanged(self, freq: float):
        if self.sweepOn:
            self.signalGenerator.setStartFrequency(float(freq), self.comboBox_startFreqUnit.currentText())
        else:
            self.signalGenerator.setFrequency(float(freq), self.comboBox_startFreqUnit.currentText())
            
    def on_comboBox_startFreqUnit_activated(self):
        # Could handle some multiplication here
        # Lets keep a unified current freq value based out sig gen return value
        self.deleteLater
        
    def on_spinBox_stopFreq_valueChanged(self, freq: float):
        if self.sweepOn:
            self.signalGenerator.setStopFrequency(float(freq), self.comboBox_stopFreqUnit.currentText())
            
    def on_comboBox_stopFreqUnit_activated(self):
        # Could handle some multiplication here
        # Lets keep a unified current freq value based out sig gen return value
        self.deleteLater
        
    def on_spinBox_dwell_valueChanged(self, time: float):
        if self.sweepOn:
            self.signalGenerator.setStepDwell(float(time), self.comboBox_dwellUnit.currentText())
            
    def on_comboBox_dwellUnit_activated(self):
        # Capture Spec Floor
        if self.comboBox_dwellUnit.currentText() == Time.Microsecond.value:
            if self.spinBox_dwell.value() < 1.05:
                self.spinBox_dwell.setValue(1.05)

    def on_spinBox_stepCount_valueChanged(self, steps: int):
        if self.sweepOn:
            self.signalGenerator.setStepCount(steps)
    
    def on_pushButton_startSweep_pressed(self):
        self.signalGenerator.startFrequencySweep()
        self.toggleSweepUI(enabled=False)
        self.pushButton_pauseSweep.setEnabled(True)
        
    def on_pushButton_pauseSweep_pressed(self):
        self.signalGenerator.stopFrequencySweep()
        
    def on_radioButton_modType_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_amState:
                self.modulationType = Modulation.AM
                self.signalGenerator.setPMState(False)
                self.signalGenerator.setFMState(False)
                self.signalGenerator.setAMState(True)
                self.toggleModControlTypeUI(am=True)
            elif sender == self.radioButton_fmState:
                self.modulationType = Modulation.FM
                self.signalGenerator.setPMState(False)
                self.signalGenerator.setAMState(False)
                self.signalGenerator.setFMState(True)
                self.toggleModControlTypeUI(am=False)
                self.comboBox_depthDevUnit.clear()
                self.comboBox_depthDevUnit.addItems([Frequency.Hz, Frequency.kHz, Frequency.MHz])
            elif sender == self.radioButton_pmState:
                self.modulationType = Modulation.PM
                self.signalGenerator.setFMState(False)
                self.signalGenerator.setAMState(False)
                self.signalGenerator.setPMState(True)
                self.toggleModControlTypeUI(am=False)
                self.comboBox_depthDevUnit.clear()
                self.comboBox_depthDevUnit.addItems(['Rad', 'Deg', 'PiRad'])
                self.label_ampmMode.setText('Bandwidth Mode')
                
    def on_radioButton_source_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_intSource:
                self.internalModulation = True
                self.toggleModSourceUI(internal=True)
                self.setCurrentModSource(internal=True)
            elif sender == self.radioButton_extSource:
                self.internalModulation = False
                self.toggleModSourceUI(internal=False)
                self.setCurrentModSource(internal=False)
                
    def on_radioButton_coupling_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_acCoupling:
                if self.modulationType == Modulation.AM and self.internalModulation:
                    self.signalGenerator.setAMType(True)
                    self.comboBox_depthDevUnit.clear()
                    self.comboBox_depthDevUnit.addItems(['%'])
                else:
                    self.setCurrentModCoupling(False)
            elif sender == self.radioButton_acdcCoupling:
                if self.modulationType == Modulation.AM and self.internalModulation:
                    self.signalGenerator.setAMType(False)
                    self.comboBox_depthDevUnit.clear()
                    self.comboBox_depthDevUnit.addItems(['dBm'])
                else:
                    self.setCurrentModCoupling(True)
                
    def on_radioButton_modMode_toggled(self):
        sender = self.sender()
        if sender.isChecked():
            if sender == self.radioButton_basicMode:
                self.setCurrentModMode(True)
            elif sender == self.radioButton_deepHighMode:
                self.setCurrentModMode(False)
                
    def spinBox_depthDev_valueChanged(self, depthOrDev: float):
        if self.modulationType == Modulation.AM:
            if self.radioButton_acCoupling.isChecked():
                self.signalGenerator.setAMLinearDepth(depthOrDev)
            else:
                self.signalGenerator.setAMExpDepth(depthOrDev)
        elif self.modulationType == Modulation.FM:
            self.signalGenerator.setFMStep(depthOrDev)
        elif self.modulationType == Modulation.PM:
            self.signalGenerator.setPMStep(depthOrDev)
        
    def comboBox_depthDevUnit_activated(self):
        #TODO
        self.deleteLater
    
    def spinBox_modFreq_valueChanged(self, freq: float):
        if self.modulationType == Modulation.AM:
            self.signalGenerator.setAMFrequency(freq)
        elif self.modulationType == Modulation.FM:
            self.signalGenerator.setFMFrequency(freq)
        elif self.modulationType == Modulation.PM:
            self.signalGenerator.setPMFrequency(freq)
            
    def comboBox_modFreqUnit_activated(self):
        #TODO
        self.deleteLater
        
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
        if self.modulationType == Modulation.AM:
            self.signalGenerator.setAMCoupling(dc)
        elif self.modulationType == Modulation.FM:
            self.signalGenerator.setFMCoupling(dc)
        elif self.modulationType == Modulation.PM:
            self.signalGenerator.setPMCoupling(dc)
    
    def setCurrentModSource(self, internal: bool):
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
                self.radioButton_acdcCoupling.setText('AC + DC')
                self.radioButton_acdcCoupling.setEnabled(False)
        else:
            self.label_couplingTypeTitle.setText('Exteneral Coupling')
            self.radioButton_acCoupling.setText('AC Only')
            self.radioButton_acCoupling.setEnabled(True)
            self.radioButton_acdcCoupling.setText('AC + DC')
            self.radioButton_acdcCoupling.setEnabled(True)
        
    def toggleModControlTypeUI(self, am: bool):
        if am:
            self.radioButton_deepHighMode.setText('Deep')
            self.label_amDepthFPMDev.setText('Peak Depth')
            self.label_couplingTypeTitle.setText('AM Type')
            self.radioButton_acCoupling.setText('Linear')
            self.radioButton_acCoupling.setEnabled(True)
            self.radioButton_acCoupling.setChecked(True)
            self.radioButton_acdcCoupling.setText('Exponential')
            self.radioButton_acdcCoupling.setEnabled(True)
        else:
            self.radioButton_deepHighMode.setText('High')
            self.label_amDepthFPMDev.setText('Peak Deviation')
            self.label_couplingTypeTitle.setText('Exteneral Coupling')
            self.radioButton_acCoupling.setText('AC Only')
            self.radioButton_acdcCoupling.setText('AC + DC')
            self.radioButton_acCoupling.setEnabled(True)
            self.radioButton_acdcCoupling.setEnabled(False)        
        
    def on_amDepthBox_valueChanged(self, depth: float):
        self.amDepth = depth
        self.signalGenerator.setAmpModDepth(float(depth))

    def on_amFreqBox_valueChanged(self, freq: float):
        self.amFreq = freq
      
    def on_setFieldIntensityBox_valueChanged(self, strength: float):
        self.desiredFieldIntensity = float(strength)

    def on_pauseButton_pressed(self):
        #TODO: Make it a clear button
        self.signalGenerator.clearErrors()
        
    def on_startButton_pressed(self):
        #TODO: Start/Pause
        #TODO: Dis/Enable Freq Settings
        if self.rfOutOn:
            self.signalGenerator.setRFOut(False)
        else:
            self.signalGenerator.setRFOut(True)
        
    def displayAlert(self, text):
        self.alert = QMessageBox()
        self.alert.setText(text)
        self.alert.exec()
    
    def on_fieldProbe_identityReceived(self, model: str, revision: str, serial: str):
        self.pushButton_detectFieldProbe.hide()
        #TODO: self.connectFieldProbeButton.setIcon(':/icons/connected.png')
        self.fieldProbeLabel.setText('ETS Lindgren Field Probe HI-' + model + ' ' + serial)
        self.fieldProbe.getEField()
      
    def on_fieldProbe_fieldIntensityReceived(self, x: float, y: float, z: float, composite: float):
        self.measuredFieldIntensity = composite
        self.updateFieldStrengthUI(x, y, z, composite)
        if self.ouputOn and self.powerControl:
            output = self.pidController.calculate(composite)
            #rint("PID Out: " + str(output))
            if output > 14:
                output = 14
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
        self.label_chargeLevel.setText(str(level))
        
    def on_fieldProbe_temperatureReceived(self, temp: float):
        self.label_temperature.setText(str(temp))
    
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
            self.rfOutOn = True
            if self.sweepOn:
                self.signalGenerator.startFrequencySweep(self.startFrequency, self.stopFrequency, self.steps, self.stepDwell, True)
                self.sweepRunning = True
        else:
            print("RF Off")
            self.pushButton_rfOn.setEnabled(True)
            self.pushButton_rfOff.setEnabled(False)
            self.rfOutOn = False
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
        self.connectSigGenButton.setText('Connected')
        #TODO: self.connectSigGenButton.setIcon(':/icons/connected.png')
        self.sigGenLabel.setText(''.join(message.split(',')))
        
    def on_sigGen_frequencySet(self, frequency: float):
        self.currentOutputFrequency = frequency
        self.frequencyPlot.plotData(QTime.currentTime(), frequency)
    
    def on_sigGen_powerSet(self, power: float):
        self.currentOutputPower = power
        self.controlLoopAdjLcd.display(power)
        self.intensityPlot.plotData(QTime.currentTime(), power)
    
    def on_sigGen_sweepFinished(self):
        self.sweepRunning = False
        self.signalGenerator.setRFOut(False)
        self.toggleSweepUI(enabled=True)
        self.pushButton_startSweep.setEnabled(True)
        
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

        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    #app.setWindowIcon(QtGui.QIcon(':/icons/field_controller.ico'))
    window = MainWindow()
    window.show()
    #app.aboutToQuit(window.killThreads())
    sys.exit(app.exec_())
    
    
#self.freqStartBox.valueChanged.connect(self.on_freqStartBox_valueChanged)
# TODO: self.freqStartBox.setValue(self.startFrequency) & all others
#self.freqStopBox.valueChanged.connect(self.on_freqStopBox_valueChanged)
#self.stepDwellBox.valueChanged.connect(self.on_stepDwellBox_valueChanged)
#self.stepCountBox.valueChanged.connect(self.on_stepCountBox_valueChanged)
#self.amDepthBox.valueChanged.connect(self.on_amDepthBox_valueChanged)
#self.amFreqBox.valueChanged.connect(self.on_amFreqBox_valueChanged)
#self.setFieldIntensityBox.valueChanged.connect(self.on_setFieldIntensityBox_valueChanged)
#self.startButton.pressed.connect(self.on_startButton_pressed)
#self.linearSweepButton.toggled.connect(self.on_linearSweepButton_toggled)
#self.expSweepButton.toggled.connect(self.on_expSweepButton_toggled)
#self.sweepOffButton.toggled.connect(self.on_sweepOffButton_toggled)