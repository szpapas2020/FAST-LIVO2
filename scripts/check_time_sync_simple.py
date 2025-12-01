#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版时间同步检查工具
直接使用rostopic命令检查时间戳
"""

import rospy
from sensor_msgs.msg import Image
from std_msgs.msg import Header
import subprocess
import re

def check_time_sync():
    """检查时间同步"""
    rospy.init_node('time_sync_checker_simple', anonymous=True)
    
    rospy.loginfo("=" * 70)
    rospy.loginfo("激光雷达与图像时间同步检查工具（简化版）")
    rospy.loginfo("=" * 70)
    
    # 获取配置参数
    try:
        img_time_offset = rospy.get_param('/time_offset/img_time_offset', 0.1)
        exposure_time_init = rospy.get_param('/time_offset/exposure_time_init', 0.0)
        rospy.loginfo("\n配置参数:")
        rospy.loginfo("  - img_time_offset: %.6f 秒", img_time_offset)
        rospy.loginfo("  - exposure_time_init: %.6f 秒", exposure_time_init)
    except:
        rospy.logwarn("无法获取配置参数，使用默认值")
        img_time_offset = 0.1
        exposure_time_init = 0.0
    
    rospy.loginfo("\n" + "=" * 70)
    rospy.loginfo("📊 实时时间戳监控")
    rospy.loginfo("=" * 70)
    rospy.loginfo("按Ctrl+C退出")
    rospy.loginfo("=" * 70 + "\n")
    
    # 存储最近的时间戳
    lidar_times = []
    img_times = []
    
    def lidar_callback(msg):
        """激光雷达回调"""
        try:
            # 尝试从AnyMsg中提取时间戳
            # 使用rospy.deserialize_message或者直接访问
            if hasattr(msg, '_buff'):
                # 尝试反序列化
                try:
                    from livox_ros_driver2.msg import CustomMsg
                    lidar_msg = rospy.deserialize_message(msg._buff, CustomMsg)
                    timestamp = lidar_msg.header.stamp.to_sec()
                except:
                    # 如果失败，尝试直接访问
                    if hasattr(msg, 'header'):
                        timestamp = msg.header.stamp.to_sec()
                    else:
                        return
            elif hasattr(msg, 'header'):
                timestamp = msg.header.stamp.to_sec()
            else:
                return
            
            lidar_times.append(timestamp)
            if len(lidar_times) > 10:
                lidar_times.pop(0)
        except Exception as e:
            pass
    
    def img_callback(msg):
        """图像回调"""
        try:
            raw_timestamp = msg.header.stamp.to_sec()
            corrected_timestamp = raw_timestamp + img_time_offset
            img_capture_time = corrected_timestamp + exposure_time_init
            
            img_times.append({
                'raw': raw_timestamp,
                'corrected': corrected_timestamp,
                'capture': img_capture_time
            })
            if len(img_times) > 10:
                img_times.pop(0)
            
            # 如果有激光雷达数据，计算时间差
            if len(lidar_times) > 0:
                latest_lidar = lidar_times[-1]
                time_diff = img_capture_time - latest_lidar
                
                status = "✅" if abs(time_diff) < 0.01 else "⚠️" if abs(time_diff) < 0.05 else "❌"
                
                print(f"\r{status} 图像: {img_capture_time:.6f} | "
                      f"激光: {latest_lidar:.6f} | "
                      f"时间差: {time_diff*1000:+.1f}ms", end="", flush=True)
        except Exception as e:
            pass
    
    # 订阅
    rospy.Subscriber('/livox/lidar', rospy.AnyMsg, lidar_callback)
    rospy.Subscriber('/left_camera/image', Image, img_callback)
    
    rospy.spin()

if __name__ == '__main__':
    try:
        check_time_sync()
    except rospy.ROSInterruptException:
        print()  # 换行
        pass

