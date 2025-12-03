#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复降采样PCD文件
功能：从原始PCD文件生成降采样版本
"""

import rospy
import open3d as o3d
import os
import sys
import argparse

def downsample_pcd(input_file, output_file, voxel_size=0.15):
    """对PCD文件进行降采样"""
    print(f"加载点云文件: {input_file}")
    pcd = o3d.io.read_point_cloud(input_file)
    
    if len(pcd.points) == 0:
        print(f"错误: 点云文件为空!")
        return False
    
    print(f"原始点数: {len(pcd.points)}")
    
    # 降采样
    print(f"使用体素大小 {voxel_size}m 进行降采样...")
    downsampled_pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    
    print(f"降采样后点数: {len(downsampled_pcd.points)}")
    print(f"降采样比例: {len(downsampled_pcd.points)/len(pcd.points)*100:.2f}%")
    
    # 保存降采样后的点云
    print(f"保存降采样点云到: {output_file}")
    o3d.io.write_point_cloud(output_file, downsampled_pcd)
    
    # 检查文件大小
    input_size = os.path.getsize(input_file) / (1024*1024)
    output_size = os.path.getsize(output_file) / (1024*1024)
    print(f"\n文件大小:")
    print(f"  原始文件: {input_size:.2f} MB")
    print(f"  降采样文件: {output_size:.2f} MB")
    print(f"  压缩比例: {output_size/input_size*100:.2f}%")
    
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='修复降采样PCD文件')
    parser.add_argument('--input', '-i', 
                       default='/home/fsy/ros_ws/src/FAST-LIVO2/Log/PCD/all_raw_points.pcd',
                       help='输入PCD文件路径')
    parser.add_argument('--output', '-o',
                       default='/home/fsy/ros_ws/src/FAST-LIVO2/Log/PCD/all_downsampled_points.pcd',
                       help='输出降采样PCD文件路径')
    parser.add_argument('--voxel_size', '-v', type=float, default=0.15,
                       help='体素大小（米），默认0.15')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        sys.exit(1)
    
    if downsample_pcd(args.input, args.output, args.voxel_size):
        print("\n✓ 降采样完成!")
    else:
        print("\n✗ 降采样失败!")
        sys.exit(1)

