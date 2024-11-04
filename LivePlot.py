from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

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
        
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Frequency (MHz)')
        self.ax.set_title('Frequency Sweep')
        

    def init_plot(self, x_min: float = 0.0, x_max: float = 100.0, y_min: float = 0.0, y_max: float = 500.0):
        print("Initializing plot: x_min = {}, x_max = {}, y_min = {}, y_max = {}".format(x_min, x_max, y_min, y_max))
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw_idle()
        return self.line,

    def update_plot(self, time: float, freq: float):
        #print("Updating plot: x = {}, y = {}".format(x, y))
        self.x_data.append(time)
        self.y_data.append(freq)
        if (time > self.ax.get_xlim()[1]):
            self.ax.set_xlim(self.x_data[0], self.x_data[-1] + 0.1)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()

        self.draw_idle()
        return self.line,
    
    def clear_plot(self):
        print("Clearing plot")
        self.x_data.clear()
        self.y_data.clear()
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
        self.freq_data = []
        self.setpoint_data = []
        self.composite_data = []
        self.x_data = []
        self.y_data = []
        self.z_data = []
        
        self.line1, = self.ax.plot(self.freq_data, self.setpoint_data, '-b', label='Setpoint')
        self.line2, = self.ax.plot(self.freq_data, self.composite_data, '-r', label='Composite')
        self.line3, = self.ax.plot(self.freq_data, self.x_data, '-g', label='X')
        self.line4, = self.ax.plot(self.freq_data, self.y_data, '-c', label='Y')
        self.line5, = self.ax.plot(self.freq_data, self.z_data, '-y', label='Z')
        
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.set_xlabel('Frequency (MHz)')
        self.ax.set_ylabel('E-Field (V/m)')
        self.ax.set_title('Field Strength')
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
    
    def clear_plot(self):
        print("Clearing plot")
        self.freq_data.clear()
        self.setpoint_data.clear()
        self.composite_data.clear()
        self.x_data.clear()
        self.y_data.clear()
        self.z_data.clear()
        
        #self.ax.set_xlim(0, self.ax.get_xlim()[1] - self.ax.get_xlim()[0])
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw_idle()
        return self.line1, self.line2, self.line3, self.line4, self.line5

    def update_plot(self, freq: float, setpoint: float, composite: float, x: float, y: float, z: float):
        print("Updating plot: freq = {}, setpoint = {}, composite = {}, x = {}, y = {}, z = {}".format(freq, setpoint, composite, x, y, z))
        self.freq_data.append(freq)
        self.setpoint_data.append(setpoint)
        self.composite_data.append(composite)
        self.x_data.append(x)
        self.y_data.append(y)
        self.z_data.append(z)
        '''
        if (freq > self.ax.get_xlim()[1]):
            self.freq_data.pop(0)
            self.setpoint_data.pop(0)
            self.composite_data.pop(0)
            self.x_data.pop(0)
            self.y_data.pop(0)
            self.z_data.pop(0)
            self.ax.set_xlim(self.freq_data[0], self.freq_data[-1] + 0.1)
        '''    
        self.line1.set_data(self.freq_data, self.setpoint_data)
        self.line2.set_data(self.freq_data, self.composite_data)
        self.line3.set_data(self.freq_data, self.x_data)
        self.line4.set_data(self.freq_data, self.y_data)
        self.line5.set_data(self.freq_data, self.z_data)
        
        self.ax.relim()
        self.ax.autoscale_view()

        self.draw_idle()
        
        return self.line1, self.line2, self.line3, self.line4, self.line5