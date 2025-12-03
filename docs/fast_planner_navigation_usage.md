# FAST-LIVO2 重定位模式 + Fast-Planner 导航使用说明

## 概述

本文档介绍如何使用 FAST-LIVO2 重定位模式配合 Fast-Planner 进行导航规划。系统会在加载预建地图后，允许在 RViz 中设置初始位姿，然后使用 Fast-Planner 进行路径规划和导航。

## 系统架构

```
FAST-LIVO2 (重定位)
    ├── 加载预建PCD地图
    ├── 实时激光雷达定位 (/aft_mapped_to_init)
    ├── 实时点云发布 (/cloud_registered)
    └── 自动启动 Fast-Planner
            ├── 路径规划 (/planning/bspline)
            ├── 轨迹服务器 (traj_server)
            └── 路径点生成器 (waypoint_generator)
```

## 前置要求

### 1. 环境准备

- ROS 环境已配置
- FAST-LIVO2 已编译
- Fast-Planner 已编译
- 预建的 PCD 地图文件

### 2. 检查依赖

```bash
# 检查ROS包是否可用
rospack find fast_livo
rospack find plan_manage
rospack find waypoint_generator
```

### 3. 准备PCD地图

确保有预建的 PCD 地图文件，默认路径：
```
$(find fast_livo)/Log/PCD/all_downsampled_points.pcd
```

## 快速开始

### 1. 启动系统

```bash
# 启动FAST-LIVO2重定位（会自动启动Fast-Planner）
roslaunch fast_livo mapping_mid360_relocalization.launch
```

### 2. 设置初始位姿

在 RViz 中：
1. 点击工具栏的 **"2D Pose Estimate"** 按钮
2. 在地图上点击并拖拽，设置机器人的初始位置和朝向
3. 确保位姿设置准确（影响重定位成功率）

### 3. 设置导航目标

在 RViz 中：
1. 点击工具栏的 **"2D Nav Goal"** 按钮
2. 在地图上点击目标位置并拖拽设置朝向
3. Fast-Planner 会自动规划路径并开始导航

## 详细配置

### Launch 文件参数

#### FAST-LIVO2 重定位参数

```bash
roslaunch fast_livo mapping_mid360_relocalization.launch \
    pcd_file:=/path/to/your/map.pcd \  # PCD地图文件路径
    rviz:=true                          # 是否启动RViz
```

#### Fast-Planner 参数

```bash
roslaunch fast_livo mapping_mid360_relocalization.launch \
    enable_fast_planner:=true \         # 是否启用Fast-Planner（默认true）
    map_size_x:=40.0 \                  # 地图X方向大小（米）
    map_size_y:=40.0 \                  # 地图Y方向大小（米）
    map_size_z:=5.0 \                   # 地图Z方向大小（米）
    max_vel:=3.0 \                      # 最大速度（m/s）
    max_acc:=2.0 \                      # 最大加速度（m/s²）
    flight_type:=1                      # 导航模式：1=2D Nav Goal, 2=全局路径点
```

### 参数说明

#### `enable_fast_planner`
- **类型**: boolean
- **默认值**: `true`
- **说明**: 是否自动启动 Fast-Planner。设置为 `false` 可禁用 Fast-Planner。

#### `map_size_x/y/z`
- **类型**: double
- **默认值**: `40.0 / 40.0 / 5.0`
- **说明**: Fast-Planner 的 SDF 地图大小。根据实际环境大小调整：
  - 小环境（<20m）：`map_size_x:=20.0 map_size_y:=20.0`
  - 中等环境（20-50m）：`map_size_x:=40.0 map_size_y:=40.0`
  - 大环境（>50m）：`map_size_x:=60.0 map_size_y:=60.0`

#### `max_vel` / `max_acc`
- **类型**: double
- **默认值**: `3.0 / 2.0`
- **说明**: 机器人的最大速度和加速度限制。根据机器人性能调整：
  - 低速机器人：`max_vel:=1.0 max_acc:=1.0`
  - 中速机器人：`max_vel:=3.0 max_acc:=2.0`
  - 高速机器人：`max_vel:=5.0 max_acc:=3.0`

#### `flight_type`
- **类型**: int
- **默认值**: `1`
- **说明**: 导航模式
  - `1`: 使用 2D Nav Goal（在 RViz 中手动点击目标）
  - `2`: 使用全局路径点（自动按顺序访问预设路径点）

## 话题说明

### 订阅的话题

| 话题名称 | 类型 | 说明 |
|---------|------|------|
| `/livox/lidar` | CustomMsg | FAST-LIVO2 订阅的激光雷达原始数据 |
| `/livox/imu` | Imu | FAST-LIVO2 订阅的 IMU 数据 |
| `/left_camera/image` | Image | FAST-LIVO2 订阅的相机图像（如果启用） |
| `/initialpose` | PoseWithCovarianceStamped | RViz 2D Pose Estimate 设置的初始位姿 |
| `/move_base_simple/goal` | PoseStamped | RViz 2D Nav Goal 设置的导航目标 |

### 发布的话题

| 话题名称 | 类型 | 说明 |
|---------|------|------|
| `/aft_mapped_to_init` | Odometry | FAST-LIVO2 的位姿输出（Fast-Planner 使用） |
| `/cloud_registered` | PointCloud2 | FAST-LIVO2 的实时点云（Fast-Planner 使用） |
| `/pcd_map` | PointCloud2 | 预加载的 PCD 地图点云 |
| `/path` | Path | FAST-LIVO2 的路径轨迹 |
| `/planning/bspline` | Bspline | Fast-Planner 的 B 样条轨迹 |
| `/planning/pos_cmd` | Odometry | Fast-Planner 的位置命令 |
| `/planning/replan` | Empty | Fast-Planner 的重规划触发信号 |

## TF 树结构

```
camera_init (map frame)
  └── aft_mapped
      └── base_link (通过 static_transform_publisher)
```

**注意**: Fast-Planner 使用 `camera_init` 作为世界坐标系，与 FAST-LIVO2 保持一致。

## 使用流程

### 标准流程

1. **启动系统**
   ```bash
   roslaunch fast_livo mapping_mid360_relocalization.launch
   ```

2. **等待系统初始化**
   - FAST-LIVO2 加载预建地图
   - Fast-Planner 初始化 SDF 地图
   - 等待终端显示 "Ready" 或类似信息

3. **设置初始位姿**
   - 在 RViz 中使用 "2D Pose Estimate"
   - 确保位姿准确（影响重定位成功率）

4. **验证定位**
   - 检查 `/aft_mapped_to_init` 话题是否有数据
   - 在 RViz 中查看机器人位姿是否正确

5. **设置导航目标**
   - 在 RViz 中使用 "2D Nav Goal"
   - Fast-Planner 会自动规划路径

6. **监控导航**
   - 在 RViz 中查看规划轨迹
   - 监控终端输出的导航状态

### 高级用法

#### 使用全局路径点导航

1. 编辑 `fast_livo2_navigation.launch` 文件，设置路径点：
   ```xml
   <arg name="flight_type" value="2"/>
   <arg name="point_num" value="3"/>
   <arg name="point0_x" value="10.0"/>
   <arg name="point0_y" value="5.0"/>
   <arg name="point0_z" value="1.0"/>
   <!-- 更多路径点... -->
   ```

2. 启动系统后，机器人会自动按顺序访问路径点

#### 禁用 Fast-Planner

如果只需要重定位功能，不需要导航：
```bash
roslaunch fast_livo mapping_mid360_relocalization.launch \
    enable_fast_planner:=false
```

## 故障排除

### 问题 1: Fast-Planner 无法启动

**症状**: 终端显示找不到 `plan_manage` 包

**解决方案**:
```bash
# 检查包是否存在
rospack find plan_manage

# 如果不存在，检查编译
cd ~/ros_ws
catkin_make
source devel/setup.bash
```

### 问题 2: 坐标系不匹配

**症状**: RViz 中看不到点云或位姿不正确

**解决方案**:
1. 检查 TF 树：`rosrun tf view_frames`
2. 确认 `camera_init` 坐标系存在
3. 检查 Fast-Planner 的 `frame_id` 参数是否为 `camera_init`

### 问题 3: 路径规划失败

**症状**: 设置目标后没有规划路径

**解决方案**:
1. 检查位姿话题：`rostopic echo /aft_mapped_to_init`
2. 检查点云话题：`rostopic echo /cloud_registered`
3. 检查目标话题：`rostopic echo /move_base_simple/goal`
4. 查看 Fast-Planner 终端输出，查找错误信息

### 问题 4: 地图大小不合适

**症状**: 规划路径超出地图范围

**解决方案**:
根据实际环境调整地图大小：
```bash
roslaunch fast_livo mapping_mid360_relocalization.launch \
    map_size_x:=60.0 \
    map_size_y:=60.0 \
    map_size_z:=5.0
```

### 问题 5: 速度/加速度限制不合适

**症状**: 机器人运动不流畅或超出能力

**解决方案**:
根据机器人性能调整速度和加速度：
```bash
roslaunch fast_livo mapping_mid360_relocalization.launch \
    max_vel:=1.5 \
    max_acc:=1.0
```

## 性能优化

### 1. 地图大小优化

- **小地图**: 计算速度快，但覆盖范围小
- **大地图**: 覆盖范围大，但计算速度慢
- **建议**: 根据实际使用场景选择合适的大小

### 2. 速度和加速度优化

- **保守设置**: 安全性高，但导航速度慢
- **激进设置**: 导航速度快，但可能超出机器人能力
- **建议**: 根据机器人实际性能逐步调整

### 3. 点云处理优化

如果点云数据量大导致延迟：
- 在 FAST-LIVO2 配置中调整点云过滤参数
- 降低点云发布频率

## 调试工具

### 1. 检查话题

```bash
# 列出所有话题
rostopic list

# 检查位姿话题
rostopic echo /aft_mapped_to_init

# 检查点云话题频率
rostopic hz /cloud_registered

# 检查规划轨迹
rostopic echo /planning/bspline
```

### 2. 检查 TF 树

```bash
# 查看 TF 树
rosrun tf view_frames

# 实时查看 TF 树
rosrun rqt_tf_tree rqt_tf_tree
```

### 3. 检查节点状态

```bash
# 列出所有节点
rosnode list

# 检查节点信息
rosnode info /fast_planner_node
rosnode info /laserMapping
```

### 4. RViz 可视化

在 RViz 中添加以下显示：
- **PointCloud2**: `/cloud_registered` (实时点云)
- **PointCloud2**: `/pcd_map` (预加载地图)
- **Odometry**: `/aft_mapped_to_init` (位姿)
- **Path**: `/path` (路径轨迹)
- **MarkerArray**: `/planning/visualization/exp_traj` (规划轨迹)

## 示例命令

### 基本启动

```bash
roslaunch fast_livo mapping_mid360_relocalization.launch
```

### 自定义地图文件

```bash
roslaunch fast_livo mapping_mid360_relocalization.launch \
    pcd_file:=/home/user/maps/my_map.pcd
```

### 小环境配置

```bash
roslaunch fast_livo mapping_mid360_relocalization.launch \
    map_size_x:=20.0 \
    map_size_y:=20.0 \
    map_size_z:=3.0 \
    max_vel:=1.5 \
    max_acc:=1.0
```

### 大环境配置

```bash
roslaunch fast_livo mapping_mid360_relocalization.launch \
    map_size_x:=60.0 \
    map_size_y:=60.0 \
    map_size_z:=8.0 \
    max_vel:=5.0 \
    max_acc:=3.0
```

## 相关文档

- [FAST-LIVO2 重定位使用说明](relocalization_usage.md)
- [时间同步解决方案](time_sync_solution.md)
- [Fast-Planner README](../../Fast-Planner/README.md)

## 技术支持

如遇到问题，请检查：
1. ROS 环境是否正确配置
2. 所有依赖包是否已编译
3. 话题和 TF 树是否正确
4. 终端输出的错误信息

---

**最后更新**: 2024年
**版本**: 1.0

