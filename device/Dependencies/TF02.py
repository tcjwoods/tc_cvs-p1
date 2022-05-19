
import serial

class TF02:

    def __init__(self):
        # Constants
        self._HEADER = 0x59

        # Variables
        self.TF02_PIX = None
        self.DISTANCE = None
        self.STRENGTH = None
        self.a, self.b, self.c, self.d, self.e, self.f = None, None, None, None, None, None
        self.check = None
        self.i = None

        self.serial = serial.Serial('/dev/serial0', baudrate=115200)

    def __loop__(self):
        if self.serial.in_waiting > 0:
            if self.serial.read() == self._HEADER:
                if self.serial.read() == self._HEADER:
                    self.a = self.serial.read()
                    self.b = self.serial.read()
                    self.c = self.serial.read()
                    self.d = self.serial.read()
                    self.e = self.serial.read()
                    self.f = self.serial.read()
                    self.check = sum(self.a, self.b, self.c, self.d, self.e, self.f, self._HEADER, self._HEADER)
                    if self.serial1.read() == (self.check & 0xff):
                        self.DISTANCE = (self.a + (self.b * 256))
                        self.STRENGTH = (self.c + (self.d * 256))

    def getDistance(self):
        self.serial.flushInput()
        exit_flag = False
        exit_counter = 0
        while self.serial.in_waiting > 0:
            if self.serial.read() == self._HEADER:
                if self.serial.read() == self._HEADER:
                    self.a = self.serial.read()
                    self.b = self.serial.read()
                    self.c = self.serial.read()
                    self.d = self.serial.read()
                    self.e = self.serial.read()
                    self.f = self.serial.read()
                    self.check = sum([self.a, self.b, self.c, self.d, self.e, self.f, self._HEADER, self._HEADER])
                    if self.serial.read() == (self.check & 0xff):
                        self.DISTANCE = (self.a + (self.b * 256))
                        self.STRENGTH = (self.c + (self.d * 256))
                        return self.DISTANCE
            else:
                exit_counter += 1
                if exit_counter > 50:
                    # Times out after 50 failed attempts to read
                    return 0.00
