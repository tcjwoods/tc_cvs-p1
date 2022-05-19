"""

Clearance Verification System
Script: main.py
Description: The purpose of this script is to control the CVS device.  The device fields
             commands from a client device via MQTT and captures data relevant to the
             clearance measurement process used when performing work near tracks in which
             it is possible for train to strike installed equipment

"""

# Import all dependencies
import os, time, math, serial, smbus, board, spidev, signal
import gpiozero as gpio
import RPi.GPIO as GPIO
import matplotlib.pyplot as plt
import Dependencies.tfmp.tfmplus as tfmP
from Dependencies.tfmp.tfmplus import *
import paho.mqtt.client as mqtt
import csv
from Dependencies.encoder import Encoder
import signal

# Tracking Variables
timeout_counter = 0
success_counter = 0

# Pin Definitions
MPU_SDA = 2
MPU_SCL = 3
SM_M0 = 13
SM_M1 = 6
SM_M2 = 5
SM_STEP = 23
SM_DIR = 24
SM_EN = 12
TFM_TX = 14
TFM_RX = 15
LAS_OUT = 18
HS_IN = 19

# Additional Constants
tfm_addr = 0x10
SPI_BUS = 0
LE_CSP = 0
mpu_addr = 0x68

# Device Instances
spi = None
myMQTT = None
i2cbus = None
mySerial=None

# Calibration Values
scan_offset_x = 0.00
scan_offset_y = 0.00
scan_offset_d = 0.00
z_calib = 0.00

# Stepper Motor Variables
sm_CurrentAngle = 0.00
sm_CurrentResolution = 0.00

# Command Queue Variables
command_queue = []

# TF-Mini Plus Variables
dist = 0.00
flux = 0.00
temp = 0.00

# SPI Encoder Commands
AMT_NOP = 0x00
AMT_POS = 0x10
AMT_ZER = 0x70
speed_hz = 500000
delay_us = 3

# Calibration Variables
_calibration_values = None

# MQTT Parameter Variables
_broker_address = "192.168.42.1"
_mqtt_topics = ["command", "debug"]

##### Timeout Exception Class #####

class TimeOutException(Exception):
    pass

##### MQTT Callback #####

def on_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode("utf-8")
    command_queue.append(payload)
    
##### Initialization Functions #####
    
# System Initialization
def system_init():
    console_init()
    print("Beginning system initialization now..\n")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    calib_init() # Calibration
    mqtt_init()  # MQTT Broker + Client
    mpu_init()   # MPU-6050
    tfm_init()   # TF-Mini Plus
    enc_init()   # Quadrapture Encoders (2)
    sm_init()    # Stepper Motor
    print("System initialization complete.\n")
    print("CVS Access Information")
    print("AP SSID: CVS_AP")
    print("AP PSKY: Clearance1")
    print("System IP: 192.168.42.10\n")

# Console Greeting Initialization
def console_init():
    # Print System Information
    print("Clearance Verification System - Version 1.0\n")
    print("Script Name: '/home/pi/Desktop/cvs_data_manager/main.py")
    print("Script Version: 1.0")
    print("Last Update: n/a\n")

# Calibration Initialization
def calib_init():
    global _calibration_values
    print("Initializing Calibration Settings..")
    _calibration_values = []
    with open('/home/pi/Desktop/cvs_data_manager/Resources/calibration_values.csv') as calib_file:
        reader = csv.reader(calib_file, delimiter=',')
        line = 0
        for row in reader:
            if line != 0:
                param = row[0]
                value = float(row[1])
                _calibration_values.append(value)
            line += 1
    print("Calibration Settings initialization complete.\n")

# MQTT Broker and Client Initialization
def mqtt_init():
    global myMQTT
    print("Initializing Network Services..") 
    # Restart access point
    print("Restarting isc-dhcp-server.service now..")
    os.system("sudo systemctl restart isc-dhcp-server.service")
    print("Restarting hostapd.service now..")
    os.system("sudo systemctl restart hostapd")
    print("Restarting mosquitto.service now..")
    os.system("sudo systemctl restart mosquitto")
    # Initialize MQTT Broker
    print("Restarting mosquitto.service now..")
    os.system("sudo systemctl restart mosquitto")
    # Initialize MQTT Client
    myMQTT = mqtt.Client("cvs-datamanager")
    myMQTT.connect(_broker_address)
    print("Broker addr: ", _broker_address)
    for topic in _mqtt_topics:
        myMQTT.subscribe(topic)
        print("Subscribed Topic: ", topic)
    myMQTT.on_message = on_message    
    print("Network Services initialization complete.\n")

# MPU-6050 Initialization
def mpu_init():
    # Initialize MPU-6050
    global i2cbus
    print("Initializing MPU-6050..")
    i2cbus = smbus.SMBus(1)
    time.sleep(1)
    try:
        i2cbus.write_byte_data(mpu_addr, 0x19, 7)
        i2cbus.write_byte_data(mpu_addr, 0x6B, 1)
        i2cbus.write_byte_data(mpu_addr, 0x1A, 0)
        i2cbus.write_byte_data(mpu_addr, 0x1B, 24)
        i2cbus.write_byte_data(mpu_addr, 0x38, 1)
    except Exception as e:
        print("MPU-6050 initialization failed")
        return
    print("MPU-6050 initialization complete.\n")

# Rotary Encoder Initialization
def enc_init():
    global spi
    print("Initializing AMT203-V Encoder..")
    spi = spidev.SpiDev()
    spi.open(0, 0)
    print("AMT203-V Encoder initialization complete.\n")
    
# TF-Mini Plus Initialization
def tfm_init():
    global mySerial
    
    # Initialize TF-Mini Plus, Laser, SM Driver
    print("Initializing Sensor Head..")
    if (tfmP.begin("/dev/serial0", 115200)):
        print("TF-Mini Plus ready.")
    else:
        print("TF-Mini Plus failed to initialize.")
    GPIO.setup(LAS_OUT, GPIO.OUT)
    # Set up timeout signal
    #signal.signal(signal.SIGALRM, timeout_handler())
    print("Sensor Head initialization complete.\n")


# Stepper Motor + A4988 Initialization
def sm_init():
    print("Initializing stepper motor and driver..")
    GPIO.setup(SM_STEP, GPIO.OUT)
    GPIO.setup(SM_DIR, GPIO.OUT)
    GPIO.setup(SM_EN, GPIO.OUT)
    GPIO.setup(SM_M0, GPIO.OUT)
    GPIO.setup(SM_M1, GPIO.OUT)
    GPIO.setup(SM_M2, GPIO.OUT)
    GPIO.setup(HS_IN, GPIO.IN)
    GPIO.output(SM_EN, GPIO.HIGH)
    print("Stepper motor initialization complete.\n")
    
##### Secondary Functions #####
    
# Function to handle TFM Capture Timeout
def handler(signum, frame):
    global timeout_counter
    timeout_counter += 1
    print("Distance capture timed out.")
    raise TimeOutException()


signal.signal(signal.SIGVTALRM, handler)


def hs_is_found():
    sensor_state = GPIO.input(HS_IN)
    if sensor_state == 0:
        return True
    else:
        return False


def enc_retrieve(as_angle):
    # Flush SPI Buffer
    result = None
    while result != [165]:
        result = spi.xfer2([AMT_NOP, ], speed_hz)
    # Capture Current Position
    result = spi.xfer2([AMT_POS, ], speed_hz)
    while result == [165]:
        result = spi.xfer2([AMT_POS, ], speed_hz)
    if result == [16]:
        msb = spi.xfer2([AMT_NOP, ], speed_hz)[0]
        lsb = spi.xfer2([AMT_NOP, ], speed_hz)[0]
        result = msb << 8 | lsb
        position = result & 0x3FFF
        angle = (position / 4096.0) * 360.00
        angle = angle - 109.3359375
        if as_angle:
            return angle
        else:
            return angle * (math.pi/180.0)
    else:
        return 0.00

def mpu_read_raw(addr):
    high = i2cbus.read_byte_data(mpu_addr, addr)
    low = i2cbus.read_byte_data(mpu_addr, addr+1)
    value = high << 8 | low
    if (value > 32768):
        value = value - 65536
    return value

def mpu_retrieve(axis):
    acc_x = 0.00
    acc_y = 0.00
    acc_z = 0.00
    # Average over 250 Iterations
    total_iterations = 250
    for value_count in range(0, total_iterations):
        acc_x += mpu_read_raw(0x3B)
        acc_y += mpu_read_raw(0x3D)
        acc_z += mpu_read_raw(0x3F)
    acc_x = acc_x / total_iterations
    acc_y = acc_y / total_iterations
    acc_z = acc_z / total_iterations
    ang_x = math.atan2(-acc_y, -acc_z) * (180.00 / math.pi)
    ang_y = math.atan2(-acc_x, -acc_z) * (180.00 / math.pi)
    ang_z = math.atan2(-acc_y, -acc_x) * (180.00 / math.pi)
    ang_z += z_calib
    if ang_z > 180:
        ang_z = - (360 - ang_z)
    ang_z += 180.00
    if axis == "Z":
        return ang_z
    else:
        return None

def sm_determine_resolution(as_angle):
    ms0 = GPIO.input(SM_M0)
    ms1 = GPIO.input(SM_M1)
    ms2 = GPIO.input(SM_M2)
    this_resolution = 0.00
    pin_sum = ms0 + ms1 + ms2
    if pin_sum == 0:
        this_resolution = "1.800"
    elif pin_sum == 2:
        this_resolution = "0.225"
    else:
        if ms0 == 1:
            this_resolution = "0.900"
        else:
            this_resolution = "0.450"
    if as_angle:
        return this_resolution
    else:
        return [ms0, ms1, ms2]
    
def tfm_capture_distance():
    this_distance = None
    attempt_count = 0
    while this_distance is None:
        attempt_count += 1
        try:
            #signal.setitimer(signal.ITIMER_VIRTUAL, 1.0)
            if tfmP.getData():
                this_distance = tfmP.dist / 2.52
            else:
                this_distance = None
        except TimeOutException as e_TOE:
            this_distance = None
        finally:
            pass
            #signal.setitimer(signal.ITIMER_VIRTUAL, 0)
        if attempt_count >= 9:
            print("Failed to capture distance in time..")
            return 0.00
    return this_distance


def tfm_capture_distance_rapid():
    this_dist = None
    attempt_counter = 0
    signal.setitimer(signal.ITIMER_VIRTUAL, 1.0)
    try:
        if tfmP.getData():
            this_dist = tfmP.dist / 2.54
            signal.setitimer(signal.ITIMER_VIRTUAL, 0)
        else:
            this_dist = 0.00
            signal.setitimer(signal.ITIMER_VIRTUAL, 0)
    except TimeOutException as e_to:
        this_dist = 0.00
        signal.setitimer(signal.ITIMER_VIRTUAL, 0)
    return this_dist


def sm_step():
    GPIO.output(SM_STEP, GPIO.HIGH)
    time.sleep(0.005)
    GPIO.output(SM_STEP, GPIO.LOW)
    time.sleep(0.005)

def sm_set_resolution(pin_combination):
    GPIO.output(SM_M0, pin_combination[0])
    GPIO.output(SM_M1, pin_combination[1])
    GPIO.output(SM_M2, pin_combination[2])
    print(f"SM RESOLUTION SET: {pin_combination}")
    print(f"SM0: {GPIO.input(SM_M0)}")
    print(f"SM1: {GPIO.input(SM_M1)}")
    print(f"SM2: {GPIO.input(SM_M2)}")
    
def sm_set_direction(CCW):
    GPIO.output(SM_DIR, CCW)
    
##### Primary Functions #####
    
resolution_dict = {"1.800": [0,0,0],
                   "0.900": [1,0,0],
                   "0.450": [0,1,0],
                   "0.225": [1,1,0]}

def LE(unused_parameter):
    # Retrieve Current Angle Value
    this_angle = enc_retrieve(True)
    # Publish to MQTT Channel
    print(f"LEA:{this_angle}\n")
    myMQTT.publish("/data/LEA", str(this_angle))

def RE(unused_parameter):
    # Retrieve Current Angle Value
    this_angle = enc_retrieve(True)
    # Publish to MQTT Channel
    print(f"REA:{this_angle}\n")
    myMQTT.publish("/data/REA", str(this_angle))

def SE(unused_parameter):
    # Retrieve Current Angle Value
    this_angle = mpu_retrieve("Z")
    # Calculate SEA and SEO Values
    this_SEA = this_angle
    this_SEO = 56.5 * math.sin(this_SEA * (math.pi / 180.0))
    # Publish to MQTT Channel
    print(f"SEA:{this_SEA}")
    print(f"SEO:{this_SEO}\n")
    myMQTT.publish("/data/SEA", str(this_SEA))
    myMQTT.publish("/data/SEO", str(this_SEO))

def SP_RAPID(unused_parameter):
    CYCLES = 10
    # Rotates rapidly for 10 cycles, with very low timeout for distance
    sm_set_resolution([1, 1, 0])
    current_resolution = 0.225
    steps = int((CYCLES * 360.0) / current_resolution)
    print(f"Executing {CYCLES} scan cycles, with {steps} total steps..\n")
    for step_counter in range(0, steps):
        # Capture Distance
        this_dist = tfm_capture_distance_rapid()
        # Step Once
        sm_step()
        # Perform Calculations
        this_angle = (step_counter * current_resolution) - 90.0
        this_x = this_dist * math.cos(this_angle * (math.pi / 180.0))
        this_y = this_dist * math.sin(this_angle * (math.pi / 180.0))
        print(f"SP:{step_counter+1}|{this_x}|{this_y}\n")
        myMQTT.publish("/data/SP", f"{this_x}|{this_y}")
    print("Scan completed.\n")
    myMQTT.publish("/data/SP", "SP:1")

def SP(unused_parameter):
    start_time = time.time()
    # Verify Motor is Home
    #HM(None)
    # Set Resolution to 0.225
    sm_set_resolution([1, 1, 0])
    current_resolution = 0.225
    # Determine number of measurements to make
    # current_resolution = float(sm_determine_resolution(True))
    steps = 360 / float(current_resolution)
    # Perform Scan
    print(f"Executing Scan: {steps} points")
    for step_counter in range(0, int(steps)):
        # Capture Distance
        this_distance = tfm_capture_distance_rapid()
        # Step Motor
        sm_step()
        # Calculate Cortesian Equivalent to Vector
        this_angle = (step_counter * current_resolution) - 90.0
        print(f"Dist: {this_distance}")
        print(f"Angle: {this_angle}")
        this_x = this_distance * math.cos(this_angle * (math.pi / 180.0))
        this_y = this_distance * math.sin(this_angle * (math.pi / 180.0))
        # Publish to MQTT Channel
        print(f"SP:{step_counter+1}|{this_x}|{this_y}\n")
        myMQTT.publish("/data/SP", f"{this_x}|{this_y}")
    end_time = time.time()
    duration = end_time - start_time
    print(f"Scan Completed.")
    print(f"Total Points: {steps}")
    print(f"Capture Success Rate: {(steps - timeout_counter) / steps}%")
    print(f"Timed Out Captures: {timeout_counter}")
    print(f"Scan Duration: {duration}")
    print(f"Avg Time/Point: {duration/steps}\n")
    # Re-Home Motor
    #HM()
    # Publish Complete Flag to MQTT Channel
    myMQTT.publish("/data/SP", "SP:1")
    
def SR(resolution):
    if resolution == "":
        resolution = "0.225"
    # Determine Pin States for Desired Resolution
    pin_combination = resolution_dict[resolution]
    # Set Pins to Desired Combination
    sm_set_resolution(pin_combination)
    print(f"SR:{sm_determine_resolution(False)}")
    
def HM(unused_parameter):
    # Enable Laser an Motor (If not Already Enabled)
    TL(True)
    TM(True)
    sm_set_direction(True)
    # Set Resolution to Eighth Stepping
    prior_resolution_combo = sm_determine_resolution(False)
    new_resolution_combo = resolution_dict["0.225"]
    sm_set_resolution(new_resolution_combo)
    # Move Scanner until Homing Sensor is Triggered
    exit_flag = False
    while (exit_flag == False):
        # Check Homing Sensor
        if (hs_is_found()):
            exit_flag = True
            print("SM: Home")
            break
        else:
            sm_step()
    # Disable Laser and Motor, Reset Resolution to Orignial
    sm_set_resolution(prior_resolution_combo)
    TL(False)
    TM(False)
    
def TL(state):
    # Set Laser Pin output to supplied state
    if (state == None):
        state = GPIO.input(LAS_OUT)
        state = not state
    GPIO.output(LAS_OUT, state)
    
def TM(state):
    # Set Motor Enable Pin output to supplied state
    if (state == None):
        state = GPIO.input(SM_EN)
    GPIO.output(SM_EN, not state)
    print(state)
    
##### Primary Loop #####
    
command_dict = {"ERLE": LE,
                "ERRE": RE,
                "ERSE": SE,
                "ETHM": HM,
                "ETSR": SR,
                "ETSP": SP_RAPID,
                "ETTL": TL,
                "ETTM": TM}
def primary_loop():
    print("Primary data loop entered..\n")
    exit_flag = False
    myMQTT.loop_start()
    while (exit_flag == False):
        if (len(command_queue) == 0):
            # Currently no commands
            pass
        elif (len(command_queue) > 0):
            # Currently at least 1 command
            this_command = command_queue[0]
            prefix = this_command[0:4]
            print(f"Command Received: {this_command}")
            this_function = command_dict[prefix]
            this_parameter = None
            if (len(this_command) > 4):
                this_parameter = this_command[5:]
            this_function(this_parameter)
            command_queue.pop(0)
    
##### Test Loop #####

def test_loop():
    # Test Motor
    print("Setting motor to full step..")
    sm_set_resolution([1, 1, 0])
    GPIO.output(SM_EN, GPIO.LOW)
    GPIO.output(LAS_OUT, GPIO.HIGH)
    print("Complete.\n")
    print("Now moving motor 360 degrees (200 Steps)..")
    for step_count in range(0, 1600):
        print(f"Step: {step_count}")
        sm_step()
        time.sleep(0.025)
    print("Test of motor completed, stepped 200 times.\n")
    GPIO.output(SM_EN, GPIO.HIGH)
    GPIO.output(LAS_OUT, GPIO.LOW)

##### Initial Function #####
    
if __name__ == "__main__":
    time.sleep(4)
    # Initialize System
    system_init()
    # Check "Test Mode" Flag, Enter if Applicable
    test_flag = False
    if test_flag:
        test_loop()
        while True:
            pass
    # Enter Primary Loop
    primary_loop()

