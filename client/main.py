"""
Script Intro

"""

# Imports
import subprocess
import os
import PyQt5
import sys
import csv
import math
import pyodbc
import sqlite3
import pyqtgraph as pg
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import geopandas
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from Classes.profile import Profile
from Classes.mqtt import mqttClient as mqtt

##### Table Model Class ##### (Move to own file)

class MyTableModel(QAbstractTableModel):
    def __init__(self, parent, mylist, header, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.mylist = mylist
        self.header = header

    def rowCount(self, parent):
        return len(self.mylist)

    def columnCount(self, parent):
        return len(self.mylist[0])

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        return self.mylist[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None

##### Interface Class #####
class CVS_Interface(QMainWindow):

    def closeEvent(self, QCloseEvent):
        print("Closing now..")

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
        self.adjusted_envelope = None # Envelope Coordinates of Adjusted Points

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

        # Initialize Profile Selection Table
        self.table_profiles_headers = ['ID', 'Line', 'Track', 'Stationing', 'Timestamp']

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
        self.profiles = []
        self.profile_load_all()
        if len(self.profiles) > 0:
            self.current_profile = self.profiles[0]
        else:
            self.current_profile = Profile()

        # Check Connection to CVS_AP
        self.myMQTT = mqtt()
        #wifi = subprocess.check_output(['iwgetid', '-r'])
        #data = wifi.decode('utf-8')
        #if ("CVS_AP" in data):
        #    # Initialize MQTT
        #    self.myMQTT = mqtt(self)
        #    self.myMQTT.stateChanged.connect(self.mqtt_state_change)
        #    self.myMQTT.messageSignal.connect(self.on_messageSignal)
        #    self.myMQTT.hostname = "192.168.42.10"
        #    self.myMQTT.connectToHost()
        #    self.myMQTT.subscribe("/data/LEA")
        #    self.myMQTT.subscribe("/data/REA")
        #    self.myMQTT.subscribe("/data/SEA")
        #    self.myMQTT.subscribe("/data/SEO")
        #    self.myMQTT.subscribe("/data/SP")
        #else:
        #    QMessageBox.information(self, "Connection Error!", "Not connected to device via CVS_AP. Reconnect and try again.")
        #    #self.close()
        #    #sys.exit()

        # Show window and populate data controls
        self.show()
        self.data_update()

        # !Testing!
        test_flag = False
        if test_flag:
            #self.test_profile_update()
            #self.test_clearance_calculations()
            #self.test_br_outside()
            #self.test_save_profile()
            pass

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

    def profile_load_all(self):
        # Collects all profiles from SQL DB
        try:
            # Retrieve profiles from DB
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), r"Resources/cvs_local.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            query = "select * from profiles"
            cursor.execute(query)
            data = cursor.fetchall()
            table_data = []
            self.profiles = []
            for row in data:
                this_profile = Profile()
                this_profile.bulk_data_upload(row)
                self.profiles.append(this_profile)
                table_data.append([this_profile.ID,
                                   this_profile.line,
                                   this_profile.track,
                                   this_profile.stationing,
                                   this_profile.date])
            # Add profiles to table view
            table_model = MyTableModel(self, table_data, self.table_profiles_headers)
            self.lstProfiles.setModel(table_model)
        except Exception as e:
            print(e)


    def profile_select(self):
        # Activates selected profile
        indexes = self.lstProfiles.selectionModel().selectedRows()
        for index in indexes:
            this_index = index.row()
            self.current_profile = self.profiles[this_index]
        print(f"Selected profile with ID = {self.current_profile.ID}")
        self.data_update()
        self.plot_scanpoints()

    def profile_create(self):
        self.current_profile = Profile()
        self.data_update()
        self.plot_scanpoints()
        self.lstProfiles.clearSelection()
        QMessageBox.information(self, "Create Scan", "A new profile was created. You may begin capturing data now.")

    def profile_save(self):
        try:
            if self.current_profile.line is None:
                ok = False
                while not ok:
                    response, ok = QInputDialog.getText(self, "Missing Information", "Enter Train Line/Yard:")
                self.current_profile.line = response
            if self.current_profile.track is None:
                ok = False
                while not ok:
                    response, ok = QInputDialog.getText(self, "Missing Information", "Enter Track Number:")
                self.current_profile.track = response
            if self.current_profile.stationing is None:
                ok = False
                while not ok:
                    response, ok = QInputDialog.getText(self, "Missing Information", "Enter Stationing:")
                self.current_profile.stationing = response
            table = "profiles"
            # Connect to DB
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), r"Resources/cvs_local.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            # Check if Existing
            select_query = f"select * from profiles where " \
                           f"DATE='{self.current_profile.date}';"
            cursor.execute(select_query)
            select_results = cursor.fetchall()
            save_query = None
            if len(select_results) > 0:
                # Found a match, update instead of insert
                save_query = self.current_profile.generate_update_query(table)
            else:
                # Did not find, so insert instead of update
                save_query = self.current_profile.generate_insert_query(table)
            # Execute save query
            cursor.execute(save_query[0], save_query[1])
            conn.commit()
            conn.close()
            self.profile_load_all()
            self.data_update()
            print("Profile saved successfully.")
        except Exception as e:
            print(e)

    def profile_delete(self):
        indexes = self.lstProfiles.selectionModel().selectedRows()
        delete_index = None
        for index in indexes:
            delete_index = index.row()
        response = QMessageBox.information(self, "Confirm Deletion", f"Are you sure you would like to delete the selected scan (ID = {self.profiles[delete_index].ID})?", QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if response == QMessageBox.Yes:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), r"Resources/cvs_local.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM profiles WHERE ID=?", [self.profiles[delete_index].ID])
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Delete Successful", "The profile was successfully deleted.")
            self.profile_load_all()
        else:
            QMessageBox.information(self, "Delete Aborted", "The profile was NOT deleted.")


    def profile_synchronize(self):
        pass

# Data Visualization Functions

    def data_update(self):
        # Clear Data Table
        headers = ["Parameter", "Value"]
        params = ["ID", "LINE", "TRACK", "STATIONING", "LEA", "REA", "BR", "CE", "EE", "SEA", "SEO", "SP"]
        self.lstScanData.clearSpans()
        # Get New Data
        this_id = self.current_profile.ID
        this_line = self.current_profile.line
        this_track = self.current_profile.track
        this_stationing = self.current_profile.stationing
        this_lea = self.current_profile.LEA
        this_rea = self.current_profile.REA
        this_br, this_ce, this_ee = None, None, None
        if self.current_profile.brAvailable():
            inside = self.rbInside.isChecked()
            this_br = self.current_profile.bendRadius()
            this_ce = self.current_profile.centerExcess()
            this_ee = self.current_profile.endExcess()
        this_sea = self.current_profile.SEA
        this_seo = self.current_profile.SEO
        this_sp = len(self.current_profile.SP)
        values = [this_id, this_line, this_track, this_stationing, this_lea, this_rea, this_br, this_ce, this_ee, this_sea, this_seo, this_sp]
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
        self.adjusted_envelope = []
        for env_coord in self.base_envelope:
            if env_coord[3] == self.current_profile.envelope:
                this_x = env_coord[1]
                this_y = env_coord[2]
                if not self.current_profile.SEA is None:
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
                self.adjusted_envelope.append([this_x, this_y])
        env_x, env_y = [], []
        for p in self.adjusted_envelope:
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

    def calculate_clearances(self):
        envelope_polygon = Polygon(self.adjusted_envelope)
        envelope_geo = geopandas.GeoSeries(envelope_polygon)

        for point in self.current_profile.SP:
            this_point = Point(point[0], point[1])
            # Within Envelope Check
            violation = envelope_polygon.contains(this_point)
            # X Clearance
            if not violation:
                point_geo = geopandas.GeoSeries(this_point)
                envelope_geo.boundary.distance(point_geo)
                



    def scanpoint_is_violation(self, scan_point):
        return False

# Export Functions


# Test Functions
    def test_profile_update(self):
        # Create NEW profile and save
        self.current_profile = Profile()
        self.current_profile.line = "TEST"
        self.current_profile.track = "TEST"
        self.current_profile.stationing = "TEST"
        self.current_profile.REA = 0.00
        self.current_profile.LEA = 180.00
        self.current_profile.SEA = 0.00
        self.current_profile.inside = True
        self.profile_save()
        # Modfiy profile and update
        self.current_profile.REA = 6.00
        self.current_profile.LEA = 174.00
        self.current_profile.SEA = 0.50
        self.profile_save()

    def test_clearance_calculations(self):
        # Confirmed to function properly
        scanned_points = [[1,1], [2,2], [3,3], [4,4]]
        envelope_points = [[2.5,2.5], [-2.5,2.5], [-2.5,-2.5], [2.5,-2.5]]

        polygon = Polygon(envelope_points)
        geo_series = geopandas.GeoSeries(polygon)
        for point in scanned_points:
            this_point = Point(point[0], point[1])
            violation = polygon.contains(this_point)
            geo_point = geopandas.GeoSeries(this_point)
            this_distance = geo_series.distance(geo_point)
            print(point)
            print(f"Is Violation: {violation}")
            print(f"Distance to Envelope: {this_distance}\n")


    def test_br_outside(self):
        self.current_profile = Profile()
        self.current_profile.line = "TEST"
        self.current_profile.track = "TEST"
        self.current_profile.stationing = "TEST"
        self.current_profile.REA = 4.90 # 4.9 from tangent OC
        self.current_profile.LEA = 173.8 # 6.2 from tangent OC
        br = self.current_profile.bendRadius(False)
        print(br)

    def test_save_profile(self):
        # Create profile and assign as current
        self.current_profile = Profile()
        self.current_profile.line = "TEST"
        self.current_profile.track = "TEST"
        self.current_profile.stationing = "TEST"
        self.current_profile.SEA = 0.123
        self.current_profile.REA = -4.394
        self.current_profile.LEA = 179.209

        self.profile_save()

if __name__ == "__main__":
    this_app = QApplication(sys.argv)
    this_window = CVS_Interface(this_app)
    sys.exit(this_app.exec_())

##### Testing Functions #####

