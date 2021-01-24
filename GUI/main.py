from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import QTime, QDateTime, QSettings
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QLineEdit, QSpinBox

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
		
		self.selectedHeaders = []
		
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
		
		# handle custom datetime selection for tab 'all'
		self.allStartDateTimePicker = DateTimePicker(self, self.allStartDateTimeButton, defaultStartDateTime, title = "Select start datetime for plotting all data") 
		self.allEndDateTimePicker = DateTimePicker(self, self.allEndDateTimeButton, defaultEndDateTime, title = "Select end datetime for plotting all data") 
		self.allStartDateTimeButton.clicked.connect(self.onAllStartDateTimeClicked)
		self.allEndDateTimeButton.clicked.connect(self.onAllEndDateTimeClicked)
		
		self.allStartDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onAllDateTimeChanged)
		self.allEndDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onAllDateTimeChanged)
		
		self.onlineAllModeCheckBox.stateChanged.connect(self.setOnlineMode)
		
		# handle custom datetime selection for tab 'custom'
		self.customStartDateTimePicker = DateTimePicker(self, self.customStartDateTimeButton, defaultStartDateTime, title = "Select start datetime for plotting custom data") 
		self.customEndDateTimePicker = DateTimePicker(self, self.customEndDateTimeButton, defaultEndDateTime, title = "Select end datetime for plotting custom data") 
		self.customStartDateTimeButton.clicked.connect(self.onCustomEndDateTimeClicked)
		self.customEndDateTimeButton.clicked.connect(self.onCustomEndDateTimeClicked)
		
		self.customStartDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onCustomDateTimeChanged)
		self.customEndDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onCustomDateTimeChanged)
		
		self.actionQuit.triggered.connect(self.quit)
		self.actionQuit.setShortcut('Q')
		
		self.showMaximized()
		
		self.allMplWidget.canvas.setLayout(self.data.headers)
		self.plotAllData()
		
		self.tabWidget.setCurrentIndex(1)
		
		# Get settings to restore checkboxes 
		self.settings = QSettings(".GUI_settings", QSettings.IniFormat)
		self.selectedPlotNo = []
		checkBoxes = (self.gridLayout_6.itemAt(i).widget() for i in range(self.gridLayout_6.count())) 
		for checkBox in checkBoxes:
			checkBox.setChecked(self.settings.value("custom_tab_1_selection/"+checkBox.text(), False, type=bool))
			# connect the slot to the signal by clicking the checkbox to save the state settings
			checkBox.clicked.connect(partial(self.saveCheckBoxSettings, checkBox))
			checkBox.stateChanged.connect(self.checkCheckboxes)
		
		# Get settings to restore tab names 	
		for id in range(2, self.tabWidget.count()-1):
			name = self.settings.value("tab_names/tab"+str(id), "none", type=str)
			if name != "none":
				self.tabWidget.tabBar().setTabText(id, name)
		
		# Get settings to restore fields in Settings tab
		widgets = self.settingsTab.findChildren(QLineEdit)
		for widget in widgets:
			if isinstance(widget, QLineEdit):
				value = self.settings.value("settings/"+str(widget.objectName()), "none", type=str)
				if value != "none":
					widget.setText(value)
					
		widgets = self.settingsTab.findChildren(QSpinBox)
		for widget in widgets:	
			if isinstance(widget, QSpinBox):
				value = self.settings.value("settings/"+str(widget.objectName()), 1, type=int)
				widget.setValue(value)
			
		# add custom plot tabs if needed
		print (self.customTabCount.value())
			
		self.checkCheckboxes()
		
		self.tabNameEditor = QLineEdit(self)
		self.tabNameEditor.setWindowFlags(QtCore.Qt.Popup)
		self.tabNameEditor.setFocusProxy(self)
		self.tabNameEditor.editingFinished.connect(self.handleTabEditingFinished)
		self.tabNameEditor.installEventFilter(self)
		
		self.tabWidget.tabBarDoubleClicked.connect(self.tabDoubleClickEvent)
		
		# save values of QLineEdit & QSpinBox widgets in Settings tab
		widgets = self.settingsTab.findChildren(QLineEdit)
		for widget in widgets:
			if isinstance(widget, QSpinBox):
				widget.textChanged.connect(partial(self.saveQSpinBox, widget))
				
		widgets = self.settingsTab.findChildren(QSpinBox)
		for widget in widgets:
			if isinstance(widget, QSpinBox):
				widget.textChanged.connect(partial(self.saveQSpinBox, widget))
				
	def saveQLineEdit(self, widget):
		self.settings.setValue("settings/"+ widget.objectName(), widget.text())
		self.settings.sync()
		
	def saveQSpinBox(self, widget):
		self.settings.setValue("settings/"+ widget.objectName(), widget.value())
		self.settings.sync()
		
	"""
	Detects double click on tab name and enables renaming
	This method does not affect tabs 0-1 and last tab
	"""
	def tabDoubleClickEvent(self):
		id = self.tabWidget.tabBar().currentIndex()
		if id >= 2 and id < self.tabWidget.count()-1:
			self.editTab(id)
		
	def editTab(self, id):
		rect = self.tabWidget.tabBar().tabRect(id)
		self.tabNameEditor.setFixedSize(rect.size())
		self.tabNameEditor.move(self.mapToGlobal(rect.topLeft()))
		self.tabNameEditor.setText(self.tabWidget.tabBar().tabText(id))
		if not self.tabNameEditor.isVisible():
			self.tabNameEditor.show()
			
	def handleTabEditingFinished(self):
		id = self.tabWidget.tabBar().currentIndex()
		if id >= 0:
			self.tabNameEditor.hide()
			self.tabWidget.tabBar().setTabText(id, self.tabNameEditor.text())
			self.saveTabNames(id, self.tabNameEditor.text())
			
	def saveCheckBoxSettings(self, checkBox):
		self.settings.setValue("custom_tab_1_selection/"+checkBox.text(), checkBox.isChecked())
		self.settings.sync()
		
	def saveTabNames(self, id, name):
		self.settings.setValue("tab_names/tab"+str(id), name)
		self.settings.sync()

	def plotAllData(self):
		self.allMplWidget.canvas.plot(self.data.headers, self.data.table)
				
	def onAllStartDateTimeClicked(self):
		self.allStartDateTimePicker.show()		
	
	def onAllEndDateTimeClicked(self):
		self.allEndDateTimePicker.show()	
		
	def onCustomEndDateTimeClicked(self):
		self.customStartDateTimePicker.show()		
	
	def onCustomEndDateTimeClicked(self):
		self.customEndDateTimePicker.show()
		
	def onAllDateTimeChanged(self):
		status = self.data.load(timeRange = [self.allStartDateTimePicker.dateTimeEdit.dateTime(), 
							   self.allEndDateTimePicker.dateTimeEdit.dateTime()])
		if status != "":
			QMessageBox.warning(self, "Warning", status)
		else:
			self.plotCustomData()
			
	def onCustomDateTimeChanged(self):
		status = self.data.load(timeRange = [self.customStartDateTimePicker.dateTimeEdit.dateTime(), 
							   self.customEndDateTimePicker.dateTimeEdit.dateTime()])
		if status != "":
			QMessageBox.warning(self, "Warning", status)
		else:
			self.plotAllData()
			
	def setOnlineMode(self):
		if self.onlineAllModeCheckBox.checkState() == 0:
			status = False
			self.onlineThread.join()
			log.debug("Online plotting thread stopped")
		elif self.onlineAllModeCheckBox.checkState() == 2:
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
		while self.onlineAllModeCheckBox.checkState() == 2:
			time.sleep(1)
			if self.data.newData == True:
				#self.allMplWidget.canvas.cla()
				self.plotAllData()
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
		
	def plotCustomData(self):
		self.customMplWidget.canvas.cla()
		if self.selectedHeaders != []:
			self.customMplWidget.canvas.initAxes()
			self.customMplWidget.canvas.setLayout(self.selectedHeaders)
			self.customMplWidget.canvas.plot(self.selectedHeaders, self.data.table)
		
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
		
		self.selectedHeaders = [self.data.headers[0]]
		for i in range(1, len(self.data.headers)):
			if i in self.selectedPlotNo:
				self.selectedHeaders.append(self.data.headers[i])
				
		self.plotCustomData()
		
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