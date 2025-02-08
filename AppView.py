from PyQt5 import QtCore
"""
This module provides a PyQt5-based GUI application for controlling field intensity using signal generators and field probes.
It includes classes for managing equipment limits, PID gains, and the main application window.
Classes:
    EquipmentLimits: Manages frequency and power limits for antennas and amplifiers.
    PIDGainsPopUp: A dialog for setting PID controller gains.
    MainWindow: The main application window for the field intensity controller.
"""
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from qt_material import apply_stylesheet

from MainWindow import Ui_MainWindow
from SignalGenerator import AgilentN5181A, Time, Frequency
from FieldProbe import ETSLindgrenHI6006
from FieldController import FieldController
from LivePlot import FrequencyPlot, PowerPlot
from PID import PIDController
from EquipmentLimits import EquipmentLimits
from ExportWidget import ExportWidget

import os
import sys
import math
import time
import numpy as np
from datetime import datetime

import signal
from PyQt5.QtCore import QResource

CURRENT_DIR = os.path.curdir

try:
    # Include in try/except block if you're also targeting Mac/Linux
    from PyQt5.QtWinExtras import QtWin
    myappid = 'something.else'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)    
except ImportError:
    pass

        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    #app.setWindowIcon(QtGui.QIcon(':/icons/field_controller.ico'))
    window = MainWindow()
    
    apply_stylesheet(app, theme='dark_cyan.xml')
    window.show()
    #app.aboutToQuit(window.killThreads())
    signal.signal(signal.SIGINT, window.closeEvent)
    sys.exit(app.exec_())