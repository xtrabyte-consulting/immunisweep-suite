from PyQt5 import QtCore
"""
This module provides a PyQt5-based GUI application for controlling field intensity using signal generators and field probes.
It includes classes for managing equipment limits, PID gains, and the main application window.
Classes:
    EquipmentLimits: Manages frequency and power limits for antennas and amplifiers.
    PIDGainsPopUp: A dialog for setting PID controller gains.
    MainWindow: The main application window for the field intensity controller.
"""

from PyQt5.QtWidgets import (
    QApplication, QDialog, QMainWindow, QVBoxLayout,
    QPushButton, QLabel, QWidget
)


from qt_material import apply_stylesheet

from RadiatedImmunity import RadiatedImmunity

import os
import sys
import numpy as np
from datetime import datetime

import signal
from PyQt5.QtCore import QResource

CURRENT_DIR = os.path.curdir
RADIATED_IMMUNITY = 'Radiated Immunity'
CONDUCTED_IMMUNITY = 'Conducted Immunity'
CONDUCTED_IMMUNITY_CALIBRATION = 'Conducted Immunity Calibration'

try:
    # Include in try/except block if you're also targeting Mac/Linux
    from PyQt5.QtWinExtras import QtWin
    myappid = 'something.else'
    QtWin.setCurrentProcessExplicitAppUserModelID(myappid)    
except ImportError:
    pass

class TestSelectionDialog(QDialog):
    """
    A simple dialog acting as a splash screen to choose the test type.
    """
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle('Test Selection')
        self.selected_test = None
        
        layout = QVBoxLayout()

        label = QLabel("Please select the test type:")
        layout.addWidget(label) 

        self.radiated_button = QPushButton("Radiated Immunity")
        self.conducted_button = QPushButton("Conducted Immunity")
        self.conducted_cal_button = QPushButton("Conducted Immunity Calibration")
        self.radiated_button.clicked.connect(self.openRadiatedImmunity)
        self.conducted_button.clicked.connect(self.openConductedImmunity)
        self.conducted_cal_button.clicked.connect(self.openConductedImmunityCalibration)
        layout.addWidget(self.radiated_button)
        layout.addWidget(self.conducted_button)

        self.setLayout(layout)
        
    def openRadiatedImmunity(self):
        self.selected_test = RADIATED_IMMUNITY
        self.accept()

    def openConductedImmunity(self):
        self.selected_test = CONDUCTED_IMMUNITY
        self.accept()

    def openConductedImmunityCalibration(self):
        self.selected_test = CONDUCTED_IMMUNITY_CALIBRATION
        self.accept()
        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    #app.setWindowIcon(QtGui.QIcon(':/icons/field_controller.ico'))

    # Show the splash/selection dialog.
    
    selection_dialog = TestSelectionDialog()
    apply_stylesheet(app, theme='dark_cyan.xml')
    if selection_dialog.exec_() == QDialog.Accepted:
        if selection_dialog.selected_test == RADIATED_IMMUNITY:
            window = RadiatedImmunity()
        elif selection_dialog.selected_test == CONDUCTED_IMMUNITY:
            window = ConductedImmunity()
        elif selection_dialog.selected_test == CONDUCTED_IMMUNITY_CALIBRATION:
            window = ConductedImmunityCalibration()
        else:
            print("No valid test selected. Exiting.")
            sys.exit(0)
        apply_stylesheet(app, theme='dark_cyan.xml')
        window.show()
    else:
        # The dialog was cancelled or closed without selection.
        sys.exit(0)
    
    
    #window.show()
    #app.aboutToQuit(window.killThreads())
    signal.signal(signal.SIGINT, window.closeEvent)
    sys.exit(app.exec_())