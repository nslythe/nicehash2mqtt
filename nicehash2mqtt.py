#!python

import argparse

import pynicehash
from paho.mqtt import client as mqtt_client
import random
import time
import json
import datetime
import logging

class MqttMiningRigDevice(object):
    def __init__(self, device_id, device):
        self.device: pynicehash.MiningDevice = device
        self.device_id = device_id

class MqttMiningRig(object):
    def __init__(self, rig_id, publisher, rig):
        self.rig: pynicehash.MiningRig = rig
        self.rig_id = rig_id
        self.publisher = publisher
        self.devices: list[MqttMiningRigDevice] = []

    def config(self):
        device_id = 0
        for d in self.rig.devices:
            self.devices.append(MqttMiningRigDevice(device_id, d))
            device_id += 1
        
        for d in self.devices:
            self.send_switch_config(d)
            self.send_sensor_config(d, "_temp", "°C")
            self.send_sensor_config(d, "_load", "%")
            topic = self.get_nicehash2mqtt_topic(d) + "/set"
            self.publisher.subscribe(topic, self.get_received_command_fnc(d))

    def publish(self):
        logging.getLogger(__name__).info(f"Update data from nicehash")

        self.rig.update()

        self.devices = []
        device_id = 0
        for d in self.rig.devices:
            self.devices.append(MqttMiningRigDevice(device_id, d))
            device_id += 1
        
        for d in self.devices:
            status = "INACTIVE"
            available = "online"
            if d.device.status == pynicehash.DeviceMiningStatusEnum.DISABLED:
                available = "offline"
            if d.device.status == pynicehash.DeviceMiningStatusEnum.BENCHMARKING or\
                d.device.status == pynicehash.DeviceMiningStatusEnum.MINING:
                status = "MINING"
            self.publisher.publish(self.get_nicehash2mqtt_topic(d) + "/state", status)
            self.publisher.publish(self.get_nicehash2mqtt_topic(d) + "/available", available)
            self.publisher.publish(self.get_nicehash2mqtt_topic(d)+ "_temp" + "/state", d.device.temperature)
            self.publisher.publish(self.get_nicehash2mqtt_topic(d)+ "_temp" + "/available", "online")
            self.publisher.publish(self.get_nicehash2mqtt_topic(d)+ "_load" + "/state", d.device.load)
            self.publisher.publish(self.get_nicehash2mqtt_topic(d)+ "_load" + "/available", "online")
            

    def get_switch_config_topic(self, device: MqttMiningRigDevice):
        return f"homeassistant/switch/nicehash2mqtt_{self.rig_id}_{device.device_id}/switch/config"

    def get_sensor_config_topic(self, device: MqttMiningRigDevice, sufix):
        return f"homeassistant/sensor/nicehash2mqtt_{self.rig_id}_{device.device_id}{sufix}/sensor/config"

    def get_nicehash2mqtt_topic(self, device: MqttMiningRigDevice):
        return f"nicehash2mqtt/nicehash2mqtt_{self.rig_id}_{device.device_id}"


    def send_switch_config(self, device: MqttMiningRigDevice):
        self.publisher.publish(self.get_switch_config_topic(device), json.dumps({
            "state_topic": self.get_nicehash2mqtt_topic(device) + "/state",
            "command_topic" : self.get_nicehash2mqtt_topic(device) + "/set",
            "availability_topic" : self.get_nicehash2mqtt_topic(device) + "/available",
            "payload_available": "online",
            "payload_not_available": "offline",
            "name": device.device.name,
            "unique_id": f"{device.device.parent_rig.id}_{device.device_id}_state",
            "force_update": True,
            "icon": "mdi:pickaxe",
            "payload_on": "MINING",
            "payload_off": "INACTIVE",
            "device": {
                "configuration_url" : "https://www.nicehash.com/my/mining/rigs",
                "name": self.rig.name,
                "identifiers": [self.rig.id],
                "manufacturer": "nicehash2mqtt"
            }
        }), retain=True)

    def send_sensor_config(self, device: MqttMiningRigDevice, sufix, unit):
        self.publisher.publish(self.get_sensor_config_topic(device, sufix), json.dumps({
            "state_topic": self.get_nicehash2mqtt_topic(device) + sufix + "/state",
            "unit_of_measurement": unit,
            "availability_topic" : self.get_nicehash2mqtt_topic(device) + sufix + "/available",
            "name": device.device.name,
            "unique_id": f"{device.device.parent_rig.id}_{device.device_id}" + sufix,
            "force_update": True,
            "icon": "mdi:thermometer",
            "device": {
                "configuration_url" : "https://www.nicehash.com/my/mining/rigs",
                "name": self.rig.name,
                "identifiers": [self.rig.id],
                "manufacturer": "nicehash2mqtt"
            }
        }), retain=True)


    def get_received_command_fnc(self, device: MqttMiningRigDevice):
        def received_command(payload):
            if payload == "MINING":
                device.device.start_mining()
            elif payload == "INACTIVE":
                device.device.stop_mining()
            else:
                raise Exception()
            self.publisher.publish(self.get_nicehash2mqtt_topic(device) + "/state", "MINING")

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

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
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
        self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(self.user, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker, self.port)

    def subscribe(self, topic, fnc):
        self.client.subscribe(topic)
        self.subscribe_topic[topic] = fnc

    def start(self):
        self.client._reconnect_on_failure = True
        self.client.loop_start()

    def publish(self, topic, value, retain=False):
         result = self.client.publish(topic, value, retain = retain)


def init_logging(*, level = logging.INFO):
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=level,
        datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger("amqp").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("model").setLevel(logging.INFO)

def main():
    init_logging(level=logging.INFO)
 
    state_delay = 10
    api_url = "https://api2.nicehash.com"

    parser = argparse.ArgumentParser()
    parser.add_argument("--organisation", help="")
    parser.add_argument("--api_key", help="")
    parser.add_argument("--api_secret", help="")
    parser.add_argument("--mqtt_server", help="")
    parser.add_argument("--mqtt_port", help="", type=int)
    parser.add_argument("--mqtt_user", help="", default="")
    parser.add_argument("--mqtt_password", help="", default="")
    args = parser.parse_args()

    logging.basicConfig(level = logging.INFO)

    logging.info("starting")

    try:
        nh = pynicehash.NiceHash(api_url, args.organisation, args.api_key, args.api_secret)
        publisher = MqttPublisher(args.mqtt_server, args.mqtt_port, args.mqtt_user, args.mqtt_password)
        publisher.connect()

        rigs = []
        rig_id = 0
        for r in nh.get_rigs():
            if r.is_managed:
                mqtt_rig = MqttMiningRig(rig_id, publisher, r)
                mqtt_rig.config()
                rigs.append(mqtt_rig)
                rig_id += 1

    except:
        logging.exception("Failed")
    
    publisher.start()

    last_ran = datetime.datetime(year=1979, month=1, day=1)
    while True:
        for r in rigs:
            try:
                if (datetime.datetime.now() - last_ran).seconds >= state_delay:
                    r.publish()
                    last_ran = datetime.datetime.now()
            except:
                logging.exception("Publish failed")
        time.sleep(0.1)

if __name__ == "__main__":
    main()
