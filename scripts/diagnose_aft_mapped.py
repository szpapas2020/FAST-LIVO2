#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断脚本：检查影响 aft_mapped 坐标的所有因素

使用方法：
    rosrun fast_livo diagnose_aft_mapped.py
"""

import rospy
import tf2_ros
import geometry_msgs.msg
from nav_msgs.msg import Odometry
import time
import math

class AftMappedDiagnostic:
    def __init__(self):
        rospy.init_node('aft_mapped_diagnostic', anonymous=True)
        
        # TF 相关
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        
        # 订阅话题
        self.sub_odom = rospy.Subscriber('/aft_mapped_to_init', Odometry, self.odom_callback)
        self.last_odom = None
        self.odom_count = 0
        
        # 存储历史数据
        self.aft_mapped_history = []
        self.max_history = 100
        
        rospy.loginfo("=" * 80)
        rospy.loginfo("aft_mapped 坐标诊断工具")
        rospy.loginfo("=" * 80)
        
    def quaternion_to_euler(self, q):
        """四元数转欧拉角"""
        import math
        roll = math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x * q.x + q.y * q.y))
        pitch = math.asin(2 * (q.w * q.y - q.z * q.x))
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return roll, pitch, yaw
    
    def odom_callback(self, msg):
        """接收 /aft_mapped_to_init 话题"""
        self.last_odom = msg
        self.odom_count += 1
    
    def check_tf_tree(self):
        """检查 TF 树结构"""
        print("\n" + "=" * 80)
        print("1. TF 树结构检查")
        print("=" * 80)
        
        # 检查 map -> camera_init
        try:
            transform = self.tf_buffer.lookup_transform('map', 'camera_init', rospy.Time(0), timeout=rospy.Duration(2.0))
            pos = transform.transform.translation
            rot = transform.transform.rotation
            print(f"✓ map -> camera_init 变换存在")
            print(f"  位置: ({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})")
        except Exception as e:
            print(f"✗ 无法获取 map -> camera_init 变换: {e}")
        
        # 检查 camera_init -> aft_mapped
        try:
            transform = self.tf_buffer.lookup_transform('camera_init', 'aft_mapped', rospy.Time(0), timeout=rospy.Duration(2.0))
            pos = transform.transform.translation
            rot = transform.transform.rotation
            print(f"\n✓ camera_init -> aft_mapped 变换存在")
            print(f"  位置: ({pos.x:.6f}, {pos.y:.6f}, {pos.z:.6f})")
            
            # 判断是否为单位变换
            dist = math.sqrt(pos.x**2 + pos.y**2 + pos.z**2)
            if dist < 0.001:
                print(f"  → 单位变换（我们的 TF 正在覆盖 FAST-LIVO2 的动态 TF）")
            else:
                print(f"  → 非单位变换（距离: {dist:.6f} m）")
                print(f"  → FAST-LIVO2 的动态 TF 可能正在生效")
        except Exception as e:
            print(f"\n✗ 无法获取 camera_init -> aft_mapped 变换: {e}")
        
        # 检查 map -> aft_mapped
        try:
            transform = self.tf_buffer.lookup_transform('map', 'aft_mapped', rospy.Time(0), timeout=rospy.Duration(2.0))
            pos = transform.transform.translation
            rot = transform.transform.rotation
            roll, pitch, yaw = self.quaternion_to_euler(rot)
            print(f"\n✓ map -> aft_mapped 变换存在")
            print(f"  位置: ({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})")
            print(f"  姿态: Roll={math.degrees(roll):.2f}°, Pitch={math.degrees(pitch):.2f}°, Yaw={math.degrees(yaw):.2f}°")
        except Exception as e:
            print(f"\n✗ 无法获取 map -> aft_mapped 变换: {e}")
    
    def check_odometry_topic(self):
        """检查 /aft_mapped_to_init 话题"""
        print("\n" + "=" * 80)
        print("2. /aft_mapped_to_init 话题检查")
        print("=" * 80)
        
        if self.last_odom is None:
            print("✗ 未收到 /aft_mapped_to_init 话题数据")
            print("  请确保 FAST-LIVO2 节点正在运行")
            return
        
        pos = self.last_odom.pose.pose.position
        rot = self.last_odom.pose.pose.orientation
        roll, pitch, yaw = self.quaternion_to_euler(rot)
        
        print(f"✓ 话题数据正常（已接收 {self.odom_count} 条消息）")
        print(f"  位置: ({pos.x:.3f}, {pos.y:.3f}, {pos.z:.3f})")
        print(f"  姿态: Roll={math.degrees(roll):.2f}°, Pitch={math.degrees(pitch):.2f}°, Yaw={math.degrees(yaw):.2f}°")
        print(f"  时间戳: {self.last_odom.header.stamp}")
        print(f"  Frame ID: {self.last_odom.header.frame_id} -> {self.last_odom.child_frame_id}")
    
    def check_initial_pose_handler(self):
        """检查 initial_pose_handler 节点"""
        print("\n" + "=" * 80)
        print("3. initial_pose_handler 节点检查")
        print("=" * 80)
        
        try:
            nodes = rospy.get_node_names()
            if '/initial_pose_handler' in nodes:
                print("✓ initial_pose_handler 节点正在运行")
                
                # 检查参数
                try:
                    map_frame = rospy.get_param('/initial_pose_handler/map_frame', 'unknown')
                    base_frame = rospy.get_param('/initial_pose_handler/base_frame', 'unknown')
                    aft_mapped_frame = rospy.get_param('/initial_pose_handler/aft_mapped_frame', 'unknown')
                    camera_offset_x = rospy.get_param('/initial_pose_handler/camera_offset_x', 0.0)
                    camera_offset_z = rospy.get_param('/initial_pose_handler/camera_offset_z', 0.0)
                    base_link_height = rospy.get_param('/initial_pose_handler/base_link_height', 0.0)
                    
                    print(f"\n  参数配置:")
                    print(f"    map_frame: {map_frame}")
                    print(f"    base_frame: {base_frame}")
                    print(f"    aft_mapped_frame: {aft_mapped_frame}")
                    print(f"    camera_offset_x: {camera_offset_x} m")
                    print(f"    camera_offset_z: {camera_offset_z} m")
                    print(f"    base_link_height: {base_link_height} m")
                except Exception as e:
                    print(f"  无法读取参数: {e}")
            else:
                print("✗ initial_pose_handler 节点未运行")
                print("  请确保 launch 文件已启动该节点")
        except Exception as e:
            print(f"✗ 检查节点时出错: {e}")
    
    def monitor_aft_mapped_movement(self, duration=10):
        """监控 aft_mapped 的移动"""
        print("\n" + "=" * 80)
        print("4. aft_mapped 移动监控（持续 %d 秒）" % duration)
        print("=" * 80)
        print("正在监控...")
        
        start_time = time.time()
        last_pos = None
        max_delta = 0.0
        total_delta = 0.0
        count = 0
        
        rate = rospy.Rate(10)  # 10Hz
        
        while not rospy.is_shutdown() and (time.time() - start_time) < duration:
            try:
                transform = self.tf_buffer.lookup_transform('map', 'aft_mapped', rospy.Time(0), timeout=rospy.Duration(0.5))
                pos = transform.transform.translation
                
                if last_pos is not None:
                    delta_x = pos.x - last_pos.x
                    delta_y = pos.y - last_pos.y
                    delta_z = pos.z - last_pos.z
                    delta = math.sqrt(delta_x**2 + delta_y**2 + delta_z**2)
                    
                    max_delta = max(max_delta, delta)
                    total_delta += delta
                    count += 1
                
                last_pos = pos
                
            except Exception as e:
                rospy.logwarn("无法获取 TF: %s", str(e))
            
            rate.sleep()
        
        if count > 0:
            avg_delta = total_delta / count
            print(f"\n监控结果:")
            print(f"  采样次数: {count}")
            print(f"  最大单次移动: {max_delta*1000:.2f} mm")
            print(f"  平均单次移动: {avg_delta*1000:.2f} mm")
            
            if max_delta < 0.01:  # < 1cm
                print(f"  → 移动幅度正常（< 1cm），这是 ICP 匹配的正常行为")
            elif max_delta < 0.1:  # < 10cm
                print(f"  → 移动幅度较大（1-10cm），可能需要检查初始位姿")
            else:
                print(f"  → 移动幅度很大（> 10cm），异常！请检查:")
                print(f"     1. 初始位姿设置是否准确")
                print(f"     2. 地图与当前环境是否匹配")
                print(f"     3. ICP 匹配参数是否需要调整")
        else:
            print("✗ 无法获取足够的监控数据")
    
    def run_diagnosis(self):
        """运行完整诊断"""
        rospy.sleep(2.0)  # 等待节点启动
        
        # 1. 检查 TF 树
        self.check_tf_tree()
        
        # 2. 检查话题
        self.check_odometry_topic()
        
        # 3. 检查节点
        self.check_initial_pose_handler()
        
        # 4. 监控移动
        self.monitor_aft_mapped_movement(duration=10)
        
        # 总结
        print("\n" + "=" * 80)
        print("诊断总结")
        print("=" * 80)
        print("影响 aft_mapped 坐标的主要因素:")
        print("1. FAST-LIVO2 内部状态更新（IMU、ICP、VIO）")
        print("2. initial_pose_handler 的 TF 发布（100Hz，未来时间戳）")
        print("3. FAST-LIVO2 的动态 TF 发布（10Hz，当前时间戳）")
        print("\n详细分析请参考: docs/aft_mapped_coordinate_analysis.md")
        print("=" * 80)

if __name__ == '__main__':
    try:
        diagnostic = AftMappedDiagnostic()
        diagnostic.run_diagnosis()
    except rospy.ROSInterruptException:
        pass

