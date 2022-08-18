"""

"""

# Python Packages
import base64
import csv
import os
import sqlite3
import subprocess
import sys
import time
import cv2
import fillpdf.fillpdfs
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import *
import pyqtgraph as pg
import pyqtgraph.exporters
# Custom Classes
from PyQt5.QtGui import QCloseEvent

from locationProfile import LocationProfile
from mqtt import mqttClient as mqtt

verification_interface_file = r'interface/verification.ui'

# Clearance Verification Class

class Verification(QtWidgets.QMainWindow):

    def __init__(self, optional_parameters):
        super(Verification, self).__init__()
        QtWidgets.QWidget.__init__(self)
        uic.loadUi(verification_interface_file, self, None, None)

        # Connect Controls to Functions
        self.btnSuperElevation.clicked.connect(self.super_elevation)
        self.btnBendRadius.clicked.connect(self.bend_radius)
        self.btnScan.clicked.connect(self.scan)
        self.btnNewProfile.clicked.connect(self.new_profile)
        self.btnSaveProfile.clicked.connect(self.save_profile)
        self.btnImage.clicked.connect(self.capture_images)
        self.actNew.triggered.connect(self.new_profile)
        self.actSave.triggered.connect(self.save_profile)
        self.actReport.triggered.connect(self.generate_clearance_report)
        self.actExit.triggered.connect(sys.exit)

        # Initialize Visualizer
        self.visualizer = pg.PlotWidget()
        self.imv = pg.ImageView()
        self.visualizer.showGrid(x=True, y=True)
        self.visualizer.setXRange(-200, 200)
        self.visualizer.setYRange(-50, 250)
        self.visualizer.showAxis('bottom')
        self.visualizer.showAxis('left')
        # Plot Item for Train Envelope
        self.plot_envelope = pg.PlotCurveItem(size=7, pen=pg.mkPen(0, 255, 0, 120), connected=True, symbol='o')  # Green
        self.visualizer.addItem(self.plot_envelope)
        # Plot Item for Scanned Environment
        self.plot_scan = pg.ScatterPlotItem(size=5, pen=pg.mkPen(255, 255, 255, 120), connected=True,
                                            symbol='o')  # White
        self.visualizer.addItem(self.plot_scan)
        # Plot Item for Scanned Violations
        self.plot_violation = pg.ScatterPlotItem(size=5, pen=pg.mkPen(255, 0, 0, 120), brush='r',
                                                 connected=False, symbol='x', symbolPen='r')  # Red
        self.plot_violation.setBrush('r')
        self.plot_violation.setSymbol('x')
        self.visualizer.addItem(self.plot_violation)
        self.plotter_layout = QtWidgets.QVBoxLayout()
        self.plotter_layout.addWidget(self.visualizer)
        self.frmVisualizer.setLayout(self.plotter_layout)

        self.point_clicked = pg.SignalProxy(self.visualizer.sceneObj.sigMouseClicked, slot=self.get_mouse_coordinates)

        # Parse passed parameters
        passed_parameters = optional_parameters.split(",")  # [Line, Track, Stationing, Date]

        # Load Profiles from Local DB
        self.current_profile = None
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/local.db')
        db_conn = sqlite3.connect(db_path)
        db_cursor = db_conn.cursor()
        db_query = 'select * from profiles'
        db_cursor.execute(db_query)
        data = db_cursor.fetchall()
        for profile in data:
            if passed_parameters[3] in profile:
                self.current_profile = LocationProfile(passed_parameters)
                self.current_profile.upload_data(profile)
        if self.current_profile is None:
            self.current_profile = LocationProfile(passed_parameters)
        # Load Train Envelope
        base_envelope = []
        envelope_file = open('data/envelope.csv')
        reader = csv.reader(envelope_file, delimiter=',')
        line = 0
        for row in reader:
            if not line == 0:
                ID = int(row[0])
                X = float(row[1])
                Y = float(row[2])
                DIV = str(row[3]).strip()
                base_envelope.append(row)
            line += 1
        self.current_profile.update_base_envelope(base_envelope)

        # Connect to MQTT Broker
        try:
            # Check CVS_AP Connection
            wifi = subprocess.check_output(['iwgetid', '-r'])
            data = wifi.decode('utf-8')
            if not "CVS_AP" in data:
                #raise Exception()
                pass
            # Connect to Host
            self.mqtt = mqtt(self)
            self.mqtt.stateChanged.connect(self.mqtt_state_changed)
            self.mqtt.messageSignal.connect(self.mqtt_message_received)
            self.mqtt.hostname = "192.168.42.10"
            self.mqtt.connectToHost()
            self.mqtt.subscribe("/data/LE")     # Left Encoder
            self.mqtt.subscribe("/data/RE")     # Right Encoder
            self.mqtt.subscribe("/data/SE")     # Super Elevation
            self.mqtt.subscribe("/data/SP")     # Scan Points
            self.mqtt.subscribe("/data/LI")     # Inside Image
            self.mqtt.subscribe("/data/RI")     # Outside Image
        except Exception as e:
            # No AP Connection or Failed MQTT Connection
            QtWidgets.QMessageBox.information(self, "CVS_AP Not Detected!", "Connection to the device cannot be "
                                                                            "established. Check that WiFi is connected"
                                                                            "device access point.\nSSID: CVS_AP\n"
                                                                            "Passkey: None")

        # Update display to show data
        self.update_display()

    # Window Action Functions

    def closeEvent(self, QCloseEvent):
        # Check if need to save
        if self.current_profile.changes_made:
            response = QtWidgets.QMessageBox.information(self, "Save Before Exit?", "Changes have been made to current"
                                                                                    " profile. Would you like to save?",
                                                         QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                         QtWidgets.QMessageBox.No)
            if response == QtWidgets.QMessageBox.Yes:
                self.save_profile()
                QtWidgets.QMessageBox.information(self, "Profile Saved!", "Profile has been saved. Close this window to"
                                                                          " exit now!")
            else:
                QtWidgets.QMessageBox.information(self, "Profile Not Saved!", "Profile has not been saved. Close this "
                                                                              "window to exit now!")

    # MQTT Functions

    def mqtt_state_changed(self):
        if self.mqtt.m_state == self.mqtt.Disconnected:
            self.txtMQTTStatus.setStyleSheet('QLabel {color: #FF0000;}')
            self.txtMQTTStatus.setText("Disconnected from Device")
        elif self.mqtt.m_state == self.mqtt.Connecting:
            self.txtMQTTStatus.setStyleSheet('QLabel {color: #FF8000;}')
            self.txtMQTTStatus.setText("Attempting to Connect to Device")
        elif self.mqtt.m_state == self.mqtt.Connected:
            self.txtMQTTStatus.setStyleSheet('QLabel {color: #009900;}')
            self.txtMQTTStatus.setText("Connected to Device")

    def mqtt_message_received(self, message):
        message_topic = message.topic
        if not message_topic == "/data/LI" and not message_topic == "/data/RI":
            message_payload = message.payload.decode('utf-8')
        else:
            message_payload = message.payload
        # Call appropriate function
        if message_topic == "/data/LE":
            self.LEA(message_payload)
        elif message_topic == "/data/RE":
            self.REA(message_payload)
        elif message_topic == "/data/SE":
            self.SE(message_payload)
        elif message_topic == "/data/SP":
            self.SP(message_payload)
        elif message_topic == "/data/LI":
            self.IM(message_payload, 1)  # Inside Image
        elif message_topic == "/data/RI":
            self.IM(message_payload, 2)  # Outside Image

    # Control Functions

    def capture_images(self):
        # Verify MQTT Connection -
        self.mqtt.publish("/command", "ETCI")

    def super_elevation(self):
        # Verify MQTT Connection
        if self.mqtt.m_state == self.mqtt.Connected:
            response = QtWidgets.QMessageBox.information(self,
                                                         "Check Proper Orientation",
                                                         "Please ensure that the device is in the proper orientation."
                                                         " The BR Mechanism should be on the rail that is on the "
                                                         "outside of the curve.",
                                                         QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                                                         QtWidgets.QMessageBox.Cancel)
            if response == QtWidgets.QMessageBox.Ok:
                # Send command
                self.mqtt.publish("/command", "ERSE")
            else:
                QtWidgets.QMessageBox.information(self, "Task Aborted",
                                                  "Task has been aborted, RE value not collected.")
        else:
            # Alert to disconnect
            QtWidgets.QMessageBox.information(self, "Connection Error", "You are not connected to the device, so the "
                                                                        "command cannot be sent. Please check device "
                                                                        "connection.")
        # Wait for response and update data display
        time.sleep(1)
        #self.update_display()

    def bend_radius(self):
        # Verify MQTT Connection
        if self.mqtt.m_state == self.mqtt.Connected:
            # Connected, so allow function to continue
            pass
        else:
            # Alert to disconnect
            QtWidgets.QMessageBox.information(self, "Connection Error", "You are not connected to the device, so the "
                                                                        "command cannot be sent. Please check device "
                                                                        "connection.")
            return
        # Proper Orientation of Device Pop-Up
        response = QtWidgets.QMessageBox.information(self,
                                                     "Check Proper Orientation",
                                                     "Please ensure that the device is in the proper orientation."
                                                     " The BR Mechanism should be on the rail that is on the "
                                                     "outside of the curve.",
                                                     QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                                                     QtWidgets.QMessageBox.Cancel)
        if response == QtWidgets.QMessageBox.Cancel:
            QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, no data collected.")
            return

        # Confirm Orientation Direction
        collection_items = ("North", "South")
        item, result = QtWidgets.QInputDialog.getItem(self, "Orientation of Device",
                                                      "Which direction on the track is the direction indicator facing?",
                                                      collection_items, 0, False)
        if result and item:
            if item == "North":
                self.current_profile.orientation_direction = 1
            elif item == "South":
                self.current_profile.orientation_direction = 2
            else:
                QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, no data collected.")
                return
        else:
            QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, no data collected.")
            return

        # Collect Inside/Outside information
        collection_items = ("Inside of Curve", "Outside of Curve")
        item, result = QtWidgets.QInputDialog.getItem(self, "Location of Interest",
                                                      "Where is the equipment to be verified? ",
                                                      collection_items, 0, False)
        if result and item:
            if item == "Inside of Curve":
                self.current_profile.location_of_interest = 1
            elif item == "Outside of Curve":
                self.current_profile.location_of_interest = 2
            else:
                QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, no data collected.")
                return
        else:
            QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, no data collected.")
            return

        # Collect Division information
        collection_items = ("A Division", "B Division")
        item, result = QtWidgets.QInputDialog.getItem(self, "Train Division",
                                                      "What division should be used for calculations? ",
                                                      collection_items, 0, False)
        if result and item:
            if item == "A Division":
                self.current_profile.division = 1
            elif item == "B Division":
                self.current_profile.division = 2
            else:
                QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, no data collected.")
                return
        else:
            QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, no data collected.")
            return

        # Left Encoder Value
        if self.current_profile.location_of_interest == 1:
            track_shoe_length = "25"
        elif self.current_profile.location_of_interest == 2:
            track_shoe_length = "50"
        response = QtWidgets.QMessageBox.information(self, "Capture LE",
                                          f"Ensure that the {track_shoe_length}' track shoe is attached to the track"
                                          f" to the left of the device. Also ensure that the string is tight with no"
                                          f" sag in the line. Click OK once ready to capture LE value.",
                                          QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                                          QtWidgets.QMessageBox.Ok)
        if response == QtWidgets.QMessageBox.Ok:
            self.mqtt.publish("/command", "ERLE")
            time.sleep(1)
        else:
            QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, LE value not collected.")
            return

        # Right Encoder Value
        response = QtWidgets.QMessageBox.information(self, "Capture RE",
                                          f"Ensure that the {track_shoe_length}' track shoe is attached to the track"
                                          f" to the right of the device. Also ensure that the string is tight with no"
                                          f" sag in the line. Click OK once ready to capture RE value.",
                                          QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                                          QtWidgets.QMessageBox.Ok)
        if response == QtWidgets.QMessageBox.Ok:
            self.mqtt.publish("/command", "ERRE")
            time.sleep(1)
        else:
            QtWidgets.QMessageBox.information(self, "Task Aborted", "Task has been aborted, RE value not collected.")
            return

        # Wait for responses, and update data display
        #self.update_display()

    def scan(self):
        # Verify MQTT Connection
        if self.mqtt.m_state == self.mqtt.Connected:
            # Connected, so dont exit function
            response = QtWidgets.QMessageBox.information(self,
                                                         "Check Proper Orientation",
                                                         "Please ensure that the device is in the proper orientation."
                                                         " The BR Mechanism should be on the rail that is on the "
                                                         "outside of the curve.",
                                                         QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                                                         QtWidgets.QMessageBox.Cancel)
            if response == QtWidgets.QMessageBox.Ok:
                # Toggle Motor On
                self.mqtt.publish("/command", "ETTM:1")
                time.sleep(1)
                # Execute Scan
                self.mqtt.publish("/command", "ETSP")
                QtWidgets.QMessageBox.information(self, "Scan Started", "The scan has been started. Once complete you will"
                                                                        " be notified.")
        else:
            # Alert to disconnect
            QtWidgets.QMessageBox.information(self, "Connection Error", "You are not connected to the device, so the "
                                                                        "command cannot be sent. Please check device "
                                                                        "connection.")
            return



    # Response Functions

    def SE(self, value):
        # Scrape response and cast to float
        received_value = float(value)
        # Perform Necessary Calculations
        calculated_value = received_value
        # Check if leaning away or towards
        if calculated_value > 0:
            lean = 2
        else:
            lean = 1
        loi = self.current_profile.location_of_interest
        if lean == loi:
            lean = "towards"
        elif not lean == loi:
            lean = "away"
        # Assign value to current profile
        self.current_profile.update_super_elevation(calculated_value)
        # Notify User of Values
        QtWidgets.QMessageBox.information(self, "Super Elevation", f"Super Elevation Received!\n"
                                                                   f"SE: {self.current_profile.super_elevation} deg. "
                                                                   f"{lean}.")
        # Update GUI
        self.update_display()

    def LEA(self, value):
        # Scrape value and cast to float
        received_value = float(value)
        # Perform necessary calculations
        calculated_value = received_value
        # Assign value to current profile
        self.current_profile.update_left_encoder(calculated_value)
        # Notify User of Values
        QtWidgets.QMessageBox.information(self, "Left Angle", f"Left Angle Received!\n"
                                                              f"LEA: {self.current_profile.left_encoder} deg.")
        # Update GUI
        self.update_display()

    def REA(self, value):
        # Scrape value and cast to float
        received_value = float(value)
        # Perform necessary calculations
        calculated_value = received_value
        # Assign value to current profile
        self.current_profile.update_right_encoder(calculated_value)
        # Notify User of Values
        QtWidgets.QMessageBox.information(self, "Right Angle", f"Right Angle Received!\n"
                                                              f"REA: {self.current_profile.right_encoder} deg.")
        # Update GUI
        self.update_display()

    def SP(self, value):
        # Catch "Scan Complete" Flag
        if value == "SP:1":
            self.update_display()
            QtWidgets.QMessageBox.information(self, "Scan Completed", f"The scan has been completed. "
                                                                      f"{len(self.current_profile.scan_points)} scan"
                                                                      f" points were collected.")
            #self.mqtt.publish("/command", "ETCI:0")  # Inside Camera
            #time.sleep(1)
            #self.mqtt.publish("/command", "ETCI:1")  # Outside Camera
            self.update_display()
            return
        # Scrape value and cast to coordinates to floats
        x = float(value[1:value.index(",")])
        y = float(value[value.index(",")+1:-1])
        # Check if in deadzone
        if (x < 60 and x > -60 and y > 0 and y < 10):
            return  #  - Make sure this works and catches below device deadzone
        # Append point to sp list of current profile
        self.current_profile.append_scan_point([x, y])
        # Check if 5*n th value, and update display
        if len(self.current_profile.scan_points) % 5 == 0:
            self.update_display()

    def IM(self, image_data, location):
        if location == 1:   # Inside Image
            image_file = open(r'temp/temp_image_inside.png', 'wb')
            image_file.write(image_data)
            self.current_profile.update_image(image_data, 'i')
            image_file.close()
        elif location == 2: # Outside Image
            image_file = open(r'temp/temp_image_outside.png', 'wb')
            image_file.write(image_data)
            self.current_profile.update_image(image_data, 'o')
            image_file.close()

    # Profile Management Functions

    def new_profile(self):
        # Ask to save if changes were made
        if self.current_profile.changes_made:
            response = QtWidgets.QMessageBox.information(self, "Save Changes?", "Changes were made to this location"
                                                                                " profile. Would you like to save "
                                                                                "these changes?",
                                                         QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                         QtWidgets.QMessageBox.Yes)
            if response == QtWidgets.QMessageBox.Yes:
                self.save_profile()
                QtWidgets.QMessageBox.information(self, "Changes Saved", "All changes were successfully saved!")


    def save_profile(self):
        # Check if profile exists in database
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), r'data/local.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = f"select * from profiles where DATE={self.current_profile.date};"
        cursor.execute(query)
        results = cursor.fetchall()
        if results:
            query = self.current_profile.generate_save_query(True)
        else:
            query = self.current_profile.generate_save_query(False)
        cursor.execute(query[0], query[1])
        conn.commit()
        conn.close()

    def get_profile_information(self):
        # Used to collect data about a new profile to be created
        input_dialog = QtWidgets.QInputDialog
        this_line = None
        this_track = None
        this_stationing = None
        this_date = None
        this_type = None

        this_line = input_dialog.getText(self, f'Line/Location', "Enter Line/Location of New Profile:")
        this_track = input_dialog.getText(self, f"Track", "Enter Track of New Profile (## or N/a):")
        this_stationing = input_dialog.getText(self, f"Stationing", "Enter Stationing of New Profile (####+## or N/a):")
        this_date = time.strftime("")

        return [this_line, this_track, this_stationing, ]

    # Interface Management Functions

    def update_display(self):
        # Update Envelope
        self.plot_envelope.clear()
        envelope_x = []
        envelope_y = []
        for point in self.current_profile.active_envelope:
            envelope_x.append(point[0])
            envelope_y.append(point[1])
        self.plot_envelope.setData(x=envelope_x, y=envelope_y)

        # Display Equipment Side
        if self.current_profile.location_of_interest == 2:
            self.txtEquipmentInside.setDisabled(True)
            self.txtEquipmentOutside.setDisabled(False)
        elif self.current_profile.location_of_interest == 1:
            self.txtEquipmentInside.setDisabled(False)
            self.txtEquipmentOutside.setDisabled(True)

        # Update Scan
        self.plot_scan.clear()
        scan_x = []
        scan_y = []
        for point in self.current_profile.scan_points:
            scan_x.append(point[0])
            scan_y.append(point[1])
        self.plot_scan.setData(x=scan_x, y=scan_y)

        # Update Violations
        self.plot_violation.clear()
        violation_x = []
        violation_y = []
        clearances = self.current_profile.calculate_clearances()
        min_horizontal_clearance = sys.float_info.max
        min_vertical_clearance = sys.float_info.max
        for point in clearances:
            if True in point:
                violation_x.append(point[3])
                violation_y.append(point[4])
            if min_horizontal_clearance > point[0]:
                min_horizontal_clearance = point[0]
            if min_vertical_clearance > point[1]:
                min_vertical_clearance = point[1]
        if min_horizontal_clearance == sys.float_info.max:
            min_horizontal_clearance = "N/a"
        if min_vertical_clearance == sys.float_info.max:
            min_vertical_clearance = "N/a"
        self.plot_violation.setData(x=violation_x, y=violation_y)
        self.txtHorizontalClearance.setText(str(min_horizontal_clearance))
        self.txtVerticalClearance.setText(str(min_vertical_clearance))

        # Update Super Elevation
        if self.current_profile.super_elevation is None:
            self.txtSuperElevation.setText(f"Not Collected")
        else:
            if self.current_profile.super_elevation > 0:
                lean = 2
            else:
                lean = 1
            loi = self.current_profile.location_of_interest
            if lean == loi:
                lean = "towards"
            elif not lean == loi:
                lean = "away"
            if self.current_profile.super_elevation is None:
                self.txtSuperElevation.setText(f"Not Collected")
            else:
                self.txtSuperElevation.setText(f"{abs(self.current_profile.super_elevation):.2f} deg. {lean}")

        # Update Bend Radius(s)
        if self.current_profile.bend_radius is None:
            self.txtBendRadius.setText(f"Not Collected")
        else:
            if self.current_profile.location_of_interest == 2:
                self.txtBendRadius.setText(f"L: {self.current_profile.bend_radius[0]:.2f}' | R: {self.current_profile.bend_radius[1]:.2f}'")
            elif self.current_profile.location_of_interest == 1:
                self.txtBendRadius.setText(f"{self.current_profile.bend_radius[0]:.2f}'")

        # Update Excess(s)
        if self.current_profile.excess is None:
            self.txtExcess.setText(f"Not Collected")
        else:
            if self.current_profile.location_of_interest == 2:
                # Outside of Curve
                self.txtExcess.setText(f'L: {self.current_profile.excess[0][1]:.2f}" | R: {self.current_profile.excess[1][1]:.2f}" (EE)')
            elif self.current_profile.location_of_interest == 1:
                # Inside of Curve
                self.txtExcess.setText(f'{self.current_profile.excess[0][0]:.2f}" (CE)')

    # Report Related Functions

    def generate_clearance_report(self):
        # Retreive template and data fields
        template_file = r'data/report.pdf'
        report_dict = fillpdf.fillpdfs.get_form_fields(template_file)

        # Retreive Images
        image_plot = f'temp/temp_image_plot_{str(time.time())}.jpg'
        plot_exporter = pg.exporters.ImageExporter(self.visualizer.sceneObj)
        plot_exporter.export(image_plot)
        image_inside = open(r'temp/temp_image_inside.png')
        image_outside = open(r'temp/temp_image_outside.png')

        # Retreive Data
        location = None
        excess = None
        if self.current_profile.location_of_interest == 1:
            location = "Inside of Curve"
            center_excess = f"{self.current_profile.excess[0][0]:.2f} in. (CE)"
            end_excess = f"{self.current_profile.excess[0][1]:.2f} in. (EE)"
            bend_radius = self.current_profile.bend_radius[0]
        elif self.current_profile.location_of_interest == 2:
            location = "Outside of Curve"
            center_excess = f"{min(self.current_profile.excess[0][0], self.current_profile.excess[1][0]):.2f} in."
            end_excess = f"{max(self.current_profile.excess[0][1], self.current_profile.excess[1][1]):.2f} in."
            bend_radius = min(self.current_profile.bend_radius[0], self.current_profile.bend_radius[1])
        min_h = 999999.99
        min_v = 999999.99
        for p in self.current_profile.calculate_clearances():
            if p[2]:
                min_h = 0.00
                min_v = 0.00
                break
            else:
                if min_h > p[0]:
                    min_h = p[0]
                if min_v > p[1]:
                    min_v = p[1]
        report_dict = {
            'frmLine': self.current_profile.line,
            'frmTrack': self.current_profile.track,
            'frmStationing': self.current_profile.stationing,
            'frmEquipment': self.current_profile.equipment,
            'frmDate': time.strftime('%m/%d/%Y %H:%M', time.localtime(int(float(self.current_profile.date)))),
            'frmPerformed': "",  #  Add this field to creation of scan
            'frmInside': location,
            'frmSuper': f"{self.current_profile.super_elevation:.2f} deg.",
            'frmBend': f"{bend_radius:.0f} ft.",
            'frmCenter': center_excess,
            'frmEnd': end_excess,
            'frmClearance': f"Horiz:{min_h:.1f}, Vert:{min_v} in."
        }

        # Generate PDF
        out_path, check = QtWidgets.QFileDialog.getSaveFileName(None, "Save Report As..", "",
                                                                "PDF Files (*.pdf);;All Files (*)")
        if ".pdf" not in out_path:
            out_path += '.pdf'
        temp_file_a = out_path[0:-4] + "_temp_a.pdf"
        temp_file_b = out_path[0:-4] + "_temp_b.pdf"
        temp_file_c = out_path[0:-4] + "_temp_c.pdf"
        fillpdf.fillpdfs.write_fillable_pdf(template_file, temp_file_a, report_dict, flatten=False)
        fillpdf.fillpdfs.place_image(image_plot, 93, 250, temp_file_a, temp_file_b, 1, width=400, height=190)    # Plot
        fillpdf.fillpdfs.place_image(image_inside, 110, 450, temp_file_b, temp_file_c, 1, width=200, height=120)  # In
        fillpdf.fillpdfs.place_image(image_outside, 285, 450, temp_file_c, out_path, 1, width=200, height=120) # Out

        # Clean Up Temp Files
        try:
            os.remove(f"{os.getcwd()}/{image_plot}")
            os.remove(temp_file_a)
            os.remove(temp_file_b)
            os.remove(temp_file_c)
            image_inside.close()
            image_outside.close()
        except:
            pass
        print("Export Completed.")
        QtWidgets.QMessageBox.information(self, "Export Complete!", f"Export of the Clearance Report is complete.\n"
                                                                    f"File: {out_path}")

    # !!TESTING!!
    def get_mouse_coordinates(self, event):
        # Get Coordinates of Clicked Point
        coordinates = event[0]
        point = coordinates.pos()
        x = point.x()
        y = point.y()

        # Find SP of Clicked Point
        clearances = self.current_profile.calculate_clearances()
        min_x = 999999.9
        min_y = 999999.9
        current_x = None
        current_y = None
        for point in clearances:
            delta_x = abs(point[3] - x)
            delta_y = abs(point[4] - y)
            if delta_x < min_x and delta_y < min_y:
                min_x = delta_x
                min_y = delta_y
                current_x = point[3]
                current_y = point[4]
        for point in clearances:
            if point[3] == current_x and point[4] == current_y:
                h_clearance = point[0]
                v_clearance = point[1]
                violation = point[2]
                if violation:
                    QtWidgets.QMessageBox.information(self,
                                                      "Point Clearance",
                                                      f"This point is within the envelope."
                                                      f" There is {h_clearance} in. of horizontal clearance and "
                                                      f"{v_clearance} in. of vertical clearance.")
                    return
                else:
                    QtWidgets.QMessageBox.information(self,
                                                      "Point Clearance",
                                                      f"This point has {h_clearance} in. of horizontal clearance and "
                                                      f"{v_clearance} in. of vertical clearance.")
                    return
