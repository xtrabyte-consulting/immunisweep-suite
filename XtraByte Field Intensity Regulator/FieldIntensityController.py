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
        self.prev_error = 0
        self.integral = 0
        
    def calculate(self, desired_field: float, current_field: float) -> float:
        error = desired_field - current_field
        self.integral += error
        derivative = error - self.prev_error

        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative

        self.prev_error = error

        return output
    
    def clear(self):
        self.prev_error = 0
        self.integral = 0

class MainWindow(QMainWindow, Ui_MainWindow):
    
    desiredFieldIntensity = 0.0
    measuredFieldIntensity = 0.0
    startFrequency = 0.1
    stopFrequency = 6000.0
    steps = 1
    stepDwell = 1.05
    amDepth = 0.0
    amFreq = 1.0
    currentOutputPower = 0.0
    currentOutputFrequency = startFrequency
    sweepOn = True
    modulationOn = False
    rfOutOn = False
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('XtraByte Field Controller')
        self.fieldProbe = ETSLindgrenHI6006('COM5')
        self.fieldProbe.fieldIntensityReceived.connect(self.on_fieldProbe_fieldIntensityReceived)
        self.fieldProbe.identityReceived.connect(self.on_fieldProbe_identityReceived)
        self.fieldProbe.serialConnectionError.connect(self.on_fieldProbe_serialConnectionError)
        self.fieldProbe.fieldProbeError.connect(self.on_fieldProbe_fieldProbeError)
        self.signalGenerator = AgilentN5181A('192.168.100.79', 5024)
        self.signalGenerator.instrumentDetected.connect(self.on_sigGen_instrumentDetected)
        self.signalGenerator.instrumentConnected.connect(self.on_sigGen_instrumentConnected)
        self.signalGenerator.frequencySet.connect(self.on_sigGen_frequencySet)
        self.signalGenerator.powerSet.connect(self.on_sigGen_powerSet)
        self.signalGenerator.error.connect(self.on_sigGen_error)
        self.signalGenerator.rfOutSet.connect(self.on_sigGen_rfOutSet)
        self.signalGenerator.sweepFinished.connect(self.on_sigGen_sweepFinished)
        self.connectFieldProbeButton.pressed.connect(self.on_connectFieldProbeButton_pressed)
        self.connectSigGenButton.pressed.connect(self.on_connectSigGenButton_pressed)
        self.freqStartBox.valueChanged.connect(self.on_freqStartBox_valueChanged)
        # TODO: self.freqStartBox.setValue(self.startFrequency) & all others
        self.freqStopBox.valueChanged.connect(self.on_freqStopBox_valueChanged)
        self.stepDwellBox.valueChanged.connect(self.on_stepDwellBox_valueChanged)
        self.stepCountBox.valueChanged.connect(self.on_stepCountBox_valueChanged)
        self.amDepthBox.valueChanged.connect(self.on_amDepthBox_valueChanged)
        self.amFreqBox.valueChanged.connect(self.on_amFreqBox_valueChanged)
        self.setFieldIntensityBox.valueChanged.connect(self.on_setFieldIntensityBox_valueChanged)
        self.startButton.pressed.connect(self.on_startButton_pressed)
        self.freqGroup = QButtonGroup()
        self.freqGroup.addButton(self.linearSweepButton)
        self.freqGroup.addButton(self.expSweepButton)
        self.freqGroup.addButton(self.sweepOffButton)
        self.modGroup = QButtonGroup()
        self.modGroup.addButton(self.ampModButton)
        self.modGroup.addButton(self.phaseModButton)
        self.modGroup.addButton(self.modOffButton)
        self.linearSweepButton.toggled.connect(self.on_linearSweepButton_toggled)
        self.expSweepButton.toggled.connect(self.on_expSweepButton_toggled)
        self.sweepOffButton.toggled.connect(self.on_sweepOffButton_toggled)
        self.ampModButton.toggled.connect(self.on_ampModButton_toggled)
        self.phaseModButton.toggled.connect(self.on_phaseModButton_toggled)
        self.modOffButton.toggled.connect(self.on_modOffButton_toggled)
        self.pidController = PIDController(1.0, 1.0, 0.5)
        self.sweepRunning = False
        self.setOn = True
        self.pauseButton.setText("Clear Err")
        self.startDeviceDetection()
        
    def startDeviceDetection(self):
        self.alerted = False
        self.signalGenerator.detect()
        self.fieldProbe.start()

    def killThreads(self):
        self.fieldProbe.stop()
        #self.signalGenerator.stopDetection()
        self.signalGenerator.stop()
    
    def on_connectFieldProbeButton_pressed(self):
        self.fieldProbe.start()

    def on_connectSigGenButton_pressed(self):
        self.signalGenerator.retryDetection()

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
        self.connectFieldProbeButton.setText('Connected')
        #TODO: self.connectFieldProbeButton.setIcon(':/icons/connected.png')
        self.fieldProbeLabel.setText('ETS Lindgren Field Probe HI-' + model + ' ' + serial)
        self.fieldProbe.getEField()
      
    def on_fieldProbe_fieldIntensityReceived(self, x, y, z, intensity: float):
        self.measuredFieldIntensity = intensity
        self.fieldIntensityLcd.display(intensity)
        if self.rfOutOn:
            output = self.pidController.calculate(self.desiredFieldIntensity, intensity)
            print("PID Out: " + str(output))
            if output > 14:
                output = 14
            if output < -110:
                output = -110
            self.signalGenerator.setPower(output)
        
    def on_fieldProbe_fieldProbeError(self, message: str):
        print(f"Probe Error: {message}")
        self.displayAlert(message)
        
    def on_fieldProbe_serialConnectionError(self, message: str):
        print(message)
        self.displayAlert(message)
    
    def on_sigGen_rfOutSet(self, on: bool):
        if on:
            print('RF On')
            self.startButton.setText('Stop')
            self.rfOutOn = True
            if self.sweepOn:
                self.signalGenerator.startFrequencySweep(self.startFrequency, self.stopFrequency, self.steps, self.stepDwell, True)
                self.sweepRunning = True
        else:
            print("RF Off")
            self.startButton.setText('Start')
            self.rfOutOn = False
            if self.sweepOn and self.sweepRunning:
                self.signalGenerator.stopFrequencySweep()
                self.sweepRunning = False
            # Stop Freq Sweep
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
    
    def on_sigGen_powerSet(self, power: float):
        self.currentOutputPower = power
        self.controlLoopAdjLcd.display(power)
    
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