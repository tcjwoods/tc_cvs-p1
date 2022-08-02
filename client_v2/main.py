"""
    TODO - Script Introduction
"""

# Python Packages
import sys
from PyQt5 import QtWidgets
from PyQt5 import uic
# Custom Classes
from menu import Menu
from verification import Verification
#from classes.installation import Installation

import shapely

# Find UI Files
menu_interface_file = r'interface/menu.ui'
verification_interface_file = r'interface/verification.ui'
installation_interface_file = r'interface/installation.ui'

# Create Form/Base Objects
#menu_form, menu_base = uic.loadUiType(menu_interface_file)
#check_form, check_base = uic.loadUiType(menu_interface_file)
#minimum_form, minimum_base = uic.loadUiType(menu_interface_file)


# Minimum Distance Class
class Installation(QtWidgets.QMainWindow):

    def __init__(self, optional_parameters):
        super(Installation, self).__init__()
        QtWidgets.QWidget.__init__(self)
        uic.loadUi(installation_interface_file, self, None, None)


# Controller Class
class Controller:
    # Handles switching of the active window shown

    def __init__(self):
        pass

    def show_menu(self):
        self.menu = Menu()
        self.menu.switch_installation.connect(self.show_installation)
        self.menu.switch_verification.connect(self.show_verification)
        self.menu.show()

    def show_verification(self, profile_identifiers):
        self.verification = Verification(profile_identifiers)
        self.menu.close()
        self.verification.show()

    def show_installation(self, profile_identifiers):
        self.installation = Installation(profile_identifiers)
        self.menu.close()
        self.installation.show()

    def show_calibration(self):
        pass


# Main.Py Execution
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    controller = Controller()
    controller.show_menu()
    sys.exit(app.exec_())
