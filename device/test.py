# Script to test functionality of TF02 Class
import signal
import sys
import time
import Dependencies.tfmp.tfmplus as tfmp


# Custom TimeOutError class - used by signal timer
class TimeOutException(Exception):
    pass


# Handler for TimeOutException():
def timeout_handler(signum, frame):
    print("Timeout limit reached.")
    raise TimeOutException


# Function to determine scan speed when modifying the timeout periods of both the tfmp class and signal timeout
def timeout_test(quantity_points):

    results = []

    # Setup timeout handler
    signal.signal(signal.SIGVTALRM, timeout_handler)

    # Initialize Sensor
    tfmp.begin("/dev/serial0", 115200)

    # List of test parameters
    timer_types = [signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF]
    timeouts = []
    # Populate timeout list
    for i in range(1, 5):
        for j in range(1, 5):
            timeouts.append([i*0.25, j*250])
    # Perform test for each case
    for timeout in timeouts:
        these_results = []
        print("Test Case: ", timeout)
        sig_timeout = timeout[0]
        sen_timeout = timeout[1]
        start_time = time.time()
        # Perform test for 500 points
        for x in range(0, quantity_points):
            this_distance = None
            signal.setitimer(signal.ITIMER_VIRTUAL, sig_timeout)
            try:
                if tfmp.getData(sen_timeout):
                    this_distance = tfmp.dist
                    signal.setitimer(signal.ITIMER_VIRTUAL, 0)
                else:
                    this_distance = 0.00
                    signal.setitimer(signal.ITIMER_VIRTUAL, 0)
            except TimeOutException as to:
                print("Timed Out - CVS")
                this_distance = 0.00
            finally:
                print("Distance: ", this_distance, '\n')
                these_results.append(this_distance)
        # Analyze Test
        stop_time = time.time()
        duration = stop_time - start_time
        success_count = 0
        for p in these_results:
            if not p == 0.00:
                success_count += 1
        success_rate = (success_count / quantity_points) * 100
        results.append([timeout, duration, success_rate])
        print("Case Complete.")
        print([timeout, duration, success_rate], "\n")
    print("All Cases Complete.")
    print(f"[Test Case, Duration, Success Rate]")
    best_rate = [["n/a", "n/a"], 99999999.99, 0.00]
    best_time = [["n/a", "n/a"], 99999999.99, 0.00]
    for result in results:
        print(result)
        if result[1] < best_time[1]:
            best_time = result
        if result[2] > best_rate[2]:
            best_rate = result
    print("\n")
    print("Best Rate Case: ", best_rate)
    print("Best Time Case: ", best_time)

def timeout_test_retries(quantity_points):

    print("Timeout Testing - Retry enabled\n")

    results = []

    # Setup timeout handler
    signal.signal(signal.SIGVTALRM, timeout_handler)

    # Initialize Sensor
    tfmp.begin("/dev/serial0", 115200)

    # List of test parameters
    timer_types = [signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF]
    timeouts = []
    # Populate timeout list
    for i in range(1, 5):
        for j in range(1, 5):
            timeouts.append([i*0.25, j*250])
    # Perform test for each case
    for timeout in timeouts:
        these_results = []
        print("Test Case: ", timeout)
        sig_timeout = timeout[0]
        sen_timeout = timeout[1]
        start_time = time.time()
        # Perform test for 500 points
        for x in range(0, quantity_points):
            this_distance = None

            pt_start_time = time.time()
            while this_distance is None:
                signal.setitimer(signal.ITIMER_VIRTUAL, sig_timeout)
                try:
                    if tfmp.getData(sen_timeout):
                        this_distance = tfmp.dist
                        signal.setitimer(signal.ITIMER_VIRTUAL, 0)
                    else:
                        this_distance = None
                        signal.setitimer(signal.ITIMER_VIRTUAL, 0)
                except TimeOutException as to:
                    print("Timed Out - CSV")
                    this_distance = None
                if this_distance is None and (time.time() - pt_start_time > 1000):
                    this_distance = 0.00
            print(f"{timeout} - [{x+1}]: {this_distance}")
            these_results.append(this_distance)
        print("\n")
        # Analyze Test
        stop_time = time.time()
        duration = stop_time - start_time
        success_count = 0
        for p in these_results:
            if not p == 0.00:
                success_count += 1
        success_rate = (success_count / quantity_points) * 100
        results.append([timeout, duration, success_rate])
        print("Case Complete.")
        print([timeout, duration, success_rate], "\n")
    print("All Cases Complete.")
    print(f"[Test Case, Duration, Success Rate]")
    best_rate = [["n/a", "n/a"], 99999999.99, 0.00]
    best_time = [["n/a", "n/a"], 99999999.99, 0.00]
    for result in results:
        print(result)
        if result[1] < best_time[1]:
            best_time = result
        if result[2] > best_rate[2]:
            best_rate = result
    print("\n")
    print("Best Rate Case: ", best_rate)
    print("Best Time Case: ", best_time)

def timeout_test_retries1(quantity_points):

    print("Timeout Testing - Retry enabled\n")

    results = []

    # Setup timeout handler
    signal.signal(signal.SIGVTALRM, timeout_handler)

    # Initialize Sensor
    tfmp.begin("/dev/serial0", 115200)

    # List of test parameters
    timer_types = [signal.ITIMER_REAL, signal.ITIMER_VIRTUAL, signal.ITIMER_PROF]
    timeouts = []
    # Populate timeout list
    for i in range(1, 5):
        for j in range(1, 5):
            timeouts.append([i*0.25, j*250])
    # Perform test for each case
    for timeout in timeouts:
        these_results = []
        print("Test Case: ", timeout)
        sig_timeout = timeout[0]
        sen_timeout = timeout[1]
        start_time = time.time()
        # Perform test for 500 points
        for x in range(0, quantity_points):
            this_distance = None
            attempt_count = 0

            pt_start_time = time.time()
            while this_distance is None:
                signal.setitimer(signal.ITIMER_VIRTUAL, sig_timeout)
                try:
                    attempt_count += 1
                    if tfmp.getData(sen_timeout):
                        this_distance = tfmp.dist
                        signal.setitimer(signal.ITIMER_VIRTUAL, 0)
                    else:
                        this_distance = None
                        signal.setitimer(signal.ITIMER_VIRTUAL, 0)
                except TimeOutException as to:
                    print("Timed Out - CSV")
                    this_distance = None
                if this_distance is None and attempt_count >= 5:
                    this_distance = 0.00
            print(f"{timeout} - [{x+1}]: {this_distance}")
            these_results.append(this_distance)
        print("\n")
        # Analyze Test
        stop_time = time.time()
        duration = stop_time - start_time
        success_count = 0
        for p in these_results:
            if not p == 0.00:
                success_count += 1
        success_rate = (success_count / quantity_points) * 100
        results.append([timeout, duration, success_rate])
        print("Case Complete.")
        print([timeout, duration, success_rate], "\n")
    print("All Cases Complete.")
    print(f"[Test Case, Duration, Success Rate]")
    best_rate = [["n/a", "n/a"], 99999999.99, 0.00]
    best_time = [["n/a", "n/a"], 99999999.99, 0.00]
    for result in results:
        print(result)
        if result[1] < best_time[1]:
            best_time = result
        if result[2] > best_rate[2]:
            best_rate = result
    print("\n")
    print("Best Rate Case: ", best_rate)
    print("Best Time Case: ", best_time)

def test_tf02():
    # Create instance of sensor
    sensor_setup = tfmp.begin("/dev/serial0", 115200)
    print(f"Sensor Status: {sensor_setup}")
    # Configure Sensor
    #if tfmp.sendCommand(tfmp.SOFT_RESET, 0):
        #print("Sensor successfully reset.")
    #if tfmp.sendCommand(tfmp.SET_FRAME_RATE, tfmp.FRAME_100):
        #print("Sensor framerate succesfully set.")
    # Try to capture distance 500 Times, noting average time and failure rate
    test_start_time = time.time()
    sensor_values = []
    for i in range(0, 1600):
        #print("start")
        time.sleep(0.01)
        #print("done sleeping")
        tfmp.getData()
        #print("done capturing")
        sensor_values.append([tfmp.dist, tfmp.flux, tfmp.temp])
        print(f"[{i+1}] {time.time()} - {tfmp.dist} cm. - {tfmp.printStatus()}")
    print()
    # Calculate test results
    test_stop_time = time.time()
    test_duration = test_stop_time - test_start_time
    success_counter = 0
    failure_counter = 0
    total_distance = 0.00
    for value in sensor_values:
        #print(value)
        if value[0] == 0.00 or value[0] is None:
            failure_counter += 1
        else:
            success_counter += 1
            total_distance += value[0]
    average_distance = total_distance / success_counter
    success_rate = success_counter / (success_counter + failure_counter)
    # Print results
    print("TF-02 Test Results:")
    print(f"Total Attempts:\t{success_counter + failure_counter}")
    print(f"Successful Attempts:\t{success_counter}")
    print(f"Success Rate:\t{success_rate*100.00}%")
    print(f"Total Duration:\t{test_duration} seconds.")
    print(f"Average Duration:\t{test_duration / (success_counter + failure_counter)} seconds.")
    print(f"Average Distance:\t{average_distance} cm.\n")

def test_cameras():
    print("Beginning test of USB cameras.\n")
    import pygame
    import pygame.camera
    from pygame.locals import *
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg

    pygame.init()
    pygame.camera.init()

    print("Attempting to find cameras.")
    camera_list = pygame.camera.list_cameras()
    print(camera_list)

    print(f"{len(camera_list)} cameras detected.\n")

    cam1 = None
    cam2 = None

    # Initialize cameras
    print("Attempting to initialize cameras..")
    if camera_list:
        cam1 = pygame.camera.Camera(camera_list[0], (640, 480))
        print(f"{camera_list[0]} initialized..")
    if len(camera_list > 1):
        cam2 = pygame.camera.Camer(camera_list[1], (640, 480))
        print(f"{camera_list[1]} initialized..")
    print()

    # Capture an image
    print("Attempting to capture and display images..")
    for cam in camera_list:
        if camera_list:
            cam1.start()
            cam1_image = cam1.get_image()
            print("Camera 1 image captured.")
            # Display image
            imgplot1 = plt.imshow(cam1_image)
            print("Camera 1 image displayed.")
            plt.show()
        if len(camera_list > 1):
            cam2.start()
            cam2_image = cam2.get_image()
            print("Camera 2 image captured.")
            # Display image
            imgplot2 = plt.imshow(cam2_image)
            print("Camera 2 image displated.")
            plt.show()
    print()

    print("Camera testing complete.")
    while True:
        time.sleep(1)


if __name__ == "__main__":

    # Start test
    test_cameras()

    # Farewell
    print("All tests completed.  Exiting now..")
    sys.exit()

