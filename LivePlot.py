import sys
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class FrequencyPlot(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Create a Figure and Canvas
        plt.ion()
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Data to plot
        self.x_data = []
        self.y_data = []
        
        self.line, = self.ax.plot(self.x_data, self.y_data, '-g')
        

    def init_plot(self, x_min: float = 0.0, x_max: float = 100.0, y_min: float = 0.0, y_max: float = 500.0):
        print("Initializing plot: x_min = {}, x_max = {}, y_min = {}, y_max = {}".format(x_min, x_max, y_min, y_max))
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Frequency (Hz)')
        self.ax.set_title('Frequency vs Time')
        self.draw_idle()
        return self.line,

    def update_plot(self, x: float, y: float):
        print("Updating plot: x = {}, y = {}".format(x, y))
        self.x_data.append(x)
        self.y_data.append(y)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()

        self.draw_idle()
        return self.line,