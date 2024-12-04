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

import os
import sys
import math
import time

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

class PIDGainsPopUp(QDialog):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle('PID Gains')
        
        layout = QVBoxLayout()

        self.spinbox_Kp = QDoubleSpinBox()
        self.label_Kp = QLabel("Proportional Gain")
        self.spinbox_Kp.setValue(self.main_window.pid_controller.Kp)

        self.spinbox_Ki = QDoubleSpinBox()
        self.label_Ki = QLabel("Integral Gain")
        self.spinbox_Ki.setValue(self.main_window.pid_controller.Ki)

        self.spinbox_Kd = QDoubleSpinBox()
        self.label_Kd = QLabel("Derivative Gain")
        self.spinbox_Kd.setValue(self.main_window.pid_controller.Kd)

        layout.addWidget(self.label_Kp)
        layout.addWidget(self.spinbox_Kp)

        layout.addWidget(self.label_Ki)
        layout.addWidget(self.spinbox_Ki)

        layout.addWidget(self.label_Kd)
        layout.addWidget(self.spinbox_Kd)

        # Add dialog buttons (OK and Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.save_values)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

        self.setLayout(layout)
        
    def save_values(self):
        # Save the values of the spin boxes to the main window's PID controller gains
        self.main_window.pid_controller.setGains(self.spinbox_Kp.value(), self.spinbox_Ki.value(), self.spinbox_Kd.value())

        # Close the dialog
        self.accept()

class MainWindow(QMainWindow, Ui_MainWindow):
    
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('ImmuniSweep Suite')
        
        # Field Probe Signal -> Slot Connections
        self.field_probe = ETSLindgrenHI6006()
        self.field_probe.identityReceived.connect(self.on_fieldProbe_identityReceived)
        self.field_probe.batteryReceived.connect(self.on_fieldProbe_batteryReceived)
        self.field_probe.temperatureReceived.connect(self.on_fieldProbe_temperatureReceived)
        self.field_probe.serialConnectionError.connect(self.on_fieldProbe_serialConnectionError)
        self.field_probe.fieldProbeError.connect(self.on_fieldProbe_fieldProbeError)
        self.field_probe.fieldIntensityReceived.connect(self.on_fieldProbe_fieldIntensityReceived)
        
        # Signal Generator Signal -> Slot Connections
        self.signal_generator = AgilentN5181A()
        self.signal_generator.instrumentDetected.connect(self.on_sigGen_instrumentDetected)
        self.signal_generator.instrumentConnected.connect(self.on_sigGen_instrumentConnected)
        self.signal_generator.error.connect(self.on_sigGen_error)
        self.signal_generator.rfOutSet.connect(self.on_sigGen_rfOutSet)
        self.signal_generator.modStateSet.connect(self.on_sigGen_modStateSet)
        self.signal_generator.modFreqSet.connect(self.on_sigGen_modFrequencySet)
        self.signal_generator.amTypeSet.connect(self.on_sigGen_amTypeSet)
        self.signal_generator.modDepthSet.connect(self.on_sigGen_modDepthSet)
        
        # Create Field Controller nd move it to a QThread
        #self.pid_controller = PIDController(0.4, 0.0, 0.0)
        self.field_controller = FieldController(self.signal_generator, self.field_probe, None)
        self.field_controller_thread = QThread()
        self.field_controller.moveToThread(self.field_controller_thread)
        
        #self.field_controller.move_timers_to_thread(self.field_controller_thread)
        
        self.dwell_timer = QTimer(self)
        self.dwell_timer.timeout.connect(self.on_dwell_complete)
        
        # Connect Field Controller Signals to UI Slots
        self.field_controller.frequencyUpdated.connect(self.on_fieldController_frequencySet)
        self.field_controller.powerUpdated.connect(self.on_fieldController_powerUpdated)
        self.field_controller.fieldUpdated.connect(self.on_fieldController_fieldUpdated)
        self.field_controller.sweepCompleted.connect(self.on_fieldController_sweepCompleted)
        self.field_controller.sweepStatus.connect(self.on_fieldController_sweepStatus)
        self.field_controller.highFieldDetected.connect(self.on_fieldController_highFieldDetected)
        self.field_controller.startDwell.connect(self.start_dwell_timer)
        #Start the thread
        self.field_controller_thread.start()
        
        # Initialize State
        self.sweep_in_progress = False
        self.output_on = False
        self.modulation_on = False
        self.dwell_complete = True
        self.measured_field_strength = 0.0
        self.target_field_strength = 1.0
        self.x_field = 0.0
        self.y_field = 0.0
        self.z_field = 0.0
        self.output_power = -30.0
        self.output_frequency = 100.0
        self.antenna_gain = 10.0
        self.amplifier_gain = 40.0
        self.distance = 0.1
        self.start_freq = 300.0
        self.stop_freq = 1000.0
        self.dwell_time = 0.5
        self.sweep_term = 0.01
        self.equipment_limits = EquipmentLimits(0.1, 0.1, 6000.0, 6000.0, 15.0)
        self.sweep_start_time = time.time()
        self.power_start_time = time.time()
        
        self.single_alert_window = None
        
        ### UI Input and Control Signal -> Slot Connections
        # Device detection
        self.pushButton_detectSigGen.pressed.connect(self.on_pushButton_detectSigGen_pressed)
        self.pushButton_detectFieldProbe.pressed.connect(self.on_pushButton_detectFieldProbe_pressed)
        
        # Output Power/State Control
        self.spinBox_targetStrength.setRange(0, 10)
        self.spinBox_targetStrength.valueChanged.connect(self.on_spinBox_targetStrength_valueChanged)
        self.spinBox_targetStrength.setStyleSheet('QDoubleSpinBox { color: white; }')
        self.pushButton_rfOn.pressed.connect(self.on_pushButton_rfState_pressed)
        #self.pushButton_rfOff.pressed.connect(self.on_pushButton_rfState_pressed)
        #self.pushButton_setGains.pressed.connect(lambda: PIDGainsPopUp(self).exec_())
        
        # Output Frequency Control
        self.spinBox_startFreq.valueChanged[float].connect(self.on_spinBox_startFreq_valueChanged)
        self.spinBox_startFreq.setStyleSheet('QDoubleSpinBox { color: white; }')
        self.spinBox_stopFreq.valueChanged[float].connect(self.on_spinBox_stopFreq_valueChanged)
        self.spinBox_stopFreq.setStyleSheet('QDoubleSpinBox { color: white; }')
        self.spinBox_dwell.valueChanged.connect(self.on_spinBox_dwell_valueChanged)
        self.spinBox_dwell.setStyleSheet('QDoubleSpinBox { color: white; }')
        self.comboBox_dwellUnit.activated.connect(self.on_comboBox_dwellUnit_activated)
        self.comboBox_dwellUnit.setStyleSheet('''
            QComboBox QAbstractItemView {
                color: #f0f0f0; /* Set the font color of the dropdown items */
            }
            QComboBox { 
                color: white; 
            }
        ''')
        self.doubleSpinBox_sweepTerm.valueChanged.connect(self.on_spinBox_sweepTerm_valueChanged)
        self.doubleSpinBox_sweepTerm.setStyleSheet('QDoubleSpinBox { color: white; }')
        self.pushButton_startSweep.pressed.connect(self.on_pushButton_startSweep_pressed)
        #self.pushButton_pauseSweep.pressed.connect(self.on_pushButton_pauseSweep_pressed)
        
        # Output Modulation Control
        self.spinBox_modDepth.valueChanged[float].connect(self.spinBox_modDepth_valueChanged)
        self.spinBox_modDepth.setStyleSheet('QDoubleSpinBox { color: white; }')
        self.spinBox_modFreq.valueChanged[float].connect(self.spinBox_modFreq_valueChanged)
        self.spinBox_modFreq.setStyleSheet('QDoubleSpinBox { color: white; }')
        #self.pushButton_modulationOff.pressed.connect(self.pushButton_modulationState_pressed)
        self.pushButton_modulationOn.pressed.connect(self.pushButton_modulationState_pressed)
        
        # Amplifier and Antenna Selections
        self.comboBox_amplifier.currentIndexChanged[str].connect(self.on_comboBox_amplifier_activated)
        self.comboBox_amplifier.setStyleSheet('''
            QComboBox QAbstractItemView {
                color: #f0f0f0; /* Set the font color of the dropdown items */
            }
            QComboBox { 
                color: white; 
            }
        ''')
        self.comboBox_antenna.currentIndexChanged[str].connect(self.on_comboBox_antenna_activated)
        self.comboBox_antenna.setStyleSheet('''
            QComboBox QAbstractItemView {
                color: #f0f0f0; /* Set the font color of the dropdown items */
            }
            QComboBox { 
                color: white; 
            }
        ''')
        
        # Closed-Loop Power Control
        self.pid_controller = PIDController(0.6, 0.0, 0.3) # Good @ 4 V/m with horn
        
        # Initiate Plots
        self.sweep_plot_widget = QWidget(self)
        self.sweep_plot = FrequencyPlot(self.sweep_plot_widget, width=4, height=3, dpi=100)
        self.gridLayout_frequencyPlot.addWidget(self.sweep_plot)
        
        self.power_plot_widget = QWidget(self)
        self.field_plot = PowerPlot(self.power_plot_widget, width=4, height=3, dpi=100)
        self.gridLayout_powerPlot.addWidget(self.field_plot)
        
        # Plot timers
        self.sweep_timer = QTimer(self)
        self.sweep_timer.timeout.connect(self.update_sweep_plot)
        
        self.field_timer = QTimer(self)
        self.field_timer.timeout.connect(self.update_field_data_plot)

        self.doubleSpinBox_sweepTerm.setValue(self.sweep_term)
        self.spinBox_startFreq.setValue(self.start_freq)
        self.spinBox_stopFreq.setValue(self.stop_freq)
        self.comboBox_amplifier.setCurrentIndex(0)
        self.comboBox_antenna.setCurrentIndex(0)
        self.label_validSettings.setText('Please Select Antenna and Amplifier')
        self.label_validSettings.setStyleSheet('color: red')
        
        # Other UI Setup
        #self.pushButton_pauseSweep.setEnabled(False)
        pixmap = QPixmap('broadcast-off.png')
        scaledPixmap = pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_rfOutState.setPixmap(scaledPixmap)
        pixmap = QPixmap('thermometer.png')
        scaledPixmap = pixmap.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_temperatureTitle.setPixmap(scaledPixmap)
        pixmap = QPixmap('battery.png')
        scaledPixmap = pixmap.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_chargeTitle.setPixmap(scaledPixmap)
        self.progressBar_freqSweep.setValue(0)
        self.progressBar_freqSweep.setHidden(True)
        
        self.pushButton_startSweep.setText('Sweep Off')
        
        self.startDeviceDetection()
        
    def startDeviceDetection(self):
        self.alerted = False
        self.signal_generator.detect()
        self.field_probe.start()
        
    def on_pushButton_detectSigGen_pressed(self):
        self.signal_generator.detect()
        
    def on_pushButton_detectFieldProbe_pressed(self):
        self.field_probe.start()
    
    def start_dwell_timer(self, time: int):
        print(f"Starting Dwell Timer for {time} ms")
        self.dwell_timer.start(time)
        
    def on_dwell_complete(self):
        print("Dwell Complete, stepping sweep...")
        self.dwell_timer.stop()
        self.field_controller.step_sweep()    
        
    def on_comboBox_amplifier_activated(self, amplifier: str):
        print(f"Amplifier Selected: {amplifier}")
        if amplifier == 'AR 25A250AMB':
            self.equipment_limits.setMaxPower(0.0)
            self.equipment_limits.setAmplifierMinFrequency(1.0)
            self.equipment_limits.setAmplifierMaxFrequency(300.0)
            self.amplifier_gain = 45.0
            self.label_amplifierStats.setText('Min Freq: 1 MHz\nMax Freq: 300 MHz\nPower In: 0 dBm')
        elif amplifier == 'IFI SMX25':
            self.equipment_limits.setMaxPower(0.0)
            self.equipment_limits.setAmplifierMinFrequency(300.0)
            self.equipment_limits.setAmplifierMaxFrequency(1000.0)
            self.amplifier_gain = 45.0
            self.label_amplifierStats.setText('Min Freq: 300 MHz\nMax Freq: 1000 MHz\nPower In: 0 dBm')
        elif amplifier == 'IFI S3110':
            self.equipment_limits.setMaxPower(0.0)
            self.equipment_limits.setAmplifierMinFrequency(800.0)
            self.equipment_limits.setAmplifierMaxFrequency(3000.0)
            self.amplifier_gain = 45.0
            self.label_amplifierStats.setText('Min Freq: 800 MHz\nMax Freq: 3000 MHz\nPower In: 0 dBm')
        elif amplifier == 'MC ZVE8G':
            self.equipment_limits.setMaxPower(0.0)
            self.equipment_limits.setAmplifierMinFrequency(2000.0)
            self.equipment_limits.setAmplifierMaxFrequency(8000.0)
            self.amplifier_gain = 45.0
            self.label_amplifierStats.setText('Min Freq: 2000 MHz\nMax Freq: 8000 MHz\nPower In: 0 dBm')
        elif amplifier == 'Generic':
            self.equipment_limits.setMaxPower(10.0)
            self.equipment_limits.setAmplifierMinFrequency(700.0)
            self.equipment_limits.setAmplifierMaxFrequency(3500.0)
            self.amplifier_gain = 20.0
            self.label_amplifierStats.setText('Min Freq: 700 MHz\nMax Freq: 3500 MHz\nPower In: 10 dBm')
        elif amplifier == '--Please Select--':
            self.pushButton_startSweep.setEnabled(False)
            self.pushButton_rfOn.setEnabled(False)
            return
        self.applyFrequencyLimits(self.spinBox_startFreq.value(), self.spinBox_stopFreq.value())
        
            
    def on_comboBox_antenna_activated(self, antenna: str):
        print(f"Antenna Selected: {antenna}")
        if antenna == 'ETS 3143B':
            self.equipment_limits.setAntennaMinFrequency(30.0)
            self.equipment_limits.setAntennaMaxFrequency(3000.0)
            self.antenna_gain = 5.0
            self.label_antennaStats.setText('Min Freq: 30 MHz\nMax Freq: 3000 MHz')
        elif antenna == 'EMCO 3155':
            self.equipment_limits.setAntennaMinFrequency(1000.0)
            self.equipment_limits.setAntennaMaxFrequency(18000.0)
            self.antenna_gain = 5.0
            self.label_antennaStats.setText('Min Freq: 1 GHz\nMax Freq: 18 GHz')
        elif antenna == 'TekBox TBMA4':
            self.equipment_limits.setAntennaMinFrequency(1000.0)
            self.equipment_limits.setAntennaMaxFrequency(6000.0)
            self.antenna_gain = 9.0
            self.label_antennaStats.setText('Min Freq: 1 GHz\nMax Freq: 6 GHz')
        elif antenna == '--Please Select--':
            self.pushButton_startSweep.setEnabled(False)
            self.pushButton_rfOn.setEnabled(False)
            return
        self.applyFrequencyLimits(self.spinBox_startFreq.value(), self.spinBox_stopFreq.value())
                
    def on_spinBox_targetStrength_valueChanged(self, target):
        print(f"Spin box value changed: {target}")
        self.target_field_strength = float(target)
        self.field_controller.setTargetField(float(target))
        self.field_plot.rescale_plot(self.field_controller.getStartFrequency(), self.field_controller.getStopFrequency(), 0.0, (self.field_controller.getTargetField() * 3.0))
    
    def on_pushButton_rfState_pressed(self):
        if self.output_on:
            self.signal_generator.setRFOut(False)
            self.pushButton_rfOn.setText('RF Off')
        else:
            self.signal_generator.setRFOut(True)
            self.pushButton_rfOn.setText('RF On')
    
    def on_connectFieldProbeButton_pressed(self):
        self.field_probe.start()

    def on_connectSigGenButton_pressed(self):
        self.signal_generator.retryDetection()

    def toggleSweepUI(self, enabled: bool):
        self.spinBox_startFreq.setEnabled(enabled)
        self.spinBox_stopFreq.setEnabled(enabled)
        self.spinBox_dwell.setEnabled(enabled)
        
        
    def applyFrequencyLimits(self, start_freq: float, stop_freq: float) -> bool:
        print(f"Start Frequency: {start_freq}, Stop Frequency: {stop_freq}, Min: {self.equipment_limits.getMinFrequency()}, Max: {self.equipment_limits.getMaxFrequency()}")
        if start_freq < self.equipment_limits.getMinFrequency() or stop_freq < self.equipment_limits.getMinFrequency():
            self.label_validSettings.setText('Invalid Setting: Frequency Too Low')
            self.label_validSettings.setStyleSheet('color: red')
            self.pushButton_startSweep.setEnabled(False)
            self.pushButton_rfOn.setEnabled(False)
            valid = False
        elif start_freq > self.equipment_limits.getMaxFrequency() or stop_freq > self.equipment_limits.getMaxFrequency():
            self.label_validSettings.setText('Invalid Setting: Frequency Too High')
            self.label_validSettings.setStyleSheet('color: red')
            self.pushButton_startSweep.setEnabled(False)
            self.pushButton_rfOn.setEnabled(False)
            valid = False
        else:
            self.label_validSettings.setText('Valid Settings')
            self.label_validSettings.setStyleSheet('color: green')
            self.pushButton_startSweep.setEnabled(True)
            self.pushButton_rfOn.setEnabled(True)
            valid = True
        return valid
    
    @pyqtSlot(str)            
    def on_fieldController_highFieldDetected(self, message: str):
        self.displaySingleAlert(f"High Field Detected. Check log at {message} for details.")
        #self.field_controller.stop_sweep()

    def on_spinBox_startFreq_valueChanged(self, freq: float):
        print(f"Spin box value changed: Types: {type(freq)}")
        valid = self.applyFrequencyLimits(float(freq), self.spinBox_stopFreq.value())
        if valid:
            self.field_controller.setStartFrequency(float(freq))
            self.field_controller.setStopFrequency(self.spinBox_stopFreq.value())
            self.start_freq = float(freq)
            self.stop_freq = self.spinBox_stopFreq.value()
            self.reset_sweep_plot_view()
            
    def on_spinBox_stopFreq_valueChanged(self, freq: float):
        valid = self.applyFrequencyLimits(self.spinBox_startFreq.value(), float(freq))
        if valid:
            self.field_controller.setStopFrequency(float(freq))
            self.field_controller.setStartFrequency(self.spinBox_startFreq.value())
            self.stop_freq = float(freq)
            self.start_freq = self.spinBox_stopFreq.value()
            self.reset_sweep_plot_view()

    def on_spinBox_dwell_valueChanged(self, time: float):
        self.dwell_time = float(time)
        self.field_controller.setDwellTime(float(time), self.comboBox_dwellUnit.currentText())
        self.reset_sweep_plot_view()
            
    def on_comboBox_dwellUnit_activated(self):
        # Capture Spec Floor
        if self.comboBox_dwellUnit.currentText() == Time.Millisecond.value:
            if self.spinBox_dwell.value() < 0.00105:
                self.spinBox_dwell.setValue(0.00105)

    def on_spinBox_sweepTerm_valueChanged(self, term: float):
        print("Sweep Term: " + str(term))
        self.sweep_term = float(term)
        self.field_controller.setSweepTerm(float(term))
        self.reset_sweep_plot_view()
    
    def reset_sweep_plot_view(self):
        self.sweep_plot.init_plot(0.0, self.field_controller.getSweepTime(), self.field_controller.getStartFrequency(), self.field_controller.getStopFrequency())
        self.field_plot.rescale_plot(self.field_controller.getStartFrequency(), self.field_controller.getStopFrequency(), 0.0, (self.field_controller.getTargetField() * 3.0))
    
    def on_pushButton_startSweep_pressed(self):
        if self.field_controller.is_sweeping:
            print("Push Button Stop Sweep")
            #self.sweep_in_progress = False
            #self.toggleSweepUI(enabled=True)
            self.pushButton_startSweep.setText('Sweep Off')
            self.progressBar_freqSweep.setHidden(True)
            self.field_controller.stop_sweep()
        else:
            print("Push Button Start Sweep")
            self.sweep_plot.clear_plot()
            self.sweep_start_time = time.time()
            #self.sweep_in_progress = True
            self.sweep_timer.start(100)  # Update every 100 ms
            self.field_timer.start(100)  # Update every 10 ms
            self.pushButton_startSweep.setText('Sweep On')
            self.progressBar_freqSweep.setHidden(False)
            #self.toggleSweepUI(enabled=False)
            self.field_controller.start_sweep()
    
    '''   
    def on_pushButton_pauseSweep_pressed(self):
        self.field_controller.stop_sweep()
    ''' 
    
    def complete_sweep(self):    
        self.sweep_timer.stop()
        self.toggleSweepUI(enabled=True)
                
    def spinBox_modDepth_valueChanged(self, percent: float):
        self.signal_generator.setAMLinearDepth(float(percent))
    
    def applyModFrequencyUnits(self, freq: float, unit: str) -> (float, str):
        if unit == Frequency.Hz.value:
            if freq < 0.1:
                freq = 0.1
            elif freq > 1000.0:
                freq /= 1000.0
                unit = Frequency.kHz.value
        elif unit == Frequency.kHz.value:
            if freq > 10000.0:
                freq /= 1000.0
                unit = Frequency.MHz.value
            elif freq < 0.1:
                freq *= 1000.0
                unit = Frequency.Hz.value
        elif unit == Frequency.MHz.value:
            if freq > 20.0:
                freq = 20.0
            elif freq < 0.1:
                freq *= 1000.0
                unit = Frequency.kHz.value
        else:
            freq = 1.0
            unit = Frequency.kHz.value
        return float(freq), str(unit)
    
    def spinBox_modFreq_valueChanged(self, freq: float):
        if freq > 20000.0 or freq < 0.0001:
            self.label_validSettings.setText('Invalid AM Frequency Setting')
            self.label_validSettings.setStyleSheet('color: red')
            self.pushButton_modulationOn.setEnabled(False)
            return
        self.label_validSettings.setText('Valid Settings')
        self.label_validSettings.setStyleSheet('color: green')
        self.pushButton_modulationOn.setEnabled(True)
        self.signal_generator.setAMFrequency(freq)
        
    def pushButton_modulationState_pressed(self):
        if self.modulation_on:
            self.pushButton_modulationOn.setText('Modulation Off')
            self.signal_generator.setModulationState(False)
        else:
            self.pushButton_modulationOn.setText('Modulation On')
            self.signal_generator.setModulationState(True)
        
    def displayAlert(self, text):
        self.alert = QMessageBox()
        self.alert.setText(text)
        self.alert.exec()
        
    def displaySingleAlert(self, text):
        if self.single_alert_window is not None:
            return
        self.single_alert_window = QMessageBox(self)
        self.single_alert_window.setIcon(QMessageBox.Warning)
        self.single_alert_window.setText(text)
        self.single_alert_window.setWindowTitle('Alert')
        self.single_alert_window.setStandardButtons(QMessageBox.Ok)
        self.single_alert_window.buttonClicked.connect(self.on_single_alert_button_clicked)
        self.single_alert_window.show()
        
    def on_single_alert_button_clicked(self, button):
        self.single_alert_window.close()
        self.single_alert_window = None
    
    @pyqtSlot(str, str, str, str)
    def on_fieldProbe_identityReceived(self, model: str, revision: str, serial: str, calibration: str):
        self.pushButton_detectFieldProbe.hide()
        pixmap = QPixmap('HI-6006.png')
        scaledPixmap = pixmap.scaled(275, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_fieldProbe.setPixmap(scaledPixmap)
        self.label_fieldProbeName.setText('ETS Lindgren ' + model + ' Serial: ' + serial)

    @pyqtSlot(float, float, float, float)
    def on_fieldProbe_fieldIntensityReceived(self, x: float, y: float, z: float, composite: float):
        self.measured_field_strength = composite
        self.updateFieldStrengthUI(composite, x, y, z)
            
    def calculatePowerOut(self) -> float:
        power_watts = (math.pow(self.pid_controller.getTargetValue(), 2) * math.pow(self.distance, 2)) / (30.0 * self.antenna_gain)
        power_dbm = 10 * math.log10(power_watts * 1000)
        power_dbm -= self.amplifier_gain
        #print(f"Power in dBm: {power_dbm}")
        return power_dbm
    
    def updateFieldStrengthUI(self, composite: float, x: float, y: float, z: float):
        self.lcdNumber_avgStrength.display(composite)
        self.lcdNumber_xMag.display(x)
        self.lcdNumber_yMag.display(y)
        self.lcdNumber_zMag.display(z)
    
    def on_fieldController_fieldUpdated(self, composite: float, x, y, z):
        self.lcdNumber_avgStrength.display(composite)
        self.lcdNumber_xMag.display(x)
        self.lcdNumber_yMag.display(y)
        self.lcdNumber_zMag.display(z)
        self.measured_field_strength = composite
        self.x_field = x
        self.y_field = y
        self.z_field = z
        
    def update_field_data_plot(self):
        self.field_plot.update_plot(self.output_frequency, setpoint = self.field_controller.getTargetField(), composite=self.measured_field_strength, x=self.x_field, y=self.y_field, z=self.z_field)
    
    def on_fieldProbe_batteryReceived(self, level: int):
        self.label_chargeLevel.setText(f'{str(level)} %')
        
    def on_fieldProbe_temperatureReceived(self, temp: float):
        self.label_temperature.setText(f'{str(temp)} °F')
    
    def on_fieldProbe_fieldProbeError(self, message: str):
        self.displaySingleAlert("ETS-Lindgren HI-6006:" + message)
        
    def on_fieldProbe_serialConnectionError(self, message: str):
        self.displaySingleAlert("Probe Connection:" + message)
    
    def on_sigGen_rfOutSet(self, on: bool):
        if on:
            self.field_plot.clear_plot()
            pixmap = QPixmap('broadcast-on.png')
            self.power_start_time = time.time()
            self.field_timer.start(100)  # Update every 100 ms
            self.pushButton_rfOn.setText('RF On')
        else:
            pixmap = QPixmap('broadcast-off.png')
            self.field_timer.stop()
            self.pushButton_rfOn.setText('RF Off')
        scaledPixmap = pixmap.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_rfOutState.setPixmap(scaledPixmap)
        self.output_on = on
        if self.comboBox_amplifier.currentIndex() == 0 or self.comboBox_antenna.currentIndex() == 0:
            self.pushButton_startSweep.setEnabled(False)
            self.pushButton_rfOn.setEnabled(False)
            self.label_validSettings.setText('Please Select Antenna and Amplifier')
            self.label_validSettings.setStyleSheet('color: red')
        self.field_controller.pid_controller.clear()
    
    def on_sigGen_instrumentDetected(self, detected: bool):
        if detected:
            self.signal_generator.stopDetection()
            self.signal_generator.connect()
        else:
            self.signal_generator.retryDetection()
            if not self.alerted:
                self.displaySingleAlert("Signal Generator Disconnected. Please connect via LAN.")
                self.alerted = True        
    
    def on_sigGen_instrumentConnected(self, message: str):
        self.pushButton_detectSigGen.hide()
        identity = message.split(',')
        company = identity[0]
        model = identity[1]
        serial = identity[2]
        self.label_sigGenName.setText(company + ' ' + model + ' Serial: ' + serial)
        pixmap = QPixmap('AgilentN5181A.png')
        scaledPixmap = pixmap.scaled(275, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)
        self.label_sigGen.setPixmap(scaledPixmap)
        # Initialize sig gen to match UI
        self.signal_generator.setRFOut(False)
        self.signal_generator.setModulationState(False)
        self.signal_generator.setStartFrequency(300.0)
        self.signal_generator.setStopFrequency(1000.0)
        self.signal_generator.setFrequency(300.0, Frequency.MHz.value)
        self.signal_generator.setPower(-30.0)
        
    def on_fieldController_frequencySet(self, frequency: float):
        print("Frequency Set: " + str(frequency))
        self.output_frequency = frequency
        self.lcdNumber_freqOut.display(round(frequency, 9))
        #self.sweep_plot.update_plot(time.time() - self.sweep_start_time, frequency)
        
    def update_sweep_plot(self):
        t = time.time() - self.sweep_start_time
        #print("Elapsed Time: " + str(t) + " Current Frequency: " + str(self.output_frequency))
        self.sweep_plot.update_plot(t, self.output_frequency)
    
    def on_fieldController_powerUpdated(self, power: float):
        self.output_power = power
        print("Power Set: " + str(self.output_power))
        self.lcdNumber_powerOut.display(power)
    
    def on_fieldController_sweepCompleted(self):
        self.complete_sweep()
        
    def on_fieldController_sweepStatus(self, percent: float):
        self.lcdNumber_sweepProgress.display(percent)
        self.progressBar_freqSweep.setValue(int(percent))
        
    def on_sigGen_modStateSet(self, on: bool):
        if on:
            self.pushButton_modulationOn.setText('Modulation On')
        else:
            self.pushButton_modulationOn.setText('Modulation Off')
        #self.pushButton_modulationOff.setEnabled(on)
        self.modulation_on = on
    
    def on_sigGen_modFrequencySet(self, modType: int, frequency: float):
        self.spinBox_modFreq.valueChanged.disconnect()
        self.spinBox_modFreq.setValue(frequency)
        self.spinBox_modFreq.valueChanged[float].connect(self.spinBox_modFreq_valueChanged)
    
    def on_sigGen_modDepthSet(self, depth: float):
        self.spinBox_modDepth.valueChanged.disconnect()
        self.spinBox_modDepth.setValue(depth)
        self.spinBox_modDepth.valueChanged.connect(self.spinBox_modDepth_valueChanged)
    
    def on_sigGen_amTypeSet(self, linear: bool):
        if linear:
            self.label_modUnit.setText('%')
        else:
            self.label_modUnit.setText('dBm')
        
    def on_sigGen_error(self, message: str):
        print("Signal Generator Error: " + message)
        #self.field_controller.stop_sweep()
        self.displaySingleAlert(message)
    
    def closeEvent(self, event):
        self.field_probe.stop()
        self.signal_generator.stop()
        self.field_controller_thread.quit()
        del self.field_probe
        del self.signal_generator
        del self.field_controller
        QApplication.quit()
        sys.exit()

        
if __name__ == '__main__':

    app = QApplication(sys.argv)
    #app.setWindowIcon(QtGui.QIcon(':/icons/field_controller.ico'))
    window = MainWindow()
    
    apply_stylesheet(app, theme='dark_cyan.xml')
    window.show()
    #app.aboutToQuit(window.killThreads())
    signal.signal(signal.SIGINT, window.closeEvent)
    sys.exit(app.exec_())