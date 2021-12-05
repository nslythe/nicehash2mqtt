import pynicehash
from paho.mqtt import client as mqtt_client
import random
import time
import json
import logging

class MqttMiningRig(object):
    def __init__(self, publisher, rig):
        self.rig = rig
        self.publisher = publisher

    def config(self):
        for d in self.rig.devices:
            self.send_config(d)
            self.publisher.subscribe(self.get_topic(d) + "/set", self.get_received_command_fnc(d))            

    def publish(self):
        self.rig.update()
        
        for d in self.rig.devices:
            status = "INACTIVE"
            available = "online"
            if d.status == "MINING" or d.status == "BENCHMARKING" or d.status == "PENDING":
                status = "MINING"
            if d.status == "UNKNOWN" or d.status == "DISABLED" or d.status == "OFFLINE":
                available = "offline"
            self.publisher.publish(self.get_topic(d) + "/state", status)
            self.publisher.publish(self.get_topic(d) + "/available", available)

    def get_topic(self, device):
        return f"homeassistant/switch/pynicehash/{device.parent_rig.id}_{device.id}"

    def send_config(self, device):
        topic = self.get_topic(device) + "/config"
        self.publisher.publish(topic, json.dumps({
            "state_topic": self.get_topic(device) + "/state",
            "command_topic" : self.get_topic(device) + "/set",
            "availability_topic" : self.get_topic(device) + "/available",
            "name": f"{device.parent_rig.name.upper()} {device.name}",
            "unique_id": f"{device.parent_rig.id}_{device.id}_state",
            "force_update": True,
            "icon": "mdi:pickaxe",
            "payload_on": "MINING",
            "payload_off": "INACTIVE",
        }))

    def get_received_command_fnc(self, device):
        def received_command(payload):
            if payload == "MINING":
                mining_status = pynicehash.MiningStatus.START
            elif payload == "INACTIVE":
                mining_status = pynicehash.MiningStatus.STOP
            else:
                raise Exception()
            self.rig.set_device_status(device, mining_status)
            self.publish()

        return received_command

class MqttPublisher(object):
    def __init__(self, server, port, user = "", password = ""):
        self.broker = server
        self.port = port
        self.user = user
        self.password = password
        self.client_id = f'pynicehash-{random.randint(0, 1000)}'
        self.client = None
        self.subscribe_topic = {}

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.getLogger(__name__).info("Connected to mqtt")
        else:
            logging.getLogger(__name__).error(f"Failed to connect to mqtt error_code {rc}")

    def on_message(self, client, userdata, msg):
        logging.getLogger(__name__).info(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        
        if msg.topic in self.subscribe_topic:
            self.subscribe_topic[msg.topic](msg.payload.decode())
        else:
            raise Exception()

    def connect(self):
        self.client = mqtt_client.Client(self.client_id)
        self.client.username_pw_set(self.user, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker, self.port)

    def subscribe(self, topic, fnc):
        self.client.subscribe(topic)
        self.subscribe_topic[topic] = fnc

    def start(self):
        self.client.loop_start()

    def publish(self, topic, value):
        result = self.client.publish(topic, value)

