from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import QTime, QDateTime
from PyQt5.QtWidgets import QMessageBox

import warnings
warnings.filterwarnings("ignore", "(?s).*MATPLOTLIBDATA.*", category=UserWarning)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from functools import partial

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import matplotlib as mpl

from MplWidget import MplWidget

import sys
import logging as log
import argparse
import itertools
import threading

from DataLoader import Data
from DateTimePicker import DateTimePicker

import time

LOG_FORMAT = "%(asctime)s %(levelname)-8s: %(message)s\t"
TIMESTAMP_FORMAT = '%d-%m-%YT%H:%M:%S'
COLOUR_ARR = ['crimson', 'silver', 'indigo', 'coral', 'saddlebrown', 'orange', 'black', 'olive', 'brown', 'navy', 'darkseagreen', 'red', 'teal', 'dodgerblue', 'deeppink']
POINT_ARR = ['o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd', 'P', 'X']
# Enter file here.
Ui_MainWindow, QtBaseClass = uic.loadUiType("datalogger.ui")

global colours, points

def genPointStyles(count):
	global colours, points

	colours = itertools.cycle(COLOUR_ARR[:count])
	points = itertools.cycle(POINT_ARR[:count])
	
def getGridSize(columnCount):
	if columnCount == 1:
		return "11"
	if columnCount == 2:
		return "21"
	if columnCount == 3:
		return "31"
	if columnCount == 4:
		return "22"
	if columnCount == 5 or columnCount == 6:
		return "32"
	if columnCount >= 7 and columnCount >= 9:
		return "33"
	if columnCount >= 10 and columnCount >= 12:
		return "43"
	log.warning("Unsupported data column count %d!" % (columnCount))
	sys.exit()
		
class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
	def __init__(self):
		#get initial CSV data
		self.data = Data()
		defaultStartDateTime, defaultEndDateTime = self.data.getTimestampRange()
		self.data.load(timeRange = [defaultStartDateTime, defaultEndDateTime])
		
		QtWidgets.QMainWindow.__init__(self)
		Ui_MainWindow.__init__(self)
		self.setupUi(self)
		self.startDateTimePicker = DateTimePicker(self, self.startDateTimeButton, defaultStartDateTime) 
		self.endDateTimePicker = DateTimePicker(self, self.endDateTimeButton, defaultEndDateTime) 
		self.startDateTimeButton.clicked.connect(self.onStartDateTimeClicked)
		self.endDateTimeButton.clicked.connect(self.onEndDateTimeClicked)
		
		self.startDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onDateTimeChanged)
		self.endDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onDateTimeChanged)
		
		self.onlineModeCheckBox.stateChanged.connect(self.setOnlineMode)
		self.plotData()
		
		self.showMaximized()
		
	def plotData(self):
		global colours, points
		genPointStyles(self.data.getColumnCount())
		
		series = self.data.headers
		time = self.data.table[series[0]]
		grid = getGridSize(self.data.getColumnCount()-1)
		for i in range (1, self.data.getColumnCount()):
			self.widget.canvas.setLayout(grid+str(i))
			self.widget.canvas.ax.scatter(time, 
									self.data.table[series[i]],
									c = next(colours),
									marker = next(points))
			self.widget.canvas.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
			self.widget.canvas.fig.autofmt_xdate()  
			self.widget.canvas.ax.set_xlabel (series[0], fontsize=10)
			self.widget.canvas.ax.set_ylabel (series[i], fontsize= 10)
			self.widget.canvas.ax.autoscale(enable=True, axis='both', tight=None)
		self.widget.canvas.draw()

		
	def onStartDateTimeClicked(self):
		self.startDateTimePicker.show()		
	
	def onEndDateTimeClicked(self):
		self.endDateTimePicker.show()	
		
	def onDateTimeChanged(self):
		status = self.data.load(timeRange = [self.startDateTimePicker.dateTimeEdit.dateTime(), 
							   self.endDateTimePicker.dateTimeEdit.dateTime()])
		if status != "":
			QMessageBox.warning(self, "Warning", status)
		else:
			self.widget.canvas.cla()
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
		self.endDateTimeButton.setEnabled(not status)
		self.data.setOnlineMode(status)
		
	def __onlinePlotThread(self):
		while self.onlineModeCheckBox.checkState() == 2:
			time.sleep(1)
			if self.data.newData == True:
				self.plotData()
				self.data.newData = False

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