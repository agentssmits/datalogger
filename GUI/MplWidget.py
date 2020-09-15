# Python Qt5 bindings for GUI objects
from PyQt5 import QtWidgets
# import the Qt5Agg FigureCanvas object, that binds Figure to
# Qt5Agg backend. It also inherits from QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.lines import Line2D

# Matplotlib Figure object
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

import itertools
import logging as log

COLOUR_ARR = ['crimson', 'silver', 'indigo', 'coral', 'saddlebrown', 'orange', 'black', 'olive', 'brown', 'navy', 'darkseagreen', 'red', 'teal', 'dodgerblue', 'deeppink']
POINT_ARR = ['o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd', 'P', 'X']

def getGridSize(columnCount):
	if columnCount == 1:
		return (1,1)
	if columnCount == 2:
		return (2,1)
	if columnCount == 3:
		return (3,1)
	if columnCount == 4:
		return (2,2)
	if columnCount == 5 or columnCount == 6:
		return (3,2)
	if columnCount >= 7 and columnCount <= 9:
		return (3,3)
	if columnCount >= 10 and columnCount <= 12:
		return (4,3)
	log.warning("Unsupported data column count %d!" % (columnCount))
	return (1,1)

class MplCanvas(FigureCanvas):
	"""Class to represent the FigureCanvas widget"""
	def __init__(self):
		"""The constructor"""
		# setup Matplotlib Figure and Axis
		self.fig = Figure()
		# initialization of the canvas
		FigureCanvas.__init__(self, self.fig)
		# we define the widget as expandable
		FigureCanvas.setSizePolicy(self,
			QtWidgets.QSizePolicy.Expanding,
			QtWidgets.QSizePolicy.Expanding)
		# notify the system of updated policy
		FigureCanvas.updateGeometry(self)
		
		self.initAxes()
		
	def initAxes(self):
		"""Ŗeset axes, format X axis as time axis"""
		self.fig.autofmt_xdate()  
		self.ax = []
		self.line = []
		
	def setLayout(self, headers):
		"""
		Set number and arragement of subplots according to
		data column count
		"""
		colours = itertools.cycle(COLOUR_ARR)
		points = itertools.cycle(POINT_ARR)
		
		plotCount = len(headers) - 1
		grid = getGridSize(plotCount)
		
		for i in range (0, plotCount):
			ax = self.fig.add_subplot(grid[0], grid[1], i+1)
			line = Line2D([], [], color=next(colours), marker = next(points))
			ax.add_line(line)
			
			ax.set_xlabel (headers[0], fontsize=10)
			ax.set_ylabel (headers[i+1], fontsize= 10)
			ax.autoscale(enable=True, axis='both', tight=None)
			
			self.ax.append(ax)
			self.line.append(line)
			
	def plot(self, headers, table):
		""""
		Plot data from table according to column names 
		specified in headers list
		"""
		try:
			time = table[headers[0]]
			for i in range(0, len(headers)-1):
				self.line[i].set_data(time, table[headers[i+1]])
				self.ax[i].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
				self.ax[i].relim()
				self.ax[i].autoscale_view()
			self.draw()
		except Exception as e:
			print(e)
			
	def cla(self):
		"""Clear all axes of all subplots in figure"""
		allaxes = self.fig.get_axes()
		for ax in allaxes:
			ax.cla()
		self.fig.clear() # causes crash sometimes
	 
class MplWidget(QtWidgets.QWidget):
	"""Widget defined in Qt Designer"""
	def __init__(self, parent = None):
		"""The constructor"""
		# initialization of Qt MainWindow widget
		QtWidgets.QWidget.__init__(self, parent)
		# set the canvas to the Matplotlib widget
		self.canvas = MplCanvas()
		
		self.toolbar = NavigationToolbar(self.canvas, self)
		
		# create a vertical box layout
		self.vbl = QtWidgets.QVBoxLayout()
		# add mpl widget to vertical box
		self.vbl.addWidget(self.canvas)
		# set the layout to th vertical box
		
		# set the layout
		self.vbl.addWidget(self.toolbar)
			
		self.setLayout(self.vbl)