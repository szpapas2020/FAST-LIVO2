# FAST-LIVO2 重定位模式快速开始

## 快速启动

```bash
cd /home/fsy/ros_ws
source devel/setup.bash

# 启动重定位模式
roslaunch fast_livo mapping_mid360_relocalization.launch
```

## 在 RViz 中设置初始位姿

1. 点击工具栏中的 **"2D Pose Estimate"** 按钮
2. 在地图上点击并拖动设置机器人位置和朝向
3. 系统会自动开始重定位

## 文件清单

### 新建文件
- `config/mid360_relocalization.yaml` - 重定位配置文件
- `launch/mapping_mid360_relocalization.launch` - 重定位启动文件
- `scripts/publish_pcd_map_simple.py` - PCD 地图发布脚本
- `scripts/initial_pose_handler.py` - 初始位姿处理脚本
- `docs/relocalization_usage.md` - 详细使用说明

### 使用的 PCD 文件
- `Log/PCD/all_downsampled_points.pcd` - 预建地图文件（需要先建图生成）

## 更多信息

详细使用说明请参考：`docs/relocalization_usage.md`
