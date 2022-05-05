"""
Class Intro Here..
"""

from cmath import pi
import math
import time
from sympy import symbols, Eq

class Profile:

    def __init__(self):
        # Identification Fields
        self.date = None
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

    def bendRadius(self, inside):
        if (self.brAvailable()):
            if inside:
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
                # !!!!!!!!NEED TO CONFIRM!!!!!!!!!
                lx = 600 * math.cos(self.LEA * (pi / 180.0))
                ly = 600 * math.sin(self.LEA * (pi / 180.0))
                rx = 600 * math.cos(self.REA * (pi / 180.0))
                ry = 600 * math.sin(self.REA * (pi / 180.0))
                # Left Radius
                l_slope = (ly / lx)
                l_slope_perp = -1/l_slope
                lcy = l_slope_perp * (0 - (lx/2)) + (ly/2)
                lcx = 0
                lbr = math.sqrt(lcx**2 + lcy**2)
                # Right Radius
                r_slope = (ry / rx)
                r_slope_perp = -1 / r_slope
                rcy = r_slope_perp * (0 - (rx/2)) + (ry/2)
                rcx = 0
                rbr = math.sqrt(rcx**2+rcy**2)
                return [lbr, rbr] #min(lbr, rbr)
                #!!!!!!!!!!NEED TO CONFIRM!!!!!!!!!!!!!
        else:
            return None
            
    def centerExcess(self, inside):
        if self.brAvailable():
            return ((12 * (50**2))/8) / min(self.bendRadius(inside))
        else:
            return 0.00

    def endExcess(self, inside):
        if self.brAvailable():
            return 2945 / min(self.bendRadius(inside))
        else:
            return 0.00

    def seAvailable(self):
        if self.SEA == None:
            return False
        if self.SEO == None:
            return False
        return True

    def scan_string(self):
        out_string = ""
        if len(self.SP) > 0:
            for point in self.SP:
                if out_string != "":
                    out_string += ", "
                out_string += f"{point[0]}|{point[1]}"
        else:
            out_string = "None"
        return out_string

    def generate_save_query(self, table):
        if self.date == None:
            self.date = time.time()
        this_query = f"insert into {table} (DATE, LINE, TRACK, STATIONING, LEA, REA, BR, CE, EE, SEA, SP)"
        this_query += f" VALUES ('{self.date}', '{self.line}', '{self.track}', '{self.stationing}', {self.LEA}, {self.REA},"
        this_query += f" {self.bendRadius()}, {self.centerExcess()}, {self.endExcess()}, {self.SEA}, '{self.scan_string()}');"
        return this_query

    def bulk_data_upload(self, data):
        # Passes list of all data points, in same order as sql tables
        data = data[0]
        self.date = data[1]
        self.line = data[2]
        self.track = data[3]
        self.stationing = data[4]
        self.LEA = data[5]
        self.REA = data[6]
        self.SEA = data[10]
        sp_string = ""
        sp_string = data[11]
        if sp_string != "None":
            while sp_string != "":
                if "," in sp_string:
                    this_point = sp_string[0:sp_string.index(",")]
                    sp_string = sp_string[sp_string.index(",")+1:]
                else:
                    this_point = sp_string
                    sp_string = ""
                br_index = this_point.index("|")
                this_x = float(this_point[0:br_index])
                this_y = float(this_point[br_index+1:])
                self.SP.append([this_x, this_y])
        else:
            self.SP = []

