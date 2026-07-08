#!/usr/bin/env python3
import paho.mqtt.client as mqtt, json, subprocess, os, time

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "robot/patrol"
patrol_process = None

def start_patrol():
    global patrol_process
    if patrol_process is None or patrol_process.poll() is not None:
        subprocess.run(["pkill", "lidar_avoider"])
        patrol_process = subprocess.Popen(["python3", "/home/rock/simple_patrol.py"])
        print("巡检已启动")
    else:
        print("巡检已在运行中")

def stop_patrol():
    global patrol_process
    if patrol_process is not None and patrol_process.poll() is None:
        patrol_process.terminate()
        patrol_process.wait()
        patrol_process = None
        subprocess.run(["ros2", "run", "lidar_avoider", "lidar_avoider"], cwd="/home/rock/astra_ws")
        print("巡检已停止，避障已恢复")

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    cmd = data.get("cmd")
    if cmd == "start_patrol": start_patrol()
    elif cmd == "stop_patrol": stop_patrol()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()