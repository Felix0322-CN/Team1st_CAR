#!/usr/bin/env python3
import rclpy, math, json
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import paho.mqtt.client as mqtt

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "robot/obstacle"

class ObstacleAlert(Node):
    def __init__(self):
        super().__init__('obstacle_alert')
        self.sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.get_logger().info("障碍物告警节点已启动")

    def scan_callback(self, msg):
        min_dist = float('inf')
        for i, r in enumerate(msg.ranges):
            if msg.range_min < r < msg.range_max:
                angle = msg.angle_min + i * msg.angle_increment
                if abs(angle) < math.radians(30):
                    if r < min_dist: min_dist = r
        alert = min_dist < 0.5
        self.mqtt_client.publish(MQTT_TOPIC, json.dumps({"obstacle": alert}))
        if alert:
            self.get_logger().warn(f"障碍物告警: {min_dist:.2f}m")

def main():
    rclpy.init()
    node = ObstacleAlert()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()