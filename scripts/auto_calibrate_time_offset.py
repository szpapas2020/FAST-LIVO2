#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动校准时间偏移工具
功能：实时监测图像和激光雷达时间戳，自动计算并建议最优的 img_time_offset 值
"""

import rospy
import numpy as np
from collections import deque
from sensor_msgs.msg import Image
import sys
import os

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

class TimeOffsetCalibrator:
    def __init__(self):
        rospy.init_node('auto_calibrate_time_offset', anonymous=True)
        
        # 数据缓冲区（保存最近的时间戳）
        self.lidar_timestamps = deque(maxlen=1000)
        self.img_timestamps = deque(maxlen=1000)
        self.time_diffs = deque(maxlen=1000)
        
        # 统计信息
        self.lidar_count = 0
        self.img_count = 0
        
        # 配置参数（话题名称可配置）
        self.lidar_topic = rospy.get_param('~lidar_topic', '/livox/lidar')
        self.image_topic = rospy.get_param('~image_topic', '/left_camera/image')
        self.sample_duration = rospy.get_param('~sample_duration', 30.0)  # 采样时长（秒）
        self.min_samples = rospy.get_param('~min_samples', 100)  # 最少样本数
        
        # 检查话题是否存在
        self.check_topics()
        
        # 订阅话题
        rospy.Subscriber(self.lidar_topic, CustomMsg, self.lidar_callback)
        rospy.Subscriber(self.image_topic, Image, self.img_callback)
        
        self.start_time = rospy.Time.now()
        self.calibration_done = False
        
        rospy.loginfo("=" * 70)
        rospy.loginfo("自动时间偏移校准工具")
        rospy.loginfo("=" * 70)
        rospy.loginfo("激光雷达话题: %s", self.lidar_topic)
        rospy.loginfo("图像话题: %s", self.image_topic)
        rospy.loginfo("采样时长: %.1f 秒", self.sample_duration)
        rospy.loginfo("最少样本数: %d", self.min_samples)
        rospy.loginfo("=" * 70)
        rospy.loginfo("正在采集数据，请确保图像和激光雷达都在正常发布...")
        rospy.loginfo("=" * 70)
        
        # 定时检查
        self.timer = rospy.Timer(rospy.Duration(1.0), self.check_calibration)
    
    def check_topics(self):
        """检查话题是否存在"""
        import time
        rospy.loginfo("检查话题可用性...")
        
        # 等待话题列表更新
        time.sleep(1.0)
        
        available_topics = [topic[0] for topic in rospy.get_published_topics()]
        
        lidar_found = False
        image_found = False
        
        # 检查激光雷达话题
        if self.lidar_topic in available_topics:
            lidar_found = True
            rospy.loginfo("✓ 找到激光雷达话题: %s", self.lidar_topic)
        else:
            rospy.logwarn("✗ 未找到激光雷达话题: %s", self.lidar_topic)
            # 尝试查找类似的Livox话题
            livox_topics = [t for t in available_topics if 'livox' in t.lower() or 'lidar' in t.lower()]
            if livox_topics:
                rospy.logwarn("  发现可能的Livox话题:")
                for topic in livox_topics:
                    rospy.logwarn("    - %s", topic)
                rospy.logwarn("  提示: 可以使用参数 ~lidar_topic:=<话题名> 指定正确的话题")
        
        # 检查图像话题
        if self.image_topic in available_topics:
            image_found = True
            rospy.loginfo("✓ 找到图像话题: %s", self.image_topic)
        else:
            rospy.logwarn("✗ 未找到图像话题: %s", self.image_topic)
            # 尝试查找类似的图像话题
            image_topics = [t for t in available_topics if 'image' in t.lower() or 'camera' in t.lower()]
            if image_topics:
                rospy.logwarn("  发现可能的图像话题:")
                for topic in image_topics:
                    rospy.logwarn("    - %s", topic)
                rospy.logwarn("  提示: 可以使用参数 ~image_topic:=<话题名> 指定正确的话题")
        
        if not lidar_found:
            rospy.logerr("=" * 70)
            rospy.logerr("错误: 激光雷达话题不存在！")
            rospy.logerr("=" * 70)
            rospy.logerr("可能的原因:")
            rospy.logerr("  1. 激光雷达驱动未启动")
            rospy.logerr("  2. 激光雷达硬件未连接")
            rospy.logerr("  3. 话题名称配置错误")
            rospy.logerr("")
            rospy.logerr("解决方案:")
            rospy.logerr("  1. 检查激光雷达驱动是否正常运行")
            rospy.logerr("  2. 使用 'rostopic list' 查看可用话题")
            rospy.logerr("  3. 使用参数指定正确的话题名称:")
            rospy.logerr("     rosrun fast_livo auto_calibrate_time_offset.py _lidar_topic:=<实际话题名>")
            rospy.logerr("=" * 70)
        
        if not image_found:
            rospy.logerr("=" * 70)
            rospy.logerr("警告: 图像话题不存在！")
            rospy.logerr("=" * 70)
        
        rospy.loginfo("")
    
    def lidar_callback(self, msg):
        """激光雷达回调"""
        self.lidar_count += 1
        timestamp = msg.header.stamp.to_sec()
        self.lidar_timestamps.append(timestamp)
    
    def img_callback(self, msg):
        """图像回调"""
        self.img_count += 1
        timestamp = msg.header.stamp.to_sec()
        self.img_timestamps.append(timestamp)
        
        # 如果有激光雷达数据，计算时间差
        if len(self.lidar_timestamps) > 0:
            # 找到最接近的激光雷达时间戳
            lidar_times = np.array(self.lidar_timestamps)
            time_diff = timestamp - lidar_times[-1]  # 使用最新的激光雷达时间戳
            self.time_diffs.append(time_diff)
    
    def check_calibration(self, event):
        """检查是否完成校准"""
        elapsed = (rospy.Time.now() - self.start_time).to_sec()
        
        if self.calibration_done:
            return
        
        # 检查是否满足条件
        if elapsed >= self.sample_duration and len(self.time_diffs) >= self.min_samples:
            self.perform_calibration()
            self.calibration_done = True
        else:
            # 显示进度
            progress = min(100, (elapsed / self.sample_duration) * 100)
            status_msg = "校准进度: %.1f%% | 图像: %d | 激光: %d | 时间差样本: %d" % (
                         progress, self.img_count, self.lidar_count, len(self.time_diffs))
            
            # 如果激光数据为0，添加警告
            if self.lidar_count == 0:
                status_msg += " [警告: 无激光数据]"
            
            rospy.loginfo(status_msg)
            
            # 如果超过5秒还没有激光数据，给出提示
            if elapsed > 5.0 and self.lidar_count == 0:
                rospy.logwarn("提示: 已运行 %.1f 秒但仍未收到激光数据，请检查:" % elapsed)
                rospy.logwarn("  1. 激光雷达驱动是否启动: roslaunch livox_ros_driver2 xxx.launch")
                rospy.logwarn("  2. 话题名称是否正确: rostopic list | grep livox")
                rospy.logwarn("  3. 使用参数指定话题: _lidar_topic:=<实际话题名>")
    
    def perform_calibration(self):
        """执行校准计算"""
        rospy.loginfo("=" * 70)
        rospy.loginfo("开始计算最优时间偏移...")
        rospy.loginfo("=" * 70)
        
        if len(self.time_diffs) == 0:
            rospy.logerr("没有足够的数据进行校准！")
            return
        
        time_diffs_array = np.array(self.time_diffs)
        
        # 计算统计信息
        mean_diff = np.mean(time_diffs_array)
        median_diff = np.median(time_diffs_array)
        std_diff = np.std(time_diffs_array)
        min_diff = np.min(time_diffs_array)
        max_diff = np.max(time_diffs_array)
        
        # 使用中位数作为推荐值（对异常值更鲁棒）
        recommended_offset = -median_diff
        
        # 计算置信度（基于标准差）
        confidence = max(0, 100 - (std_diff / abs(mean_diff) * 100)) if abs(mean_diff) > 0 else 0
        
        rospy.loginfo("=" * 70)
        rospy.loginfo("校准结果")
        rospy.loginfo("=" * 70)
        rospy.loginfo("样本数量: %d", len(time_diffs_array))
        rospy.loginfo("时间差统计:")
        rospy.loginfo("  平均值: %.6f 秒 (%.2f 天)", mean_diff, mean_diff / 86400)
        rospy.loginfo("  中位数: %.6f 秒 (%.2f 天)", median_diff, median_diff / 86400)
        rospy.loginfo("  标准差: %.6f 秒", std_diff)
        rospy.loginfo("  最小值: %.6f 秒 (%.2f 天)", min_diff, min_diff / 86400)
        rospy.loginfo("  最大值: %.6f 秒 (%.2f 天)", max_diff, max_diff / 86400)
        rospy.loginfo("")
        rospy.loginfo("推荐配置:")
        rospy.loginfo("  img_time_offset: %.6f 秒 (约 %.2f 天)", 
                     recommended_offset, abs(recommended_offset) / 86400)
        rospy.loginfo("  置信度: %.1f%%", confidence)
        rospy.loginfo("=" * 70)
        
        # 生成配置文件更新建议
        config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'config', 'mid360.yaml'
        )
        
        rospy.loginfo("")
        rospy.loginfo("配置文件更新建议:")
        rospy.loginfo("  文件: %s", config_file)
        rospy.loginfo("  将 img_time_offset 设置为: %.6f", recommended_offset)
        rospy.loginfo("")
        
        # 保存结果到文件
        result_file = '/tmp/time_offset_calibration_result.txt'
        with open(result_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("时间偏移校准结果\n")
            f.write("=" * 70 + "\n")
            f.write(f"样本数量: {len(time_diffs_array)}\n")
            f.write(f"时间差平均值: {mean_diff:.6f} 秒 ({mean_diff/86400:.2f} 天)\n")
            f.write(f"时间差中位数: {median_diff:.6f} 秒 ({median_diff/86400:.2f} 天)\n")
            f.write(f"时间差标准差: {std_diff:.6f} 秒\n")
            f.write(f"\n推荐配置:\n")
            f.write(f"  img_time_offset: {recommended_offset:.6f}\n")
            f.write(f"  置信度: {confidence:.1f}%\n")
            f.write("=" * 70 + "\n")
        
        rospy.loginfo("结果已保存到: %s", result_file)
        rospy.loginfo("=" * 70)

if __name__ == '__main__':
    try:
        calibrator = TimeOffsetCalibrator()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

