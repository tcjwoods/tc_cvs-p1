"""
Script Intro

"""

# Import Necessary Libraries #
import subprocess
import os
import requests
import PyQt5
import sys
import csv
import math
import time
import pyodbc
import sqlite3
import pyqtgraph as pg
import pyqtgraph.exporters
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import geopandas
import mysql.connector
from mysql.connector import errorcode
from fillpdf import fillpdfs
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from Classes.profile import Profile
from Classes.mqtt import mqttClient as mqtt
from Classes.tableModel import MyTableModel
import pdfrw
# TODO - Determine which imports can be removed

# Interface Class #

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
        self.rbAD.clicked.connect(self.envelope_change)
        self.rbBD.clicked.connect(self.envelope_change)
        self.rbInside.clicked.connect(self.envelope_change)
        self.rbOutside.clicked.connect(self.envelope_change)
        self.actNewScan.triggered.connect(self.profile_create)
        self.actSaveScan.triggered.connect(self.profile_save)
        self.actClearanceReport.triggered.connect(self.export_report)
        self.actClearanceScan.triggered.connect(self.export_scan)
        self.actDataTable.triggered.connect(self.export_data)
        self.actScanPoints.triggered.connect(self.export_scan_data)
        self.lstProfiles.doubleClicked.connect(self.profile_select)
        self.actCloudUpload.triggered.connect(self.profile_cloud)

        # Response Dictionary
        self.response_dict = {
            "SEA": self.SEA,
            "SEO": self.SEO,
            "LE": self.LEA,
            "RE": self.REA,
            "SP": self.SP,
            "IMO": self.IM_OUTSIDE,
            "IMI": self.IM_INSIDE}

        # MQTT Topic List
        self.mqtt_topics = [
            "/data/LE",
            "/data/RE",
            "/data/SEA",
            "/data/SEO",
            "/data/SP",
            "/data/IMG",
            "/debug"]

        # Initialize Plotter
        self.plotter = pg.plot()
        self.imv = pg.ImageView()
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
        self.plot_violation = pg.ScatterPlotItem(size=5, pen=pg.mkPen(255, 0, 0, 120), brush='r',
                                                 connected=False, symbol='x', symbolPen='r') # Red
        self.plot_violation.setBrush('r')
        self.plot_violation.setSymbol('x')
        self.plotter.addItem(self.plot_violation)
        self.plot_min_violation = pg.ScatterPlotItem(size=15, pen=pg.mkPen(204, 255, 0, 120), brush='r',
                                                     symbol='x', symbolPen='r') # Neon Green
        self.plotter.addItem(self.plot_min_violation)
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
        # Create a temp default save profile
        self.current_profile = Profile()
        # Set Curve to Inside by Default
        self.rbInside.setChecked(True)
        # Set Envelope to A Division by Default
        self.rbAD.setChecked(True)

        # Check Current Connections
        self.device_connection = False
        self.internet_connection = False
        # Connection to Device
        self.myMQTT = mqtt()
        wifi = subprocess.check_output(['iwgetid', '-r'])
        data = wifi.decode('utf-8')
        if ("CVS_AP" in data):
            # Initialize MQTT
            self.myMQTT = mqtt(self)
            self.myMQTT.stateChanged.connect(self.mqtt_state_change)
            self.myMQTT.messageSignal.connect(self.on_message)
            self.myMQTT.hostname = "192.168.42.10"
            self.myMQTT.connectToHost()
            self.myMQTT.subscribe("/data/LE")
            self.myMQTT.subscribe("/data/RE")
            self.myMQTT.subscribe("/data/SEA")
            self.myMQTT.subscribe("/data/SEO")
            self.myMQTT.subscribe("/data/SP")
            self.device_connection = True
        else:
            self.device_connection = False
            QMessageBox.information(self, "Connection Error!", "Not connected to device via CVS_AP. You will not be"
                                                               "able to perform clearance measurements until connected"
                                                               " to CVS_AP.")
            #self.close()
            #sys.exit()
        # Connection to Internet
        url = "https://www.google.com"
        try:
            #request = requests.get(url, timeout=1)
            #self.internet_connection = True
            #QMessageBox.information(self, "Internet Connection!", "You are currently connected to the internet. Cloud "
             #                                                     "upload features have been enabled.")
            pass
        except Exception as e:
            self.internet_connection = False
            QMessageBox.information(self, "Internet Connection!", "You are not connected to the internet. Cloud "
                                                                  "upload features have been disabled.")

        # Show window and populate data controls
        self.show()
        self.data_update()
        self.plot_scanpoints()
        QMessageBox.information(self, "Empty Scan Profile", "You are operating in a blank scan profile and all data"
                                                            " will require profile to be saved. Scan information"
                                                            " (Line, Track, Stationing) will be captured when saving."
                                                            " To open an existing profile, select and load a profile"
                                                            " from the profile menu.")

        # !Testing!
        test_flag = False
        if test_flag:
            #self.test_profile_update()
            #self.test_clearance_calculations()
            #self.test_br_outside()
            #self.test_save_profile()
            pass

# MQTT Functions

    def reconnect(self):
        while self.myMQTT.m_state == self.myMQTT.Disconnected:
            # Check if wifi connected
            try:
                wifi = subprocess.check_output(['iwgetid', '-r'])
                data = wifi.decode('utf-8')
                if "CVS_AP" in data:
                    self.myMQTT.connectToHost()
            except Exception:
                # Not connected to wifi
                time.sleep(1)


    def mqtt_state_change(self):
        if self.myMQTT.m_state == self.myMQTT.Connected:
            QMessageBox.information(self, "Connection Established", "Connection to device established.")
            print("Connection established to device.\n")
        elif self.myMQTT.m_state == self.myMQTT.Disconnected:
            # TODO - Swap to messagebox
            QMessageBox.information(self, "Connection Lost", "Connection to device was lost. Attempting to reconnect.")
            self.reconnect()

    def on_message(self, msg):
        print(f'RESP: {msg}')
        top = msg[msg.index("/", 2)+1:msg.index("|")]
        val = msg[msg.index("|")+1:]
        this_function = self.response_dict[top]
        this_function(val)
        if top in ["SEA", "SEO", "LE", "RE"]:
            self.data_update()
        if top in ["IMO"]:
            self.IM_OUTSIDE(val)
        if top in ["IMI"]:
            self.IM_INSIDE(val)
        if top in ["SP"]:
            self.SP(val)

# Control Functions
    
    def ERLE(self):
        self.myMQTT.publish("/command", "ERLE")

    def ERRE(self):
        self.myMQTT.publish("/command", "ERRE")

    def ERSE(self):
        self.myMQTT.publish("/command", "ERSE")

    def ETHM(self):
        self.myMQTT.publish("/command", "ETHM")

    def ETSR(self):
        this_resolution = "1.800" #self.cmbScanResolution.currentText()
        self.myMQTT.publish("/command", f"ETSR:{this_resolution}")

    def ETSP(self):
        #self.ETSR()
        self.myMQTT.publish("/command", "ETSP")

    def ETTL(self):
        self.myMQTT.publish("/command", "ETTL")

    def ETTM(self):
        self.myMQTT.publish("/command", "ETTM")

    def ETCE(self):
        self.myMQTT.publish("/command", "ETCE")

    def envelope_change(self):
        # Envelope Division
        if self.rbAD.isChecked():
            self.current_profile.a_division = True
        elif self.rbBD.isChecked():
            self.current_profile.a_division = False
        # Inside/Outside Curve
        if self.rbInside.isChecked():
            self.current_profile.inside = True
        else:
            self.current_profile.inside = False
        self.data_update()


# Data Handle Functions

    def LEA(self, value):
        print(value)
        self.current_profile.LEA = float(value)

    def REA(self, value):
        self.current_profile.REA = float(value)

    def SEA(self, value):
        self.current_profile.SEA = float(value)
        self.current_profile.SEO = math.sin(float(value)) * 56.5

    def SEO(self, value):
        self.current_profile.SEO = float(value)

    def SP(self, value):
        if not value == "SP:1":
            x_offset = 0.00
            y_offset = 10.375
            this_x = float(value[1:value.index(",")]) + x_offset
            this_y = float(value[value.index(",")+2:-1]) + y_offset
            self.current_profile.SP.append([this_x, this_y])
        update = False
        if value == "SP:1":
            update = True
        if len(self.current_profile.SP) % 10 == 0:
            update = True
        if update:
            self.data_update()


    def IM_INSIDE(self, value):
        image_data = value
        im_file = open(r'Temp/temp_im_inside.jpg', 'wb')
        im_file.write(image_data)
        self.current_profile.im_inside = image_data
        im_file.close()

    def IM_OUTSIDE(self, value):
        image_data = value
        im_file = open(r'Temp/temp_im_outside.jpg', 'wb')
        im_file.write(image_data)
        self.current_profile.im_outside = image_data
        im_file.close()

# Clearance Calculation Functions

    def calculate_clearances(self):
        clearances = []
        envelope_polygon = Polygon(self.adjusted_envelope)
        envelope_geo = geopandas.GeoSeries(envelope_polygon)
        min_dist = 9999.99
        min_x, min_y = 0.0, 0.0
        for point in self.current_profile.SP:
            this_distance = None
            this_violation = None
            this_point = Point(point[0], point[1])
            # Within Envelope Check
            this_violation = envelope_polygon.contains(this_point)
            # Calculate Clearance
            point_geo = geopandas.GeoSeries(this_point)
            this_distance = envelope_geo.boundary.distance(point_geo)[0]
            if this_violation: this_distance = -this_distance
            if this_distance < min_dist:
                min_dist = this_distance
                min_x = point[0]
                min_y = point[1]
            clearances.append([this_violation, this_distance])
        return [clearances, min_x, min_y]

    def scanpoint_is_violation(self, scan_point):
        envelope_polygon = Polygon(self.adjusted_envelope)
        envelope_geo = geopandas.GeoSeries(envelope_polygon)
        this_point = Point(scan_point[0], scan_point[1])
        return envelope_polygon.contains(this_point)

# Profile Handle Functions

    def profile_load_all(self):
        # Collects all profiles from SQL DB
        try:
            # Retrieve profiles from Local DB
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), r"Resources/cvs_local.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            query = "select * from profiles"
            cursor.execute(query)
            data = cursor.fetchall()
            table_data = []
            self.profiles = []
            for row in data:
                print(row)
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
        # Checks if needs to save current profile
        response = QMessageBox.information(self, "Save Current?", f"Would you like to save the current scan profile before selecting another?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if response == QMessageBox.Yes:
            self.profile_save()
        # Activates selected profile
        indexes = self.lstProfiles.selectionModel().selectedRows()
        for index in indexes:
            this_index = index.row()
            self.current_profile = self.profiles[this_index]
        # Update interface controls
        if self.current_profile.inside:
            self.rbInside.setChecked(True)
        else:
            self.rbOutside.setChecked(True)
        if self.current_profile.a_division:
            self.rbAD.setChecked(True)
        else:
            self.rbBD.setChecked(True)
        print(f"Selected profile with ID = {self.current_profile.ID}")
        self.data_update()
        self.plot_scanpoints()

    def profile_create(self):
        # Checks if needs to save current profile
        response = QMessageBox.information(self, "Save Current?", f"Would you like to save the current scan profile before creating another?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if response == QMessageBox.Yes:
            self.profile_save()
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


    def profile_cloud(self):
        # TODO - Update to handle image data
        local_path = r"Resources/cvs_local.db"
        # Retrieve current state of local db
        local_conn = sqlite3.connect(local_path)
        local_cursor = local_conn.cursor()
        local_cursor.execute("SELECT * FROM Profiles")
        local_results = local_cursor.fetchall()
        for profile in self.profiles:
            found = False
            changes = False
            # Find matching profile from db
            for db_profile in local_results:
                this_date = db_profile[1]
                if this_date == profile.date:
                    found = True
                    if not profile.line == db_profile[2]:
                        changes = True
                    if not profile.track == db_profile[3]:
                        changes = True
                    if not profile.stationing == db_profile[4]:
                        changes = True
                    if not profile.LEA == db_profile[5]:
                        changes = True
                    if not profile.REA == db_profile[6]:
                        changes = True
                    if not profile.bendRadius() == db_profile[7]:
                        changes = True
                    if not profile.centerExcess() == db_profile[8]:
                        changes = True
                    if not profile.endExcess() == db_profile[9]:
                        changes = True
                    if not profile.SEA == db_profile[10]:
                        changes = True
                    if not profile.scan_string() == db_profile[11]:
                        changes = True
                    if changes:
                        # Push changes to local DB
                        query = profile.generate_update_query("Profiles")
                        local_cursor.execute(query[0], query[1])
                    break
            if not found:
                query = profile.generate_insert_query("Profiles")
                local_cursor.execute(query[0], query[1])
        local_conn.commit()
        local_cursor.close()
        local_conn.close()

        # Cloud DB Changes
        if self.internet_connection:
            # Retrieve current state of cloud db
            config = {
                'server': 'sql-cvs-dev-eastus.database.windows.net',
                'database': 'db-cvs-dev-eastus',
                'username': 'tcjwoods',
                'password': 'Clearance1!'
            }
            conn_string = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:sql-cvs-dev-eastus.database.windows.net," \
                          "1433;Database=db-cvs-dev-eastus;Uid=tcjwoods;Pwd=Clearance1!;Encrypt=yes;" \
                          "TrustServerCertificate=no;Connection Timeout=30;"
            cloud_conn = pyodbc.connect(conn_string)

            cloud_cursor = cloud_conn.cursor()
            query = "SELECT * FROM Profiles"
            cloud_cursor.execute(query)
            cloud_results = cloud_cursor.fetchall()
            for profile in self.profiles:
                found = False
                changes = False
                for db_profile in cloud_results:
                    this_date = db_profile[1]
                    if this_date == profile.date:
                        found = True
                        if not profile.line == db_profile[2]:
                            changes = True
                        if not profile.track == db_profile[3]:
                            changes = True
                        if not profile.stationing == db_profile[4]:
                            changes = True
                        if not profile.LEA == db_profile[5]:
                            changes = True
                        if not profile.REA == db_profile[6]:
                            changes = True
                        if not profile.bendRadius() == db_profile[7]:
                            changes = True
                        if not profile.centerExcess() == db_profile[8]:
                            changes = True
                        if not profile.endExcess() == db_profile[9]:
                            changes = True
                        if not profile.SEA == db_profile[10]:
                            changes = True
                        if not profile.scan_string() == db_profile[11]:
                            changes = True
                        if changes:
                            # Push changes to local DB
                            query = profile.generate_update_query("Profiles")
                            cloud_cursor.execute(query[0], query[1])
                        break
                if not found:
                    query = profile.generate_insert_query("Profiles")
                    cloud_cursor.execute(query[0], query[1])
            cloud_conn.commit()
            cloud_cursor.close()
            cloud_conn.close()


# Data Visualization Functions

    def data_update(self):
        # Update Visualized Scan
        self.adjusted_envelope = []
        this_BRAvailable = self.current_profile.brAvailable()
        this_CE = self.current_profile.centerExcess()
        this_BR = self.current_profile.bendRadius()
        this_EE = self.current_profile.endExcess()
        this_inside = self.rbInside.isChecked()
        if self.rbAD.isChecked():
            desired_division = "A Division"
        else:
            desired_division = "B Division"
        for env_coord in self.base_envelope:
            if env_coord[3] == desired_division:
                this_x = env_coord[1]
                this_y = env_coord[2]
                if not self.current_profile.SEA is None:
                    vect_rad = math.sqrt(this_x**2 + this_y**2)
                    vect_ang = (math.atan2(this_y, this_x) * (180.0 / math.pi)) + self.current_profile.SEA
                    this_x = vect_rad * math.cos(vect_ang * (math.pi / 180.0))
                    this_y = vect_rad * math.sin(vect_ang * (math.pi / 180.0))
                if this_BRAvailable:
                    br_adj = 0.00
                    if this_inside:
                        br_adj = this_CE
                    else:
                        br_adj = this_EE
                    this_x = this_x + br_adj
                self.adjusted_envelope.append([this_x, this_y])
        env_x, env_y = [], []
        for p in self.adjusted_envelope:
            env_x.append(p[0])
            env_y.append(p[1])
        self.plot_envelope.clear()
        self.plot_envelope.setData(x=env_x, y=env_y)
        self.plot_min_violation.clear()
        self.plot_scanpoints()
        # Clear Data Table
        self.lstScanData.clearSpans()
        # Retrieve Data
        this_id = self.current_profile.ID
        this_line = self.current_profile.line
        this_track = self.current_profile.track
        this_stationing = self.current_profile.stationing
        this_lea = self.current_profile.LEA
        this_rea = self.current_profile.REA
        if self.current_profile.brAvailable():
            temp_br = self.current_profile.bendRadius()
            if None in temp_br:
                this_br = temp_br[0]
                this_lbr = None
                this_rbr = None
            else:
                this_lbr = temp_br[0]
                this_rbr = temp_br[1]
                this_br = min(temp_br)
        else:
            this_lbr = None
            this_rbr = None
            this_br = None
        this_ce = self.current_profile.centerExcess()
        this_ee = self.current_profile.endExcess()
        this_sea = self.current_profile.SEA
        this_seo = self.current_profile.SEO
        this_SP = len(self.current_profile.SP)
        this_violation = None
        this_clearance = None
        # Check Clearances
        clearance_return = self.calculate_clearances()
        these_clearances = clearance_return[0]
        this_clearance = 9999999
        this_violation = False
        if these_clearances:
            these_violations, these_distances = map(list, zip(*these_clearances))
            this_violation = True in these_violations
            this_clearance = min(these_distances)
            self.plot_min_violation.addPoints([clearance_return[1]], [clearance_return[2]])
        else:
            this_violation = False
            min_clearance = 0.00
        # Populate Data Table
        table_parameters = ["ID",
                            "LINE",
                            "TRACK",
                            "STATIONING",
                            "LEA",
                            "REA",
                            "BR Left",  # Index = 6
                            "BR Right", # Index = 7
                            "BR",       # Index = 8
                            "CE",       # Index = 9
                            "EE",       # Index = 10
                            "SEA",
                            "SEO",
                            "SP",
                            "SP Violation",
                            "Min Clearance"]
        table_values = [this_id,
                        this_line,
                        this_track,
                        this_stationing,
                        this_lea,
                        this_rea,
                        this_lbr,
                        this_rbr,
                        this_br,
                        this_ce,
                        this_ee,
                        this_sea,
                        this_seo,
                        this_SP,
                        this_violation,
                        this_clearance]
        if self.current_profile.inside:
            table_parameters.pop(10)
            table_parameters.pop(7)
            table_parameters.pop(6)
            table_values.pop(10)
            table_values.pop(7)
            table_values.pop(6)
        else:
            table_parameters.pop(9)
            table_parameters.pop(8)
            table_values.pop(9)
            table_values.pop(8)
        self.lstScanData.setRowCount(len(table_values))
        self.lstScanData.setColumnCount(2)
        self.lstScanData.setHorizontalHeaderLabels(table_parameters)
        header = self.lstScanData.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for row in range(0, len(table_values)):
            self.lstScanData.setItem(row, 0, QtWidgets.QTableWidgetItem(table_parameters[row]))
            self.lstScanData.item(row, 0).setText(str(table_parameters[row]))
            self.lstScanData.setItem(row, 1, QtWidgets.QTableWidgetItem(str(table_values[row])))
            self.lstScanData.item(row,1).setText(str(table_values[row]))


    def plot_scanpoints(self):
        self.plot_scan.clear()
        self.plot_violation.clear()
        vio_x, vio_y = [], []
        for scan_point in self.current_profile.SP:
            if not (scan_point[0] == 0.0) and not (scan_point[1] == 0.0):
                #self.plot_scan.addPoints([scan_point[0]], [scan_point[1]])
                if self.scanpoint_is_violation(scan_point):
                    vio_x.append(scan_point[0])
                    vio_y.append(scan_point[1])
                else:
                    self.plot_scan.addPoints([scan_point[0]], [scan_point[1]])
        self.plot_violation.setData(x=vio_x, y=vio_y)

# Export Functions

    def export_report(self):
        # Exports data as "Clearance Verification Report" PDF
        input_file = 'Resources/report_template.pdf'
        data_dict = fillpdfs.get_form_fields(input_file)
        print(data_dict)
        # Assign data to dictionary for filling
        violation_flag = False
        min_clearance = 9999.99
        clearance_resp = self.calculate_clearances()
        clearances = clearance_resp[0]
        min_x = clearance_resp[1]
        min_y = clearance_resp[2]
        for c in clearances:
            if c[0] == True:
                violation_flag = True
            if c[1] < min_clearance:
                min_clearance = c[1]

        if min_clearance == 9999.99:
            min_clearance = "N/a"
        # Retrieve Visualized JPG
        plot_file = 'Temp/cvs_visual_export_' + str(time.time()) + '.jpg'
        #with open(filename, 'w'):
            # Create file
        #    pass
        #self.imv.export(filename)
        exporter = pg.exporters.ImageExporter(self.plotter.sceneObj)
        exporter.export(plot_file)
        # Retrieve Images
        inside_image = open(r'Temp/temp_im_inside.jpg')
        outside_image = open(r'Temp/temp_im_outside.jpg')
        # Compile Data for Report
        data_dict = {
            'frmLine': self.current_profile.line,
            'frmTrack': self.current_profile.track,
            'frmStationing': self.current_profile.stationing,
            'frmEquipment': self.current_profile.equipment,
            'frmDate': self.current_profile.date_string(),
            'frmPerformed': "",  # TODO Add this field to creation of scan
            'frmInside': f"{self.current_profile.inside:.2f}",
            'frmSuper': f"{self.current_profile.SEA:.2f} deg.",
            'frmBend': f"{min(self.current_profile.bendRadius()):.2f} ft.",
            'frmCenter': f"{self.current_profile.centerExcess():.2f} in.",
            'frmEnd': f"{self.current_profile.endExcess():.2f} in.",
            'frmClearance': f"{min_clearance:.2f} in."
        }
        print(data_dict)
        # Save and Flatten PDF
        output_file, check = QFileDialog.getSaveFileName(None, "Save Report As..", "", "PDF Files (*.pdf);;All Files (*)")
        if ".pdf" not in output_file:
            output_file += '.pdf'
        temp_file = output_file[0:-4] + "_temp.pdf"
        temp_file1 = output_file[0:-4] + "_temp1.pdf"
        temp_file2 = output_file[0:-4] + "_temp2.pdf"
        fillpdfs.write_fillable_pdf(input_file, temp_file, data_dict, flatten=True)
        fillpdfs.place_image(plot_file, 93, 250, temp_file, temp_file1, 1, width=400, height=190)  # Visualized Scan
        fillpdfs.place_image(inside_image, 110, 450, temp_file1, temp_file2, 1, width=200, height=120)  # Inside Image
        fillpdfs.place_image(inside_image, 285, 450, temp_file2, output_file, 1, width=200, height=120)  # Outside Image

        #fillpdfs.flatten_pdf(output_file, output_file, False)

        # Clean up temp files
        try:
            os.remove(plot_file)
            os.remove(temp_file)
            os.remove(temp_file1)
            os.remove(temp_file2)
        except:
            pass
        print("Export of Clearance Report completed.\n")

    def export_data(self):
        # !!!!! Need to Test !!!!! #
        # Exports data as a table of relevant clearance information as CSV
        file, check = QFileDialog.getSaveFileName(None, "Save Data Table As..", "", "CSV Files (*.csv);;All Files (*)")
        if not ".csv" in file:
            file = file + ".csv"
        violations = False
        min_clearance = 9999.99
        for p in self.calculate_clearances():
            if p[0]:
                violations = True
            if p[1] < min_clearance:
                min_clearance = p[1]
        with open(file, newline='\n', mode='w') as export_file:
            writer = csv.writer(export_file, delimiter=',')
            export_data = [["Line/Location:", self.current_profile.line],
                           ["Track:", self.current_profile.track],
                           ["Stationing:", self.current_profile.stationing],
                           ["Equipment:", self.current_profile.equipment],
                           ["Capture Date:", self.current_profile.date_string()],
                           ["Inside of Curve:", self.current_profile.inside],
                           ["Left Encoder Angle", self.current_profile.LEA],
                           ["Right Encoder Angle:", self.current_profile.REA],
                           ["Bend Radius:", self.current_profile.bendRadius()],
                           ["Center Excess:", self.current_profile.centerExcess()],
                           ["End Excess:", self.current_profile.endExcess()],
                           ["Super Elevation Angle:", self.current_profile.SEA],
                           ["Total Scan Points:", len(self.current_profile.SP)],
                           ["Contains Violations:", violations],
                           ["Minimum Clearance:", min_clearance]]
            for line in export_data:
                #out_line = line[0] + ',' + line[1]
                writer.writerow(line)
        print("Export of Clearance Data completed.\n")

    def export_scan(self):
        # !!!!! Need to Test !!!!! #
        # Exports visualized scan as JPG
        filename, check = QFileDialog.getSaveFileName(None, "Save Scan Export As..", "", "JPG Files (*.jpg);;"
                                                                                         "All Files (*)")
        if ".jpg" not in filename:
            filename += ".jpg"
        exporter = pg.exporters.ImageExporter(self.plotter.sceneObj)
        exporter.export(filename)
        print("Export of Visualized Scan completed.\n")

    def export_scan_data(self):
        # !!!!! Need to Test !!!!! #
        # Exports scan points as CSV
        filename, check = QFileDialog.getSaveFileName(None, "Save Scan Data As..", "", "CSV Files (*.csv);;"
                                                                                       "All Files (*)")
        if ".csv" not in filename:
            filename += ".csv"
        header_data = [
            ["Track/Location:", self.current_profile.track],
            ["Line:", self.current_profile.line],
            ["Stationing:", self.current_profile.stationing],
            ["Equipment:", self.current_profile.equipment],
            ["Date:", self.current_profile.get_timestamp()],
            ["Total Scan Points:", len(self.current_profile.SP)],
            ["Scan Points:", ""],
            ["SP X Coordinate", "SP Y Coordinate"]
        ]
        with open(filename) as export_file:
            writer = csv.writer(export_file)
            for line in header_data:
                writer.writerow(line)
            for sp in self.current_profile.SP:
                writer.writerow(sp)
        print("Export of Scan Data completed.\n")

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
