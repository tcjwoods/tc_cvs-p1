"""
    /classes/locationProfile.py
"""

# Profile Class
import math
import sys

import shapely.geometry.polygon

DEG_TO_RAD = (math.pi / 180.00)
RAD_TO_DEG = (180.00 / math.pi)

class LocationProfile:

    def __init__(self, profile_identifiers):

        # Populate Identifiers from Passed Parameters
        self.line = profile_identifiers[0]
        self.track = profile_identifiers[1]
        self.stationing = profile_identifiers[2]
        self.date = float(profile_identifiers[3])
        self.type = int(profile_identifiers[4])          # 1 = Verification, 2 = Installation
        self.equipment = None
        self.operator = None

        # Change Tracking
        self.changes_made = False

        # Instance Variables
        self.left_encoder = None                    # Float
        self.right_encoder = None                   # Float
        self.super_elevation = None                 # Float
        self.bend_radius = None                     # [ BR1, BR2]
        self.excess = None                          # [ [CE1, EE1], [CE2, EE2] ]
        self.horizontal_excess = None               # Float
        self.vertical_excess = None                 # Float
        self.location_of_interest = None            # 1 = Inside, 2 = Outside
        self.orientation_direction = None           # 1 = North, 2 = South
        self.division = None                        # 1 = Division A, 2 = Division B
        self.scan_points = []                       # [ [X,Y], .. ]
        self.images = [None, None]                  # [ IM_Left, IM_Right ]

        # Envelope Storage
        self.base_envelope = []                     # [ [ID, X, Y, DIV], ... ]
        self.active_envelope = []                   # [ [X, Y], ... ]

    def update_base_envelope(self, values):
        # Scrape coordinates from passed list
        for value in values:
            envelope_point = value # [ID, X, Y, DIV]
            self.base_envelope.append(envelope_point)
        # Update Active Envelope
        self.adjust_envelope()

    def update_super_elevation(self, value):
        # Set value of instance variable
        self.super_elevation = value
        # Adjust base envelope
        self.adjust_envelope()
        self.changes_made = True

    def update_left_encoder(self, value):
        # Set value of instance variable
        self.left_encoder = value
        # Determine bend radius
        self.calculate_bend_radius()
        # Adjust base envelope
        self.adjust_envelope()
        self.changes_made = True

    def update_right_encoder(self, value):
        # Set value of instance variable
        self.right_encoder = value
        # Determine bend radius
        self.calculate_bend_radius()
        # Adjust base envelope
        self.adjust_envelope()
        self.changes_made = True

    def append_scan_point(self, value):
        # Scrape values from passed list
        X = value[0]
        Y = value[1]
        # Append to List
        self.scan_points.append([X, Y])
        self.changes_made = True

    def update_image(self, image_data, side):
        if side == 'i':
            self.images[0] = image_data
        elif side == 'o':
            self.images[1] = image_data
        self.changes_made = True

    def calculate_bend_radius(self):
        # Ensure both angles are captured
        if self.left_encoder is None or self.right_encoder is None:
            return

        # Catch Straight Track Edge Case
        if self.left_encoder == 180.0 and self.right_encoder == 0.0:
            self.bend_radius = [math.inf, math.inf]
            self.excess = [[0.0, 0.0], [0.0, 0.0]]    # [Center, End]
            return

        # Determine which calculation to use
        if self.location_of_interest == 1:
            # Inside of Curve Calculations
            lx = 25 * 12 * math.cos(self.left_encoder * DEG_TO_RAD)
            ly = 25 * 12 * math.sin(self.left_encoder * DEG_TO_RAD)
            rx = 25 * 12 * math.cos(self.right_encoder * DEG_TO_RAD)
            ry = 25 * 12 * math.sin(self.right_encoder * DEG_TO_RAD)

            # Determine Slopes
            l_slope = (ly / lx)
            r_slope = (ry / rx)

            l_slope_perp = -1 / l_slope
            r_slope_perp = -1 / r_slope

            # Find center x coordinate
            cx = ((l_slope * r_slope) * (ly - ry) + r_slope * lx - l_slope * rx) / (2 * (r_slope - l_slope))

            # Find center y coordinate
            cy = l_slope_perp * (cx - (lx / 2)) + (ly / 2)

            # Determine Bend Radius
            bend_radius = math.sqrt(cx ** 2 + cy ** 2)
            self.bend_radius = [bend_radius, None]

        elif self.location_of_interest == 2:
            # Outside of Curve Calculations
            lx = 50 * 12 * math.cos(self.left_encoder * DEG_TO_RAD)
            ly = 50 * 12 * math.sin(self.left_encoder * DEG_TO_RAD)
            rx = 50 * 12 * math.cos(self.right_encoder * DEG_TO_RAD)
            ry = 50 * 12 * math.sin(self.right_encoder * DEG_TO_RAD)

            # Left Radius
            l_slope = (ly / lx)
            l_slope_perp = -1 / l_slope
            lcy = l_slope_perp * (0 - (lx / 2)) + (ly / 2)
            lcx = 0
            lbr = math.sqrt(lcx ** 2 + lcy ** 2) / 12.0

            # Right Radius
            r_slope = (ry / rx)
            r_slope_perp = -1 / r_slope
            rcy = r_slope_perp * (0 - (rx / 2)) + (ry / 2)
            rcx = 0
            rbr = math.sqrt(rcx ** 2 + rcy ** 2) / 12.0
            self.bend_radius = [lbr, rbr]

        else:
            return

        # Update the excesses
        self.calculate_excess()

    def calculate_excess(self):
        # Check if BR and division were declared
        if self.bend_radius is None or self.division is None:
            return

        # Check which excess calculations to use
        if self.location_of_interest == 1:
            # Inside of Curve, 1 BR to work with @ [0]
            if self.division == 1:
                center_excess = 1944 / self.bend_radius[0]
                end_excess = 1512 / self.bend_radius[0]
                self.excess = [[center_excess, end_excess], []]
            elif self.division == 2:
                center_excess = 4374 / self.bend_radius[0]
                end_excess = 2945 / self.bend_radius[0]
                self.excess = [[center_excess, end_excess], []]
        elif self.location_of_interest == 2:
            # Outside of Curve, 2 BR to work with @ [0 - LBR] and [1 - RBR]
            if self.division == 1:
                left_center_excess = 1944 / self.bend_radius[0]
                left_end_excess = 1512 / self.bend_radius[0]
                right_center_excess = 1944 / self.bend_radius[1]
                right_end_excess = 1512 / self.bend_radius[1]
                self.excess = [[left_center_excess, left_end_excess], [right_center_excess, right_end_excess]]
            elif self.division == 2:
                left_center_excess = 4374 / self.bend_radius[0]
                left_end_excess = 2945 / self.bend_radius[0]
                right_center_excess = 4374 / self.bend_radius[1]
                right_end_excess = 4374 / self.bend_radius[1]
                self.excess = [[left_center_excess, left_end_excess], [right_center_excess, right_end_excess]]
        self.adjust_envelope()

    def adjust_envelope(self):
        self.active_envelope.clear()
        # Determine variation due to track parameters
        excess = 0.00
        super_elevation = 0.00
        if self.excess is not None:
            if self.location_of_interest == 1:
                excess = -self.excess[0][0]
            elif self.location_of_interest == 2:
                excess = max(self.excess[0][1], self.excess[1][1])
        if self.super_elevation is not None:
            super_elevation = self.super_elevation
        # Scrape correct division's envelope
        desired_division = None
        if self.division == 1:
            desired_division = "A Division"
        elif self.division == 2:
            desired_division = "B Division"
        for point in self.base_envelope:    # [ID, X, Y, DIV]
            # Check for appropriate division
            if point[3] == desired_division:
                x = float(point[1])
                y = float(point[2])
                vector_radius = math.sqrt(x**2 + y**2)
                vector_angle = (math.atan2(y, x) * RAD_TO_DEG) - super_elevation
                adjusted_x = vector_radius * math.cos(vector_angle * DEG_TO_RAD) + excess
                adjusted_y = vector_radius * math.sin(vector_angle * DEG_TO_RAD)
                self.active_envelope.append([adjusted_x, adjusted_y])

    def upload_data(self, parameter_list):
        self.date = parameter_list[1]
        self.type = parameter_list[2]
        self.line = parameter_list[3]
        self.track = parameter_list[4]
        self.stationing = parameter_list[5]
        self.location_of_interest = parameter_list[6]
        self.division = parameter_list[7]
        self.left_encoder = parameter_list[8]
        self.right_encoder = parameter_list[9]
        self.super_elevation = parameter_list[13]
        if not parameter_list[14] is None:
            scanned_points = str(parameter_list[14]).split(",")
            for p in scanned_points:
                coordinates = p.split("|")
                x = float(coordinates[0])
                y = float(coordinates[1])
                self.scan_points.append([x, y])
        self.images = [parameter_list[15], parameter_list[16]]
        if self.images[0] is not None:
            inside_image = open('temp/temp_image_inside.png', 'wb')
            inside_image.write(self.images[0])
            inside_image.close()
        if self.images[1] is not None:
            outside_image = open('temp/temp_image_outside.png', 'wb')
            outside_image.write(self.images[1])
            outside_image.close()
        self.calculate_bend_radius()

    def calculate_clearances(self):
        # Create Polygon for Adjusted Envelope
        polygon_coordinates = []
        for point in self.active_envelope:
            polygon_coordinates.append((point[0], point[1]))
        envelope_polygon = shapely.geometry.Polygon(polygon_coordinates)
        # Cycle Scan Points
        min_horizontal_clearance = sys.float_info.max
        min_vertical_clearance = sys.float_info.max
        clearances = []  # [ [horizontal, vertical, violation], ... ]
        for scan_point in self.scan_points:
            h_intersects = None
            v_intersects = None
            # Define a point for scan point
            sp_x = scan_point[0]
            sp_y = scan_point[1]
            sp_point = shapely.geometry.Point((sp_x, sp_y))
            # Define Clearance Lines
            h_line_coords = [(sp_x, sp_y), (0, sp_y)]
            v_line_coords = [(sp_x, sp_y), (sp_x, -25)]
            h_line = shapely.geometry.LineString(h_line_coords)
            v_line = shapely.geometry.LineString(v_line_coords)
            # Determine Intersection Points
            h_intersects = envelope_polygon.boundary.intersection(h_line)
            if not isinstance(h_intersects, shapely.geometry.multipoint.MultiPoint):
                h_intersects = list(h_intersects.coords)
            else:
                h_intersects = []
            v_intersects = envelope_polygon.boundary.intersection(v_line)
            if not isinstance(v_intersects, shapely.geometry.multipoint.MultiPoint):
                v_intersects = list(v_intersects.coords)
            else:
                v_intersects = []
            # Determine if violation
            violation = envelope_polygon.contains(sp_point)
            # Catch Violation Cases
            if violation:
                h_clearance = 0.0
                v_clearance = 0.0
            else:
                # Catch Regular Cases
                if (not h_intersects == []) and (not v_intersects == []):
                    h_clearance = abs(sp_x-h_intersects[0][0])
                    v_clearance = min(abs(sp_y - v_intersects[0][1]), abs(sp_y - v_intersects[1][1]))
                else:
                    # Catch Horiz Clear Case
                    if not h_intersects and not v_intersects:
                        h_clearance = math.inf
                        v_clearance = math.inf
                    elif not v_intersects:
                        h_clearance = abs(sp_x - h_intersects[0][0])
                        v_clearance = math.inf
                    elif not h_intersects:
                        h_clearance = math.inf
                        v_clearance = min(abs(sp_y - v_intersects[0][1]), abs(sp_y - v_intersects[1][1]))
                    else:
                        h_clearance = 0
                        v_clearance = 0
            clearances.append([h_clearance, v_clearance, violation, sp_x, sp_y])
        return clearances

    def generate_scan_string(self):
        scan_string = ""
        for scan_point in self.scan_points:
            x = scan_point[0]
            y = scan_point[1]
            if len(scan_string) > 1:
                scan_string = scan_string + f", {x}|{y}"
            else:
                scan_string = f"{x}|{y}"
        return scan_string

    def generate_save_query(self, exists):
        # Determine if update or insert query
        if exists:
            # Update Record
            parameters = (self.type,
                          self.line,
                          self.track,
                          self.stationing,
                          self.location_of_interest,
                          self.division,
                          self.left_encoder,
                          self.right_encoder,
                          None,
                          None,
                          None,
                          self.super_elevation,
                          self.generate_scan_string(),
                          self.images[0],
                          self.images[1],
                          self.date)
            query = f"UPDATE profiles SET TYPE=?, LINE=?, TRACK=?, STATIONING=?, INSIDE=?, A_DIVISION=?, LEA=?, REA=?" \
                    f", BR=?, CE=?, EE=?, SEA=?, SP=?, IM_INSIDE=?, IM_OUTSIDE=? WHERE DATE=?;"
        else:
            # Insert Record
            parameters = (self.date,
                          self.type,
                          self.line,
                          self.track,
                          self.stationing,
                          self.location_of_interest,
                          self.division,
                          self.left_encoder,
                          self.right_encoder,
                          None,
                          None,
                          None,
                          self.super_elevation,
                          self.generate_scan_string(),
                          self.images[0],
                          self.images[1])
            query = f"INSERT INTO profiles (DATE, TYPE, LINE, TRACK, STATIONING, INSIDE, A_DIVISION, LEA, REA, BR, " \
                    f"CE, EE, SEA, SP, IM_INSIDE, IM_OUTSIDE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
        return [query, parameters]
