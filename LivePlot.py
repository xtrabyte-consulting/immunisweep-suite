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
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Data to plot
        self.x_data = []
        self.y_data = []
        
        # Initialize an empty line on the plot
        self.line, = self.ax.plot(self.x_data, self.y_data, 'r-')
        
        # Animation function
        #self.anim = FuncAnimation(self.fig, self.update_plot, init_func=self.init_plot, interval=1000)
        
    def init_plot(self, x_min: float = 0.0, x_max: float = 100.0, y_min: float = 0.0, y_max: float = 6000.0):
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)
        self.line.set_data([], [])
        return self.line,
    
    def set_start_frequency(self, start_frequency: float):
        self.ax.set_xlim(0.0, None)
        self.ax.set_ylim(start_frequency, None)
        
    def set_stop_frequency(self, stop_frequency: float, steps: int, dwell_time: float):
        self.ax.set_xlim(0.0, (steps * dwell_time))
        self.ax.set_ylim(None, stop_frequency)

    def update_plot(self, x: float, y: float):
        self.x_data.append(x)
        self.y_data.append(y)
        self.line.set_data(self.x_data, self.y_data)
        #self.ax.relim()
        return self.line,