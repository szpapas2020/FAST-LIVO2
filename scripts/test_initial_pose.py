#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试初始位姿设置功能
用于验证 2D Pose Estimate 是否正常工作
"""

import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped
import math

def test_initial_pose():
    """测试发布初始位姿"""
    rospy.init_node('test_initial_pose', anonymous=True)
    
    pub = rospy.Publisher('/initialpose', PoseWithCovarianceStamped, queue_size=1)
    
    rospy.sleep(1.0)  # 等待订阅者连接
    
    # 创建测试消息
    msg = PoseWithCovarianceStamped()
    msg.header.stamp = rospy.Time.now()
    msg.header.frame_id = "camera_init"  # 使用 FAST-LIVO2 的地图坐标系
    
    # 设置位置（示例：x=1.0, y=2.0, z=0.0）
    msg.pose.pose.position.x = 1.0
    msg.pose.pose.position.y = 2.0
    msg.pose.pose.position.z = 0.0
    
    # 设置朝向（示例：yaw=45度）
    yaw = math.radians(45.0)
    msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
    msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
    
    # 设置协方差（位置不确定性）
    msg.pose.covariance[0] = 0.25  # x
    msg.pose.covariance[7] = 0.25  # y
    msg.pose.covariance[35] = 0.06853891945200942  # yaw (约15度)
    
    print("=" * 60)
    print("发布测试初始位姿消息...")
    print("Position: x=%.3f, y=%.3f, z=%.3f" % (msg.pose.pose.position.x, 
                                                msg.pose.pose.position.y,
                                                msg.pose.pose.position.z))
    print("Orientation: yaw=%.1f°" % math.degrees(yaw))
    print("Frame ID: %s" % msg.header.frame_id)
    print("=" * 60)
    
    # 发布消息
    pub.publish(msg)
    rospy.sleep(0.5)
    
    print("消息已发布！请检查 initial_pose_handler 节点的输出。")
    print("如果看到 'Initial pose set successfully!' 说明功能正常。")

if __name__ == '__main__':
    try:
        test_initial_pose()
    except rospy.ROSInterruptException:
        pass

