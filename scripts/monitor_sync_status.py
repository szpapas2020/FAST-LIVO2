#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控FAST-LIVO2数据同步状态
实时显示缓冲区状态和同步信息
"""

import rospy
import subprocess
import re
from collections import deque

class SyncStatusMonitor:
    def __init__(self):
        rospy.init_node('sync_status_monitor', anonymous=True)
        
        self.log_file = None
        self.find_log_file()
        
        rospy.loginfo("=" * 70)
        rospy.loginfo("FAST-LIVO2 数据同步状态监控")
        rospy.loginfo("=" * 70)
        
        if self.log_file:
            rospy.loginfo("日志文件: %s", self.log_file)
        else:
            rospy.logwarn("未找到日志文件，将监控rosout")
        
        rospy.loginfo("=" * 70 + "\n")
        
        # 存储最近的状态
        self.sync_states = deque(maxlen=20)
        
        # 定时检查
        self.timer = rospy.Timer(rospy.Duration(1.0), self.check_sync_status)
    
    def find_log_file(self):
        """查找日志文件"""
        import glob
        import os
        log_files = glob.glob('/tmp/fast_livo*.log')
        if log_files:
            # 获取最新的日志文件
            self.log_file = max(log_files, key=os.path.getmtime)
    
    def check_sync_status(self, event):
        """检查同步状态"""
        if self.log_file:
            try:
                # 读取日志文件的最后几行
                result = subprocess.run(
                    ['tail', '-50', self.log_file],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                log_lines = result.stdout
            except:
                log_lines = ""
        else:
            log_lines = ""
        
        # 解析同步状态
        sync_info = {
            'waiting_lidar': False,
            'waiting_img': False,
            'waiting_imu': False,
            'buffer_lidar': 0,
            'buffer_img': 0,
            'buffer_imu': 0,
            'loop_count': 0,
            'last_lidar_time': None,
            'last_img_time': None,
            'data_cut': False
        }
        
        # 查找等待信息
        if '[ SYNC ] Waiting for LiDAR' in log_lines or 'lidar_buffer: 0' in log_lines:
            sync_info['waiting_lidar'] = True
        
        if '[ SYNC ] Waiting for image' in log_lines or 'img_buffer: 0' in log_lines:
            sync_info['waiting_img'] = True
        
        if '[ SYNC ] Waiting for IMU' in log_lines or 'imu_buffer: 0' in log_lines:
            sync_info['waiting_imu'] = True
        
        # 解析缓冲区状态
        buffer_match = re.search(r'lidar_buffer: (\d+), imu_buffer: (\d+), img_buffer: (\d+)', log_lines)
        if buffer_match:
            sync_info['buffer_lidar'] = int(buffer_match.group(1))
            sync_info['buffer_imu'] = int(buffer_match.group(2))
            sync_info['buffer_img'] = int(buffer_match.group(3))
        
        # 解析循环计数
        loop_match = re.search(r'loop: (\d+)', log_lines)
        if loop_match:
            sync_info['loop_count'] = int(loop_match.group(1))
        
        # 解析时间戳
        lidar_match = re.search(r'Get LiDAR, its header time: ([0-9.]+)', log_lines)
        if lidar_match:
            sync_info['last_lidar_time'] = float(lidar_match.group(1))
        
        img_match = re.search(r'Get image, its header time: ([0-9.]+)', log_lines)
        if img_match:
            sync_info['last_img_time'] = float(img_match.group(1))
        
        # 检查数据丢弃
        if '[ Data Cut ]' in log_lines or 'Throw one image' in log_lines:
            sync_info['data_cut'] = True
        
        # 显示状态
        self.display_status(sync_info)
    
    def display_status(self, info):
        """显示状态"""
        print("\r" + " " * 100, end="")  # 清行
        
        # 状态指示
        status_icon = "✅" if not (info['waiting_lidar'] or info['waiting_img'] or info['waiting_imu']) else "⏳"
        
        # 缓冲区状态
        buffer_status = f"激光:{info['buffer_lidar']} 图像:{info['buffer_img']} IMU:{info['buffer_imu']}"
        
        # 等待状态
        waiting = []
        if info['waiting_lidar']:
            waiting.append("激光")
        if info['waiting_img']:
            waiting.append("图像")
        if info['waiting_imu']:
            waiting.append("IMU")
        
        waiting_str = f"等待: {', '.join(waiting)}" if waiting else "同步正常"
        
        # 时间戳信息
        time_info = ""
        if info['last_lidar_time']:
            time_info += f"激光:{info['last_lidar_time']:.1f} "
        if info['last_img_time']:
            time_info += f"图像:{info['last_img_time']:.1f}"
        
        # 数据丢弃警告
        cut_warning = " ⚠️数据丢弃" if info['data_cut'] else ""
        
        print(f"\r{status_icon} {buffer_status} | {waiting_str} | {time_info}{cut_warning}", end="", flush=True)
        
        # 每5秒输出一次详细报告
        if int(rospy.Time.now().to_sec()) % 5 == 0:
            print()  # 换行
            rospy.loginfo("=" * 70)
            rospy.loginfo("📊 详细同步状态")
            rospy.loginfo("   - 缓冲区: 激光雷达=%d, 图像=%d, IMU=%d", 
                         info['buffer_lidar'], info['buffer_img'], info['buffer_imu'])
            rospy.loginfo("   - 等待状态: %s", waiting_str)
            if info['last_lidar_time'] and info['last_img_time']:
                time_diff = info['last_img_time'] - info['last_lidar_time']
                rospy.loginfo("   - 时间差: %.6f 秒 (%.1f 毫秒)", time_diff, time_diff * 1000)
            if info['data_cut']:
                rospy.logwarn("   ⚠️  检测到数据丢弃！")
            rospy.loginfo("=" * 70)

if __name__ == '__main__':
    try:
        monitor = SyncStatusMonitor()
        rospy.spin()
    except rospy.ROSInterruptException:
        print()  # 换行
        pass

