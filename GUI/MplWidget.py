# Python Qt5 bindings for GUI objects
from PyQt5 import QtWidgets
# import the Qt5Agg FigureCanvas object, that binds Figure to
# Qt5Agg backend. It also inherits from QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# Matplotlib Figure object
from matplotlib.figure import Figure

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
		
	def setLayout(self, layout):
		"""Set number and arragement of subplots according to
		data column count"""
		self.ax = self.fig.add_subplot(layout)
		
	def cla(self):
		"""Clear all axes of all subplots in figure"""
		allaxes = self.fig.get_axes()
		for ax in allaxes:
			ax.cla()
		self.fig.clear()
	 
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