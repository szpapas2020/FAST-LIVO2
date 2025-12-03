#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PCD 地图发布节点
功能：加载 PCD 文件并发布为 ROS PointCloud2 话题，用于重定位模式下的地图显示
"""

import rospy
import pcl
import pcl_helper
import sensor_msgs.msg
from sensor_msgs.msg import PointCloud2
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
        
        # 检查文件是否存在
        if not os.path.exists(self.pcd_file):
            rospy.logerr("PCD file not found: %s", self.pcd_file)
            sys.exit(1)
        
        rospy.loginfo("Loading PCD file: %s", self.pcd_file)
        
        # 加载 PCD 文件
        try:
            # 尝试加载为 RGB 点云
            try:
                self.cloud = pcl.PointCloud_PointXYZRGB()
                pcl.load(self.pcd_file, self.cloud)
                rospy.loginfo("Loaded RGB point cloud with %d points", self.cloud.size())
                self.has_rgb = True
            except:
                # 如果失败，尝试加载为普通点云
                self.cloud = pcl.PointCloud()
                pcl.load(self.pcd_file, self.cloud)
                rospy.loginfo("Loaded point cloud with %d points", self.cloud.size())
                self.has_rgb = False
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
            if self.has_rgb:
                cloud_msg = pcl_helper.toROS(self.cloud, self.frame_id, rospy.Time.now())
            else:
                # 转换为 PointXYZI 格式
                cloud_xyz = pcl.PointCloud()
                for i in range(self.cloud.size()):
                    pt = self.cloud[i]
                    cloud_xyz.push_back(pcl.PointXYZ(pt[0], pt[1], pt[2]))
                cloud_msg = pcl_helper.toROS(cloud_xyz, self.frame_id, rospy.Time.now())
            
            self.pub.publish(cloud_msg)
            rospy.logdebug("Published point cloud with %d points", len(self.cloud))
        except Exception as e:
            rospy.logerr("Error publishing point cloud: %s", str(e))

if __name__ == '__main__':
    try:
        publisher = PCDMapPublisher()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

