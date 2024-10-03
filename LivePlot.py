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
        self.ax.set_title('Frequency Sweep')
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
    
class PowerPlot(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Create a Figure and Canvas
        plt.ion()
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Data to plot
        self.time_data = []
        self.setpoint_data = []
        self.composite_data = []
        self.x_data = []
        self.y_data = []
        self.z_data = []
        
        self.line1, = self.ax.plot(self.time_data, self.setpoint_data, '-b', label='Setpoint')
        self.line2, = self.ax.plot(self.time_data, self.composite_data, '-r', label='Composite')
        self.line3, = self.ax.plot(self.time_data, self.x_data, '-g', label='X')
        self.line4, = self.ax.plot(self.time_data, self.y_data, '-c', label='Y')
        self.line5, = self.ax.plot(self.time_data, self.z_data, '-y', label='Z')
        
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('E-Field (V/m)')
        self.ax.set_title('Field Intensity')
        self.ax.legend()
        self.draw_idle()
        

    def rescale_plot(self, x_min: float = 0.0, x_max: float = 10.0, y_min: float = 0.0, y_max: float = 10.0):
        print("Rescaling plot: x_min = {}, x_max = {}, y_min = {}, y_max = {}".format(x_min, x_max, y_min, y_max))
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw_idle()
        return self.line1, self.line2, self.line3, self.line4, self.line5

    def update_plot(self, time: float, setpoint: float, composite: float, x: float, y: float, z: float):
        print("Updating plot: time = {}, composite = {}, x = {}, y = {}, z = {}".format(time, setpoint, composite, x, y, z))
        self.time_data.append(time)
        self.setpoint_data.append(setpoint)
        self.composite_data.append(composite)
        self.x_data.append(x)
        self.y_data.append(y)
        self.z_data.append(z)
        
        if (time > self.ax.get_xlim()[1]):
            self.time_data.pop(0)
            self.setpoint_data.pop(0)
            self.composite_data.pop(0)
            self.x_data.pop(0)
            self.y_data.pop(0)
            self.z_data.pop(0)
            self.ax.set_xlim(self.time_data[0], self.time_data[-1] + 1)
            
        self.line1.set_data(self.time_data, self.setpoint_data)
        self.line2.set_data(self.time_data, self.composite_data)
        self.line3.set_data(self.time_data, self.x_data)
        self.line4.set_data(self.time_data, self.y_data)
        self.line5.set_data(self.time_data, self.z_data)
        
        self.ax.relim()
        self.ax.autoscale_view()

        self.draw_idle()
        
        return self.line1, self.line2, self.line3, self.line4, self.line5