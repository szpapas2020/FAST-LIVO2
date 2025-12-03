#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时时间同步监控工具
功能：实时显示图像和激光雷达时间戳差异，帮助诊断同步问题
"""

import rospy
import numpy as np
from collections import deque
from sensor_msgs.msg import Image
import sys

# 尝试导入 Livox 消息类型
try:
    import livox_ros_driver2.msg as livox_msg
    CustomMsg = livox_msg.CustomMsg
except ImportError:
    try:
        import livox_ros_driver.msg as livox_msg
        CustomMsg = livox_msg.CustomMsg
    except ImportError:
        rospy.logerr("无法导入 Livox 消息类型，请检查 livox_ros_driver 或 livox_ros_driver2 是否安装")
        sys.exit(1)

class TimeSyncMonitor:
    def __init__(self):
        rospy.init_node('monitor_time_sync_realtime', anonymous=True)
        
        # 数据缓冲区
        self.lidar_timestamps = deque(maxlen=100)
        self.img_timestamps = deque(maxlen=100)
        self.time_diffs = deque(maxlen=100)
        
        # 统计信息
        self.lidar_count = 0
        self.img_count = 0
        
        # 订阅话题
        rospy.Subscriber('/livox/lidar', CustomMsg, self.lidar_callback)
        rospy.Subscriber('/left_camera/image', Image, self.img_callback)
        
        # 配置参数
        self.img_time_offset = rospy.get_param('/laserMapping/time_offset/img_time_offset', 0.0)
        
        rospy.loginfo("=" * 70)
        rospy.loginfo("实时时间同步监控工具")
        rospy.loginfo("=" * 70)
        rospy.loginfo("当前配置: img_time_offset = %.6f 秒", self.img_time_offset)
        rospy.loginfo("=" * 70)
        rospy.loginfo("实时监控中... (Ctrl+C 退出)")
        rospy.loginfo("=" * 70)
        
        # 定时显示统计信息
        self.timer = rospy.Timer(rospy.Duration(2.0), self.print_statistics)
    
    def lidar_callback(self, msg):
        """激光雷达回调"""
        self.lidar_count += 1
        timestamp = msg.header.stamp.to_sec()
        self.lidar_timestamps.append(timestamp)
    
    def img_callback(self, msg):
        """图像回调"""
        self.img_count += 1
        raw_timestamp = msg.header.stamp.to_sec()
        corrected_timestamp = raw_timestamp + self.img_time_offset
        
        self.img_timestamps.append({
            'raw': raw_timestamp,
            'corrected': corrected_timestamp
        })
        
        # 如果有激光雷达数据，计算时间差
        if len(self.lidar_timestamps) > 0:
            lidar_time = self.lidar_timestamps[-1]
            time_diff = corrected_timestamp - lidar_time
            self.time_diffs.append(time_diff)
            
            # 实时显示
            status = "✅" if abs(time_diff) < 0.01 else "⚠️" if abs(time_diff) < 0.1 else "❌"
            print(f"\r{status} 图像(修正后): {corrected_timestamp:.6f} | "
                  f"激光: {lidar_time:.6f} | "
                  f"时间差: {time_diff*1000:+.1f}ms | "
                  f"图像: {self.img_count} | 激光: {self.lidar_count}", 
                  end="", flush=True)
    
    def print_statistics(self, event):
        """打印统计信息"""
        if len(self.time_diffs) == 0:
            return
        
        time_diffs_array = np.array(self.time_diffs)
        mean_diff = np.mean(time_diffs_array)
        std_diff = np.std(time_diffs_array)
        min_diff = np.min(time_diffs_array)
        max_diff = np.max(time_diffs_array)
        
        print()  # 换行
        print("=" * 70)
        print("统计信息 (最近 %d 个样本):" % len(time_diffs_array))
        print("  平均时间差: %.6f 秒 (%.1f ms)" % (mean_diff, mean_diff * 1000))
        print("  标准差: %.6f 秒 (%.1f ms)" % (std_diff, std_diff * 1000))
        print("  最小值: %.6f 秒 (%.1f ms)" % (min_diff, min_diff * 1000))
        print("  最大值: %.6f 秒 (%.1f ms)" % (max_diff, max_diff * 1000))
        
        # 评估同步状态
        if abs(mean_diff) < 0.01:
            print("  状态: ✅ 同步良好")
        elif abs(mean_diff) < 0.1:
            print("  状态: ⚠️  同步可接受")
        else:
            print("  状态: ❌ 同步不良，建议调整 img_time_offset")
            print("  建议偏移: %.6f 秒" % (-mean_diff))
        print("=" * 70)

if __name__ == '__main__':
    try:
        monitor = TimeSyncMonitor()
        rospy.spin()
    except KeyboardInterrupt:
        print("\n监控已停止")
    except rospy.ROSInterruptException:
        pass

