import socket
from datetime import datetime
import random
import time
import os

from signal import signal, SIGINT
from sys import exit, exc_info

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

global conn, s

def gracefulStop():
	global conn, s
	try:
		conn.sendall("stop".encode())
		conn.close()
		s.close()
	except Exception as e:
		printErr(e)
			
def gracefulStopHandler(signal_received, frame):
	print('SIGINT or CTRL-C detected. Exiting gracefully')
	gracefulStop()
	exit(0)
	
def printErr(e):
	print("Exception: %s" % str(e))
	print("Caused by:")
	exc_type, exc_obj, exc_tb = exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	print(exc_type, fname, exc_tb.tb_lineno)
	
def genTimestamp():
	now = datetime.now()
	return now.strftime("%Y-%m-%d %H:%M:%S")
	
def genData():
	retVal = ""
	for i in range(0, 4):
		retVal += ",%.6f" % (random.uniform(0, 5+i*4))
		
	return retVal
	
def genLine():
	return "%s%s" % (genTimestamp(), genData())

if __name__ == "__main__":
	global conn, s
	signal(SIGINT, gracefulStopHandler)
	
	while True:
		try:
			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
				s.bind((HOST, PORT))
				s.listen()
				print("Waiting for client")
				conn, addr = s.accept()
				with conn:
					print('Connected by', addr)
					while True:
						data = genLine()
						print(data)
						conn.sendall(data.encode())
						time.sleep(1)
		except Exception as e:
			printErr(e)
			gracefulStop()