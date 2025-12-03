#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器人TF变换发布节点
根据机器人的物理结构发布TF变换

机器人结构：
- base_link: 底盘中心（地面）
- camera: 上方1.8m，前方0.4m
- lidar: 与camera标定过（使用标定参数）
- 阿克曼结构：前后轴距1.5m，左右轮距0.9m
"""

import rospy
import tf2_ros
import geometry_msgs.msg
from math import pi

class RobotTFPublisher:
    def __init__(self):
        rospy.init_node('robot_tf_publisher', anonymous=True)
        
        # 获取参数
        self.base_frame = rospy.get_param('~base_frame', 'base_link')
        self.camera_frame = rospy.get_param('~camera_frame', 'camera')
        self.lidar_frame = rospy.get_param('~lidar_frame', 'livox')
        
        # 摄像头位置（相对于base_link）
        # 前方0.4m，上方1.8m
        self.camera_x = rospy.get_param('~camera_x', 0.4)  # 前方
        self.camera_y = rospy.get_param('~camera_y', 0.0)  # 左右（中心）
        self.camera_z = rospy.get_param('~camera_z', 1.8)  # 上方
        self.camera_roll = rospy.get_param('~camera_roll', 0.0)  # 绕X轴
        self.camera_pitch = rospy.get_param('~camera_pitch', 0.0)  # 绕Y轴
        self.camera_yaw = rospy.get_param('~camera_yaw', 0.0)  # 绕Z轴
        
        # 激光雷达位置（如果已知相对于base_link的位置）
        # 如果不知道，可以从camera和标定参数计算
        self.lidar_x = rospy.get_param('~lidar_x', None)
        self.lidar_y = rospy.get_param('~lidar_y', None)
        self.lidar_z = rospy.get_param('~lidar_z', None)
        self.lidar_roll = rospy.get_param('~lidar_roll', 0.0)
        self.lidar_pitch = rospy.get_param('~lidar_pitch', 0.0)
        self.lidar_yaw = rospy.get_param('~lidar_yaw', 0.0)
        
        # 如果lidar位置未指定，尝试从标定参数计算
        # 从FAST-LIVO2配置文件中读取标定参数
        if self.lidar_x is None:
            try:
                # 尝试从参数服务器读取标定参数
                extrin_T = rospy.get_param('/extrin_calib/extrinsic_T', [0.0, 0.0, 0.0])
                # extrinsic_T是lidar相对于camera的平移
                # 需要加上camera相对于base_link的位置
                self.lidar_x = self.camera_x + extrin_T[0]
                self.lidar_y = self.camera_y + extrin_T[1]
                self.lidar_z = self.camera_z + extrin_T[2]
                rospy.loginfo("Using lidar position from calibration: (%.3f, %.3f, %.3f)", 
                            self.lidar_x, self.lidar_y, self.lidar_z)
            except:
                # 如果无法读取，使用默认值（假设lidar在camera附近）
                self.lidar_x = self.camera_x
                self.lidar_y = self.camera_y
                self.lidar_z = self.camera_z
                rospy.logwarn("Could not read calibration parameters, using camera position for lidar")
        
        # TF广播器
        self.tf_broadcaster = tf2_ros.StaticTransformBroadcaster()
        
        # 发布TF变换
        self.publish_transforms()
        
        rospy.loginfo("Robot TF publisher started")
        rospy.loginfo("Base frame: %s", self.base_frame)
        rospy.loginfo("Camera frame: %s at (%.3f, %.3f, %.3f)", 
                     self.camera_frame, self.camera_x, self.camera_y, self.camera_z)
        rospy.loginfo("Lidar frame: %s at (%.3f, %.3f, %.3f)", 
                     self.lidar_frame, self.lidar_x, self.lidar_y, self.lidar_z)
    
    def euler_to_quaternion(self, roll, pitch, yaw):
        """将欧拉角转换为四元数"""
        import math
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        
        q = geometry_msgs.msg.Quaternion()
        q.w = cr * cp * cy + sr * sp * sy
        q.x = sr * cp * cy - cr * sp * sy
        q.y = cr * sp * cy + sr * cp * sy
        q.z = cr * cp * sy - sr * sp * cy
        return q
    
    def publish_transforms(self):
        """发布所有TF变换"""
        transforms = []
        
        # base_link -> camera
        t_camera = geometry_msgs.msg.TransformStamped()
        t_camera.header.stamp = rospy.Time.now()
        t_camera.header.frame_id = self.base_frame
        t_camera.child_frame_id = self.camera_frame
        t_camera.transform.translation.x = self.camera_x
        t_camera.transform.translation.y = self.camera_y
        t_camera.transform.translation.z = self.camera_z
        t_camera.transform.rotation = self.euler_to_quaternion(
            self.camera_roll, self.camera_pitch, self.camera_yaw
        )
        transforms.append(t_camera)
        
        # base_link -> lidar (或 camera -> lidar)
        # 如果lidar位置已知，直接从base_link发布
        # 否则从camera发布（使用标定参数）
        if self.lidar_x is not None and abs(self.lidar_x - self.camera_x) > 0.01:
            # 如果lidar位置与camera明显不同，从base_link发布
            t_lidar = geometry_msgs.msg.TransformStamped()
            t_lidar.header.stamp = rospy.Time.now()
            t_lidar.header.frame_id = self.base_frame
            t_lidar.child_frame_id = self.lidar_frame
            t_lidar.transform.translation.x = self.lidar_x
            t_lidar.transform.translation.y = self.lidar_y
            t_lidar.transform.translation.z = self.lidar_z
            t_lidar.transform.rotation = self.euler_to_quaternion(
                self.lidar_roll, self.lidar_pitch, self.lidar_yaw
            )
            transforms.append(t_lidar)
        else:
            # 如果lidar在camera附近，从camera发布（使用标定参数）
            try:
                extrin_T = rospy.get_param('/extrin_calib/extrinsic_T', [0.0, 0.0, 0.0])
                extrin_R = rospy.get_param('/extrin_calib/extrinsic_R', [1, 0, 0, 0, 1, 0, 0, 0, 1])
                
                t_lidar = geometry_msgs.msg.TransformStamped()
                t_lidar.header.stamp = rospy.Time.now()
                t_lidar.header.frame_id = self.camera_frame
                t_lidar.child_frame_id = self.lidar_frame
                t_lidar.transform.translation.x = extrin_T[0]
                t_lidar.transform.translation.y = extrin_T[1]
                t_lidar.transform.translation.z = extrin_T[2]
                
                # 旋转矩阵转四元数（简化处理，假设主要是平移）
                # 如果需要精确的旋转，需要从旋转矩阵计算四元数
                t_lidar.transform.rotation = self.euler_to_quaternion(
                    self.lidar_roll, self.lidar_pitch, self.lidar_yaw
                )
                transforms.append(t_lidar)
            except:
                rospy.logwarn("Could not read calibration parameters for lidar-camera transform")
        
        # 批量发布所有变换
        self.tf_broadcaster.sendTransform(transforms)
        rospy.loginfo("Published %d TF transforms", len(transforms))

if __name__ == '__main__':
    try:
        publisher = RobotTFPublisher()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

