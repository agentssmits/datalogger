import socket
from datetime import datetime
import random
import time

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

def genTimestamp():
	now = datetime.now()
	return now.strftime("%Y-%m-%d %H:%M:%S")
	
def genData():
	retVal = ""
	for i in range(0, 4):
		retVal += ",%.6f" % (random.uniform(0, 5+i*4))
		
	return retVal
	
def genLine():
	return "%s%s\r\n" % (genTimestamp(), genData())

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