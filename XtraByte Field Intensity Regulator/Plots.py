import typing
import pglive
import pyqtgraph as pg
import numpy as np
from pyqtgraph import PlotWidget, plot
from pyqtgraph.Qt import QtGui, QtCore
from PyQt5.QtCore import QObject, QThread, QTimer
from PyQt5 import QtWidgets
import threading
import queue
from queue import Queue
from threading import Thread
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget

class PowerPlot(QtWidgets.QGraphicsScene):
    
    def __init__(self,  title="Field Intensity", labels={'left': "Power (dBm)", 'bottom': 'Time (sec)'}):
        super().__init__()
        self.powerPlotView = LivePlotWidget(title=title)
        self.powerPlot = LiveLinePlot(labels=labels)
        self.powerPlotView.addItem(self.powerPlot)
        self.dataConnector = DataConnector(self.powerPlot, max_points=300, update_rate=50)
        self.addWidget(self.powerPlotView)
        self.updateQueue = Queue()
        
        
    def startPlot(self):
        self.plotRunning = True
        self.updateThread = Thread(target=self.updatePlot)
        self.updateThread.start()
        
    def stopPot(self):
        self.plotRunning = False
        self.updateThread.join()
        
    def plotData(self, x, y):
        self.updateQueue.put((x, y))
        
    def updatePlot(self):
        while self.plotRunning:
            point = self.updateQueue.get()
            x, y = point[0], point[1]
            self.dataConnector.cb_append_data_point(x, y)
        
            
        

class FrquencyPlot(pg.GraphicsView):
    
    def __init__(self, parent = None, title = "Frquency") -> None:
        super().__init__(parent)
        
        self.verticalLayout = QtWidgets.QVBoxLayout()
        
        self.updateThread = threading.Thread(target=self.updateData)
        self.plotWidget = pg.PlotWidget(title=title, plotItem=self.plotItem)
        self.plot = pg.PlotItem(labels= {'left': "Frequency (MHz)", 'bottom': 'Time (sec)'}, title=title)
        
        self.data = np.array([[]])
        self.plot.plot(self.data)
        self.curve = self.plotWidget.addItem()
        
        
        
        self.plotWidget.centralLayout = self.verticalLayout
        
        self.plotItem = pg.PlotDataItem()
        self.plotWidget.addItem(self.plot)
        self.addItem(self.plotWidget)
        self.plotItem.appendData()
    
        pg.Gra
        
        
    def updateData(self):
        self.__delattr__