from PyQt5.QtWidgets import *

class ConductedImmunity(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(ConductedImmunity, self).__init__(*args, **kwargs)
        self.setWindowTitle('Conducted Immunity')