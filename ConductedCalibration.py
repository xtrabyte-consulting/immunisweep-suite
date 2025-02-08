from PyQt5.QtWidgets import *

from ConductedCalibrationWindow import Ui_MainWindow

class ConductedCalibration(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(ConductedCalibration, self).__init__(*args, **kwargs)
        self.setWindowTitle('Conducted Immunity Calibration')
        self.start_cal_button = QPushButton("Start Calibration")
        self.start_cal_button.clicked.connect(self.startCalibration)
