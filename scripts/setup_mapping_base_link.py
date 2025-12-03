#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建图模式下的 base_link 和 camera_init 初始化脚本
功能：在建图模式下，发布 base_link 和 camera_init 的正确 TF 关系
camera_init 的高度 = base_link 高度 + base_link 到摄像头的高度
"""

import rospy
import tf2_ros
import geometry_msgs.msg
import time

class MappingBaseLinkSetup:
    def __init__(self):
        rospy.init_node('mapping_base_link_setup', anonymous=True)
        
        # 获取参数
        self.base_link_height = rospy.get_param('~base_link_height', 0.25)  # base_link 距离地面的高度（米）
        self.camera_offset_x = rospy.get_param('~camera_offset_x', 0.4)  # 相机在 base_link 前方（米）
        self.camera_offset_y = rospy.get_param('~camera_offset_y', 0.0)  # 相机在 base_link 左右（米）
        self.camera_offset_z = rospy.get_param('~camera_offset_z', 0.8)  # 相机在 base_link 上方（米）
        
        # TF 相关
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.tf_broadcaster = tf2_ros.StaticTransformBroadcaster()
        
        # 等待 FAST-LIVO2 创建 camera_init
        rospy.sleep(3.0)
        
        # 发布 base_link 和 camera_init 的 TF
        self.setup_transforms()
        
        rospy.loginfo("=" * 60)
        rospy.loginfo("建图模式 base_link 和 camera_init 初始化完成")
        rospy.loginfo("=" * 60)
        rospy.loginfo("base_link 高度: %.3f m（距离地面）", self.base_link_height)
        rospy.loginfo("相机偏移: (%.3f, %.3f, %.3f) m（相对于 base_link）", 
                     self.camera_offset_x, self.camera_offset_y, self.camera_offset_z)
        rospy.loginfo("camera_init 高度: %.3f m（base_link 高度 + 相机高度）", 
                     self.base_link_height + self.camera_offset_z)
        rospy.loginfo("=" * 60)
    
    def setup_transforms(self):
        """设置 base_link 和 camera_init 的 TF"""
        transforms = []
        
        try:
            # 获取 camera_init 的当前位置
            try:
                # 尝试从 odom 或 world 获取 camera_init 位置
                transform = self.tf_buffer.lookup_transform('odom', 'camera_init', rospy.Time(0), timeout=rospy.Duration(1.0))
                camera_init_x = transform.transform.translation.x
                camera_init_y = transform.transform.translation.y
                camera_init_z = transform.transform.translation.z
                rospy.loginfo("检测到 camera_init 位置: (%.3f, %.3f, %.3f)", camera_init_x, camera_init_y, camera_init_z)
            except:
                # 如果获取不到，假设 camera_init 在原点
                camera_init_x = 0.0
                camera_init_y = 0.0
                camera_init_z = 0.0
                rospy.loginfo("无法获取 camera_init 位置，使用原点 (0, 0, 0)")
            
            # 计算 base_link 的位置
            # base_link 位置 = camera_init 位置 - (camera_offset_x, camera_offset_y, camera_offset_z)
            base_link_x = camera_init_x - self.camera_offset_x
            base_link_y = camera_init_y - self.camera_offset_y
            base_link_z = camera_init_z - self.camera_offset_z
            
            # 但是，在建图模式下，camera_init 的原点就是建图开始时的传感器位置
            # 如果传感器位置正确（高度 = base_link_height + camera_offset_z），那么：
            # - camera_init.z 应该 = base_link_height + camera_offset_z
            # - base_link.z 应该 = base_link_height
            
            # 发布 camera_init -> base_link 的 TF
            t_base_link = geometry_msgs.msg.TransformStamped()
            t_base_link.header.stamp = rospy.Time.now()
            t_base_link.header.frame_id = "camera_init"
            t_base_link.child_frame_id = "base_link"
            t_base_link.transform.translation.x = -self.camera_offset_x  # base_link 在 camera_init 后方
            t_base_link.transform.translation.y = -self.camera_offset_y  # base_link 在 camera_init 左右中心
            t_base_link.transform.translation.z = -self.camera_offset_z  # base_link 在 camera_init 下方
            t_base_link.transform.rotation.x = 0.0
            t_base_link.transform.rotation.y = 0.0
            t_base_link.transform.rotation.z = 0.0
            t_base_link.transform.rotation.w = 1.0
            transforms.append(t_base_link)
            
            rospy.loginfo("发布 camera_init -> base_link TF:")
            rospy.loginfo("  偏移: (%.3f, %.3f, %.3f)", 
                         -self.camera_offset_x, -self.camera_offset_y, -self.camera_offset_z)
            
        except Exception as e:
            rospy.logerr("设置 TF 时出错: %s", str(e))
            import traceback
            traceback.print_exc()
        
        if transforms:
            self.tf_broadcaster.sendTransform(transforms)
            rospy.loginfo("已发布 %d 个 TF 变换", len(transforms))
    
    def run(self):
        """运行节点"""
        rospy.spin()

if __name__ == '__main__':
    try:
        setup = MappingBaseLinkSetup()
        setup.run()
    except rospy.ROSInterruptException:
        pass

