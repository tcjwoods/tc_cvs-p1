"""
Class Intro Here..
"""

from cmath import pi
import math

class Profile:

    def __init__(self):
        # Identification Fields
        self.line = None
        self.track = None
        self.stationing = None
        # Data Fields
        self.LEA = None
        self.REA = None
        self.SEA = None
        self.SEO = None
        self.SP = []
        self.envelope = None

    def brAvailable(self):
        if self.LEA == None:
            return False
        if self.REA == None:
            return False
        return True

    def bendRadius(self):
        if (self.brAvailable()):
            lx = 300 * math.cos(self.LEA * (pi / 180.0))
            ly = 300 * math.sin(self.LEA * (pi / 180.0))
            rx = 300 * math.cos(self.REA * (pi / 180.0))
            ry = 300 * math.sin(self.REA * (pi / 180.0))
            x, y, z = complex(0, 0), complex(lx, ly), complex(rx, ry)
            w = z - x
            w /= y - x
            c = (x-y)*(w-abs(w)**2)/2j/w.imag-x
            return abs(c+x) / 12.0
        else:
            return None
            
    def centerExcess(self):
        return 4374 / self.bendRadius()

    def endExcess(self):
        return 2945 / self.bendRadius()

    def seAvailable(self):
        if self.SEA == None:
            return False
        if self.SEO == None:
            return False
        return True
