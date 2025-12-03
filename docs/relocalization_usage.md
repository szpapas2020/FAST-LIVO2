# FAST-LIVO2 重定位模式使用说明

## 概述

重定位模式允许您加载之前建图保存的 PCD 地图文件，并在 RViz 中设置机器人的初始位姿，然后继续进行定位和建图。

## 文件说明

### 配置文件
- `config/mid360_relocalization.yaml`: 重定位模式的配置文件

### Launch 文件
- `launch/mapping_mid360_relocalization.launch`: 重定位模式启动文件

### 脚本文件
- `scripts/publish_pcd_map_simple.py`: PCD 地图发布节点（加载并发布 PCD 文件）
- `scripts/initial_pose_handler.py`: 初始位姿处理节点（处理 RViz 的 2D Pose Estimate）

## 使用步骤

### 1. 准备 PCD 地图文件

确保您已经有一个建图保存的 PCD 文件：
```
src/FAST-LIVO2/Log/PCD/all_downsampled_points.pcd
```

如果没有，请先运行建图模式生成地图。

### 2. 启动重定位模式

```bash
cd /home/fsy/ros_ws
source devel/setup.bash

# 使用默认 PCD 文件路径
roslaunch fast_livo mapping_mid360_relocalization.launch

# 或指定自定义 PCD 文件路径
roslaunch fast_livo mapping_mid360_relocalization.launch pcd_file:=/path/to/your/map.pcd
```

### 3. 在 RViz 中设置初始位姿

1. **打开 RViz**（如果 launch 文件中 `rviz:=true`，RViz 会自动启动）

2. **添加点云显示**：
   - 点击 "Add" → "PointCloud2"
   - 设置 `Topic` 为 `/pcd_map`
   - 设置 `Color Transformer` 为 `RGB8`（如果点云有颜色）或 `Intensity`（如果无颜色）

3. **设置初始位姿**：
   - 点击 RViz 工具栏中的 **"2D Pose Estimate"** 按钮
   - 在地图上点击并拖动，设置机器人的初始位置和朝向
   - 位姿会通过 `/initialpose` 话题发送

4. **验证初始位姿**：
   - 查看终端输出，应该看到类似以下信息：
     ```
     [INFO] Received initial pose from RViz
     [INFO] Position: x=1.234, y=2.345, z=0.000
     [INFO] Orientation: roll=0.000, pitch=0.000, yaw=45.000
     [INFO] Published static transform: camera_init -> base_link
     [INFO] Initial pose set successfully!
     ```

### 4. 开始重定位

设置初始位姿后，系统会自动开始重定位：
- FAST-LIVO2 会使用预加载的地图进行定位
- 实时点云会发布到 `/cloud_registered` 话题
- 机器人位姿会发布到 `/aft_mapped_to_init` 话题

## 话题说明

### 订阅的话题
- `/initialpose` (geometry_msgs/PoseWithCovarianceStamped): RViz 2D Pose Estimate 发送的初始位姿

### 发布的话题
- `/pcd_map` (sensor_msgs/PointCloud2): 预加载的 PCD 地图点云
- `/cloud_registered` (sensor_msgs/PointCloud2): 实时注册的点云
- `/aft_mapped_to_init` (nav_msgs/Odometry): 机器人位姿
- `/set_initial_pose` (nav_msgs/Odometry): 初始位姿信息

## TF 树

重定位模式下的 TF 树结构：
```
camera_init (map frame)
  └── aft_mapped
      └── base_link (通过 static_transform_publisher)
```

## 参数说明

### Launch 文件参数
- `pcd_file`: PCD 地图文件路径（默认：`$(find fast_livo)/Log/PCD/all_downsampled_points.pcd`）
- `rviz`: 是否启动 RViz（默认：`true`）

### 配置文件参数 (`mid360_relocalization.yaml`)
- `relocalization/map_path`: PCD 地图文件路径
- `relocalization/enable_map_loading`: 是否启用地图加载
- `relocalization/initial_pose_topic`: 初始位姿话题名称

## 注意事项

1. **PCD 文件格式**：
   - 支持带 RGB 颜色的点云（PointXYZRGB）
   - 支持普通点云（PointXYZ）
   - 文件必须是有效的 PCD 格式

2. **初始位姿设置**：
   - 初始位姿应该尽可能准确，以提高重定位成功率
   - 如果重定位失败，可以重新设置初始位姿

3. **地图坐标系**：
   - 地图坐标系是 `camera_init`
   - 初始位姿是相对于 `camera_init` 的

4. **性能考虑**：
   - 大型 PCD 文件（>100MB）可能需要较长时间加载
   - 建议使用降采样后的地图文件（`all_downsampled_points.pcd`）

## 故障排除

### 问题1: PCD 文件未找到
```
[ERROR] PCD file not found: /path/to/file.pcd
```
**解决方案**：检查 PCD 文件路径是否正确，确保文件存在。

### 问题2: 初始位姿设置后没有反应
**解决方案**：
- 检查终端是否有错误信息
- 确认 `/initialpose` 话题是否正常发布
- 检查 TF 树是否完整

### 问题3: 点云不显示
**解决方案**：
- 检查 `/pcd_map` 话题是否有数据：`rostopic echo /pcd_map -n 1`
- 检查 RViz 中的点云显示设置
- 确认点云坐标系（`camera_init`）是否正确

## 示例命令

```bash
# 1. 启动重定位模式
roslaunch fast_livo mapping_mid360_relocalization.launch

# 2. 检查 PCD 地图是否发布
rostopic echo /pcd_map -n 1

# 3. 检查初始位姿话题
rostopic echo /initialpose -n 1

# 4. 查看 TF 树
rosrun tf view_frames
evince frames.pdf
```

## 相关文档

- [建图模式使用说明](../README.md)
- [RViz 配置说明](../rviz_cfg/README.md)

