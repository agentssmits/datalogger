from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import QTime, QDateTime
from PyQt5.QtWidgets import QMessageBox, QFileDialog

import warnings
warnings.filterwarnings("ignore", "(?s).*MATPLOTLIBDATA.*", category=UserWarning)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from functools import partial

import pandas as pd

import matplotlib as mpl

from MplWidget import MplWidget

import sys
import logging as log
import argparse
import threading
import os

from DataLoader import Data
from DateTimePicker import DateTimePicker

import time

# constants needed for logging of debug/warning/error messages
LOG_FORMAT = "%(asctime)s %(levelname)-8s: %(message)s\t"
TIMESTAMP_FORMAT = '%d-%m-%YT%H:%M:%S'

# specify *.ui file location for main window
Ui_MainWindow, QtBaseClass = uic.loadUiType("datalogger.ui")
		
class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
	def __init__(self):
		"""The constructor"""
		
		# default data time range corresponds to CSV start/end datetime
		self.data = Data()
		defaultStartDateTime, defaultEndDateTime = self.data.getTimestampRange()
		# get initial CSV data
		self.data.load(timeRange = [defaultStartDateTime, defaultEndDateTime])
		
		QtWidgets.QMainWindow.__init__(self)
		Ui_MainWindow.__init__(self)
		self.setupUi(self)
		
		# allow user to specify data root directory, by default it is current working directory
		os.chdir(os.path.dirname(__file__))
		self.rootSelEdit.setText(os.getcwd())
		self.rootSelBtn.clicked.connect(self.getDir)
		
		self.allStartDateTimePicker = DateTimePicker(self, self.allStartDateTimeButton, defaultStartDateTime) 
		self.allEndDateTimePicker = DateTimePicker(self, self.allEndDateTimeButton, defaultEndDateTime) 
		self.allStartDateTimeButton.clicked.connect(self.onAllEndDateTimeClicked)
		self.allEndDateTimeButton.clicked.connect(self.onAllEndDateTimeClicked)
		
		self.allStartDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onDateTimeChanged)
		self.allEndDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onDateTimeChanged)
		
		self.onlineModeCheckBox.stateChanged.connect(self.setOnlineMode)
		
		self.actionQuit.triggered.connect(self.quit)
		self.actionQuit.setShortcut('Q')
		
		self.showMaximized()
		
		self.widget.canvas.setLayout(self.data.headers)
		self.plotData()
		
		self.tabWidget.setCurrentIndex(1)
		
		self.selectedPlotNo = []
		checkBoxes = (self.gridLayout_6.itemAt(i).widget() for i in range(self.gridLayout_6.count())) 
		for checkBox in checkBoxes:
			checkBox.stateChanged.connect(self.checkCheckboxes)

	def plotData(self):
		self.widget.canvas.plot(self.data.headers, self.data.table)
				
	def onAllEndDateTimeClicked(self):
		self.allStartDateTimePicker.show()		
	
	def onAllEndDateTimeClicked(self):
		self.allEndDateTimePicker.show()	
		
	def onDateTimeChanged(self):
		status = self.data.load(timeRange = [self.allStartDateTimePicker.dateTimeEdit.dateTime(), 
							   self.allEndDateTimePicker.dateTimeEdit.dateTime()])
		if status != "":
			QMessageBox.warning(self, "Warning", status)
		else:
			#self.widget.canvas.cla()
			self.plotData()
			
	def setOnlineMode(self):
		if self.onlineModeCheckBox.checkState() == 0:
			status = False
			self.onlineThread.join()
			log.debug("Online plotting thread stopped")
		elif self.onlineModeCheckBox.checkState() == 2:
			status = True
			self.onlineThread = threading.Thread(target=self.__onlinePlotThread)
			self.onlineThread.daemon = True
			self.onlineThread.start()
			log.debug("Online plotting thread launched")
		else:
			return
		self.allEndDateTimeButton.setEnabled(not status)
		self.data.setOnlineMode(status)
		
	def __onlinePlotThread(self):
		while self.onlineModeCheckBox.checkState() == 2:
			time.sleep(1)
			if self.data.newData == True:
				#self.widget.canvas.cla()
				self.plotData()
				#self.plotUpdatedData()
				series = self.data.headers
				endTime = self.data.table[series[0]][-1]
				ts = pd.to_datetime(str(endTime)) 
				d = ts.strftime("%Y-%m-%d %H:%M:%S")
				self.allEndDateTimeButton.setText(d)
				self.allEndDateTimePicker.updateDateTime(d)
				self.data.newData = False
				
	def getDir(self):
		dir = QFileDialog.getExistingDirectory(
			self,
			"Select a folder",
			os.getcwd(),
			QFileDialog.ShowDirsOnly
		)
			
		self.rootSelEdit.setText(dir)
		return dir
		
	def checkCheckboxes(self):
		checkBoxes = [self.gridLayout_6.itemAt(i).widget() for i in range(self.gridLayout_6.count())] 
		for i in range(0, len(checkBoxes)):
			index = int(checkBoxes[i].text().split(" ")[1])+1
			if checkBoxes[i].isChecked():
				if index not in self.selectedPlotNo:
					self.selectedPlotNo.append(index)
			else:
				if index in self.selectedPlotNo:
					self.selectedPlotNo.remove(index)
		
		selectedHeaders = [self.data.headers[0]]
		for i in range(1, len(self.data.headers)):
			if i in self.selectedPlotNo:
				selectedHeaders.append(self.data.headers[i])

		self.widget_2.canvas.cla()
		if selectedHeaders != []:
			self.widget_2.canvas.initAxes()
			self.widget_2.canvas.setLayout(selectedHeaders)
			self.widget_2.canvas.plot(selectedHeaders, self.data.table)
		
	def quit(self):
		sys.exit(0)

if __name__ == "__main__":
	#parse input arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('-v', '--verbosity', action="count", 
                        help="-v: WARNING, -vv: INFO, -vvv: DEBUG")
	args = parser.parse_args()
	
	#setup verbosity level
	if args.verbosity:
		if args.verbosity >= 3:
			log.basicConfig(format=LOG_FORMAT,  datefmt=TIMESTAMP_FORMAT, level=log.DEBUG)
		elif args.verbosity == 2:
			log.basicConfig(format=LOG_FORMAT, datefmt=TIMESTAMP_FORMAT, level=log.INFO)
		elif args.verbosity == 1:
			log.basicConfig(format=LOG_FORMAT, datefmt=TIMESTAMP_FORMAT, level=log.WARNING)
		else:
			log.basicConfig(format=LOG_FORMAT, datefmt=TIMESTAMP_FORMAT, level=log.ERROR)

	log.getLogger('matplotlib.font_manager').disabled = True
	app = QtWidgets.QApplication(sys.argv)
	window = MyApp()
	window.show()
	sys.exit(app.exec_())