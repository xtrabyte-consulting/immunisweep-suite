
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDoubleSpinBox, QLabel, QDialogButtonBox

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