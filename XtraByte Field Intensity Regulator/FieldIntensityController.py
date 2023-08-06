from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from PyQt5 import QtGui, QtWidgets, QtCore

from PyQt5.QtGui import QPainter, QBitmap, QPolygon, QPen, QBrush, QColor
from PyQt5.QtCore import Qt

from MainWindow import Ui_MainWindow
from SignalGenerator import AgilentN5181A
from FieldProbe import ETSLindgrenHI6006

import os
import sys
import random
import types
import math

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
        self.signalGenerator.instrument_detected.connect(self.on_sigGen_instrument_detected)
        self.signalGenerator.instrument_connected.connect(self.on_sigGen_instrument_connected)
        self.signalGenerator.current_frequency.connect(self.on_sigGen_current_frequency)
        self.signalGenerator.current_power.connect(self.on_sigGen_current_power)
        self.signalGenerator.error_occured.connect(self.on_sigGen_error_occured)
        self.signalGenerator.rfOutStateReceived.connect(self.on_sigGen_rfOutStateReceived)
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
        self.linearSweepButton.toggled.connect(self.on_linearSweepButton_toggled)
        self.expSweepButton.toggled.connect(self.on_expSweepButton_toggled)
        self.sweepOffButton.toggled.connect(self.on_sweepOffButton_toggled)
        self.ampModButton.toggled.connect(self.on_ampModButton_toggled)
        self.phaseModButton.toggled.connect(self.on_phaseModButton_toggled)
        self.modOffButton.toggled.connect(self.on_modOffButton_toggled)
        self.pidController = PIDController(1.0, 1.0, 0.5)
        self.sweepRunning = False
        self.startDeviceDetection()
        
    def startDeviceDetection(self):
        self.alerted = False
        self.signalGenerator.detect()
        self.fieldProbe.start()
    
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
        self.currentOutputPower = math.log10(float(strength)) * 20
        if self.currentOutputPower > 14:
            self.currentOutputPower = 14.0
        if self.currentOutputPower < -110:
            self.currentOutputPower = -110.0
        self.desiredFieldIntensity = float(strength)
        self.controlLoopAdjLcd.display(self.currentOutputPower)

    def on_pauseButton_pressed(self):
        #TODO: Make it a clear button
        self.signalGenerator.clearErrors()
        
    def on_startButton_pressed(self):
        #TODO: Start/Pause
        #TODO: Dis/Enable Freq Settings
        self.signalGenerator.setRFOut(True)
        
    def displayAlert(self, text):
        self.alert = QMessageBox()
        self.alert.setText(text)
        self.alert.exec()
    
    def on_fieldProbe_identityReceived(self, model: str, revision: str, serial: str, calibration: str):
        self.connectFieldProbeButton.setText('Connected')
        #TODO: self.connectFieldProbeButton.setIcon(':/icons/connected.png')
        self.fieldProbeLabel.setText('ETS Lindgren Field Probe HI-' + model + ' ' + serial)
        self.fieldProbe.getEField()
      
    def on_fieldProbe_fieldIntensityReceived(self, intensity: float):
        self.measuredFieldIntensity = intensity
        self.fieldIntensityLcd.display(intensity)
        if self.rfOutOn:
            output = self.pidController.calculate(self.desiredFieldIntensity, intensity)
            print("PID Out: " + str(output))
            if output > 14:
                output = 14
            if output < -110:
                output = -110
            print("Squeezed: " + str(output))
            self.signalGenerator.setPower(output)
        #calculatedPower = math.log10(output) * 20
        #print("Power Out: " + str(calculatedPower))
        
    def on_fieldProbe_fieldProbeError(self, message: str):
        print(message)
        self.displayAlert(message)
        
    def on_fieldProbe_serialConnectionError(self, message: str):
        print(message)
        self.displayAlert(message)
    
    def on_sigGen_rfOutStateReceived(self, on: bool):
        if on:
            print('RF On')
            self.rfOutOn = True
            if self.sweepOn:
                self.signalGenerator.startFrequencySweep(self.startFrequency, self.stopFrequency, self.steps, self.stepDwell)
                self.sweepRunning = True
        else:
            print("RF Off")
            self.rfOutOn = False
            # Stop Freq Sweep
        self.pidController.clear()
    
    def on_sigGen_instrument_detected(self, detected: bool):
        if detected:
            self.signalGenerator.stopDetection()
            self.signalGenerator.connect()
        else:
            self.signalGenerator.retryDetection()
            if not self.alerted:
                self.displayAlert("Signal Generator Disconnected. Please connect SG via LAN.")
                self.alerted = True        
    
    def on_sigGen_instrument_connected(self, message: str):
        self.connectSigGenButton.setText('Connected')
        #TODO: self.connectSigGenButton.setIcon(':/icons/connected.png')
        self.sigGenLabel.setText(''.join(message.split(',')))
        
    def on_sigGen_current_frequency(self, frequency: float):
        self.currentOutputFrequency = frequency
    
    def on_sigGen_current_power(self, power: float):
        self.currentOutputPower = power
        self.controlLoopAdjLcd.display(power)
    
    def on_sigGen_sweepFinished(self):
        self.sweepRunning = False
        self.signalGenerator.setRFOut(False)
        
    def on_sigGen_error_occured(self, message: str):
        print(message)
        self.displayAlert(message)
        
    def on_linearSweepButton_toggled(self):
        if self.linearSweepButton.isChecked():
            self.sweepOn = True
            self.sweepOffButton.setChecked(False)
            self.expSweepButton.setChecked(False)
            self.freqStopBox.setDisabled(False)
            self.stepDwellBox.setDisabled(False)
            self.stepCountBox.setDisabled(False)
        else:
            self.sweepOn = False
            self.sweepOffButton.setChecked(True)
            self.expSweepButton.setChecked(False)
            self.freqStopBox.setDisabled(True)
            self.stepDwellBox.setDisabled(True)
            self.stepCountBox.setDisabled(True)
            
    def on_expSweepButton_toggled(self):
        if self.expSweepButton.isChecked():
            self.sweepOn = True
            self.sweepOffButton.setChecked(False)
            self.linearSweepButton.setChecked(False)
            self.freqStopBox.setDisabled(False)
            self.stepDwellBox.setDisabled(False)
            self.stepCountBox.setDisabled(False)
        else:
            self.sweepOn = False
            self.sweepOffButton.setChecked(True)
            self.linearSweepButton.setChecked(False)
            self.freqStopBox.setDisabled(True)
            self.stepDwellBox.setDisabled(True)
            self.stepCountBox.setDisabled(True)
    
    def on_sweepOffButton_toggled(self):
        if self.sweepOffButton.isChecked():
            self.sweepOn = False
            self.expSweepButton.setChecked(False)
            self.linearSweepButton.setChecked(False)
            self.freqStopBox.setDisabled(True)
            self.stepDwellBox.setDisabled(True)
            self.stepCountBox.setDisabled(True)
        else:
            self.sweepOn = True
            self.sweepOffButton.setChecked(False)
            self.linearSweepButton.setChecked(True)
            self.freqStopBox.setDisabled(False)
            self.stepDwellBox.setDisabled(False)
            self.stepCountBox.setDisabled(False)
        
    def on_ampModButton_toggled(self):
        if self.ampModButton.isChecked():
            self.modulationOn = True
            self.phaseModButton.setChecked(False)
            self.modOffButton.setChecked(False)
            self.amDepthBox.setDisabled(False)
            self.amFreqBox.setDisabled(False)
            self.signalGenerator.setModulationType(True)
        else:
            self.modulationOn = False
            self.phaseModButton.setChecked(False)
            self.modOffButton.setChecked(True)
            self.amDepthBox.setDisabled(True)
            self.amFreqBox.setDisabled(True)
            self.signalGenerator.setModulationState(False)
            
    def on_phaseModButton_toggled(self):
        if self.phaseModButton.isChecked():
            self.modulationOn = True
            self.ampModButton.setChecked(False)
            self.modOffButton.setChecked(False)
            self.amDepthBox.setDisabled(False)
            self.amFreqBox.setDisabled(False)
            self.signalGenerator.setModulationType(False)
        else:
            self.modulationOn = False
            self.ampModButton.setChecked(False)
            self.modOffButton.setChecked(True)
            self.amDepthBox.setDisabled(True)
            self.amFreqBox.setDisabled(True)
            self.signalGenerator.setModulationState(False)
            
    def on_modOffButton_toggled(self):
        if self.modOffButton.isChecked():
            self.modulationOn = False
            self.ampModButton.setChecked(False)
            self.phaseModButton.setChecked(False)
            self.amDepthBox.setDisabled(True)
            self.amFreqBox.setDisabled(True)
            self.signalGenerator.setModulationState(False)
        else:
            self.modulationOn = True
            self.ampModButton.setChecked(True)
            self.phaseModButton.setChecked(False)
            self.amDepthBox.setDisabled(False)
            self.amFreqBox.setDisabled(False)
            self.signalGenerator.setModulationState(True)

        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    #app.setWindowIcon(QtGui.QIcon(':/icons/field_controller.ico'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())