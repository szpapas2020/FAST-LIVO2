#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查激光雷达和图像的时间同步状态
监控时间戳差异，诊断同步问题
"""

import rospy
from sensor_msgs.msg import Image, PointCloud2
from nav_msgs.msg import Odometry
import numpy as np
from collections import deque

class TimeSyncChecker:
    def __init__(self):
        rospy.init_node('time_sync_checker', anonymous=True)
        
        # 数据缓冲区
        self.lidar_timestamps = deque(maxlen=100)
        self.img_timestamps = deque(maxlen=100)
        self.imu_timestamps = deque(maxlen=100)
        
        # 统计信息
        self.lidar_count = 0
        self.img_count = 0
        self.imu_count = 0
        
        # 订阅话题（使用通用消息类型）
        rospy.Subscriber('/livox/lidar', rospy.AnyMsg, self.lidar_callback)
        rospy.Subscriber('/left_camera/image', Image, self.img_callback)
        rospy.Subscriber('/livox/imu', rospy.AnyMsg, self.imu_callback)
        rospy.Subscriber('/aft_mapped_to_init', Odometry, self.odom_callback)
        
        # 配置参数
        self.img_time_offset = rospy.get_param('~img_time_offset', 0.1)
        self.exposure_time_init = rospy.get_param('~exposure_time_init', 0.0)
        
        rospy.loginfo("=" * 70)
        rospy.loginfo("激光雷达与图像时间同步检查工具")
        rospy.loginfo("=" * 70)
        rospy.loginfo("配置参数:")
        rospy.loginfo("  - img_time_offset: %.6f 秒", self.img_time_offset)
        rospy.loginfo("  - exposure_time_init: %.6f 秒", self.exposure_time_init)
        rospy.loginfo("=" * 70)
        
        # 等待数据积累
        rospy.sleep(3.0)
        
        # 定时检查
        self.timer = rospy.Timer(rospy.Duration(2.0), self.check_sync)
    
    def lidar_callback(self, msg):
        """激光雷达回调"""
        self.lidar_count += 1
        try:
            # 尝试获取时间戳
            if hasattr(msg, 'header'):
                timestamp = msg.header.stamp.to_sec()
                self.lidar_timestamps.append({
                    'time': timestamp,
                    'raw_time': timestamp,
                    'count': self.lidar_count
                })
        except:
            pass
    
    def img_callback(self, msg):
        """图像回调"""
        self.img_count += 1
        raw_timestamp = msg.header.stamp.to_sec()
        # 应用时间偏移（与LIVMapper.cpp中的逻辑一致）
        corrected_timestamp = raw_timestamp + self.img_time_offset
        img_capture_time = corrected_timestamp + self.exposure_time_init
        
        self.img_timestamps.append({
            'time': img_capture_time,
            'raw_time': raw_timestamp,
            'corrected_time': corrected_timestamp,
            'count': self.img_count
        })
    
    def imu_callback(self, msg):
        """IMU回调"""
        self.imu_count += 1
        # 尝试获取时间戳
        try:
            if hasattr(msg, 'header'):
                timestamp = msg.header.stamp.to_sec()
                self.imu_timestamps.append({
                    'time': timestamp,
                    'count': self.imu_count
                })
        except:
            pass
    
    def odom_callback(self, msg):
        """里程计回调（用于检查处理时间）"""
        pass
    
    def check_sync(self, event):
        """检查同步状态"""
        rospy.loginfo("\n" + "=" * 70)
        rospy.loginfo("📊 时间同步状态检查 (时间: %.2f)", rospy.Time.now().to_sec())
        rospy.loginfo("=" * 70)
        
        # 数据统计
        rospy.loginfo("\n📈 数据流统计:")
        rospy.loginfo("  - 激光雷达消息: %d 条", self.lidar_count)
        rospy.loginfo("  - 图像消息: %d 条", self.img_count)
        rospy.loginfo("  - IMU消息: %d 条", self.imu_count)
        
        # 检查时间戳
        if len(self.lidar_timestamps) > 0 and len(self.img_timestamps) > 0:
            rospy.loginfo("\n⏱️  时间戳分析:")
            
            # 最新时间戳
            latest_lidar = self.lidar_timestamps[-1]
            latest_img = self.img_timestamps[-1]
            
            rospy.loginfo("\n  最新时间戳:")
            rospy.loginfo("  - 激光雷达: %.6f (原始: %.6f)", 
                         latest_lidar['time'], latest_lidar['raw_time'])
            rospy.loginfo("  - 图像: %.6f (原始: %.6f, 修正后: %.6f, 捕获时间: %.6f)", 
                         latest_img['time'], latest_img['raw_time'], 
                         latest_img['corrected_time'], latest_img['time'])
            
            # 时间差
            time_diff = latest_img['time'] - latest_lidar['time']
            rospy.loginfo("  - 时间差 (图像-激光): %.6f 秒 (%.1f 毫秒)", 
                         time_diff, time_diff * 1000)
            
            # 频率检查
            if len(self.lidar_timestamps) >= 2:
                lidar_dt = self.lidar_timestamps[-1]['time'] - self.lidar_timestamps[-2]['time']
                lidar_freq = 1.0 / lidar_dt if lidar_dt > 0 else 0
                rospy.loginfo("  - 激光雷达频率: %.2f Hz (间隔: %.3f 秒)", lidar_freq, lidar_dt)
            
            if len(self.img_timestamps) >= 2:
                img_dt = self.img_timestamps[-1]['raw_time'] - self.img_timestamps[-2]['raw_time']
                img_freq = 1.0 / img_dt if img_dt > 0 else 0
                rospy.loginfo("  - 图像频率: %.2f Hz (间隔: %.3f 秒)", img_freq, img_dt)
            
            # 时间差统计
            if len(self.lidar_timestamps) >= 10 and len(self.img_timestamps) >= 10:
                rospy.loginfo("\n📊 时间差统计 (最近10帧):")
                time_diffs = []
                for lidar_ts in list(self.lidar_timestamps)[-10:]:
                    # 找到最接近的图像时间戳
                    closest_img = min(self.img_timestamps, 
                                    key=lambda x: abs(x['time'] - lidar_ts['time']))
                    diff = closest_img['time'] - lidar_ts['time']
                    time_diffs.append(diff)
                
                if time_diffs:
                    mean_diff = np.mean(time_diffs)
                    std_diff = np.std(time_diffs)
                    min_diff = np.min(time_diffs)
                    max_diff = np.max(time_diffs)
                    
                    rospy.loginfo("  - 平均时间差: %.6f 秒 (%.1f 毫秒)", mean_diff, mean_diff * 1000)
                    rospy.loginfo("  - 标准差: %.6f 秒 (%.1f 毫秒)", std_diff, std_diff * 1000)
                    rospy.loginfo("  - 最小时间差: %.6f 秒 (%.1f 毫秒)", min_diff, min_diff * 1000)
                    rospy.loginfo("  - 最大时间差: %.6f 秒 (%.1f 毫秒)", max_diff, max_diff * 1000)
            
            # 同步诊断
            rospy.loginfo("\n💡 同步诊断:")
            if abs(time_diff) < 0.01:
                rospy.loginfo("  ✅ 时间同步良好 (差异 < 10ms)")
            elif abs(time_diff) < 0.05:
                rospy.logwarn("  ⚠️  时间同步可接受 (差异 < 50ms)")
            elif abs(time_diff) < 0.1:
                rospy.logwarn("  ⚠️  时间同步较差 (差异 < 100ms)")
            else:
                rospy.logerr("  ❌ 时间同步差 (差异 >= 100ms)")
                rospy.logwarn("     建议:")
                rospy.logwarn("     1. 检查 img_time_offset 参数 (当前: %.3f)", self.img_time_offset)
                rospy.logwarn("     2. 检查 exposure_time_init 参数 (当前: %.3f)", self.exposure_time_init)
                rospy.logwarn("     3. 检查传感器硬件时钟同步")
        else:
            rospy.logwarn("\n⚠️  数据不足:")
            if len(self.lidar_timestamps) == 0:
                rospy.logwarn("  - 没有激光雷达数据")
            if len(self.img_timestamps) == 0:
                rospy.logwarn("  - 没有图像数据")
        
        rospy.loginfo("\n" + "=" * 70)

if __name__ == '__main__':
    try:
        checker = TimeSyncChecker()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

