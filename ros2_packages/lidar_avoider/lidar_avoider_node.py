#!/usr/bin/env python3
import rclpy, math
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist

class LidarAvoider(Node):
    def __init__(self):
        super().__init__('lidar_avoider')
        self.sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info("避障节点已启动（纯拦截）")

    def scan_callback(self, msg):
        min_dist = float('inf')
        for i, r in enumerate(msg.ranges):
            if msg.range_min < r < msg.range_max:
                angle = msg.angle_min + i * msg.angle_increment
                if abs(angle) < math.radians(30):
                    if r < min_dist: min_dist = r
        if min_dist < 0.5:
            self.pub.publish(Twist())
            self.get_logger().warn(f"障碍物 {min_dist:.2f}m，急停", throttle_duration_sec=1.0)

def main():
    rclpy.init()
    node = LidarAvoider()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()