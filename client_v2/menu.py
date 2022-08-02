

# Menu Class
import os
import sqlite3
import time
from datetime import datetime

from PyQt5 import QtWidgets, QtCore, uic
from locationProfile import LocationProfile
from tableModel import MyTableModel

menu_interface_file = '/menu.ui'


class Menu(QtWidgets.QMainWindow):
    switch_verification = QtCore.pyqtSignal(str)
    switch_installation = QtCore.pyqtSignal(str)

    def __init__(self):
        super(Menu, self).__init__()
        QtWidgets.QWidget.__init__(self)
        uic.loadUi(r'interface/menu.ui', self, None, None)

        # Instance Variables
        # N/a

        # Connect Controls to Functions
        self.btnNewClearance.clicked.connect(self.new_clearance_verification)
        self.btnNewMinimum.clicked.connect(self.new_minimum_install)
        self.btnLoadExisting.clicked.connect(self.load_existing_profile)
        self.btnSystemCalibration.clicked.connect(self.system_calibration)
        self.lstExistingProfiles.doubleClicked.connect(self.load_existing_profile)

        # Load Profiles from Local DB
        self.local_profiles = []
        table_data = []
        table_headers = ["Line", "Track", "Stationing", "Date", "Type"]
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data/local.db')
        db_conn = sqlite3.connect(db_path)
        db_cursor = db_conn.cursor()
        db_query = 'select * from profiles'
        db_cursor.execute(db_query)
        data = db_cursor.fetchall()
        for profile in data:
            # Scrape identifying information
            this_type = profile[2]
            this_line = profile[3]
            this_track = profile[4]
            this_stationing = profile[5]
            this_date = profile[1]
            # Create profile object
            this_profile = LocationProfile([this_line, this_track, this_stationing, this_date, this_type])
            self.local_profiles.append(this_profile)
            # Populate data table
            if this_type == 1:
                str_type = "Verification"
            elif this_type == 2:
                str_type = "Installation"
            str_date = time.strftime('%m-%d-%y %H:%M', time.localtime(int(float(this_date))))
            table_data.append([this_profile.line, this_profile.track, this_profile.stationing, str_date,
                               str_type])
        table_model = MyTableModel(self, table_data, table_headers)
        self.lstExistingProfiles.setModel(table_model)

    # Class Functions

    def new_clearance_verification(self):
        # Collects data about new clearance verification profile and launches appropriate window
        profile_parameters = self.get_profile_information(1)       # [Line, Track, Stationing]
        self.switch_verification.emit(profile_parameters)

    def new_minimum_install(self):
        # Collects data about new min. install distance profile and launches appropriate window
        profile_parameters = self.get_profile_information(2)    # [Line, Track, Stationing]
        self.switch_installation.emit("")

    def load_existing_profile(self):
        # Loads data from a pre-existing profile and launches the appropriate window
        selection_index = self.lstExistingProfiles.selectionModel().currentIndex()
        selection_line = selection_index.sibling(selection_index.row(), 0).data()
        selection_track = selection_index.sibling(selection_index.row(), 1).data()
        selection_stationing = selection_index.sibling(selection_index.row(), 2).data()
        selection_date = selection_index.sibling(selection_index.row(), 3).data()
        for profile in self.local_profiles:
            if not profile.line == selection_line:
                continue
            if not profile.track == selection_track:
                continue
            if not profile.stationing == selection_stationing:
                continue
            if not time.strftime('%m-%d-%y %H:%M', time.localtime(int(float(profile.date)))) == selection_date:
                continue
            if profile.type == 1:
                self.switch_verification.emit(f"{profile.line},{profile.track},"
                                              f"{profile.stationing},{profile.date},{profile.type}")
            elif profile.type == 2:
                self.switch_installation.emit(f"{profile.line},{profile.track},"
                                              f"{profile.stationing},{profile.date},{profile.type}")


    def system_calibration(self):
        # Launches the system calibration window
        pass


    def get_profile_information(self, type):
        # Used to collect data about a new profile to be created
        input_dialog = QtWidgets.QInputDialog
        this_line = None
        this_track = None
        this_stationing = None

        this_line, x = input_dialog.getText(self, f'New {type} - Line/Location', "Enter Line/Location of New Profile:")
        # TODO - Check this_line validity
        this_track, x = input_dialog.getText(self, f"New {type} - Track", "Enter Track of New Profile (## or N/a):")
        # TODO - Check this_track validity
        this_stationing, x = input_dialog.getText(self, f"New {type} - Stationing", "Enter Stationing of New Profile "
                                                                                 "(####+## or N/a):")
        # TODO - Check this_stationing validity
        this_date = time.time()
        this_type = type
        return f"{this_line},{this_track},{this_stationing},{str(this_date)},{this_type}"
