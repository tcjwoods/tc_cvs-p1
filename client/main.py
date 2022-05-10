"""
Script Intro

"""

# Imports
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
from fillpdf import fillpdfs
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from Classes.profile import Profile
from Classes.mqtt import mqttClient as mqtt
from Classes.tableModel import MyTableModel
import pdfrw

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
            self.myMQTT.messageSignal.connect(self.on_messageSignal)
            self.myMQTT.hostname = "192.168.42.10"
            self.myMQTT.connectToHost()
            self.myMQTT.subscribe("/data/LEA")
            self.myMQTT.subscribe("/data/REA")
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
            request = requests.get(url, timeout=5)
            self.internet_connection = True
            QMessageBox.information(self, "Internet Connection!", "You are currently connected to the internet. Cloud "
                                                                  "upload features have been enabled.")
        except Exception as e:
            self.internet_connection = False
            QMessageBox.information(self, "Internet Connection!", "You are not connected to the internet. Cloud "
                                                                  "upload features have been disabled.")

        # Show window and populate data controls
        self.show()
        self.data_update()
        self.plot_scanpoints()

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
        # Envelope Division
        if self.rbAD.isChecked():
            self.current_profile.envelope = "A Division"
        elif self.rbBD.isChecked():
            self.current_profile.envelope = "B Division"
        # Inside/Outside Curve
        if self.rbInside.isChecked():
            self.current_profile.inside = True
        else:
            self.current_profile.inside = False
        self.data_update()


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

# Clearance Calculation Functions

    def calculate_clearances(self):
        clearances = []
        envelope_polygon = Polygon(self.adjusted_envelope)
        envelope_geo = geopandas.GeoSeries(envelope_polygon)

        for point in self.current_profile.SP:
            this_distance = None
            this_violation = None
            this_point = Point(point[0], point[1])
            # Within Envelope Check
            this_violation = envelope_polygon.contains(this_point)
            # X Clearance
            if not this_violation:
                point_geo = geopandas.GeoSeries(this_point)
                this_distance = envelope_geo.boundary.distance(point_geo)
            else:
                this_distance = 0.00
            clearances.append([this_violation, this_distance])
        return clearances

    def scanpoint_is_violation(self, scan_point):
        envelope_polygon = Polygon(self.adjusted_envelope)
        envelope_geo = geopandas.GeoSeries(envelope_polygon)
        this_point = Point(scan_point[0], scan_point[1])
        return envelope_polygon.contains(this_point)

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
        # Update Scan Visualizer
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
        # Clear Data Table
        headers = ["Parameter", "Value"]
        params = ["ID", "LINE", "TRACK", "STATIONING", "LEA", "REA", "BR", "CE", "EE", "SEA", "SEO", "SP", "SP Violation", "Min Clearance"]
        self.lstScanData.clearSpans()
        # Get New Data
        this_id = self.current_profile.ID
        this_line = self.current_profile.line
        this_track = self.current_profile.track
        this_stationing = self.current_profile.stationing
        this_lea = self.current_profile.LEA
        this_rea = self.current_profile.REA
        this_br, this_ce, this_ee = None, None, None
        these_clearances = self.calculate_clearances()
        min_clearance = 99999.99
        this_violation = False
        for clearance in these_clearances:
            if clearance[0]:
                this_violation = True
                min_clearance = 0.00
            else:
                if clearance[1] < min_clearance:
                    min_clearance = clearance[1]
        if min_clearance == 99999.99:
            min_clearance = 0.00
        if self.current_profile.brAvailable():
            inside = self.rbInside.isChecked()
            this_br = self.current_profile.bendRadius()
            this_ce = self.current_profile.centerExcess()
            this_ee = self.current_profile.endExcess()
        this_sea = self.current_profile.SEA
        this_seo = self.current_profile.SEO
        this_sp = len(self.current_profile.SP)
        values = [this_id, this_line, this_track, this_stationing, this_lea, this_rea, this_br, this_ce, this_ee, this_sea, this_seo, this_sp, this_violation, min_clearance]
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

# Export Functions

    def export_report(self):
        # Exports data as "Clearance Verification Report" PDF
        data_dict = fillpdfs.get_form_fields('Resources/cvs_report_template.pdf')
        print(data_dict)
        # Assign data to dictionary for filling
        violation_flag = False
        min_clearance = 9999.99
        for p in self.calculate_clearances():
            if p[0]:
                violation_flag = True
            if p[1] < min_clearance:
                min_clearance = p[1]
        if min_clearance == 9999.99:
            min_clearance = "N/a"
        # Retrieve Visualized JPG
        filename = 'cvs_visual_export_' + str(time.time()) + '.jpg'
        exporter = pg.exporters.ImageExporter(self.plotter)
        exporter.export(f'Temp/{filename}]')
        # Compile Data for Report
        data_dict = {
            'frmLine': self.current_profile.line,
            'frmTrack': self.current_profile.track,
            'frmStationing': self.current_profile.stationing,
            'frmEquipment': self.current_profile.equipment,
            'frmResolution': f"{len(self.current_profile.SP)} Points",
            'frmDate': self.current_profile.date,
            'frmInside': self.current_profile.inside,
            'frmSuper': f"{self.current_profile.SEA} deg.",
            'frmRadius': f"{self.current_profile.bendRadius()} ft.",
            'frmCenter': f"{self.current_profile.centerExcess()} in.",
            'frmEnd': f"{self.current_profile.endExcess()} in.",
            'frmClearance': f"{min_clearance} in."
        }
        print(data_dict)
        # Save and Flatten PDF
        new_file_name = f"CVS Report-{self.current_profile.line}-{self.current_profile.track}-" \
                        f"{self.current_profile.date}.pdf"
        file, check = QFileDialog.getSaveFileName(None, "Save Report As..", "", "PDF Files (*.pdf);;All Files (*)")
        if ".pdf" not in file:
            file += '.pdf'
        fillpdfs.write_fillable_pdf(r"Resources/cvs_report_template.pdf", file, data_dict, flatten=True)
        fillpdfs.flatten_pdf(file, file)
        # Clean up temp files
        os.remove(f'Temp/{filename}')
        print("Export of Clearance Report completed.\n")

    def export_data(self):
        # !!!!! Need to Test !!!!! #
        # Exports data as a table of relevant clearance information as CSV
        file, check = QFileDialog.getSaveFileName(None, "Save Data Table As..", "", "CSV Files (*.csv);;All Files (*)")
        violations = False
        min_clearance = 9999.99
        for p in self.calculate_clearances():
            if p[0]:
                violations = True
            if p[1] < min_clearance:
                min_clearance = p[1]
        with open(f"{file}.csv", newline='') as export_file:
            writer = csv.writer(export_file, delimiter=',')
            export_data = [["Line/Location:", self.current_profile.line],
                           ["Track:", self.current_profile.track],
                           ["Stationing:", self.current_profile.stationing],
                           ["Equipment:", self.current_profile.equipment],
                           ["Capture Date::", self.current_profile.get_timestamp()],
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
                writer.writerow(line)
        print("Export of Clearance Data completed.\n")

    def export_scan(self):
        # !!!!! Need to Test !!!!! #
        # Exports visualized scan as JPG
        filename, check = QFileDialog.getSaveFileName(None, "Save Scan Export As..", "", "JPG Files (*.jpg);;"
                                                                                         "All Files (*)")
        if ".jpg" not in filename:
            filename += ".jpg"
        exporter = pg.exporters.ImageExporter(self.plotter)
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

##### Testing Functions #####

