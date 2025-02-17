from PyQt5.QtWidgets import *

from ConductedCalibrationWindow import Ui_MainWindow
from SpectrumAnalyzer import HPE4440A
from SignalGenerator import HPE4421B

class ConductedImmunityCalibration(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(ConductedImmunityCalibration, self).__init__(*args, **kwargs)
        self.setWindowTitle('Conducted Immunity Calibration')
        self.start_cal_button = QPushButton("Start Calibration")
        self.start_cal_button.clicked.connect(self.start_calibration)
        self.spectrum_analyzer = HPE4440A("192.168.100.90")
        self.signal_generator = HPE4421B("COM5")
        

    def start_calibration(self):
        print("Starting calibration...")
        print("Setting spectrum analyzer window to 100 kHz - 100 MHz")
        self.spectrum_analyzer.set_window(100e3, 100e6)
        self.spectrum_analyzer.set_units("V")
        self.spectrum_analyzer.set_frequency(150e3)
        self.signal_generator.set_frequency(150e3)
        self.signal_generator.set_power(-6)
        #TODO: Set to DC Coupling
        #TODO: Set to reference level of 5V