import os
import sys
import logging as log
import numpy as np
import pandas as pd
import configparser
import threading
import time
from filelock import Timeout, FileLock

from datetime import datetime

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
ROOT_DIR = "C:\\Users\\arturs\\Desktop\\datalogger\\GUI\csv\\"
CSV_LOCK_FILE = ROOT_DIR+"csv.lock"
META_LOCK_FILE = ROOT_DIR+"meta.lock"

class Metadata:
	"""Class to store basic metadata of CSV files"""
	def __init__(self):
		"""
		The constructor; path, start & end are lists with the same size
		and store corresponding metadata
		"""
	
		self.path = []
		self.start = []
		self.end = []
		"""incompleted is a sperate list of currently incompleted files"""
		self.incompleted = []
		
	def append(self, path, start, end, completed = True):
		"""Append object lists with new metadata"""
		self.path.append(path)
		self.start.append(start)
		self.end.append(end)
		
		if completed == False and path.replace(".csv", ".meta") not in self.incompleted:
			if path.endswith(".csv"):
				path = path.replace(".csv", ".meta")
			self.incompleted.append(path)
		
	def print(self):
		"""Print metadata"""
		print(self.path, self.start, self.end, self.incompleted)
		
	def getLen(self):
		"""
		Returns count of metadata entires based on start list size
		It is assumed that all lists within the class object are with the same size
		"""
		return len(self.start)
		
	def getIncompleted(self):
		"""Returns list of currently incompleted meta files"""
		return self.incompleted
		
	def removeFromInclompleted(self, metaFile):
		"""Remove meta file from incompleted list if it is marked as completed"""
		self.incompleted.remove(metaFile)

class Data:
	"""
	Class to perform selection of data according to user start/end
	datetime and to store selected data
	"""
	def __init__(self, rootDir = '.'):
		"""
		table - contains current data selection in numpy array
		headers - stores list of column headers
		rootDir - root directory where all CSV files to find
		metadata - object containing lists of metadata
		
		on init all metadata is collected by default
		"""
		self.metaLock = FileLock(META_LOCK_FILE)
		self.csvLock = FileLock(CSV_LOCK_FILE)
		
		self.table = {}
		self.prevTable = {}
		self.prevTable[0] = []
		
		self.headers = []
		self.rootDir = rootDir
		self.metadata = Metadata()
		self.onlineMode = False
		self.newData = False
		self.updateMetadata()	
		
		# launch thread periodically checking CSV files marked as incompleted to update end time
		metaMonitoringThread = threading.Thread(target=self.__checkMetaFiles)
		metaMonitoringThread.daemon = True
		metaMonitoringThread.start()

	def getAllMetaFiles(self):
		"""Get list of all meta files"""
		retVal = []
		for root, dirs, files in os.walk(self.rootDir):
			for file in files:
				if file.endswith(".meta"):
					meta = os.path.join(root, file)
					retVal.append(meta)
					
		if retVal == []:
			log.warning("No meta files found in %s!" % (self.rootDir))

		return retVal
		
	def updateMetadata(self):
		"""Update metdata with information about new files"""
		
		for metaFile in self.getAllMetaFiles():
			if metaFile.replace(".meta",".csv") not in self.metadata.path:
				try:
					start = end = ""
					meta = configparser.ConfigParser()
					with self.metaLock:
						meta.read(metaFile)
					start = datetime.strptime(meta["meta"]["start"], DATETIME_FORMAT)
					end = datetime.strptime(meta["meta"]["end"], DATETIME_FORMAT)
					completed = meta["meta"].getboolean("completed")
					# if start and end times ar ok, append them to metadata array
					if start != "" and end != "":
						self.metadata.append(metaFile.replace(".meta", ".csv"), start, end, completed = completed)
						log.debug("New meta file: %s" % (metaFile))
				except Exception as e:
					log.warning("Failed to get time form %s, exception: %s" % (metaFile, str(e)))
					
	def checkIncompleted(self):
		for metaFile in self.metadata.getIncompleted():
			meta = configparser.ConfigParser()
			with self.metaLock:
				meta.read(metaFile)
			end = datetime.strptime(meta["meta"]["end"], DATETIME_FORMAT)
			completed = meta["meta"].getboolean("completed")
			
			i = self.metadata.path.index(metaFile.replace(".meta", ".csv"))
			self.metadata.end[i] = end
			log.debug("Updated info from metafile %s" % (metaFile))
			
			if completed == True:
				self.metadata.removeFromInclompleted(metaFile)
				log.debug("Metafile %s marked as completed" % (metaFile))
				
	def __checkMetaFiles(self):
		while 1:
			time.sleep(1)
			try:
				self.checkIncompleted()
			except Exception as e:
				log.warning("Checking incompleted files failed for reason: %s", str(e))
				
			try:
				self.updateMetadata()
			except:
				log.warning("Updating meta failed for reason: %s", str(e))
				
	def getTimestampRange(self):
		"""
		Get timestamp range (min/max) based on current CSV files on
		time of launch
		"""
		try:
			return [min(self.metadata.start), max(self.metadata.end)]
		except:
			return [datetime.now(), datetime.now()]
				
		
	def selectCSVFiles(self, timeRange):
		"""
		Select all CSV files which correspond to specified
		time range
		"""
		start, end = timeRange
		retVal = []
		for i in range(0, self.metadata.getLen()):
			#check if two ranges overlap
			if start <= self.metadata.end[i] and end >= self.metadata.start[i]:
				retVal.append(self.metadata.path[i])
				
		return retVal
		
	def getHeaders(self, file):
		"""
		Get list of column headers by CSV file specified
		"""
		with self.csvLock:
			with open(file, 'r') as f:
				self.headers = f.readline().rstrip().split(',')
			
	def __genDt(self):
		"""
		Generate datatype (dt) specifiers for columns
		it is assumed that column wich header includes word "time" has type datetime64
		other columns are assumed to be f4 floats
		"""
		retVal = []
		for name in self.headers:
			if "time" in name:
				type = "datetime64[us]"
			else:
				type = "f4"
			retVal.append((name, type))
		return retVal
	
	def load(self, timeRange = [], no = 0):
		"""
		Perform data loading from selected CSV files according to 
		specified time range and converting to numpy array
		
		if no time range is specified, all data possible is loaded
		
		in case of any errors message string is returned; on success empty srtring ""
		is returned
		"""
		
		# do not load new data if previous is not ploted
		if self.newData and self.onlineMode:
			return ""
			
		self.lastStartDateTime = timeRange[0]
		
		if timeRange == []:
			fileList = self.getAllCSVFiles(self.rootDir)
		else:
			fileList = self.selectCSVFiles(timeRange)
			
		if fileList == []:
			try:
				msg = "No CSV files correspond to selected time range %s : %s" % (timeRange[0].toString("yyyy-MM-ddThh:mm:ss"), timeRange[1].toString("yyyy-MM-ddThh:mm:ss"))
			except:
				msg = "No CSV files correspond to selected time range %s : %s" % (timeRange[0].strftime("%Y-%m-%dT%H:%M:%S"), timeRange[1].strftime("%Y-%m-%dT%H:%M:%S"))
			log.warning(msg)
			return msg
						
		self.getHeaders(fileList[0])
		with self.csvLock:
			tempTable = np.concatenate(
				[np.genfromtxt(file, 
							skip_header = 1, 
							delimiter=',',
							converters={0: lambda x: pd.to_datetime(x.decode('utf-8'), format="%Y-%m-%d %H:%M:%S")}) for file in fileList], 
				axis=0) 
		
		tempTable = np.array(tempTable, self.__genDt())
		tempTable = np.sort(tempTable, axis=0)
		
		if timeRange == []:
			self.table[no] = tempTable
		else:
			self.table[no] = tempTable[np.logical_and(tempTable[self.headers[0]] >= timeRange[0], tempTable[self.headers[0]] <= timeRange[1])]
		
		if len(self.table[no]) != len(self.prevTable[no]):
			log.debug("Loaded %d columns and %d lines" % (self.getColumnCount(), self.getLineCount()))
			log.debug("Column headers: %s", str(self.headers))
			self.prevTable[no] = self.table[no]
			self.newData = True
		else:
			log.debug("No new data found!")
		
		return ""
		
	def __loadThread(self):
		while self.onlineMode:
			time.sleep(1)
			self.load([self.lastStartDateTime, datetime.now()])
	
	def getColumnCount(self):
		"""
		get column count in current data selection
		
		currently 0th CSV file is used ti retrieve headers, 
		assuming all other files have the same structure
		"""
		return (len(self.table[0][0]))
	
	def getLineCount(self):
		"""
		get line count in current data selection
		
		currently 0th CSV file is used ti retrieve headers, 
		assuming all other files have the same structure
		"""
		return np.size(self.table[0], 0)
	
	def setOnlineMode(self, mode):
		self.onlineMode = mode
		if mode == True:
			self.onlineThread = threading.Thread(target=self.__loadThread)
			self.onlineThread.daemon = True
			self.onlineThread.start()
			log.debug("Online load thread launched")
		else:
			self.onlineThread.join()
			log.debug("Online load thread stopped")
		
	def print(self):
		"""print currently selected data for debug  purposes"""
		np.set_printoptions(suppress=True)
		for line in self.table:
			print(line)

