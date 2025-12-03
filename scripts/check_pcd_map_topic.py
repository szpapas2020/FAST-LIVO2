#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 /pcd_map 话题的点云格式和颜色信息
"""

import rospy
from sensor_msgs.msg import PointCloud2
import sensor_msgs.point_cloud2 as pc2

def check_pointcloud(msg):
    """检查点云消息的格式"""
    print("=" * 60)
    print("点云消息信息:")
    print(f"  高度: {msg.height}")
    print(f"  宽度: {msg.width}")
    print(f"  点数: {msg.height * msg.width}")
    print(f"  点步长: {msg.point_step} 字节")
    print(f"  行步长: {msg.row_step} 字节")
    print(f"  是否密集: {msg.is_dense}")
    
    print(f"\n字段列表:")
    for field in msg.fields:
        print(f"  - {field.name}: offset={field.offset}, datatype={field.datatype}, count={field.count}")
    
    # 检查是否有 RGB 字段
    has_rgb = False
    has_r = False
    has_g = False
    has_b = False
    
    for field in msg.fields:
        if field.name == 'rgb':
            has_rgb = True
            print(f"\n✓ 找到 'rgb' 字段 (offset={field.offset})")
        elif field.name == 'r':
            has_r = True
            print(f"\n✓ 找到 'r' 字段 (offset={field.offset})")
        elif field.name == 'g':
            has_g = True
            print(f"\n✓ 找到 'g' 字段 (offset={field.offset})")
        elif field.name == 'b':
            has_b = True
            print(f"\n✓ 找到 'b' 字段 (offset={field.offset})")
    
    if has_rgb:
        print("\n颜色格式: RGB (打包在一个字段中)")
        print("RViz 应使用: Color Transformer = RGB8")
    elif has_r and has_g and has_b:
        print("\n颜色格式: R, G, B (三个独立字段)")
        print("RViz 应使用: Color Transformer = RGB8")
    else:
        print("\n✗ 未找到 RGB 颜色字段!")
        print("点云可能没有颜色信息，或格式不正确")
    
    # 尝试读取前几个点的颜色
    if has_rgb or (has_r and has_g and has_b):
        print("\n前5个点的颜色示例:")
        try:
            points = list(pc2.read_points(msg, field_names=('x', 'y', 'z', 'r', 'g', 'b') if (has_r and has_g and has_b) else ('x', 'y', 'z', 'rgb'), skip_nans=True))
            for i, point in enumerate(points[:5]):
                if has_rgb:
                    rgb = point[3]
                    r = (rgb >> 16) & 0xFF
                    g = (rgb >> 8) & 0xFF
                    b = rgb & 0xFF
                    print(f"  点{i}: RGB=({r}, {g}, {b})")
                else:
                    print(f"  点{i}: RGB=({point[3]}, {point[4]}, {point[5]})")
        except Exception as e:
            print(f"  无法读取颜色: {e}")
    
    print("=" * 60)
    rospy.signal_shutdown("检查完成")

if __name__ == '__main__':
    rospy.init_node('check_pcd_map_topic', anonymous=True)
    print("等待 /pcd_map 话题消息...")
    rospy.Subscriber('/pcd_map', PointCloud2, check_pointcloud, queue_size=1)
    rospy.spin()

