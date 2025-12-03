#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断地图晃动问题
"""

import rospy
import tf2_ros
from sensor_msgs.msg import PointCloud2
import sensor_msgs.point_cloud2 as pc2

def check_pcd_map():
    """检查 PCD 地图的 frame_id"""
    print("=" * 60)
    print("检查 PCD 地图配置")
    print("=" * 60)
    
    try:
        msg = rospy.wait_for_message('/pcd_map', PointCloud2, timeout=5.0)
        print(f"✓ PCD 地图 frame_id: {msg.header.frame_id}")
        if msg.header.frame_id == 'map':
            print("  ✓ 正确：地图使用 map 坐标系")
        else:
            print(f"  ✗ 错误：应该使用 'map'，但当前是 '{msg.header.frame_id}'")
        print(f"  点数: {msg.width * msg.height}")
    except rospy.ROSException:
        print("✗ 无法获取 /pcd_map 话题消息")
    
    print()

def check_tf_tree():
    """检查 TF 树"""
    print("=" * 60)
    print("检查 TF 树")
    print("=" * 60)
    
    tf_buffer = tf2_ros.Buffer()
    tf_listener = tf2_ros.TransformListener(tf_buffer)
    
    rospy.sleep(2.0)  # 等待 TF 树建立
    
    # 检查 map -> camera_init
    try:
        transform = tf_buffer.lookup_transform('map', 'camera_init', rospy.Time(0), timeout=rospy.Duration(2.0))
        print(f"✓ map -> camera_init 变换存在")
        print(f"  平移: ({transform.transform.translation.x:.3f}, {transform.transform.translation.y:.3f}, {transform.transform.translation.z:.3f})")
        print(f"  旋转: ({transform.transform.rotation.x:.3f}, {transform.transform.rotation.y:.3f}, {transform.transform.rotation.z:.3f}, {transform.transform.rotation.w:.3f})")
        
        # 检查是否是单位变换
        is_identity = (abs(transform.transform.translation.x) < 0.001 and
                      abs(transform.transform.translation.y) < 0.001 and
                      abs(transform.transform.translation.z) < 0.001 and
                      abs(transform.transform.rotation.w - 1.0) < 0.001)
        
        if is_identity:
            print("  ✓ 是单位变换（正确）")
        else:
            print("  ⚠ 不是单位变换，可能影响地图位置")
    except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
        print(f"✗ 无法获取 map -> camera_init 变换: {e}")
    
    # 检查 camera_init -> aft_mapped（应该是动态的）
    try:
        transform = tf_buffer.lookup_transform('camera_init', 'aft_mapped', rospy.Time(0), timeout=rospy.Duration(2.0))
        print(f"\n✓ camera_init -> aft_mapped 变换存在（动态）")
        print(f"  平移: ({transform.transform.translation.x:.3f}, {transform.transform.translation.y:.3f}, {transform.transform.translation.z:.3f})")
    except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
        print(f"\n✗ 无法获取 camera_init -> aft_mapped 变换: {e}")
    
    # 检查 map -> base_link
    try:
        transform = tf_buffer.lookup_transform('map', 'base_link', rospy.Time(0), timeout=rospy.Duration(2.0))
        print(f"\n✓ map -> base_link 变换存在")
        print(f"  平移: ({transform.transform.translation.x:.3f}, {transform.transform.translation.y:.3f}, {transform.transform.translation.z:.3f})")
    except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
        print(f"\n⚠ map -> base_link 变换不存在（如果未设置初始位姿，这是正常的）")
    
    print()

def check_rviz_config():
    """检查 RViz 配置建议"""
    print("=" * 60)
    print("RViz 配置检查建议")
    print("=" * 60)
    print("1. 确认 Fixed Frame 设置为 'map'")
    print("   - 在 RViz 左下角 'Global Options' 中检查")
    print("   - Fixed Frame 应该显示为 'map'")
    print()
    print("2. 确认 PCDMap 显示项的设置")
    print("   - 找到 'PCDMap' 显示项")
    print("   - 'Use Fixed Frame' 应该为 true")
    print("   - 'Topic' 应该为 '/pcd_map'")
    print()
    print("3. 如果地图仍然晃动，尝试：")
    print("   - 在 RViz 中手动将 Fixed Frame 改为 'map'")
    print("   - 重新加载 RViz 配置：File -> Open Config")
    print("   - 或重启 launch 文件")
    print()

if __name__ == '__main__':
    rospy.init_node('diagnose_map_shaking', anonymous=True)
    
    print("\n" + "=" * 60)
    print("地图晃动问题诊断工具")
    print("=" * 60)
    print()
    
    check_pcd_map()
    check_tf_tree()
    check_rviz_config()
    
    print("=" * 60)
    print("诊断完成")
    print("=" * 60)

