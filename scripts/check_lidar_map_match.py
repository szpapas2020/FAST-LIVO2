#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断脚本：检查激光雷达实时数据是否在 PCD 地图上

使用方法：
    rosrun fast_livo check_lidar_map_match.py
"""

import rospy
import numpy as np
from sensor_msgs.msg import PointCloud2
import sensor_msgs.point_cloud2 as pc2
from nav_msgs.msg import Odometry
import tf2_ros
import geometry_msgs.msg

class LidarMapMatchChecker:
    def __init__(self):
        rospy.init_node('lidar_map_match_checker', anonymous=True)
        
        # TF 相关
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        
        # 订阅话题
        self.sub_cloud = rospy.Subscriber('/cloud_registered', PointCloud2, self.cloud_callback)
        self.sub_map = rospy.Subscriber('/pcd_map', PointCloud2, self.map_callback)
        self.sub_odom = rospy.Subscriber('/aft_mapped_to_init', Odometry, self.odom_callback)
        
        # 存储数据
        self.latest_cloud = None
        self.latest_map = None
        self.latest_odom = None
        
        # 统计信息
        self.cloud_count = 0
        self.map_count = 0
        self.odom_count = 0
        
        rospy.loginfo("=" * 80)
        rospy.loginfo("激光雷达地图匹配检查工具")
        rospy.loginfo("=" * 80)
        rospy.loginfo("等待数据...")
        
        # 等待数据
        rospy.sleep(3.0)
        
    def cloud_callback(self, msg):
        """接收实时点云"""
        self.latest_cloud = msg
        self.cloud_count += 1
    
    def map_callback(self, msg):
        """接收地图点云"""
        self.latest_map = msg
        self.map_count += 1
    
    def odom_callback(self, msg):
        """接收位姿"""
        self.latest_odom = msg
    
    def check_topics(self):
        """检查话题数据"""
        print("\n" + "=" * 80)
        print("1. 话题数据检查")
        print("=" * 80)
        
        # 检查实时点云
        if self.latest_cloud is None:
            print("✗ 未收到 /cloud_registered 话题数据")
        else:
            print(f"✓ /cloud_registered 话题正常（已接收 {self.cloud_count} 条消息）")
            print(f"  点云点数: {self.latest_cloud.width * self.latest_cloud.height}")
            print(f"  坐标系: {self.latest_cloud.header.frame_id}")
        
        # 检查地图点云
        if self.latest_map is None:
            print("\n✗ 未收到 /pcd_map 话题数据")
        else:
            print(f"\n✓ /pcd_map 话题正常（已接收 {self.map_count} 条消息）")
            print(f"  地图点数: {self.latest_map.width * self.latest_map.height}")
            print(f"  坐标系: {self.latest_map.header.frame_id}")
        
        # 检查位姿
        if self.latest_odom is None:
            print("\n✗ 未收到 /aft_mapped_to_init 话题数据")
        else:
            pos = self.latest_odom.pose.pose.position
            print(f"\n✓ /aft_mapped_to_init 话题正常（已接收 {self.odom_count} 条消息）")
            print(f"  当前位置: ({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})")
    
    def analyze_point_cloud_overlap(self):
        """分析点云重叠情况"""
        print("\n" + "=" * 80)
        print("2. 点云重叠分析")
        print("=" * 80)
        
        if self.latest_cloud is None or self.latest_map is None:
            print("✗ 缺少必要的点云数据，无法进行分析")
            return
        
        try:
            # 获取实时点云的边界框
            cloud_points = list(pc2.read_points(self.latest_cloud, field_names=("x", "y", "z"), skip_nans=True))
            if len(cloud_points) == 0:
                print("✗ 实时点云为空")
                return
            
            cloud_array = np.array(cloud_points)
            cloud_min = np.min(cloud_array, axis=0)
            cloud_max = np.max(cloud_array, axis=0)
            cloud_center = np.mean(cloud_array, axis=0)
            
            print(f"实时点云统计:")
            print(f"  点数: {len(cloud_points)}")
            print(f"  边界框: ({cloud_min[0]:.2f}, {cloud_min[1]:.2f}, {cloud_min[2]:.2f}) 到 ({cloud_max[0]:.2f}, {cloud_max[1]:.2f}, {cloud_max[2]:.2f})")
            print(f"  中心点: ({cloud_center[0]:.2f}, {cloud_center[1]:.2f}, {cloud_center[2]:.2f})")
            
            # 获取地图点云的边界框
            map_points = list(pc2.read_points(self.latest_map, field_names=("x", "y", "z"), skip_nans=True))
            if len(map_points) == 0:
                print("\n✗ 地图点云为空")
                return
            
            map_array = np.array(map_points)
            map_min = np.min(map_array, axis=0)
            map_max = np.max(map_array, axis=0)
            map_center = np.mean(map_array, axis=0)
            
            print(f"\n地图点云统计:")
            print(f"  点数: {len(map_points)}")
            print(f"  边界框: ({map_min[0]:.2f}, {map_min[1]:.2f}, {map_min[2]:.2f}) 到 ({map_max[0]:.2f}, {map_max[1]:.2f}, {map_max[2]:.2f})")
            print(f"  中心点: ({map_center[0]:.2f}, {map_center[1]:.2f}, {map_center[2]:.2f})")
            
            # 检查重叠
            overlap_x = not (cloud_max[0] < map_min[0] or cloud_min[0] > map_max[0])
            overlap_y = not (cloud_max[1] < map_min[1] or cloud_min[1] > map_max[1])
            overlap_z = not (cloud_max[2] < map_min[2] or cloud_min[2] > map_max[2])
            
            print(f"\n重叠分析:")
            print(f"  X 轴重叠: {'✓' if overlap_x else '✗'}")
            print(f"  Y 轴重叠: {'✓' if overlap_y else '✗'}")
            print(f"  Z 轴重叠: {'✓' if overlap_z else '✗'}")
            
            if overlap_x and overlap_y and overlap_z:
                print(f"\n  → 点云边界框有重叠，但需要进一步检查实际匹配情况")
            else:
                print(f"\n  → ⚠️  警告：点云边界框不重叠，实时数据可能不在地图上！")
            
            # 计算中心点距离
            center_distance = np.linalg.norm(cloud_center - map_center)
            print(f"\n中心点距离: {center_distance:.2f} 米")
            
            if center_distance > 10.0:
                print(f"  → ⚠️  警告：中心点距离很大，实时数据可能不在地图上！")
            elif center_distance > 5.0:
                print(f"  → ⚠️  注意：中心点距离较大，请检查初始位姿设置")
            else:
                print(f"  → ✓ 中心点距离正常")
                
        except Exception as e:
            print(f"✗ 分析点云时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def check_icp_matching_quality(self):
        """检查 ICP 匹配质量（通过终端输出）"""
        print("\n" + "=" * 80)
        print("3. ICP 匹配质量检查")
        print("=" * 80)
        print("请查看 FAST-LIVO2 节点的终端输出，查找以下信息：")
        print("\n关键指标：")
        print("  [ LIO ] Raw feature num: <原始特征点数>")
        print("  [ LIO ] downsampled feature num: <降采样后特征点数>")
        print("  [ LIO ] effective feature num: <有效特征点数>")
        print("  [ LIO ] average residual: <平均残差>")
        print("\n判断标准：")
        print("  ✓ 正常：effective feature num > 500, average residual < 0.1 米")
        print("  ⚠️  警告：effective feature num < 100, average residual > 0.3 米")
        print("  ✗ 严重：effective feature num = 0, average residual > 1.0 米")
    
    def provide_recommendations(self):
        """提供建议"""
        print("\n" + "=" * 80)
        print("4. 建议")
        print("=" * 80)
        
        if self.latest_cloud is None or self.latest_map is None:
            print("✗ 无法提供建议，缺少必要的点云数据")
            return
        
        print("如果实时数据不在地图上，建议采取以下措施：")
        print("\n1. 重新设置初始位姿（推荐）")
        print("   - 在 RViz 中使用 2D Pose Estimate 重新设置")
        print("   - 确保初始位姿尽可能准确")
        print("   - 观察 effective feature num 是否增加")
        print("\n2. 检查地图范围")
        print("   - 确保机器人在地图覆盖范围内")
        print("   - 如果超出范围，需要扩展地图或重新建图")
        print("\n3. 重新建图")
        print("   - 如果地图与当前环境不匹配，使用建图模式重新生成")
        print("\n4. 调整 ICP 匹配参数")
        print("   - 修改 config/mid360_relocalization.yaml 中的 lio 参数")
        print("   - 增加 max_iterations，调整 voxel_size 等")
    
    def run_check(self):
        """运行完整检查"""
        # 1. 检查话题
        self.check_topics()
        
        # 2. 分析点云重叠
        self.analyze_point_cloud_overlap()
        
        # 3. 检查 ICP 匹配质量
        self.check_icp_matching_quality()
        
        # 4. 提供建议
        self.provide_recommendations()
        
        print("\n" + "=" * 80)
        print("检查完成")
        print("=" * 80)
        print("详细分析请参考: docs/lidar_not_on_map_behavior.md")
        print("=" * 80)

if __name__ == '__main__':
    try:
        checker = LidarMapMatchChecker()
        checker.run_check()
    except rospy.ROSInterruptException:
        pass

