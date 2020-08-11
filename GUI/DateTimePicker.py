from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import QTime
from functools import partial


Ui_DateTimePicker, QtDateTimePickerClass = uic.loadUiType("datetimepicker.ui")

class DateTimePicker(QtWidgets.QMainWindow, Ui_DateTimePicker):
	def __init__(self, parent, button, defaultDateTime = None):
		super(DateTimePicker, self).__init__(parent)
		self.button = button
		self.parent = parent
		self.setupUi(self)
		if defaultDateTime != None:
			self.calendarWidget.setSelectedDate(defaultDateTime.date())
			self.dateTimeEdit.setTime(defaultDateTime.time())
			
		self.updateDatetime()
		self.calendarWidget.clicked[QtCore.QDate].connect(self.updateDatetime)
		
		win = self.scrollArea.window()
		timeButtons = win.findChildren(QtWidgets.QPushButton)
		for b in timeButtons:
			timeString = b.text().split(':')
			time = QTime(int(timeString[0]), int(timeString[1]))
			b.clicked.connect(partial(self.updateTime, time))
		
	def updateDatetime(self):
		date = self.calendarWidget.selectedDate()
		self.dateTimeEdit.setDate(date)
		
		self.passDateTime()
		
	def updateTime(self, time):
		self.dateTimeEdit.setTime(time)
		
		self.passDateTime()
		
	def passDateTime(self):
		self.button.setText(self.dateTimeEdit.dateTime().toString("yyyy.MM.dd hh:mm"))