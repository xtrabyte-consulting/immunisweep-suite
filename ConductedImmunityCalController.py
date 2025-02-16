# Conducted Immunity Calibration Controller
# Agilent E4440A Series Spectrum Analyzer
# Agilent E4421B Series Signal Generator
# Conducted Immunity 150kHz - 80MHz



class ConductedImmunityCalController:
    
    
    def __init__(self, spectrum_analyzer, signal_generator):
        self.spectrum_analyzer = spectrum_analyzer
        self.signal_generator = signal_generator
        
        self.conducted_immunity.start_cal_button.clicked.connect(self.startCalibration)
        
    def startCalibration(self):
        self.spectrum_analyzer.setCenterFrequency(150e3)
        self.spectrum_analyzer.setSpan(80e6)
        self.signal_generator.setFrequency(150e3)
        self.signal_generator.setPower(-20)
        self.spectrum_analyzer.start()
        self.signal_generator.start()
        self.spectrum_analyzer.stop()
        self.signal_generator.stop()
        self.spectrum_analyzer.saveData()
        self.signal_generator.saveData()
        self.conducted_immunity.close()
        
    def run(self):
        self.conducted_immunity.show()