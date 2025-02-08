from PyQt5.QtWidgets import *

class ConductedCalibration(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(ConductedCalibration, self).__init__(*args, **kwargs)
        self.setWindowTitle('Conducted Immunity Calibration')