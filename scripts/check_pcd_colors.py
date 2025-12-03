#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 PCD 文件的颜色信息
"""

import open3d as o3d
import numpy as np
import sys

def check_pcd_colors(pcd_file):
    """检查 PCD 文件的颜色信息"""
    print(f"\n检查文件: {pcd_file}")
    print("=" * 60)
    
    try:
        pcd = o3d.io.read_point_cloud(pcd_file)
        
        print(f"点数: {len(pcd.points)}")
        print(f"有颜色: {pcd.has_colors()}")
        print(f"有法线: {pcd.has_normals()}")
        
        if pcd.has_colors() and len(pcd.colors) > 0:
            colors = np.asarray(pcd.colors)
            print(f"\n颜色信息:")
            print(f"  颜色范围: [{colors.min():.3f}, {colors.max():.3f}]")
            print(f"  颜色均值: R={colors[:,0].mean():.3f}, G={colors[:,1].mean():.3f}, B={colors[:,2].mean():.3f}")
            print(f"  颜色标准差: R={colors[:,0].std():.3f}, G={colors[:,1].std():.3f}, B={colors[:,2].std():.3f}")
            
            print(f"\n前10个点的颜色示例:")
            for i in range(min(10, len(pcd.colors))):
                r, g, b = colors[i]
                print(f"  点{i}: RGB=({r:.3f}, {g:.3f}, {b:.3f}) -> RGB8=({int(r*255)}, {int(g*255)}, {int(b*255)})")
            
            # 检查颜色分布
            unique_colors = len(np.unique(colors.reshape(-1, 3), axis=0))
            print(f"\n唯一颜色数量: {unique_colors}")
            
            if unique_colors < 100:
                print("  注意: 颜色种类较少，可能是灰度图或单色")
            elif unique_colors > 10000:
                print("  颜色种类丰富，可能是真实场景的彩色点云")
        else:
            print("\n无颜色信息")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import os
    
    # 检查降采样后的 PCD 文件
    downsampled_file = '/home/fsy/ros_ws/src/FAST-LIVO2/Log/PCD/all_downsampled_points.pcd'
    if os.path.exists(downsampled_file):
        check_pcd_colors(downsampled_file)
    
    # 检查原始 PCD 文件
    raw_file = '/home/fsy/ros_ws/src/FAST-LIVO2/Log/PCD/all_raw_points.pcd'
    if os.path.exists(raw_file):
        check_pcd_colors(raw_file)

