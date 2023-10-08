from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from PyQt5 import QtGui, QtWidgets, QtCore

from PyQt5.QtGui import QPainter, QBitmap, QPolygon, QPen, QBrush, QColor
from PyQt5.QtCore import Qt

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

from MainWindow import Ui_MainWindow
from SignalGenerator import AgilentN5181A
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
        self.measuredFiedldIntensity = 0.0
        self.desiredFieldIntensity = 0.0
        self.currentOutputPower = 0.0
        
        self.startDeviceDetection()
        
        self.freqStartBox.valueChanged.connect(self.on_freqStartBox_valueChanged)
        # TODO: self.freqStartBox.setValue(self.startFrequency) & all others
        self.freqStopBox.valueChanged.connect(self.on_freqStopBox_valueChanged)
        self.stepDwellBox.valueChanged.connect(self.on_stepDwellBox_valueChanged)
        self.stepCountBox.valueChanged.connect(self.on_stepCountBox_valueChanged)
        self.amDepthBox.valueChanged.connect(self.on_amDepthBox_valueChanged)
        self.amFreqBox.valueChanged.connect(self.on_amFreqBox_valueChanged)
        self.setFieldIntensityBox.valueChanged.connect(self.on_setFieldIntensityBox_valueChanged)
        self.startButton.pressed.connect(self.on_startButton_pressed)
        self.linearSweepButton.toggled.connect(self.on_linearSweepButton_toggled)
        self.expSweepButton.toggled.connect(self.on_expSweepButton_toggled)
        self.sweepOffButton.toggled.connect(self.on_sweepOffButton_toggled)
        
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

    def on_freqStartBox_valueChanged(self, freq: float):
        if not self.sweepRunning:
            self.signalGenerator.setFrequency(float(freq))
        self.startFrequency = freq
        
    def on_freqStopBox_valueChanged(self, freq: float):
        self.stopFrequency = freq
        
    def on_stepDwellBox_valueChanged(self, dwell: float):
        self.stepDwell = dwell
        
    def on_stepCountBox_valueChanged(self, count: int):
        self.steps = count
        
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