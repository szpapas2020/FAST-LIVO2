#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控 aft_mapped 坐标变化
实时显示 aft_mapped 在 map 坐标系中的位置和姿态
"""

import rospy
import tf2_ros
import math
import sys

class AftMappedMonitor:
    def __init__(self):
        rospy.init_node('aft_mapped_monitor', anonymous=True)
        
        # 参数
        self.map_frame = rospy.get_param('~map_frame', 'map')
        self.aft_mapped_frame = rospy.get_param('~aft_mapped_frame', 'aft_mapped')
        self.update_rate = rospy.get_param('~update_rate', 10.0)  # Hz
        self.show_delta = rospy.get_param('~show_delta', True)  # 是否显示变化量
        
        # TF 相关
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        
        # 存储上一次的位置
        self.last_position = None
        self.last_orientation = None
        
        rospy.loginfo("=" * 60)
        rospy.loginfo("aft_mapped 坐标监控节点启动")
        rospy.loginfo("监控坐标系: %s -> %s", self.map_frame, self.aft_mapped_frame)
        rospy.loginfo("更新频率: %.1f Hz", self.update_rate)
        rospy.loginfo("=" * 60)
        
        # 等待 TF 树建立
        rospy.sleep(1.0)
        
        # 创建定时器
        self.timer = rospy.Timer(rospy.Duration(1.0 / self.update_rate), self.monitor_callback)
    
    def quaternion_to_euler(self, q):
        """将四元数转换为欧拉角 (roll, pitch, yaw)"""
        roll = math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x * q.x + q.y * q.y))
        pitch = math.asin(2 * (q.w * q.y - q.z * q.x))
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return roll, pitch, yaw
    
    def monitor_callback(self, event):
        """监控回调函数"""
        try:
            # 获取 map -> aft_mapped 的变换
            transform = self.tf_buffer.lookup_transform(
                self.map_frame, 
                self.aft_mapped_frame, 
                rospy.Time(0), 
                timeout=rospy.Duration(0.1)
            )
            
            # 提取位置和姿态
            pos = transform.transform.translation
            rot = transform.transform.rotation
            
            # 转换为欧拉角
            roll, pitch, yaw = self.quaternion_to_euler(rot)
            
            # 计算变化量
            delta_x = delta_y = delta_z = 0.0
            delta_yaw = 0.0
            if self.last_position is not None and self.show_delta:
                delta_x = pos.x - self.last_position.x
                delta_y = pos.y - self.last_position.y
                delta_z = pos.z - self.last_position.z
                if self.last_orientation is not None:
                    _, _, last_yaw = self.quaternion_to_euler(self.last_orientation)
                    delta_yaw = yaw - last_yaw
                    # 处理角度跳变（-π 到 π）
                    if delta_yaw > math.pi:
                        delta_yaw -= 2 * math.pi
                    elif delta_yaw < -math.pi:
                        delta_yaw += 2 * math.pi
            
            # 显示信息
            print("\033[2J\033[H", end="")  # 清屏并移动光标到左上角
            print("=" * 80)
            print("aft_mapped 坐标监控")
            print("=" * 80)
            print(f"时间: {rospy.Time.now().to_sec():.3f}")
            print(f"坐标系: {self.map_frame} -> {self.aft_mapped_frame}")
            print("-" * 80)
            print("位置 (m):")
            print(f"  X: {pos.x:10.4f}", end="")
            if self.show_delta and self.last_position is not None:
                print(f"  [Δ: {delta_x:+8.4f}]", end="")
            print()
            print(f"  Y: {pos.y:10.4f}", end="")
            if self.show_delta and self.last_position is not None:
                print(f"  [Δ: {delta_y:+8.4f}]", end="")
            print()
            print(f"  Z: {pos.z:10.4f}", end="")
            if self.show_delta and self.last_position is not None:
                print(f"  [Δ: {delta_z:+8.4f}]", end="")
            print()
            print("-" * 80)
            print("姿态 (度):")
            print(f"  Roll:  {math.degrees(roll):8.2f}°")
            print(f"  Pitch: {math.degrees(pitch):8.2f}°")
            print(f"  Yaw:   {math.degrees(yaw):8.2f}°", end="")
            if self.show_delta and self.last_orientation is not None:
                print(f"  [Δ: {math.degrees(delta_yaw):+7.2f}°]", end="")
            print()
            print("-" * 80)
            
            # 判断是否在移动
            if self.last_position is not None:
                total_delta = math.sqrt(delta_x**2 + delta_y**2 + delta_z**2)
                if total_delta > 0.001:  # 1mm 阈值
                    print(f"状态: ⚠️  移动中 (位移: {total_delta*1000:.2f} mm)")
                else:
                    print("状态: ✓ 静止")
            else:
                print("状态: 初始化中...")
            
            print("=" * 80)
            print("按 Ctrl+C 退出")
            sys.stdout.flush()
            
            # 保存当前位置
            self.last_position = pos
            self.last_orientation = rot
            
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
            print("\033[2J\033[H", end="")
            print("=" * 80)
            print("aft_mapped 坐标监控")
            print("=" * 80)
            print(f"错误: 无法获取 {self.map_frame} -> {self.aft_mapped_frame} 的变换")
            print(f"原因: {str(e)}")
            print("=" * 80)
            print("提示: 请确保:")
            print("  1. FAST-LIVO2 节点正在运行")
            print("  2. 已设置初始位姿（2D Pose Estimate）")
            print("  3. map 和 aft_mapped 坐标系存在")
            print("=" * 80)
            sys.stdout.flush()

if __name__ == '__main__':
    try:
        monitor = AftMappedMonitor()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
    except KeyboardInterrupt:
        print("\n\n监控已停止")

