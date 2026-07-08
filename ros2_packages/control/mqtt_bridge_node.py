#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import paho.mqtt.client as mqtt
import json

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_CMD = "robot/cmd"

class MqttBridgeNode(Node):
    def __init__(self):
        super().__init__('mqtt_bridge_node')
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt_client.loop_start()
        self.get_logger().info("MQTT桥接节点已启动")

    def _on_connect(self, client, userdata, flags, rc):
        client.subscribe(MQTT_TOPIC_CMD)
        self.get_logger().info(f"已订阅 {MQTT_TOPIC_CMD}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            twist = Twist()
            twist.linear.x = float(payload.get('x', 0.0))
            twist.angular.z = float(payload.get('z', 0.0))
            self.publisher.publish(twist)
        except Exception as e:
            self.get_logger().error(f"解析失败: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = MqttBridgeNode()
    rclpy.spin(node)
    node.mqtt_client.loop_stop()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()