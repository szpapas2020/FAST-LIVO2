#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCD 地图发布节点（简化版，使用 open3d）
功能：加载 PCD 文件并发布为 ROS PointCloud2 话题，用于重定位模式下的地图显示
"""

import rospy
import open3d as o3d
import numpy as np
from sensor_msgs.msg import PointCloud2
from sensor_msgs import point_cloud2
from std_msgs.msg import Header
import os
import sys

class PCDMapPublisher:
    def __init__(self):
        rospy.init_node('pcd_map_publisher', anonymous=True)
        
        # 获取参数
        self.pcd_file = rospy.get_param('~pcd_file', 
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                        'Log/PCD/all_downsampled_points.pcd'))
        self.frame_id = rospy.get_param('~frame_id', 'camera_init')
        self.topic_name = rospy.get_param('~topic', '/pcd_map')
        self.publish_rate = rospy.get_param('~rate', 1.0)  # 发布频率 (Hz)
        self.voxel_size = rospy.get_param('~voxel_size', 0.1)  # 体素降采样大小（米），0表示不降采样
        self.max_points = rospy.get_param('~max_points', 5000000)  # 最大点数，超过则强制降采样
        
        # 检查文件是否存在
        if not os.path.exists(self.pcd_file):
            rospy.logerr("PCD file not found: %s", self.pcd_file)
            sys.exit(1)
        
        rospy.loginfo("Loading PCD file: %s", self.pcd_file)
        
        # 加载 PCD 文件
        try:
            self.pcd = o3d.io.read_point_cloud(self.pcd_file)
            if len(self.pcd.points) == 0:
                rospy.logerr("PCD file is empty!")
                sys.exit(1)
            
            num_points = len(self.pcd.points)
            rospy.loginfo("Loaded point cloud with %d points", num_points)
            
            # 如果点数过多，进行降采样
            if num_points > self.max_points or self.voxel_size > 0:
                rospy.loginfo("Downsampling point cloud...")
                if self.voxel_size > 0:
                    # 使用体素降采样
                    self.pcd = self.pcd.voxel_down_sample(voxel_size=self.voxel_size)
                    rospy.loginfo("Voxel downsampled to %d points (voxel_size=%.3f)", len(self.pcd.points), self.voxel_size)
                elif num_points > self.max_points:
                    # 如果点数仍然超过限制，使用更大的体素大小
                    target_voxel_size = (num_points / self.max_points) ** (1.0/3.0) * 0.1
                    self.pcd = self.pcd.voxel_down_sample(voxel_size=target_voxel_size)
                    rospy.loginfo("Auto downsampled to %d points (auto voxel_size=%.3f)", len(self.pcd.points), target_voxel_size)
            
            # 检查是否有颜色信息
            self.has_colors = self.pcd.has_colors()
            if self.has_colors:
                rospy.loginfo("Point cloud has RGB color information")
            else:
                rospy.loginfo("Point cloud has no color information")
                
        except Exception as e:
            rospy.logerr("Failed to load PCD file: %s", str(e))
            sys.exit(1)
        
        # 创建发布者
        self.pub = rospy.Publisher(self.topic_name, PointCloud2, queue_size=1, latch=True)
        
        # 创建定时器
        self.timer = rospy.Timer(rospy.Duration(1.0 / self.publish_rate), self.publish_map)
        
        rospy.loginfo("PCD map publisher started")
        rospy.loginfo("Publishing to topic: %s", self.topic_name)
        rospy.loginfo("Frame ID: %s", self.frame_id)
        rospy.loginfo("Publish rate: %.2f Hz", self.publish_rate)
        
        # 立即发布一次
        self.publish_map(None)
    
    def publish_map(self, event):
        """发布点云地图"""
        try:
            # 获取点云数据
            points = np.asarray(self.pcd.points)
            
            # 创建点云消息
            # 注意：地图固定在 map 坐标系中，map 的原点对应 PCD 文件的原点（建图时 camera_init 的原点）
            # 地图不会随传感器移动，始终保持固定在 map 坐标系的原点
            header = Header()
            header.stamp = rospy.Time.now()
            header.frame_id = self.frame_id  # 应该是 'map'（固定坐标系，对应 PCD 原点）
            
            if self.has_colors:
                # 有颜色信息，创建 RGB 点云
                colors = np.asarray(self.pcd.colors)
                # Open3D 的颜色范围是 [0, 1]，需要转换为 [0, 255]
                colors_uint8 = (colors * 255).astype(np.uint8)
                
                # 创建点云数据列表（使用 PointXYZRGB 格式）
                # 使用打包的 RGB 格式（UINT32，格式：0xAABBGGRR）
                points_list = []
                for i in range(len(points)):
                    x, y, z = points[i]
                    r, g, b = colors_uint8[i]
                    # 打包 RGB 为 UINT32 格式：0xAABBGGRR (A=255, B, G, R)
                    rgb_packed = (255 << 24) | (int(b) << 16) | (int(g) << 8) | int(r)
                    points_list.append([x, y, z, rgb_packed])
                
                # 创建 PointCloud2 消息（RGB 格式，使用打包的 rgb 字段）
                fields = [
                    point_cloud2.PointField('x', 0, point_cloud2.PointField.FLOAT32, 1),
                    point_cloud2.PointField('y', 4, point_cloud2.PointField.FLOAT32, 1),
                    point_cloud2.PointField('z', 8, point_cloud2.PointField.FLOAT32, 1),
                    point_cloud2.PointField('rgb', 12, point_cloud2.PointField.UINT32, 1),
                ]
                cloud_msg = point_cloud2.create_cloud(header, fields, points_list)
            else:
                # 无颜色信息，创建普通点云
                points_list = [[p[0], p[1], p[2]] for p in points]
                cloud_msg = point_cloud2.create_cloud_xyz32(header, points_list)
            
            self.pub.publish(cloud_msg)
            rospy.loginfo("Published point cloud with %d points", len(points))
        except Exception as e:
            rospy.logerr("Error publishing point cloud: %s", str(e))
            import traceback
            rospy.logerr(traceback.format_exc())

if __name__ == '__main__':
    try:
        publisher = PCDMapPublisher()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

