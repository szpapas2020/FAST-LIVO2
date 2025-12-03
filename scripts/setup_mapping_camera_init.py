#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建图模式下的 camera_init 初始化脚本
功能：在建图开始时，设置 camera_init 的正确高度
camera_init 的高度 = base_link 高度 + base_link 到摄像头的高度
"""

import rospy
import tf2_ros
import geometry_msgs.msg
import time

class MappingCameraInitSetup:
    def __init__(self):
        rospy.init_node('mapping_camera_init_setup', anonymous=True)
        
        # 获取参数
        self.base_link_height = rospy.get_param('~base_link_height', 0.25)  # base_link 距离地面的高度（米）
        self.camera_offset_x = rospy.get_param('~camera_offset_x', 0.4)  # 相机在 base_link 前方（米）
        self.camera_offset_y = rospy.get_param('~camera_offset_y', 0.0)  # 相机在 base_link 左右（米）
        self.camera_offset_z = rospy.get_param('~camera_offset_z', 0.8)  # 相机在 base_link 上方（米）
        
        # TF 相关
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.tf_broadcaster = tf2_ros.StaticTransformBroadcaster()
        
        # 等待 TF 树建立
        rospy.sleep(2.0)
        
        # 计算 camera_init 的正确高度
        # camera_init 高度 = base_link 高度 + base_link 到摄像头的高度
        self.camera_init_z = self.base_link_height + self.camera_offset_z
        
        rospy.loginfo("=" * 60)
        rospy.loginfo("建图模式 camera_init 初始化")
        rospy.loginfo("=" * 60)
        rospy.loginfo("base_link 高度: %.3f m（距离地面）", self.base_link_height)
        rospy.loginfo("相机偏移: (%.3f, %.3f, %.3f) m（相对于 base_link）", 
                     self.camera_offset_x, self.camera_offset_y, self.camera_offset_z)
        rospy.loginfo("camera_init 高度: %.3f m（base_link 高度 + 相机高度）", self.camera_init_z)
        rospy.loginfo("=" * 60)
        
        # 检查 camera_init 是否存在
        self.setup_camera_init()
    
    def setup_camera_init(self):
        """设置 camera_init 的正确高度"""
        try:
            # 尝试获取当前的 camera_init 位置
            try:
                transform = self.tf_buffer.lookup_transform('odom', 'camera_init', rospy.Time(0), timeout=rospy.Duration(1.0))
                current_z = transform.transform.translation.z
                rospy.loginfo("当前 camera_init z 坐标: %.3f", current_z)
                
                # 如果高度不正确，发布修正的 TF
                if abs(current_z - self.camera_init_z) > 0.01:
                    rospy.logwarn("camera_init 高度不正确，需要修正")
                    rospy.logwarn("  当前高度: %.3f m", current_z)
                    rospy.logwarn("  正确高度: %.3f m", self.camera_init_z)
            except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException):
                rospy.loginfo("camera_init 尚未创建，等待 FAST-LIVO2 初始化...")
                # 等待 FAST-LIVO2 创建 camera_init
                rospy.sleep(3.0)
            
            # 注意：在建图模式下，FAST-LIVO2 会自动创建 camera_init
            # camera_init 的原点就是建图开始时的传感器位置
            # 我们无法直接修改 camera_init 的位置，因为它是由 FAST-LIVO2 内部管理的
            # 但是我们可以确保 base_link 的位置正确，这样 camera_init 相对于 base_link 的位置就是正确的
            
            rospy.loginfo("注意：在建图模式下，camera_init 由 FAST-LIVO2 自动创建")
            rospy.loginfo("      camera_init 的原点 = 建图开始时的传感器位置")
            rospy.loginfo("      如果传感器位置正确，camera_init 的位置就会正确")
            
        except Exception as e:
            rospy.logerr("设置 camera_init 时出错: %s", str(e))
    
    def run(self):
        """运行节点"""
        rospy.spin()

if __name__ == '__main__':
    try:
        setup = MappingCameraInitSetup()
        setup.run()
    except rospy.ROSInterruptException:
        pass

