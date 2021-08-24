import socket
import time
import sys
import struct
import math

CUR_LUT = [0, 0.00001, 0.00005, 0.0001, 0.00025, 0.0005, 0.00075, 0.001, 0.0015, 0.002]

class Logerino:

    USE_RATIOMETRIC_OFF = 0
    USE_RATIOMETRIC_ON  = 16

    ADC_CURRENT_OFF     = 0
    ADC_CURRENT_10 	    = 1
    ADC_CURRENT_50      = 2
    ADC_CURRENT_100  	= 3
    ADC_CURRENT_250     = 4
    ADC_CURRENT_500 	= 5
    ADC_CURRENT_750     = 6
    ADC_CURRENT_1000    = 7
    ADC_CURRENT_1500    = 8
    ADC_CURRENT_2000    = 9

    ADC_SPS_2_5   = 0
    ADC_SPS_5     = 1
    ADC_SPS_10    = 2
    ADC_SPS_16_6  = 3
    ADC_SPS_20    = 4
    ADC_SPS_50 	  = 5
    ADC_SPS_60    = 6
    ADC_SPS_100   = 7
    ADC_SPS_200   = 8
    ADC_SPS_400   = 9
    ADC_SPS_800   = 10
    ADC_SPS_1000  = 11
    ADC_SPS_2000  = 12
    ADC_SPS_4000  = 13

    def __init__(self, ip, port):
        self.ip = ip                            # init variables
        self.port = port
        self.bufferSize = 1024
        self.channelData = [[]] * 12
        self.dataLen = 0
        self.timeStamps = []
        self.rawTime = []

    # for receiving data
    def receiveData(self, length):
        return self.s.recv(length)

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.s.connect((self.ip, self.port))         # try to connect
        except socket.error:
            return -1                                    # no device at ip:port

        self.s.settimeout(100)

        self.ping()                                      # check connection
        data = self.receiveData(self.bufferSize)

        if(data == b"PONG"):
            self.is_connected = 1
            return 1
        else:
            self.is_connected = 0
            return 0

    # send commands
    def sendCommand(self, command):
        self.s.sendall(command)

    # test command, for testing if can communicate with target device
    def ping(self):
        self.sendCommand(b"PING")

    # Returns current configuration of specified channel
    def getChannelInfo(self, channel):      # TODO implement
        return 0

    # Returns current configuration of all channels
    def getChannelsInfo(self):              # TODO implement
        return 0

    # returns all data from all channels
    def getChannelsData(self):

        temp = self.samplingPause() # pause sampling processes
        if(temp == 0):
            return 0

        self.sendCommand(str.encode("DA CA"))   # ask for ALL THE DATA

        deb = self.s.recv(4)
        #print(deb[0])
        #print(deb[1])
        #print(deb[2])
        #print(deb[3])
        self.dataLen = int.from_bytes(deb, "little")    # get data length

        if(self.dataLen == 0):
            return 0
        #print("receiving dat alength:", self.dataLen)

        timeMcu = int.from_bytes(self.s.recv(4), "little")    # get MCU relative time
        timeLocal = time.time()                               # get local time
        if(timeMcu == 0):
            return 0
        #print("received mcu time")

        dataBuf = [] * (self.dataLen * 4) # len 8 bits * 4

        while(1):                         # get time stamps
            if(len(dataBuf) == 0):
                dataBuf = self.s.recv(self.dataLen * 4) # 32 bits sent as 8 * 4
                #print("received ts:", len(dataBuf))
            if(len(dataBuf) < self.dataLen * 4):
                dataBuf = dataBuf + self.s.recv((self.dataLen * 4) - len(dataBuf))
                #print("received ts:", len(dataBuf))
            if(len(dataBuf) == self.dataLen * 4):
                break



        self.rawTime = [0] * self.dataLen
        for x in range(self.dataLen):
            self.rawTime[x] = int.from_bytes(dataBuf[x*4 : x*4 + 4], "little")



        dataBuf = [[]] * 12

        while(1):
            temp = self.s.recv(2)   # get current channel
            if(temp.decode() == "EN"):
                break               # read all channels

            #print("receiving channel :", temp)

            temp = int(temp)
            if(temp >= 0 and temp < 12):
                while(1):
                    if(len(dataBuf[temp]) == 0):
                        dataBuf[temp] = self.s.recv(self.dataLen * 4) # 32 bits sent as 8 * 4
                        #print("received data:",temp ,len(dataBuf[temp]))
                    if(len(dataBuf[temp]) < self.dataLen * 4):
                        dataBuf[temp] = dataBuf[temp] + self.s.recv((self.dataLen * 4) - len(dataBuf[temp]))
                        #print("received data:",temp ,len(dataBuf[temp]))
                    if(len(dataBuf[temp]) == self.dataLen * 4):
                        break
            else:
                return 0

        for x in range(12):
            dLen = len(dataBuf[x])
            if(dLen > 0):
                self.channelData[x] = [0] * (dLen // 4)
                for y in range(dLen // 4):
                    self.channelData[x][y] = int.from_bytes(dataBuf[x][y*4 : y*4 + 4], "little")    # uint8_t * 4 to int32
            else:
                self.channelData[x] = []

        timeDif = timeLocal - timeMcu / 1000
        self.timeStamps = [0] * len(self.rawTime)
        for x in range(len(self.rawTime)):        # relative time to absolute
            self.timeStamps[x] = self.rawTime[x] / 1000 + timeDif

        temp = [[],[],[]]
        temp[0] = self.channelData
        temp[1] = self.timeStamps
        temp[2] = self.rawTime

        return temp

    # returns data from specified channel
    def getChannelData(self, channel):  # TODO implement
        #    # returns all data from channel
        #self.sendCommand(str.encode("DA CS"))
        return 0

    def getChannelTimeStamps(self): # TODO implement
        return self.timeStamps

    # disable selected *channel* with "type"
    def channelDisable(self, channel):
        if(channel >= 0 and channel < 12):
            self.sendCommand(str.encode("CH DI " + "{:02d}".format(channel)))
            data = int.from_bytes(self.s.recv(1), "little") # get response
            return data
        return 0

    # enable selected *channel* with "type"
    def channelEnable(self, channel, current, ratio):
        if(channel >= 0 and channel < 12):
            self.sendCommand(str.encode("CH EN " + "{:02d}".format(channel) + " " + chr(current + ratio)))
            data = int.from_bytes(self.s.recv(1), "little") # get response
            return data
        return 0

    # converts ADC value to voltage
    def valToVoltage(self, values):
        n = len(values)
        temp = [0] * n
        if(n > 1):
            for x in range(n): # max 24 bit value
                if(values[x] < 2^23):
                    temp[x] = values[x] / 2**23 * 2.5
        return temp

    # converts ADC value to voltage then to resistance
    def valToResitance(self, values, current):
        temp = valToVoltage(values)
        n = len(temp)
        resistance = [0] * n
        if(n > 1):
            current
            for x in range(len(temp)):
                resistance[x] = temp[x] / CUR_LUT[current]
        return resistance

    # converts ratiometric ADC values to resistance
    def valToRatiometricResitance(self, values):
        n = len(values)
        resistance = [0] * n
        if(n > 1):
            for x in range(n): # max 24 bit value
                resistance[x] = values[x] / 2**23 * 2000
        return resistance

    # starts sampling or continues if previously started
    def samplingStart(self):
        self.sendCommand(str.encode("AD ST"))
        data = int.from_bytes(self.s.recv(1), "little")
        return data

    # pauses sampling
    def samplingPause(self):
        self.sendCommand(str.encode("AD SP"))
        data = int.from_bytes(self.s.recv(1), "little")
        return data

    # deletes old data, starts sampling from 0
    def samplingRestart(self):
        self.sendCommand(str.encode("AD SR"))
        data = int.from_bytes(self.s.recv(1), "little")
        return data

    # get information about the device connected to
    def identify(self):
        self.sendCommand(b"IDENT")
        data = self.receiveData(self.bufferSize).decode()
        return data


    def setSamplingRate(self, samplingRate):
        if(samplingRate >= 0 and samplingRate <= 13):
            self.sendCommand(str.encode("CH SR " + "{:02d}".format(samplingRate)))
            data = int.from_bytes(self.s.recv(1), "little") # get response
            return data
        return 0

    # close connection
    def close(self):
        #self.sendCommand(b"CLOSE")
        self.s.close()
