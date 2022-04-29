"""
Script Intro

"""

# Imports
import subprocess
import sys
import csv
import math
import pyodbc
import pyqtgraph as pg
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QHeaderView, QMessageBox, QVBoxLayout
from Classes.profile import Profile
from Classes.mqtt import mqttClient as mqtt


##### Interface Class #####
class CVS_Interface(QMainWindow):

# Class Init
    def __init__(self, app, parent=None):
        # Initialize Application/Interface
        self.app = app
        super(CVS_Interface, self).__init__(parent)
        uic.loadUi('Interface/mainwindow.ui', self)
        self.showMaximized()
        self.setWindowTitle("CVS Viewer Client - Version 0.3")
        
        # Instance Variables
        self.current_profile = None # Current Profile to Store Data
        self.base_envelope = None # Envelope Coordinates prior to adjustment

        # Initialize Controls
        self.btnSelectScan.clicked.connect(self.profile_select)
        self.btnCreateScan.clicked.connect(self.profile_create)
        self.btnSaveScan.clicked.connect(self.profile_save)
        self.btnDeleteScan.clicked.connect(self.profile_delete)
        self.btnLEA.clicked.connect(self.ERLE)
        self.btnREA.clicked.connect(self.ERRE)
        self.btnSEA.clicked.connect(self.ERSE)
        self.btnHM.clicked.connect(self.ETHM)
        self.btnSP.clicked.connect(self.ETSP)
        self.btnTL.clicked.connect(self.ETTL)
        self.btnTM.clicked.connect(self.ETTM)

        # Response Dictionary
        self.response_dict = {
            "SEA": self.SEA,
            "SEO": self.SEO,
            "LEA": self.LEA,
            "REA": self.REA,
            "SP": self.SP}

        # MQTT Topic List
        self.mqtt_topics = [
            "/data/LEA",
            "/data/REA",
            "/data/SEA",
            "/data/SEO",
            "/data/SP",
            "/debug"]

        # Initialize Plotter
        self.plotter = pg.plot()
        self.plotter.showGrid(x=True, y=True)
        self.plotter.setXRange(-250, 250)
        self.plotter.setYRange(-50, 250)
        self.plotter.setFixedHeight(500)
        self.plotter.setFixedWidth(950)
        self.plotter.showAxis('bottom')
        self.plotter.showAxis('left')
        self.plot_envelope = pg.PlotCurveItem(size=7, pen=pg.mkPen(0, 255, 0, 120), connected=True, symbol='o') # Green
        self.plotter.addItem(self.plot_envelope)
        self.plot_scan = pg.ScatterPlotItem(size=5, pen=pg.mkPen(255, 255, 255, 120), connected=True, symbol='o') # White
        self.plotter.addItem(self.plot_scan)
        self.plot_violation = pg.ScatterPlotItem(size=5, pen=pg.mkPen(255, 0, 0, 120), connected=False, symbol='x') # Red
        self.plotter_layout = QVBoxLayout()
        self.plotter_layout.addWidget(self.plotter)
        self.grpVisual.setLayout(self.plotter_layout)
        # Initialize Background Data
        # Envelope Data
        self.base_envelope = []
        with open('Resources/envelopeCoords.csv') as ef:
            reader = csv.reader(ef, delimiter=',')
            line = 0
            for row in reader:
                if line != 0:
                    ID = int(row[0])
                    x = float(row[1])
                    y = float(row[2])
                    div = str(row[3]).strip()
                    self.base_envelope.append([ID, x, y, div])
                line += 1
        # Scan Profiles
        # TODO

        # Check Connection to CVS_AP
        self.myMQTT = mqtt()
        wifi = subprocess.check_output(['iwgetid', '-r'])
        data = wifi.decode('utf-8')
        if ("CVS_AP" in data):
            # Initialize MQTT
            self.myMQTT = mqtt(self)
            self.myMQTT.stateChanged.connect(self.mqtt_state_change)
            self.myMQTT.messageSignal.connect(self.on_messageSignal)
            self.myMQTT.hostname = "192.168.42.10"
            self.myMQTT.connectToHost()
            self.myMQTT.subscribe("/data/LEA")
            self.myMQTT.subscribe("/data/REA")
            self.myMQTT.subscribe("/data/SEA")
            self.myMQTT.subscribe("/data/SEO")
            self.myMQTT.subscribe("/data/SP")
        else:
            QMessageBox.information(self, "Connection Error!", "Not connected to device via CVS_AP. Reconnect and try again.")
            self.close()
            sys.exit()

        # Start with fresh profile
        self.current_profile = Profile()

        # Show window and populate data controls
        self.show()
        self.data_update()

# MQTT Functions

    def mqtt_state_change(self):
        pass

    def on_messageSignal(self, msg):
        top = msg[msg.index("/", 2)+1:msg.index("|")]
        val = msg[msg.index("|")+1:]
        this_function = self.response_dict[top]
        this_function(val)
        self.data_update()


# Control Functions
    
    def ERLE(self):
        self.myMQTT.publish("command", "ERLE")

    def ERRE(self):
        self.myMQTT.publish("command", "ERRE")

    def ERSE(self):
        self.myMQTT.publish("command", "ERSE")

    def ETHM(self):
        self.myMQTT.publish("command", "ETHM")

    def ETSR(self):
        this_resolution = "1.800" #self.cmbScanResolution.currentText()
        self.myMQTT.publish("command", f"ETSR:{this_resolution}")

    def ETSP(self):
        self.ETSR()
        self.myMQTT.publish("command", "ETSP")

    def ETTL(self):
        self.myMQTT.publish("command", "ETTL")

    def ETTM(self):
        self.myMQTT.publish("command", "ETTM")

    def envelope_change(self):
        if self.rbAD.isChecked():
            self.current_profile.envelope = "A Division"
        elif self.rbBD.isChecked():
            self.current_profile.envelope = "B Division"
        elif self.rbCD.isChecked():
            self.current_profile.envelope = "C Division"
        elif self.rbDD.isChecked():
            self.current_profile.envelope = "D Division"


# Data Handle Functions

    def LEA(self, value):
        self.current_profile.LEA = float(value)

    def REA(self, value):
        self.current_profile.REA = float(value)

    def SEA(self, value):
        self.current_profile.SEA = float(value)

    def SEO(self, value):
        self.current_profile.SEO = float(value)

    def SP(self, value):
        if value == "SP:1":
            # Scan Complete Flag
            self.plot_scanpoints()
        else:
            this_x = float(value[0:value.index("|")])
            this_y = float(value[value.index("|")+1:])
            self.current_profile.SP.append([this_x, this_y])

# Profile Handle Functions

    def profile_save(self):
        pass

    def profile_create(self):
        pass

    def profile_update(self):
        pass

    def profile_delete(self):
        pass

    def profile_select(self):
        pass

# Data Visualization Functions

    def data_update(self):
        # Clear Data Table
        headers = ["Parameter", "Value"]
        params = ["LEA", "REA", "BR", "CE", "EE", "SEA", "SEO", "SP"]
        self.lstScanData.clearSpans()
        # Get New Data
        this_lea = self.current_profile.LEA
        this_rea = self.current_profile.REA
        this_br, this_ce, this_ee = None, None, None
        if self.current_profile.brAvailable():
            this_br = self.current_profile.bendRadius()
            this_ce = self.current_profile.centerExcess()
            this_ee = self.current_profile.endExcess()
        this_sea = self.current_profile.SEA
        this_seo = self.current_profile.SEO
        this_sp = len(self.current_profile.SP)
        values = [this_lea, this_rea, this_br, this_ce, this_ee, this_sea, this_seo, this_sp]
        # Populate Table
        self.lstScanData.setRowCount(len(params))
        self.lstScanData.setColumnCount(len(headers))
        self.lstScanData.setHorizontalHeaderLabels(headers)
        header = self.lstScanData.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for row in range(0, len(params)):
            self.lstScanData.setItem(row, 0, QtWidgets.QTableWidgetItem(params[row]))
            self.lstScanData.item(row, 0).setText(str(params[row]))
            self.lstScanData.setItem(row, 1, QtWidgets.QTableWidgetItem(str(values[row])))
            self.lstScanData.item(row,1).setText(str(values[row]))
        # Update Scan Visualizer
        adjusted_coordinates = []
        for env_coord in self.base_envelope:
            if env_coord[3] == self.current_profile.envelope:
                this_x = env_coord[1]
                this_y = env_coord[2]
                if self.current_profile.SEA != None:
                    vect_rad = math.sqrt(this_x**2 + this_y**2)
                    vect_ang = (math.atan2(this_y, this_x) * (180.0 / math.pi)) + self.current_profile.SEA
                    this_x = vect_rad * math.cos(vect_ang * (math.pi / 180.0))
                    this_y = vect_rad * math.sin(vect_ang * (math.pi / 180.0))
                if self.current_profile.brAvailable():
                    br_adj = 0.00
                    if self.rbInside.isChecked():
                        br_adj = self.current_profile.CE
                    else:
                        br_adj = self.current_profile.EE
                    this_x = this_x + br_adj
                adjusted_coordinates.append([this_x, this_y])
        env_x, env_y = [], []
        for p in adjusted_coordinates:
            env_x.append(p[0])
            env_y.append(p[1])
        self.plot_envelope.clear()
        self.plot_envelope.setData(x=env_x, y=env_y)

    def plot_scanpoints(self):
        self.plot_scan.clear()
        self.plot_violation.clear()
        vio_x, vio_y = [], []
        for scan_point in self.current_profile.SP:
            self.plot_scan.addPoints([scan_point[0]], [scan_point[1]])
            if self.scanpoint_is_violation(scan_point):
                vio_x.append(scan_point[0])
                vio_y.append(scan_point[1])
        self.plot_violation.setData(x=vio_x, y=vio_y)

# Data Validation Functions

    def scanpoint_is_violation(self, scan_point):
        return False

# Export Functions


if __name__ == "__main__":
    this_app = QApplication(sys.argv)
    this_window = CVS_Interface(this_app)
    sys.exit(this_app.exec_())