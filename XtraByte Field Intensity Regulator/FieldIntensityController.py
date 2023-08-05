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

class MainWindow(QMainWindow, Ui_MainWindow):
    
    desiredFieldIntensity = 0
    measuredFieldIntensity = 0
    startFrequency = 100
    stopFrequency = 1000
    steps = 100
    stepDwell = 100
    amDepth = 30
    amFreq = 1
    currentOutputPower = 0
    currentOutputFrequency = 1000 * startFrequency
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('XtraByte Field Controller')
        self.fieldProbe = ETSLindgrenHI6006('COM5')
        self.fieldProbe.fieldIntensityReceived.connect(self.on_fieldProbe_fieldIntensityReceived)
        self.fieldProbe.identityReceived.connect(self.on_fieldProbe_identityReceived)
        self.fieldProbe.serialConnectionError.connect(self.on_fieldProbe_serialConnectionError)
        self.fieldProbe.fieldProbeError.connect(self.on_fieldProbe_fieldProbeError)
        self.signalGenerator = AgilentN5181A('192.168.80.79', 5024)
        self.signalGenerator.instrument_detected.connect(self.on_sigGen_instrument_detected)
        self.signalGenerator.instrument_connected.connect(self.on_sigGen_instrument_connected)
        self.signalGenerator.current_frequency.connect(self.on_sigGen_current_frequency)
        self.signalGenerator.current_power.connect(self.on_sigGen_current_power)
        self.signalGenerator.error_occured.connect(self.on_sigGen_error_occured)
        #self.connectFieldProbeButton.pressed.connect(self.on_connectFieldProbeButton_pressed)
        #self.connectSigGenButton.pressed.connect(self.on_connectSigGenButton_pressed)
        self.freqStartBox.valueChanged.connect(self.on_freqStartBox_valueChanged)
        self.freqStopBox.valueChanged.connect(self.on_freqStopBox_valueChanged)
        self.stepDwellBox.valueChanged.connect(self.on_stepDwellBox_valueChanged)
        self.stepCountBox.valueChanged.connect(self.on_stepCountBox_valueChanged)
        self.amDepthBox.valueChanged.connect(self.on_amDepthBox_valueChanged)
        self.amFreqBox.valueChanged.connect(self.on_amFreqBox_valueChanged)
        self.setFieldIntensityBox.valueChanged.connect(self.on_setFieldIntensityBox_valueChanged)
        self.startButton.pressed.connect(self.on_startButton_pressed)
        self.pidController = PIDController(1.0, 1.0, 0.5)
        self.sweepRunning = False
        
    def startDeviceDetection(self):
        self.signalGenerator.detect()
        self.fieldProbe.start()
    
    def on_freqStartBox_valueChanged(self, freq: float):
        if not self.sweepRunning:
            self.signalGenerator.setFrequency(int(freq))
        self.startFrequency = freq
        
    def on_freqStopBox_valueChanged(self, freq: float):
        self.stopFrequency = freq
        
    def on_stepDwellBox_valueChanged(self, dwell: float):
        self.stepDwell = dwell
        
    def on_stepCountBox_valueChanged(self, count: int):
        self.steps = count
        
    def on_amDepthBox_valueChanged(self, depth: float):
        self.amDepth = depth
        if not self.sweepRunning:
            self.signalGenerator.setAmModDepth(depth)

    def on_amFreqBox_valueChanged(self, freq: float):
        self.amFreq = freq
      
    def on_setFieldIntensityBox_valueChanged(self, strength: float):
        self.currentOutputPower = 2 * strength / self.currentOutputFrequency
        self.desiredFieldIntensity = strength
        
    def on_startButton_pressed(self):
        self.sweepRunning = True
        self.signalGenerator.startFrequencySweep(self.startFrequency, self.stopFrequency, self.steps, self.stepDwell)
        
    def displayAlert(self, text):
        self.alert = QMessageBox()
        self.alert.setText(text)
        self.alert.exec()
    
    def on_fieldProbe_identityReceived(self, model: str, revision: str, serial: str, calibration: str):
        self.connectFieldProbeButton.setText('Connected')
        #TODO: self.connectFieldProbeButton.setIcon(':/icons/connected.png')
        self.fieldProbeLabel.setText('ETS Lindgren Field Probe HI-' + model + ' ' + serial)
      
    def on_fieldProbe_fieldIntensityReceived(self, intensity: float):
        self.measuredFieldIntensity = intensity
        self.fieldIntensityLcd.display(intensity)
        calculatedPower = self.pidController.calculate(self.desiredFieldIntensity, intensity)
        self.signalGenerator.setPower(calculatedPower)
        
    def on_fieldProbe_fieldProbeError(self, message: str):
        print(message)
        self.displayAlert(message)
        
    def on_fieldProbe_serialConnectionError(self, message: str):
        print(message)
        self.displayAlert(message)
    
    def on_sigGen_instrument_detected(self, detected: bool):
        if detected:
            self.signalGenerator.stopDetection()
            self.signalGenerator.connect()
        else:
            self.signalGenerator.retryDetection()
            self.displayAlert("Signal Generator Disconnected. Please connect SG via LAN.")        
    
    def on_sigGen_instrument_connected(self, message: str):
        self.connectSigGenButton.setText('Connected')
        #TODO: self.connectSigGenButton.setIcon(':/icons/connected.png')
        self.sigGenLabel.setText(''.join(message.split(',')))
        
    def on_sigGen_current_frequency(self, frequency: float):
        self.currentOutputFrequency = frequency
    
    def on_sigGen_current_power(self, power: float):
        self.currentOutputPower = power
        self.controlLoopAdjLcd.display(power)
        
    def on_sigGen_error_occured(self, message: str):
        print(message)
        self.displayAlert(message)

        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    #app.setWindowIcon(QtGui.QIcon(':/icons/field_controller.ico'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())