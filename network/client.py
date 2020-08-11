import socket
import time
import os

from signal import signal, SIGINT
from sys import exit, exc_info

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

global s

def gracefulStop(terminate = False):
	global s
	try:
		s.close()
		if terminate:
			exit(0)
	except Exception as e:
		printErr(e)
		
def gracefulStopHandler(signal_received, frame):
	print('SIGINT or CTRL-C detected. Exiting gracefully')
	gracefulStop(terminate = True)
	
def printErr(e):
	print("Exception: %s" % str(e))
	print("Caused by:")
	exc_type, exc_obj, exc_tb = exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	print(exc_type, fname, exc_tb.tb_lineno)
	
if __name__ == "__main__":
	global s
	signal(SIGINT, gracefulStopHandler)
	
	while True:
		try:
			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
				s.connect((HOST, PORT))
				while 1:
					data = s.recv(1024).decode()
					print('Received', data)
					if "stop" in data:
						gracefulStop(terminate = True)
					time.sleep(0.1)
		except Exception as e:
			printErr(e)
			gracefulStop()