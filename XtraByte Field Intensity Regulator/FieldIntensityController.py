from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from PyQt5 import QtGui, QtWidgets, QtCore

from PyQt5.QtGui import QPainter, QBitmap, QPolygon, QPen, QBrush, QColor
from PyQt5.QtCore import Qt

from MainWindow import Ui_MainWindow
import MainWindow
import SignalGenerator
import FieldProbe

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
        
    def calculate(self, desired_freq, current_freq):
        error = desired_freq - current_freq
        self.integral += error
        derivative = error - self.prev_error

        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative

        self.prev_error = error

        return output

class FieldIntensityController(QMainWindow, Ui_MainWindow):
    
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
    signalGenerator: SignalGenerator = None
    fieldProbe: FieldProbe = None
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('XtraByte Field Controller')
        self.fieldProbe = FieldProbe('COM5')
        self.fieldProbe.fieldIntensityReceived.connect(self.on_fieldProbe_fieldIntensityReceived)
        self.fieldProbe.identityReceived.connect(self.on_fieldProbe_identityReceived)
        self.signalGenerator = SignalGenerator('192.168.255.255', 524)
    
    def detectSigGen(self):
        self.deleteLater
        
    def sigGenDetected(self):
        self.deleteLater
        
    def connectSigGen(self):
        self.deleteLater
        
    def sigGenConnected(self):
        self.deleteLater
    
    def connectFieldProbe(self):
        self.deleteLater
        
    def on_setFieldIntensityBox_valueChanged(self, strength: float):
        self.currentOutputPower = 2 * strength / self.currentOutputFrequency
        
        
    def setStartFrequency(self):
        self.deleteLater
        
    def setStopFrequency(self):
        self.deleteLater
        
    def setStepDwell(self):
        self.deleteLater
        
    def setStepCount(self):
        self.deleteLater
        
    def setAMDepth(self):
        self.deleteLater
        
    def setAMFreq(self):
        self.deleteLater
        
    def startSignalGeneration(self):
        self.deleteLater
    
    def on_fieldProbe_identityReceived(self, model: str, revision: str, serial: str, calibration: str):
        self.connectFieldProbeButton.setText('Connected')
        #TODO: self.connectFieldProbeButton.setIcon(':/icons/connected.png')
        self.fieldProbeLabel.setText('ETS Lindgren Field Probe HI-' + model + ' ' + serial)
      
    def on_fieldProbe_fieldIntensityReceived(self, intensity: float):
        self.measuredFieldIntensity = intensity
        
        
    def on_fieldProbe_fieldProbeError(self, message: str):
        self.deleteLater
    
    def outputPowerSet(self, power: float):
        self.deleteLater
        
    def outputFrequencySet(self, frequency: float):
        self.deleteLater
        
    def signalGeneratorError(self, message: str):
        self.deleteLater

        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(':/icons/field_controller.ico'))
    window = MainWindow()
    app.exec_()