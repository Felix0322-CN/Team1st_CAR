#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
import math, time, subprocess, os

class SimplePatrol(Node):
    def __init__(self):
        super().__init__('simple_patrol')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.obstacle = False
        self.min_dist = float('inf')
        self.stuck_count = 0
        self.recovering = False
        self.turn_direction = 1
        self.get_logger().info("巡检启动（脱困版）")
        subprocess.run(["pkill", "lidar_avoider"], capture_output=True)
        time.sleep(0.5)
        self.get_logger().info("避障节点已停")

    def scan_callback(self, msg):
        if self.recovering: return
        min_dist = float('inf')
        for i, r in enumerate(msg.ranges):
            if msg.range_min < r < msg.range_max:
                angle = msg.angle_min + i * msg.angle_increment
                if abs(angle) < math.radians(30):
                    if r < min_dist: min_dist = r
        self.min_dist = min_dist
        self.obstacle = min_dist < 0.5

    def recover(self):
        self.recovering = True
        twist = Twist()
        self.get_logger().info("脱困: 后退")
        twist.linear.x = -0.15; self.pub.publish(twist); time.sleep(1.5); self.pub.publish(Twist())
        direction = self.turn_direction
        self.get_logger().info(f"脱困转向: {'左转' if direction<0 else '右转'}")
        twist.angular.z = 0.5 * direction; self.pub.publish(twist); time.sleep(2.5); self.pub.publish(Twist())
        self.turn_direction *= -1
        twist.linear.x = 0.15; self.pub.publish(twist); time.sleep(0.5); self.pub.publish(Twist())
        self.stuck_count = 0; self.obstacle = False; self.recovering = False

    def run(self):
        twist = Twist()
        self.get_logger().info("等待激光雷达数据...")
        start = time.time()
        while time.time() - start < 5:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.min_dist != float('inf'): break
        self.get_logger().info("开始巡检循环")
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.obstacle:
                self.stuck_count += 1
                if self.stuck_count >= 3: self.recover()
                else:
                    twist.linear.x = 0.0; twist.angular.z = 0.5; self.pub.publish(twist); time.sleep(1.8)
                    twist.linear.x = 0.15; twist.angular.z = 0.0; self.pub.publish(twist); time.sleep(0.3)
                    self.obstacle = False
            else:
                self.stuck_count = 0
                twist.linear.x = 0.15; twist.angular.z = 0.0; self.pub.publish(twist); time.sleep(0.1)
        self.pub.publish(Twist())

    def destroy_node(self):
        self.get_logger().info("巡检结束，恢复避障")
        subprocess.run(["ros2", "run", "lidar_avoider", "lidar_avoider"], cwd="/home/rock/astra_ws")
        super().destroy_node()

def main():
    rclpy.init()
    node = SimplePatrol()
    try: node.run()
    except KeyboardInterrupt: pass
    finally: node.destroy_node(); rclpy.shutdown()

if __name__ == '__main__':
    main()