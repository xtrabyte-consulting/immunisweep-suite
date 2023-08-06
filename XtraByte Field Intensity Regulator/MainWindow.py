# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'MainWindow.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(827, 627)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(13, 0, 1062, 571))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout_3 = QtWidgets.QGridLayout()
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.horizontalLayout.setContentsMargins(-1, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.linearSweepButton = QtWidgets.QRadioButton(self.gridLayoutWidget)
        self.linearSweepButton.setChecked(True)
        self.linearSweepButton.setObjectName("linearSweepButton")
        self.horizontalLayout.addWidget(self.linearSweepButton)
        self.expSweepButton = QtWidgets.QRadioButton(self.gridLayoutWidget)
        self.expSweepButton.setCheckable(False)
        self.expSweepButton.setObjectName("expSweepButton")
        self.horizontalLayout.addWidget(self.expSweepButton)
        self.sweepOffButton = QtWidgets.QRadioButton(self.gridLayoutWidget)
        self.sweepOffButton.setCheckable(True)
        self.sweepOffButton.setObjectName("sweepOffButton")
        self.horizontalLayout.addWidget(self.sweepOffButton)
        self.gridLayout_3.addLayout(self.horizontalLayout, 1, 1, 1, 1)
        self.stopFreqLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.stopFreqLabel.setObjectName("stopFreqLabel")
        self.gridLayout_3.addWidget(self.stopFreqLabel, 2, 0, 1, 1)
        self.stepDwellBox = QtWidgets.QDoubleSpinBox(self.gridLayoutWidget)
        self.stepDwellBox.setMinimum(1.05)
        self.stepDwellBox.setMaximum(2000.0)
        self.stepDwellBox.setProperty("value", 1.05)
        self.stepDwellBox.setObjectName("stepDwellBox")
        self.gridLayout_3.addWidget(self.stepDwellBox, 3, 1, 1, 1)
        self.pauseButton = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.pauseButton.setObjectName("pauseButton")
        self.gridLayout_3.addWidget(self.pauseButton, 8, 1, 1, 1)
        self.startButton = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.startButton.setObjectName("startButton")
        self.gridLayout_3.addWidget(self.startButton, 8, 0, 1, 1)
        self.label = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label.setObjectName("label")
        self.gridLayout_3.addWidget(self.label, 1, 0, 1, 1)
        self.freqStopBox = QtWidgets.QDoubleSpinBox(self.gridLayoutWidget)
        self.freqStopBox.setMinimum(0.25)
        self.freqStopBox.setMaximum(6000.0)
        self.freqStopBox.setProperty("value", 6000.0)
        self.freqStopBox.setObjectName("freqStopBox")
        self.gridLayout_3.addWidget(self.freqStopBox, 2, 1, 1, 1)
        self.stepDwellLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.stepDwellLabel.setObjectName("stepDwellLabel")
        self.gridLayout_3.addWidget(self.stepDwellLabel, 3, 0, 1, 1)
        self.freqStartBox = QtWidgets.QDoubleSpinBox(self.gridLayoutWidget)
        self.freqStartBox.setMinimum(0.1)
        self.freqStartBox.setMaximum(6000.0)
        self.freqStartBox.setStepType(QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType)
        self.freqStartBox.setProperty("value", 0.1)
        self.freqStartBox.setObjectName("freqStartBox")
        self.gridLayout_3.addWidget(self.freqStartBox, 0, 1, 1, 1)
        self.amFreqBox = QtWidgets.QDoubleSpinBox(self.gridLayoutWidget)
        self.amFreqBox.setMinimum(0.1)
        self.amFreqBox.setMaximum(5.0)
        self.amFreqBox.setProperty("value", 1.0)
        self.amFreqBox.setObjectName("amFreqBox")
        self.gridLayout_3.addWidget(self.amFreqBox, 7, 1, 1, 1)
        self.stepCountBox = QtWidgets.QSpinBox(self.gridLayoutWidget)
        self.stepCountBox.setMinimum(1)
        self.stepCountBox.setMaximum(100000)
        self.stepCountBox.setProperty("value", 1)
        self.stepCountBox.setDisplayIntegerBase(10)
        self.stepCountBox.setObjectName("stepCountBox")
        self.gridLayout_3.addWidget(self.stepCountBox, 4, 1, 1, 1)
        self.amDepthBox = QtWidgets.QDoubleSpinBox(self.gridLayoutWidget)
        self.amDepthBox.setObjectName("amDepthBox")
        self.gridLayout_3.addWidget(self.amDepthBox, 6, 1, 1, 1)
        self.setFreqStartLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.setFreqStartLabel.setObjectName("setFreqStartLabel")
        self.gridLayout_3.addWidget(self.setFreqStartLabel, 0, 0, 1, 1)
        self.modulationLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.modulationLabel.setObjectName("modulationLabel")
        self.gridLayout_3.addWidget(self.modulationLabel, 5, 0, 1, 1)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.ampModButton = QtWidgets.QRadioButton(self.gridLayoutWidget)
        self.ampModButton.setObjectName("ampModButton")
        self.horizontalLayout_2.addWidget(self.ampModButton)
        self.phaseModButton = QtWidgets.QRadioButton(self.gridLayoutWidget)
        self.phaseModButton.setCheckable(False)
        self.phaseModButton.setObjectName("phaseModButton")
        self.horizontalLayout_2.addWidget(self.phaseModButton)
        self.modOffButton = QtWidgets.QRadioButton(self.gridLayoutWidget)
        self.modOffButton.setChecked(True)
        self.modOffButton.setObjectName("modOffButton")
        self.horizontalLayout_2.addWidget(self.modOffButton)
        self.gridLayout_3.addLayout(self.horizontalLayout_2, 5, 1, 1, 1)
        self.stepCountLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.stepCountLabel.setObjectName("stepCountLabel")
        self.gridLayout_3.addWidget(self.stepCountLabel, 4, 0, 1, 1)
        self.depthLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.depthLabel.setObjectName("depthLabel")
        self.gridLayout_3.addWidget(self.depthLabel, 6, 0, 1, 1)
        self.modFreqLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.modFreqLabel.setObjectName("modFreqLabel")
        self.gridLayout_3.addWidget(self.modFreqLabel, 7, 0, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_3, 1, 0, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.setFieldIntensityBox = QtWidgets.QDoubleSpinBox(self.gridLayoutWidget)
        self.setFieldIntensityBox.setObjectName("setFieldIntensityBox")
        self.gridLayout_2.addWidget(self.setFieldIntensityBox, 2, 1, 1, 1)
        self.currentFieldIntesityLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.currentFieldIntesityLabel.setObjectName("currentFieldIntesityLabel")
        self.gridLayout_2.addWidget(self.currentFieldIntesityLabel, 3, 0, 1, 1)
        self.fieldProbeLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.fieldProbeLabel.setObjectName("fieldProbeLabel")
        self.gridLayout_2.addWidget(self.fieldProbeLabel, 0, 1, 1, 1)
        self.fieldIntensityLcd = QtWidgets.QLCDNumber(self.gridLayoutWidget)
        self.fieldIntensityLcd.setSmallDecimalPoint(False)
        self.fieldIntensityLcd.setDigitCount(5)
        self.fieldIntensityLcd.setProperty("value", 5.0)
        self.fieldIntensityLcd.setObjectName("fieldIntensityLcd")
        self.gridLayout_2.addWidget(self.fieldIntensityLcd, 3, 1, 1, 1)
        self.sigGenLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.sigGenLabel.setObjectName("sigGenLabel")
        self.gridLayout_2.addWidget(self.sigGenLabel, 0, 0, 1, 1)
        self.connectSigGenButton = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.connectSigGenButton.setMinimumSize(QtCore.QSize(175, 0))
        self.connectSigGenButton.setObjectName("connectSigGenButton")
        self.gridLayout_2.addWidget(self.connectSigGenButton, 1, 0, 1, 1)
        self.controlLoopAdjLcd = QtWidgets.QLCDNumber(self.gridLayoutWidget)
        self.controlLoopAdjLcd.setSmallDecimalPoint(False)
        self.controlLoopAdjLcd.setDigitCount(5)
        self.controlLoopAdjLcd.setProperty("value", 0.0)
        self.controlLoopAdjLcd.setProperty("intValue", 0)
        self.controlLoopAdjLcd.setObjectName("controlLoopAdjLcd")
        self.gridLayout_2.addWidget(self.controlLoopAdjLcd, 4, 1, 1, 1)
        self.connectFieldProbeButton = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.connectFieldProbeButton.setMinimumSize(QtCore.QSize(175, 0))
        self.connectFieldProbeButton.setObjectName("connectFieldProbeButton")
        self.gridLayout_2.addWidget(self.connectFieldProbeButton, 1, 1, 1, 1)
        self.desiredIntensityLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.desiredIntensityLabel.setObjectName("desiredIntensityLabel")
        self.gridLayout_2.addWidget(self.desiredIntensityLabel, 2, 0, 1, 1)
        self.currentOutputLabel = QtWidgets.QLabel(self.gridLayoutWidget)
        self.currentOutputLabel.setObjectName("currentOutputLabel")
        self.gridLayout_2.addWidget(self.currentOutputLabel, 4, 0, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 0, 0, 1, 1)
        self.topGraphicsView = QtWidgets.QGraphicsView(self.gridLayoutWidget)
        self.topGraphicsView.setObjectName("topGraphicsView")
        self.gridLayout.addWidget(self.topGraphicsView, 0, 1, 1, 1)
        self.bottomGraphicsView = QtWidgets.QGraphicsView(self.gridLayoutWidget)
        self.bottomGraphicsView.setObjectName("bottomGraphicsView")
        self.gridLayout.addWidget(self.bottomGraphicsView, 1, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 827, 24))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.linearSweepButton.setText(_translate("MainWindow", "Lin"))
        self.expSweepButton.setText(_translate("MainWindow", "Log"))
        self.sweepOffButton.setText(_translate("MainWindow", "Off"))
        self.stopFreqLabel.setText(_translate("MainWindow", "Stop Frequency (MHz):"))
        self.pauseButton.setText(_translate("MainWindow", "Pause"))
        self.startButton.setText(_translate("MainWindow", "Start"))
        self.label.setText(_translate("MainWindow", "Frequency Sweep:"))
        self.stepDwellLabel.setText(_translate("MainWindow", "Step Dwell (ms):"))
        self.setFreqStartLabel.setText(_translate("MainWindow", "Start Frequency (MHz):"))
        self.modulationLabel.setText(_translate("MainWindow", "Modulation:"))
        self.ampModButton.setText(_translate("MainWindow", "AM"))
        self.phaseModButton.setText(_translate("MainWindow", "ΦM"))
        self.modOffButton.setText(_translate("MainWindow", "Off"))
        self.stepCountLabel.setText(_translate("MainWindow", "Step Count:"))
        self.depthLabel.setText(_translate("MainWindow", "Depth (%):"))
        self.modFreqLabel.setText(_translate("MainWindow", "Frequency (kHz):"))
        self.currentFieldIntesityLabel.setText(_translate("MainWindow", "Current Field Intensity (V/m):"))
        self.fieldProbeLabel.setText(_translate("MainWindow", "Field Probe "))
        self.sigGenLabel.setText(_translate("MainWindow", "Signal Generator "))
        self.connectSigGenButton.setText(_translate("MainWindow", "Connect"))
        self.connectFieldProbeButton.setText(_translate("MainWindow", "Connect"))
        self.desiredIntensityLabel.setText(_translate("MainWindow", "Desired Field Intensity (V/m):"))
        self.currentOutputLabel.setText(_translate("MainWindow", "Current Output Power (dBm)"))
