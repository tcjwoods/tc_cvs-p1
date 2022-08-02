class Envelope:

    # Class Variables

    def __init__(self):
        # Instance Variables
        self.points = []
        self.division = None

    # Class Functions

    def append_coordinate(self, x, y, div):
        self.points.append([x, y, div])

    def upload_coordinates(self, points):
        for p in points:
            self.points.append(p)
