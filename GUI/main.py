from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import QTime, QDateTime, QSettings
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QLineEdit, QSpinBox, QCheckBox, QComboBox

import warnings
warnings.filterwarnings("ignore", "(?s).*MATPLOTLIBDATA.*", category=UserWarning)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from functools import partial

import pandas as pd
import numpy as np

import matplotlib as mpl

from MplWidget import MplWidget

import sys
import logging as log
import argparse
import threading
import os
import time
import csv

from DataLoader import Data
from DateTimePicker import DateTimePicker
from customTab import addCustomTabs

import logerino

# constants needed for logging of debug/warning/error messages
LOG_FORMAT = "%(asctime)s %(levelname)-8s: %(message)s\t"
TIMESTAMP_FORMAT = '%d-%m-%YT%H:%M:%S'

# specify *.ui file location for main window
Ui_MainWindow, QtBaseClass = uic.loadUiType("datalogger.ui")

# specify number of max channels of datalogger
CH_COUNT = 12

# make correspondence between sps and its code number
datalogger = logerino.Logerino("", 0)
decodeSPS = {
	2.5: 	datalogger.ADC_SPS_2_5,
	5: 		datalogger.ADC_SPS_5,
	10: 	datalogger.ADC_SPS_10,
	16.6: 	datalogger.ADC_SPS_16_6,
	20: 	datalogger.ADC_SPS_20,
	50: 	datalogger.ADC_SPS_50,
	60: 	datalogger.ADC_SPS_60,
	100:	datalogger.ADC_SPS_100,
	200:	datalogger.ADC_SPS_200,
	400:	datalogger.ADC_SPS_400,
	800:	datalogger.ADC_SPS_800,
	1000:	datalogger.ADC_SPS_1000,
	2000:	datalogger.ADC_SPS_2000,
	4000:	datalogger.ADC_SPS_4000
}

decodeCurrent = {
	0:		datalogger.ADC_CURRENT_OFF,
	10:		datalogger.ADC_CURRENT_10,
	50:		datalogger.ADC_CURRENT_50,
	100:	datalogger.ADC_CURRENT_100,
	250:	datalogger.ADC_CURRENT_250,
	500:	datalogger.ADC_CURRENT_500,
	750:	datalogger.ADC_CURRENT_750,
	1000:	datalogger.ADC_CURRENT_1000,
	1500:	datalogger.ADC_CURRENT_1500,
	2000:	datalogger.ADC_CURRENT_2000    
}

decodeRatio = {
	0:		datalogger.USE_RATIOMETRIC_OFF,
	1:		datalogger.USE_RATIOMETRIC_ON
}
		
class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
	def __init__(self, offline = False):
		"""The constructor"""
		
		self.offline = offline
		self.dataloggerChannelsEnabled = [0]*CH_COUNT
		self.dataloggerChannelCurrent = [0]*CH_COUNT
		self.dataloggerChannelRatioMes = [0]*CH_COUNT
		self.dataloggerChanelEnableCheckBoxes = []
		
		self.selectedHeaders = {}
		self.customStartDateTimePickerArr = {}
		self.customEndDateTimePickerArr = {}
		self.customStartDateTimeButtonArr = {}
		self.customEndDateTimeButtonArr = {}
		self.customMplWidgetArr = {}
		self.customSelectionCheckBoxArr = {}

		# default data time range corresponds to CSV start/end datetime
		self.data = Data()
		self.defaultStartDateTime, self.defaultEndDateTime = self.data.getTimestampRange()
		# get initial CSV data
		self.data.load(timeRange = [self.defaultStartDateTime, self.defaultEndDateTime])
		
		QtWidgets.QMainWindow.__init__(self)
		Ui_MainWindow.__init__(self)
		self.setupUi(self)
		
		# allow user to specify data root directory, by default it is current working directory
		os.chdir(os.path.dirname(__file__))
		self.rootSelEdit.setText(os.getcwd())
		self.rootSelBtn.clicked.connect(self.getDir)
		
		# handle custom datetime selection for tab 'all'
		self.allStartDateTimePicker = DateTimePicker(self, self.allStartDateTimeButton, self.defaultStartDateTime, title = "Select start datetime for plotting all data") 
		self.allEndDateTimePicker = DateTimePicker(self, self.allEndDateTimeButton, self.defaultEndDateTime, title = "Select end datetime for plotting all data") 
		self.allStartDateTimeButton.clicked.connect(self.onAllStartDateTimeClicked)
		self.allEndDateTimeButton.clicked.connect(self.onAllEndDateTimeClicked)
		
		self.allStartDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onAllDateTimeChanged)
		self.allEndDateTimePicker.dateTimeEdit.dateTimeChanged.connect(self.onAllDateTimeChanged)
		
		self.onlineAllModeCheckBox.stateChanged.connect(self.setOnlineMode)
		
		# set up shortcut q to exit
		self.actionQuit.triggered.connect(self.quit)
		self.actionQuit.setShortcut('Q')
		
		self.showMaximized()
		
		# plot data on tab "All"
		self.allMplWidget.canvas.setLayout(self.data.headers)
		self.plotAllData()
				
		# Get settings to restore fields in Settings tab
		self.settings = QSettings(".GUI_settings", QSettings.IniFormat)
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
		
		# add custom tabs needed after tab "All"
		self.tabWidget.setCurrentIndex(1)
		addCustomTabs(self, self.customTabCount.value()-1)
		self.restoreTabNames()
		
		# get settings to restore checkboxes 
		self.selectedPlotNo = {}
		# collect checkboxes from 1st custom tab
		checkBoxes = {}
		for i in range(self.gridLayout_6.count()):
			checkBoxes[i] = self.gridLayout_6.itemAt(i).widget()
		self.customSelectionCheckBoxArr[0] = checkBoxes.copy()
			
		for i in range(len(self.customSelectionCheckBoxArr)):
			for j in range(len(self.customSelectionCheckBoxArr[i])):
				checkBox = self.customSelectionCheckBoxArr[i][j]
				attr = "custom_tab_%d_selection/" % (i)
				checkBox.setChecked(self.settings.value(attr+checkBox.text(), False, type=bool))
				# connect the slot to the signal by clicking the checkbox to save the state settings
				checkBox.clicked.connect(partial(self.saveCheckBoxSettings, checkBox, i))
				checkBox.stateChanged.connect(self.checkCheckboxes)
			
		# plot custom plots according to checkboxes
		self.checkCheckboxes()
		
		# enable renaming custom tabs
		self.tabNameEditor = QLineEdit(self)
		self.tabNameEditor.setWindowFlags(QtCore.Qt.Popup)
		self.tabNameEditor.setFocusProxy(self)
		self.tabNameEditor.editingFinished.connect(self.handleTabEditingFinished)
		self.tabNameEditor.installEventFilter(self)
		self.tabWidget.tabBarDoubleClicked.connect(self.tabDoubleClickEvent)
		
		# save values of QLineEdit & QSpinBox widgets in Settings tab
		widgets = self.settingsTab.findChildren(QLineEdit)
		for widget in widgets:
			if isinstance(widget, QLineEdit):
				widget.textChanged.connect(partial(self.saveQLineEdit, widget))
				
		widgets = self.settingsTab.findChildren(QSpinBox)
		for widget in widgets:
			if isinstance(widget, QSpinBox):
				widget.textChanged.connect(partial(self.saveQSpinBox, widget))
				
		self.customTabCount.valueChanged.connect(self.updateCustomTabCount)
		
		# handle custom datetime selection for tab 'custom'

		self.customStartDateTimeButtonArr[0] = self.customStartDateTimeButton
		self.customEndDateTimeButtonArr[0] = self.customEndDateTimeButton
		self.customMplWidgetArr[0] = self.customMplWidget
		self.setupCustomTabs()
		
		# try to autoconnect to datalogger board as well as handle press of button 'datalogger_connect_btn'
		self.openDatalogger()
		self.datalogger_connect_btn.clicked.connect(self.openDatalogger)
		time.sleep(1)
		
		# another handles for controlling datalogger board
		self.datalogger_sps.currentTextChanged.connect(self.setDataloggerSampleRate)
		
		widgets = self.settingsTab.findChildren(QCheckBox)
		for widget in widgets:	
			if isinstance(widget, QCheckBox):
				if "enabled" in widget.objectName() and "datalogger" in widget.objectName():
					widget.stateChanged.connect(partial(self.dataloggerChannelCheckBoxHandler, widget))
					self.dataloggerChanelEnableCheckBoxes.append(widget)
				elif "ratio" in widget.objectName() and "datalogger" in widget.objectName():
					widget.stateChanged.connect(partial(self.checkDataloggerRatiometricMode, widget))
					
		widgets = self.settingsTab.findChildren(QComboBox)
		for widget in widgets:	
			if isinstance(widget, QComboBox):
				if "current" in widget.objectName() and "datalogger" in widget.objectName():
					widget.currentIndexChanged.connect(partial(self.checkDataloggerChannelCurrent, widget))
					
		# restore prevoius states of current combo box
		widgets = self.settingsTab.findChildren(QComboBox)
		for widget in widgets:	
			if isinstance(widget, QComboBox):
				if "current" in widget.objectName() and "datalogger" in widget.objectName():
					value = self.settings.value("settings/"+str(widget.objectName()), -1, type=int)
					if value != -1:
						widget.setCurrentIndex(value)
					
		# restore prevoius states of ratio mode checkBox
		widgets = self.settingsTab.findChildren(QCheckBox)
		for widget in widgets:	
			if isinstance(widget, QCheckBox):
				if "ratio" in widget.objectName() and "datalogger" in widget.objectName():
					value = self.settings.value("settings/"+str(widget.objectName()), False, type=bool)
					if value != False:
						widget.setChecked(value)
		
		# restore prevoius states of channel enable checkBox
		widgets = self.settingsTab.findChildren(QCheckBox)
		for widget in widgets:	
			if isinstance(widget, QCheckBox):		
				if "enabled" in widget.objectName() and "datalogger" in widget.objectName():
					value = self.settings.value("settings/"+str(widget.objectName()), False, type=bool)
					if value != False:
						widget.setChecked(value)

		# handle to start sampling
		self.datalogger_start_btn.clicked.connect(self.startSampling)
					
	def setupCustomTabs(self):
		for i in self.getCustomTabRange():
			self.customStartDateTimePickerArr[i] = DateTimePicker(self, self.customStartDateTimeButtonArr[i], self.defaultStartDateTime, title = "Select start datetime for plotting custom data") 
			self.customEndDateTimePickerArr[i] = DateTimePicker(self, self.customEndDateTimeButtonArr[i], self.defaultEndDateTime, title = "Select end datetime for plotting custom data") 
			self.customStartDateTimeButtonArr[i].clicked.connect(partial(self.onCustomStartDateTimeClicked, picker = self.customStartDateTimePickerArr[i]))
			self.customEndDateTimeButtonArr[i].clicked.connect(partial(self.onCustomEndDateTimeClicked, picker = self.customEndDateTimePickerArr[i]))
			
			self.customStartDateTimePickerArr[i].dateTimeEdit.dateTimeChanged.connect(self.onCustomDateTimeChanged)
			self.customEndDateTimePickerArr[i].dateTimeEdit.dateTimeChanged.connect(self.onCustomDateTimeChanged)
	
	def restoreTabNames(self):
		# Get settings to restore tab names 	
		for id in range(2, self.tabWidget.count()-1):
			name = self.settings.value("tab_names/tab"+str(id), "none", type=str)
			if name != "none":
				self.tabWidget.tabBar().setTabText(id, name)
						
	def getCustomTabRange(self):
		endIndex = self.tabWidget.count() - 3
		return range(0, endIndex)
			
	def updateCustomTabCount(self):
		oldCustomTabCount = self.tabWidget.count() - 3
		if self.customTabCount.value() > oldCustomTabCount:
			# add additional tabs
			tabsToAdd = self.customTabCount.value() - oldCustomTabCount
			startIndex = oldCustomTabCount + 2
			addCustomTabs(self, tabsToAdd, startIndex)
			self.restoreTabNames()
			self.plotCustomData()
		elif self.customTabCount.value() < oldCustomTabCount:
			# delete tabs
			tabsToDelete =  oldCustomTabCount - self.customTabCount.value()
			indexTo = oldCustomTabCount + 2
			indexFrom = indexTo - tabsToDelete
			
			for i in range(indexFrom, indexTo):
				self.tabWidget.removeTab(i)
				
		self.setupCustomTabs()
				
	def saveQLineEdit(self, widget):
		self.settings.setValue("settings/"+ widget.objectName(), widget.text())
		self.settings.sync()
		
	def saveQSpinBox(self, widget):
		self.settings.setValue("settings/"+ widget.objectName(), widget.value())
		self.settings.sync()
	
	def saveQCheckBox(self, widget):
		self.settings.setValue("settings/"+ widget.objectName(), widget.isChecked())
		self.settings.sync()
		
	def saveQComboBox(self, widget):
		self.settings.setValue("settings/"+ widget.objectName(), widget.currentIndex())
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
			
	def saveCheckBoxSettings(self, checkBox, index):
		attr = "custom_tab_%d_selection/" % (index)
		self.settings.setValue(attr+checkBox.text(), checkBox.isChecked())
		self.settings.sync()
		
	def saveTabNames(self, id, name):
		self.settings.setValue("tab_names/tab"+str(id), name)
		self.settings.sync()

	def plotAllData(self):
		self.allMplWidget.canvas.plot(self.data.headers, self.data.table[0])
				
	def onAllStartDateTimeClicked(self):
		self.allStartDateTimePicker.show()		
	
	def onAllEndDateTimeClicked(self):
		self.allEndDateTimePicker.show()	
		
	def onCustomStartDateTimeClicked(self, picker = None):
		if picker == None:
			self.customStartDateTimePicker.show()
		else:
			picker.show()
	
	def onCustomEndDateTimeClicked(self, picker = None):
		if picker == None:
			self.customEndDateTimePicker.show()
		else:
			picker.show()
		
	def onAllDateTimeChanged(self):
		status = self.data.load(timeRange = [self.allStartDateTimePicker.dateTimeEdit.dateTime(), 
							   self.allEndDateTimePicker.dateTimeEdit.dateTime()])
		if status != "":
			QMessageBox.warning(self, "Warning", status)
		else:
			self.plotCustomData()
			
	def onCustomDateTimeChanged(self, tabNo = 0):
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
				endTime = self.data.table[0][series[0]][-1]
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
		for i in self.getCustomTabRange():
			try:
				widget = self.customMplWidgetArr[i]
				widget.canvas.cla()
				widget.canvas.draw()
				# do not plot if only time series provided
				if len(self.selectedHeaders[i]) == 1:
					continue
				if self.selectedHeaders[i] != []:
					widget.canvas.initAxes()
					widget.canvas.setLayout(self.selectedHeaders[i])
					log.debug("Will plot for tab %d: %s", i, str(self.selectedHeaders[i]))
					widget.canvas.plot(self.selectedHeaders[i], self.data.table[0])
			except Exception as e:
				log.error("Something failed at plotting %d tab" % (i))
				log.error(str(e))
		
	def checkCheckboxes(self):
		for j in range(0, len(self.customSelectionCheckBoxArr)):
			checkBoxes = self.customSelectionCheckBoxArr[j]
			try:
				tabSelection = self.selectedPlotNo[j]
			except:
				tabSelection = []
					
			for i in range(0, len(checkBoxes)):
				index = int(checkBoxes[i].text().split(" ")[1])+1
					
				if checkBoxes[i].isChecked():
					if index not in tabSelection:
						tabSelection.append(index)
				else:
					if index in tabSelection:
						tabSelection.remove(index)
			
			self.selectedHeaders[j] = [self.data.headers[0]]
			for i in range(1, len(self.data.headers)):
				if i in tabSelection:
					self.selectedHeaders[j].append(self.data.headers[i])
			
			self.selectedPlotNo[j] = tabSelection
		self.plotCustomData()
		
	def appendDataloggerTextBox(self, text):
		verScrollBar = self.dataloggerTextResponse.verticalScrollBar()
		horScrollBar = self.dataloggerTextResponse.horizontalScrollBar()
		scrollIsAtEnd = verScrollBar.maximum() - verScrollBar.value() <= 10
		
		self.dataloggerTextResponse.append(text)
		
		if scrollIsAtEnd:
			verScrollBar.setValue(verScrollBar.maximum()) # Scrolls to the bottom
			horScrollBar.setValue(0) # scroll to the left
		
	def openDatalogger(self):
		# assume there is no connection to datalogger board
		if self.datalogger_connect_btn.text() == "Open connection":
			IP = self.datalogger_ip.text()
			PORT = int(self.datalogger_port.text())
			self.datalogger = logerino.Logerino(IP, PORT)
			if self.offline == True:
				log.debug("Emulating connection to datalogger")
				self.datalogger_connect_btn.setText("Close connection")
			else:
				log.debug("Trying to connect @ " + IP)
				status = self.datalogger.connect()   # try to connect
				if status == 1:
					self.datalogger_connect_btn.setText("Close connection")
					log.debug("Connected to datalogger succesfully")
					if self.offline == False:
						log.debug("Getting board info")
						log.debug("Returned: " + self.datalogger.identify())  # get board info
					return
				elif status == 0:
					log.error("Could not communicate with datalogger @ %s:%d" % (IP, PORT))
				elif status == -1:
					log.error("No device @ %s:%d" % (IP, PORT))
				else:
					log.error("Unkonwn error code %d returned from datalogger" % (status))
				
			self.datalogger_connect_btn.setText("Open connection")
			return
			
		# assume there is connection to datalogger board
		if self.datalogger_connect_btn.text() == "Close connection":
			if self.offline == False:
				self.datalogger.close()
			self.datalogger_connect_btn.setText("Open connection")
						
	def setDataloggerSampleRate(self):
		sps = float(self.datalogger_sps.currentText())
		if self.offline:
			log.debug("Will emulate setting of sample rate to %f sps" % (sps))
		else:
			spsCode = decodeSPS[sps]
			msg = "Will set sample rate to %f sps (code: %d)" % (sps, spsCode)
			log.debug(msg)
			self.appendDataloggerTextBox(msg)
			retVal = self.datalogger.setSamplingRate(spsCode)
			if retVal != 1:
				msg = "Setting sample rate %f failed! (code %d) " % (sps, retVal)
			else:
				msg = "Setting sample rate %f OK! (code %d) " % (sps, retVal)
			log.debug(msg)
			self.appendDataloggerTextBox(msg)

			
	def enableDataloggerChannel(self, chNo, state = True):
		self.dataloggerChannelsEnabled[chNo] = state
		if state:
			if self.offline:
				log.debug("Emulating enable of CH%d" % (chNo))
			else:
				current = self.dataloggerChannelCurrent[chNo]
				ratio = self.dataloggerChannelRatioMes[chNo]
				msg = "Enabling CH%d (current=%d, ratio=%d)" % (chNo, current, ratio)
				log.debug(msg)
				self.appendDataloggerTextBox(msg)
				retVal = self.datalogger.channelEnable(chNo, decodeCurrent[current], decodeRatio[ratio])
				if retVal != 1:
					msg = "Enabling  CH%d failed! (code %d) " % (chNo, retVal)
					self.dataloggerChanelEnableCheckBoxes[chNo].setChecked(False)
				else:
					msg = "Enabling  CH%d OK! (code %d) " % (chNo, retVal)
				log.debug(msg)
				self.appendDataloggerTextBox(msg)
		else:
			if self.offline:
				log.debug("Emulating disabling of CH%d" % (chNo))
			else:
				msg = "Disabling CH%d" % (chNo)
				log.debug(msg)
				self.appendDataloggerTextBox(msg)
				retVal = self.datalogger.channelDisable(chNo)
				if retVal != 1:
					msg = "Disabling  CH%d failed! (code %d) " % (chNo, retVal)
					self.dataloggerChanelEnableCheckBoxes[chNo].setChecked(True)
				else:
					msg = "Disabling  CH%d OK! (code %d) " % (chNo, retVal)
				log.debug(msg)
				self.appendDataloggerTextBox(msg)
			
	def dataloggerChannelCheckBoxHandler(self, checkBox):
		state = checkBox.isChecked()
		# get chNo from checkbox name, e.g. datalogger_ch0_enabled
		chNo = int(checkBox.objectName().split('_')[1].replace("ch",""))
		self.enableDataloggerChannel(chNo, state)
		self.saveQCheckBox(checkBox)
				
	def checkDataloggerRatiometricMode(self, checkBox):
		state = checkBox.isChecked()
		# get chNo from checkbox name, e.g. datalogger_ch0_ratio
		chNo = int(checkBox.objectName().split('_')[1].replace("ch",""))
		log.debug("Ratio mode for CH%d is %d" % (chNo, state))
		self.dataloggerChannelRatioMes[chNo] = state
		if self.dataloggerChannelsEnabled[chNo]:
			self.enableDataloggerChannel(chNo)
		self.saveQCheckBox(checkBox)
	
	def checkDataloggerChannelCurrent(self, comboBox):
		try:
			value = float(comboBox.currentText())
		except:
			value = 0
		# get chNo from comboBox name, e.g. datalogger_ch0_current
		chNo = int(comboBox.objectName().split('_')[1].replace("ch",""))
		log.debug("Ratio current for CH%d is %f" % (chNo, value))
		self.dataloggerChannelCurrent[chNo] = value
		if self.dataloggerChannelsEnabled[chNo]:
			self.enableDataloggerChannel(chNo)
		self.saveQComboBox(comboBox)
		
	def startSampling(self):
		if self.datalogger_start_btn.text() == "Start sampling":
			self.samplingThread = threading.Thread(target=self._samplingThread)
			self.samplingThread.daemon = True
			self.datalogger_start_btn.setText("Stop sampling")
			self.samplingThread.start()
			log.debug("Online sampling thread launched")
		else:
			try:
				self.samplingThread.join()
			except Exception as e:
				log.warning(str(e))
			log.debug("Online sampling thread stopped")
			self.datalogger_start_btn.setText("Start sampling")
			
	def _samplingThread(self):
		while self.datalogger_start_btn.text() == "Stop sampling":
			try:
				retVal = self.datalogger.samplingStart()               
				if retVal:
					time.sleep(self.datalogger_samplingTime.value())
					data = self.datalogger.getChannelsData()
					timeCol = np.array(data[1])
					ch0Col = np.array(self.datalogger.valToVoltage(data[0][0]))
					a = np.column_stack((timeCol, ch0Col))
					with open("csv/test.csv", "a") as f:
						np.savetxt(f, a, delimiter=",")
				else:
					log.error("Cant sample data")
				
				#self.datalogger.close()
				#self.openDatalogger()
			except Exception as e:
					print(data)
					log.error(str(e))
					self.datalogger_connect_btn.setText("Open connection")
					self.datalogger.close() 
					self.openDatalogger()
					self.datalogger_start_btn.setText("Start sampling")
			
		
	def quit(self):
		try:
			self.datalogger.close()
			datalogger_connect_btn.setText("Open connection")
		except:
			pass
		sys.exit(0)

if __name__ == "__main__":
	#parse input arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('-v', '--verbosity', action="count", 
                        help="-v: WARNING, -vv: INFO, -vvv: DEBUG")
	parser.add_argument("-o", "--offline", action="store_true", default=False, 
						help="specify if exclude network communication")
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
	window = MyApp(offline = args.offline)
	window.show()
	sys.exit(app.exec_())