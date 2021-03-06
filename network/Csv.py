from datetime import datetime
import configparser
from filelock import Timeout, FileLock

ROOT_DIR = "C:\\Users\\arturs\\Desktop\\datalogger\\GUI\csv\\"
HEADERS = ["time", "sensor0", "sensor1", "sensor2", "sensor3", "sensor4", "sensor5", "sensor6", "sensor7", "sensor8", "sensor9"] #TEMP!!!!
CSV_LOCK_FILE = ROOT_DIR+"csv.lock"
META_LOCK_FILE = ROOT_DIR+"meta.lock"

class Csv:
	"""Class to perform actions with CSV files"""
	def __init__(self):
		"""
		Init - set line count as 0, generate initial filenames of 
		.csv and .meta files based on current system datetime
		"""
		self.lineCount = 0
		self.metaLock = FileLock(META_LOCK_FILE)
		self.csvLock = FileLock(CSV_LOCK_FILE)
		
		self.genPath()
		self.putHeaders(HEADERS)
		self.createMeta()

	def store(self, lines):
		"""
		Append CSV file with new lines and update meta info
		if line count in CSV file exceeds 300, new filename for 
		.csv and .meta files are generated
		
		argument data is supposed to be list of line strings
		"""
		if self.lineCount > 3000:
			self.lineCount = 0
			# mark previous meta file as completed nefore creating the new one
			self.markMetaCompleted()
			self.genPath()
			self.putHeaders(HEADERS)
			self.createMeta(start = lines[0].split(",")[0])
			
		with self.csvLock:
			with open(self.csvPath, 'a', newline='') as f:
				for line in lines:
					print('Will write %s' % line, end ="")
					f.write(line)
					self.lineCount += 1
		
		self.updateMetaEnd(lines[-1].split(",")[0])
	
	def genPath(self, expName = "log"):
		"""
		Generate pair of .csv/.meta filenames based of current system datetime
		and (optionally) on experiment name
		"""
		timeStamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
		fname = timeStamp + "_" + expName
		self.csvPath = ROOT_DIR + fname + ".csv"
		self.metaPath = ROOT_DIR + fname + ".meta"
		
	def writeMeta(self):
		"""Write current metadata to file"""
		with self.metaLock:
			with open(self.metaPath, 'w') as f:
				self.meta.write(f)
	
	def createMeta(self, start = ""):
		"""
		Create new metadata, end time is assumed to be the same as start time;
		if no start info is provided, current system time is taken
		"""
		if start == "":
			start = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
		self.meta = configparser.ConfigParser()
		self.meta.add_section('meta')
		self.meta['meta']['start'] = start
		self.meta['meta']['end'] = start
		self.meta['meta']['completed'] = "no"
			
	def updateMetaEnd(self, end):
		"""Update end time of metadata and update meta file"""
		self.meta['meta']['end'] = end
		self.writeMeta()
		
	def markMetaCompleted(self):
		"""
		Mark the current metadata as completed so the GUI 
		knows that this file will not be appended anymore
		"""
		self.meta['meta']['completed'] = "yes"
		self.writeMeta()
		
	def putHeaders(self, headerList):
		headerString = ""
		for i in range(0, len(headerList)):
			headerString += headerList[i]
			if i != len(headerList)-1:
				headerString += ","
		
		with self.csvLock:
			with open(self.csvPath, 'w', newline='') as f:
				f.write(headerString+"\r\n")