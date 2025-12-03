#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键修复时间同步问题（Python版本）
最简单的方式：运行此脚本即可自动完成所有步骤
"""

import rospy
import numpy as np
from collections import deque
from sensor_msgs.msg import Image
import sys
import os
import re

# 尝试导入 Livox 消息类型
try:
    import livox_ros_driver2.msg as livox_msg
    CustomMsg = livox_msg.CustomMsg
except ImportError:
    try:
        import livox_ros_driver.msg as livox_msg
        CustomMsg = livox_msg.CustomMsg
    except ImportError:
        print("❌ 错误: 无法导入 Livox 消息类型")
        sys.exit(1)

class QuickFixTimeSync:
    def __init__(self):
        rospy.init_node('quick_fix_time_sync', anonymous=True)
        
        self.lidar_timestamps = deque(maxlen=500)
        self.img_timestamps = deque(maxlen=500)
        self.time_diffs = deque(maxlen=500)
        
        rospy.Subscriber('/livox/lidar', CustomMsg, self.lidar_callback)
        rospy.Subscriber('/left_camera/image', Image, self.img_callback)
        
        # 配置文件路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_dir = os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'config')
        self.config_file = os.path.join(config_dir, 'mid360.yaml')
        self.relocalization_config = os.path.join(config_dir, 'mid360_relocalization.yaml')
        
        print("=" * 60)
        print("🚀 FAST-LIVO2 时间同步一键修复")
        print("=" * 60)
        print("正在采集数据（30秒）...")
        print("请确保 FAST-LIVO2 正在运行...")
        print("=" * 60)
        
        # 等待30秒采集数据
        rospy.sleep(30.0)
        
        if len(self.time_diffs) < 50:
            print("❌ 错误: 数据样本不足（需要至少50个样本）")
            print("   请确保图像和激光雷达都在正常发布")
            sys.exit(1)
        
        # 计算推荐值
        self.calculate_and_update()
    
    def lidar_callback(self, msg):
        self.lidar_timestamps.append(msg.header.stamp.to_sec())
    
    def img_callback(self, msg):
        img_time = msg.header.stamp.to_sec()
        if len(self.lidar_timestamps) > 0:
            diff = img_time - self.lidar_timestamps[-1]
            self.time_diffs.append(diff)
    
    def calculate_and_update(self):
        """计算并更新配置"""
        time_diffs_array = np.array(self.time_diffs)
        recommended_offset = -np.median(time_diffs_array)
        mean_diff = np.mean(time_diffs_array)
        
        print("=" * 60)
        print("✅ 校准完成")
        print("=" * 60)
        print(f"样本数: {len(self.time_diffs)}")
        print(f"平均时间差: {mean_diff:.6f} 秒 ({mean_diff/86400:.2f} 天)")
        print(f"推荐偏移: {recommended_offset:.6f} 秒 ({abs(recommended_offset)/86400:.2f} 天)")
        print("=" * 60)
        
        # 更新配置文件
        self.update_config_file(self.config_file, recommended_offset)
        if os.path.exists(self.relocalization_config):
            self.update_config_file(self.relocalization_config, recommended_offset)
        
        print("")
        print("=" * 60)
        print("✅ 修复完成！")
        print("=" * 60)
        print("下一步: 重启 FAST-LIVO2 以使配置生效")
        print("=" * 60)
    
    def update_config_file(self, config_file, offset):
        """更新配置文件"""
        if not os.path.exists(config_file):
            print(f"⚠️  警告: 配置文件不存在: {config_file}")
            return
        
        # 备份原配置
        backup_file = f"{config_file}.backup.{rospy.Time.now().to_sec():.0f}"
        with open(config_file, 'r') as f:
            content = f.read()
        with open(backup_file, 'w') as f:
            f.write(content)
        print(f"✅ 已备份: {backup_file}")
        
        # 更新配置
        pattern = r'img_time_offset:\s*[-\d.]+'
        replacement = f'img_time_offset: {offset:.6f}'
        
        new_content = re.sub(pattern, replacement, content)
        
        with open(config_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ 已更新: {config_file}")

if __name__ == '__main__':
    try:
        fixer = QuickFixTimeSync()
    except KeyboardInterrupt:
        print("\n❌ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

