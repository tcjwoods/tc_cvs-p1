"""
Script Intro/Description
"""

""" Imports """


import os, csv, time, math, smbus, board
import signal, spidev, pygame, pygame.camera
import RPi.GPIO as GPIO
import Dependencies.tfmp.tfmplus as tfmP
from pygame.locals import *
import paho.mqtt.client as mqtt


""" Variables and Objects """


# Scan Data
data_LEA = None # Float: Left Encoder Angle
data_REA = None # Float: Right Encoder Angle
data_SEA = None # Float: Super Elevation Angle
data_SP = None  # List(List(Float)): Scan Points
# Tracker Data
track_motor_angle = None
track_motor_resolution = None
# Command Queue
queue_commands = None
# Offset Values
offset_Scan_X = None # Scan X Offset
offset_Scan_Y = None # Scan Y Offset
offset_Scan_D = None # Scan Distance Offset
offset_Scan_T = None # Scan Temp Offset
offset_Gyro_X = None # Gyro X-Axis Offset
offset_Gyro_Y = None # Gyro Y-Axis Offset
offset_Gyro_Z = None # Gyro Z-Axis Offset
offset_Gyro_T = None # Gyro Temp Offset
offset_Encoder_A = None # Encoder Angle Offset
# Encoder Objects
if_spi = None
# Gyro Objects
if_i2c = None
# Scanner Objects
if_serial = None
# Camera Objects
cam_outside = None
cam_inside = None
# MQTT Objects
if_mqtt = None


""" Pin Declarations, Addr/Bus Definition """


# Encoder Definitions
bus_spi = 0
pin_csp = 0
cmd_encoder_nop = 0x00
cmd_encoder_pos = 0x10
cmd_encoder_zer = 0x70
par_encoder_hz = 500000
par_encoder_delay = 3
# Gyro Definitions
addr_gyro = 0x68
pin_gyro_sda = 2
pin_gyro_scl = 3
# Scanner Definitions
pin_motor_m0 = 13
pin_motor_m1 = 6
pin_motor_m2 = 5
pin_motor_step = 23
pin_motor_dir = 24
pin_motor_enable = 12
pin_distance_tx = 14
pin_distance_rx = 18
pin_homing_in = 19
pin_laser_out = 18


""" Initialization """


# Primary Initialization Function
def system_initialize():

    # Greet User
    print("Clearance Verification System\n")
    print("Beginning System Initialization..")

    # Initialize AP
    print("Beginning AP initialization..")
    os.system("sudo systemctl restart isc-dhcp-server.service")
    os.system("sudo systemctl restart hostapd")
    os.system("sudo systemctl restart mosquitto")
    print("AP initialized.")

    # Restart access point
    print("Restarting isc-dhcp-server.service now..")
    #os.system("sudo systemctl restart isc-dhcp-server.service")
    print("Restarting hostapd.service now..")
    #os.system("sudo systemctl restart hostapd")
    print("Restarting mosquitto.service now..")
    #os.system("sudo systemctl restart mosquitto")

    # Initialize GPIO
    print("Beginning GPIO initialization..")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    print("GPIO Initialized.")

    # Initialize Calibration Values
    print("Beginning Calibration initialization..")
    global offset_Scan_X, offset_Scan_Y, offset_Scan_D, offset_Scan_T
    global offset_Gyro_X, offset_Gyro_Y, offset_Gyro_Z, offset_Gyro_T
    global offset_Encoder_A
    offset_values = []
    with open('/home/pi/Desktop/cvs_data_manager/Resources/calibration_values.csv') as file_calibration:
        reader = csv.reader(file_calibration, delimiter=',')
        line = 0
        for row in reader:
            if line != 0:
                param = row[0]
                value = float(row[1])
                offset_values.append(value)
            line += 1
    offset_Scan_X = offset_values[0]
    offset_Scan_Y = offset_values[1]
    offset_Scan_D = offset_values[2]
    offset_Scan_T = offset_values[3]
    offset_Gyro_X = offset_values[4]
    offset_Gyro_Y = offset_values[5]
    offset_Gyro_Z = offset_values[6]
    offset_Gyro_T = offset_values[7]
    offset_Encoder_A = offset_values[8]
    print("Calibration Initialized.")

    # Initialize MQTT Broker
    print("Beginning MQTT Broker initialization..")
    os.system("sudo systemctl restart mosquitto")
    print("MQTT Broker Initialized.")

    # Initialize MQTT Client
    print("Beginning MQTT Client initialization..")
    global if_mqtt
    if_mqtt = mqtt.Client("cvs_device_01")
    if_mqtt.connect("192.168.42.10")
    if_mqtt.subscribe("/command")
    if_mqtt.on_message = on_message
    print("MQTT Client Initialized.")

    # Initialize Gyro
    print("Beginning Gyro initialization..")
    global if_i2c
    if_i2c = smbus.SMBus(1)
    time.sleep(1)
    try:
        if_i2c.write_byte_data(addr_gyro, 0x19, 7)
        if_i2c.write_byte_data(addr_gyro, 0x6B, 1)
        if_i2c.write_byte_data(addr_gyro, 0x1A, 0)
        if_i2c.write_byte_data(addr_gyro, 0x1B, 24)
        if_i2c.write_byte_data(addr_gyro, 0x38, 1)
    except Exception as e:
        print("MPU-6050 initialization failed")
    print("Gyro Initialized.")

    # Initialize Scanner
    print("Beginning Scanner initialization..")
    global if_serial
    if not tfmP.begin("/dev/serial0", 115200):
        print("TF-02 Initialization Failed!")
    GPIO.setup(pin_laser_out, GPIO.OUT)
    GPIO.setup(pin_motor_step, GPIO.OUT)
    GPIO.setup(pin_motor_dir, GPIO.OUT)
    GPIO.setup(pin_motor_enable, GPIO.OUT)
    GPIO.setup(pin_motor_m0, GPIO.OUT)
    GPIO.setup(pin_motor_m1, GPIO.OUT)
    GPIO.setup(pin_motor_m2, GPIO.OUT)
    GPIO.setup(pin_homing_in, GPIO.IN)
    GPIO.output(pin_motor_enable, GPIO.HIGH)
    GPIO.output(pin_motor_m0, GPIO.HIGH)
    GPIO.output(pin_motor_m1, GPIO.HIGH)
    print("Scanner Initialized.")

    # Initialize Encoder
    print("Beginning Encoder initialization..")
    global if_spi
    if_spi = spidev.SpiDev()
    if_spi.open(0, 0)
    print("Encoder Initialized.")

    # Initialize Cameras
    print("Beginning Cameras initialization..")
    global cam_inside, cam_outside
    pygame.init()
    pygame.camera.init()
    cam_list = pygame.camera.list_cameras()
    if cam_list:
        # TODO - Add logic to differentiate cams via MAC Addr
        cam_inside = pygame.camera.Camera(cam_list[0], (1080, 720))
        cam_outside = pygame.camera.Camera(cam_list[1], (1080, 720))
    print("Cameras Initialized.")

    # Initialization Completed
    print("System initialization complete.\n")
    print("Access Point SSID: CVS_AP (No Password)")
    print("Device IP Address: 192.168.42.10\n")


""" MQTT Functions """


# MQTT On Message Callback
def on_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode("utf-8")
    queue_commands.append(payload)


""" Data Collection """


# Encoder Data Capture
def encoder_capture():
    result = None
    # Flush spi buffer
    while result != [165]:
        result = if_spi.xfer2([cmd_encoder_nop, ], par_encoder_hz)
    # Send position command
    result = if_spi.xfer2([cmd_encoder_pos, ], par_encoder_hz)
    while result == [165]:
        result = if_spi.xfer2([cmd_encoder_pos, ], par_encoder_hz)
    if result == [16]:
        high = if_spi.xfer2([cmd_encoder_nop, ], par_encoder_hz)[0]
        low = if_spi.xfer2([cmd_encoder_nop, ], par_encoder_hz)[0]
        result = high << 8 | low
        position = result & 0x3FFF
        angle = (position / 4096) * 360.00
        return angle
    else:
        return None


# Gyro Data Capture
def gyro_capture():
    acc_x = acc_y = acc_z = 0.00
    capture_iterations = 250
    for count in range(0, capture_iterations):
        # X Acceleration
        high = if_i2c.read_byte_data(addr_gyro, 0x3B)
        low = if_i2c.read_byte_data(addr_gyro, 0x3C)
        value = high << 8 | low
        if value > 32768: value -= 65536
        acc_x += value
        # Y Acceleration
        high = if_i2c.read_byte_data(addr_gyro, 0x3D)
        low = if_i2c.read_byte_data(addr_gyro, 0x3E)
        value = high << 8 | low
        if value > 32768: value -= 65536
        acc_y += value
        # Z Acceleration
        high = if_i2c.read_byte_data(addr_gyro, 0x3F)
        low = if_i2c.read_byte_data(addr_gyro, 0x40)
        value = high << 8 | low
        if value > 32768: value -= 65536
        acc_z += value
    # Average values to help eliminate noisy results
    acc_x /= capture_iterations
    acc_y /= capture_iterations
    acc_z /= capture_iterations
    # Convert to angles and offset by calibration values
    angle_x = math.atan2(-acc_y, -acc_z) * (180.00 / math.pi) + offset_Gyro_X
    angle_y = math.atan2(-acc_x, -acc_z) * (180.00 / math.pi) + offset_Gyro_Y
    angle_z = math.atan2(-acc_y, -acc_x) * (180.00 / math.pi) + offset_Gyro_Z
    # Shift phase to -180 to + 180
    delta = 180 - abs(angle_z)
    if angle_z > 0:
        se_angle = -delta
    else:
        se_angle = delta
    print(f"SEA: {se_angle}\n")
    return se_angle


# Distance Data Capture
def scanner_capture():
    distance = None
    count = 0
    while distance is None:
        count += 1
        try:
            if tfmP.getData():
                # Successful read
                distance = tfmP.dist / 2.52
                # Linear Calibration
                distance += 0.00630984 * distance + 0.549164
        except:
            pass
        if count >= 3:
            distance = 0.00
    return distance


# Camera Image Capture
def camera_capture(inside):
    # Inside Camera: inside == True
    # Outside Camera: inside == False
    if inside == "1":
        image_path = r'Temp/LI_temp.jpg'
        cam_inside.start()
        image = cam_inside.get_image()
        pygame.image.save(image, image_path)
        file = open(image_path, 'rb')
        file_contents = file.read()
        content_bytes = bytearray(file_contents)
        if_mqtt.publish("/data/LI", content_bytes)
        cam_inside.stop()
    if not inside:
        image_path = r'Temp/RI_temp.jpg'
        cam_outside.start()
        image = cam_outside.get_image()
        pygame.image.save(image, image_path)
        file = open(image_path, 'rb')
        file_contents = file.read()
        content_bytes = bytearray(file_contents)
        if_mqtt.publish("/data/RI", content_bytes)
        cam_outside.stop()


# Homing Sensor Check
def homing_capture():
    sensor_state = GPIO.input(pin_homing_in)
    if sensor_state == 0:
        return True
    else:
        return False


# Step Motor Once
def motor_step():
    GPIO.output(pin_motor_step, GPIO.HIGH)
    time.sleep(0.005)
    GPIO.output(pin_motor_step, GPIO.LOW)
    time.sleep(0.005)


# Toggle Motor
def motor_toggle(state):
    if state is None:
        state = not GPIO.input(pin_motor_enable)
    GPIO.output(pin_motor_enable, bool(state))


# Toggle Laser
def laser_toggle(state):
    if state is None:
        state = not GPIO.input(pin_laser_out)
    GPIO.output(pin_laser_out, bool(state))


""" Command Handlers """


# Left Encoder
def LE(unused_parameter):
    angle = encoder_capture()
    # V For 2x Res Encoder System
    angle = ((180 - angle) / 2) + 180
    if_mqtt.publish("/data/LE", str(angle))


# Right Encoder
def RE(unused_parameter):
    angle = encoder_capture()
    # V For 2x Res Encoder System
    angle = (180 - angle) / 2
    if_mqtt.publish("/data/RE", str(angle))


# Super Elevation
def SE(unused_parameter):
    angle = gyro_capture()
    if_mqtt.publish("/data/SEA", str(angle))


# Scan Profile
def SP(unused_parameter):
    total_steps = 1600 # 0.225 degrees per step
    deadzone_a = int(79.8 / 0.225)
    deadzone_b = int((360 - 80.2) / 0.225)
    for count in range(0, total_steps):
        # Determine which segment of scan
        if count < deadzone_a:
            # Initial Deadzone
            motor_step()
            time.sleep(0.01)
        elif count > deadzone_b:
            # Final Deadzone
            motor_step()
            time.sleep(0.01)
        else:
            # Scan Zone
            distance = scanner_capture()
            motor_step()
            angle = (0.225 * count) - 90
            coordinate_x = distance * math.cos(angle * (math.pi/180))
            coordinate_y = distance * math.sin(angle * (math.pi/180))
            if_mqtt.publish("/data/SP", f"{coordinate_x, coordinate_y}")
    if_mqtt.publish("/data/SP", "SP:1")


# Capture Image
def CI(inside):
    if inside == "1":
        camera_capture(True)
    elif inside == "0":
        camera_capture(False)


# Home Motor
def HM(unused_param):
    laser_toggle(1)
    motor_toggle(1)
    laser_detected = homing_capture()
    while not laser_detected:
        motor_step()
        time.sleep(0.01)


# Toggle Motor
def TM(unused_parameter):
    motor_toggle(None)


# Toggle Laser
def TL(unused_parameter):
    laser_toggle(None)


# Calibrate Encoder
def CE(unused_parameter):
    # Flush SPI buffer
    result = None
    while result != [165]:
        result = if_spi.xfer2([cmd_encoder_nop, ], par_encoder_hz)
    # Send reset command
    result = if_spi.xfer2([cmd_encoder_zer, ], par_encoder_hz)
    while result != [128]:
        result = if_spi.xfer2([cmd_encoder_nop, ], par_encoder_hz)


# Command Function Dictionary
command_dict = {"ERLE": LE,
                "ERRE": RE,
                "ERSE": SE,
                "ETHM": HM,
                "ETSP": SP,
                "ETTL": TL,
                "ETTM": TM,
                "ETCI": CI,
                "ETCE": CE}


""" Main Execution Loop """


def primary_loop():
    global queue_commands
    if_mqtt.loop_start()
    queue_commands = []
    while True:
        if len(queue_commands) == 0:
            # Currently no commands
            pass
        elif len(queue_commands) > 0:
            # Currently at least 1 command
            command = queue_commands[0]
            task = command[0:4]
            print(f"CMD: {command}")
            function = command_dict[task]
            parameter = None
            if len(command) > 4:
                parameter = command[5:]
            function(parameter)
            queue_commands.pop(0)


if __name__ == "__main__":
    system_initialize()
    primary_loop()

""" Testing """
# TODO