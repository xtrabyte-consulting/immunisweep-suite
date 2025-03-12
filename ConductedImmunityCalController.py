"""
Conducted Immunity Calibration Controller
===========================================
This module implements a controller for conducting immunity calibration using
an Agilent E4440A Series Spectrum Analyzer and an Agilent E4421B Series Signal Generator.
The calibration covers a frequency range of 150 kHz to 80 MHz.

Devices:
    - Spectrum Analyzer: Agilent E4440A Series
    - Signal Generator: Agilent E4421B Series
"""


class ConductedImmunityCalController:
    """
    Controller class for managing the conducted immunity calibration process.
    """
    
    def __init__(self, spectrum_analyzer, signal_generator):
        """
        Initialize the calibration controller with a spectrum analyzer and signal generator.
        
        Parameters:
            spectrum_analyzer: An instance of the Agilent E4440A Series Spectrum Analyzer.
            signal_generator: An instance of the Agilent E4421B Series Signal Generator.
        """
        self.spectrum_analyzer = spectrum_analyzer
        self.signal_generator = signal_generator
        
        # Connect the calibration start button to the startCalibration method.
        self.conducted_immunity.start_cal_button.clicked.connect(self.startCalibration)
        
    def startCalibration(self):
        """
        Executes the calibration process by:
            - Configuring the devices with the correct frequency and power settings.
            - Starting the devices to perform the calibration.
            - Stopping the devices after calibration.
            - Saving the acquired data.
            - Closing the calibration interface.
        """
        # Set up the spectrum analyzer configuration.
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
        """
        Launch the calibration interface.

        This method displays the conducted immunity calibration GUI, allowing the user to
        initiate and monitor the calibration process.
        """
        self.conducted_immunity.show()