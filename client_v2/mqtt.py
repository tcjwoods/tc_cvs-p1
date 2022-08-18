# File Name: cvs_mqtt.py
# Project Name: Clearance Verification System
# Author: J Woods
# Creation Date: 1/21/2022
# Last Modified: 1/21/2022
# Version: 1.0
#
# Purpose:
# The purpose of the cvs_mqtt.py file is to hold the MQTT client class.  This class is used to communicate with the CVS via the internally
# hosted wifi access point (Typically CVS_AP).
#
# TODO List:
# - Generate todo list
#
#

# Imports
import paho.mqtt.client as mqtt
from PyQt5 import QtCore


# MQTT Class Declaration
class mqttClient(QtCore.QObject):
    # Connection States
    Disconnected = 0
    Connecting = 1
    Connected = 2

    # MQTT Version
    MQTT_3_1 = mqtt.MQTTv31

    # Connection State Signals
    connected = QtCore.pyqtSignal()
    disconnected = QtCore.pyqtSignal()
    stateChanged = QtCore.pyqtSignal(int)
    hostnameChanged = QtCore.pyqtSignal(str)
    portChanged = QtCore.pyqtSignal(int)
    keepAliveChanged = QtCore.pyqtSignal(int)
    cleanSessionChanged = QtCore.pyqtSignal(bool)
    protocolVersionChanged = QtCore.pyqtSignal(int)

    # Message Signal
    messageSignal = QtCore.pyqtSignal(mqtt.MQTTMessage)

    # Class Initializer
    def __init__(self, parent=None):
        super(mqttClient, self).__init__(parent)

        # Class Parameters
        self.m_hostname = ""
        self.m_port = 1883
        self.m_keepAlive = 60
        self.m_cleanSession = False
        self.m_protocolVersion = mqttClient.MQTT_3_1
        self.m_state = mqttClient.Disconnected

        # Create Instance of Client
        self.m_client = mqtt.Client("CVSCLient", clean_session=self.m_cleanSession, protocol=self.protocolVersion,
                                    reconnect_on_failure=True, transport="tcp")

        # Connect Signals
        self.m_client.on_message = self.on_message
        self.m_client.on_connect = self.on_connect
        self.m_client.on_disconnect = self.on_disconnect

    # End of __init__()

    # State Signal
    @QtCore.pyqtProperty(int, notify=stateChanged)
    def state(self):
        return self.m_state

    @state.setter
    def state(self, state):
        if self.m_state == state: return
        self.m_state = state
        self.stateChanged.emit(state)

    # Hostname Signal
    @QtCore.pyqtProperty(str, notify=hostnameChanged)
    def hostname(self):
        return self.m_hostname

    @hostname.setter
    def hostname(self, hostname):
        if self.m_hostname == hostname: return
        self.m_hostname = hostname
        self.hostnameChanged.emit(hostname)

    # Port Signal
    @QtCore.pyqtProperty(int, notify=portChanged)
    def port(self):
        return self.m_port

    @port.setter
    def port(self, port):
        if self.m_port == port: return
        self.m_port = port
        self.portChanged.emit(port)

    # Keep Alive Signal
    @QtCore.pyqtProperty(int, notify=keepAliveChanged)
    def keepAlive(self):
        return self.m_keepAlive

    @keepAlive.setter
    def keepAlive(self, keepAlive):
        if self.m_keepAlive == keepAlive: return
        self.m_keepAlive = keepAlive
        self.keepAliveChanged.emit(keepAlive)

    # Clean Session Signal
    @QtCore.pyqtProperty(bool, notify=cleanSessionChanged)
    def cleanSession(self):
        return self.m_cleanSession

    @cleanSession.setter
    def cleanSession(self, cleanSession):
        if self.m_cleanSession == cleanSession: return
        self.m_cleanSession = cleanSession
        self.cleanSessionChanged.emit(cleanSession)

    # Protocol Version Signal
    @QtCore.pyqtProperty(int, notify=protocolVersionChanged)
    def protocolVersion(self):
        return self.m_protocolVersion

    @protocolVersion.setter
    def protocolVersion(self, protocolVersion):
        if self.m_protocolVersion == protocolVersion: return
        self.m_protocolVersion = protocolVersion
        self.protocolVersionChanged.emit(protocolVersion)

    # Connection Callbacks
    @QtCore.pyqtSlot()
    def connectToHost(self):
        if self.m_hostname:
            self.m_client.connect(self.m_hostname,
                                  port=self.port,
                                  keepalive=self.keepAlive)
            self.state = mqttClient.Connecting
            self.m_client.loop_start()

    @QtCore.pyqtSlot()
    def disconnectFromHost(self):
        self.m_client.disconnect()

    # Subscribe/Publish Callbacks

    def subscribe(self, path):
        if self.state == mqttClient.Connected:
            self.m_client.subscribe(path)

    def publish(self, path, message):
        if self.state == mqttClient.Connected:
            self.m_client.publish(path, message)

    ##### Callbacks #####

    @QtCore.pyqtSlot()
    def on_message(self, mqttc, obj, msg):
        mess = str(msg.payload)
        top = msg.topic
        mstr = top + "|" + mess
        self.messageSignal.emit(msg)

    def on_connect(self, *args):
        self.state = mqttClient.Connected
        self.connected.emit()

    def on_disconnect(self, *args):
        self.state = mqttClient.Disconnected
        self.disconnected.emit()