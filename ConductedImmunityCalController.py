# Conducted Immunity Calibration Controller
# Agilent E4440A Series Spectrum Analyzer
# Agilent E4421B Series Signal Generator
# Conducted Immunity 150kHz - 80MHz
from SpectrumAnalyzer import HPE4440A
from SignalGenerator import HPE4421B



class ConductedImmunityCalController:
    
    
    def __init__(self, spectrum_analyzer: HPE4440A, signal_generator: HPE4421B):
        self.spectrum_analyzer = spectrum_analyzer
        self.signal_generator = signal_generator
        self.signal_generator.frequencySet.connect(self.signal_generator_frequency_set)
        self.signal_generator.powerSet.connect(self.signal_generator_power_set)
        

    def start_calibration(self):
        self.spectrum_analyzer.set_window(100e3, 100e6)
        self.spectrum_analyzer.set_units("V")
        self.spectrum_analyzer.activate_marker()
        self.spectrum_analyzer.set_frequency(150e3)
        self.signal_generator.set_frequency(150e3)
        self.signal_generator.set_power(-20)
        
    def signal_generator_frequency_set(self):
        print("Signal Generator Frequency Set")

