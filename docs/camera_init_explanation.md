# camera_init 坐标系说明

## 什么是 camera_init？

`camera_init` 是 **FAST-LIVO2 的内部地图坐标系**，是 FAST-LIVO2 系统中最核心的坐标系之一。

## 基本定义

### 名称含义

- **`camera`**：表示相机/传感器坐标系
- **`init`**：表示初始化时的坐标系（建图开始时的坐标系）

### 本质

`camera_init` 是 FAST-LIVO2 **建图时创建的世界坐标系**，所有建图数据都相对于这个坐标系保存。

## 在建图阶段的作用

### 1. 坐标系的创建

- FAST-LIVO2 在建图开始时创建 `camera_init` 坐标系
- `camera_init` 的原点就是**建图开始时的传感器位置**
- 一旦创建，`camera_init` 的原点就固定不变

### 2. 数据存储

- 所有点云数据都相对于 `camera_init` 的原点保存
- PCD 文件中的点云坐标是相对于 `camera_init` 的原点的
- **PCD 文件的原点 = 建图时 `camera_init` 的原点**

### 3. 位姿发布

FAST-LIVO2 发布的所有位姿都相对于 `camera_init`：

```cpp
// LIVMapper.cpp:1337
odomAftMapped.header.frame_id = "camera_init";
odomAftMapped.child_frame_id = "aft_mapped";
```

## 在重定位阶段的作用

### 1. 与 map 坐标系的关系

在重定位模式下：

- **`map` 坐标系**：标准的 ROS 地图坐标系
- **`map` 的原点 = PCD 文件的原点 = 建图时 `camera_init` 的原点**
- 初始时，`map -> camera_init` 是单位变换（对齐）

### 2. 初始位姿设置

当用户通过 2D Pose Estimate 设置初始位姿时：

- `initial_pose_handler` 更新 `map -> camera_init` 的静态 TF
- `camera_init` 移动到新位置（用户选择的位姿）
- **地图仍然固定在 `map` 坐标系的原点，不会移动**

### 3. 运行时行为

- FAST-LIVO2 持续发布 `camera_init -> aft_mapped` 的动态 TF
- `aft_mapped` 是 FAST-LIVO2 的位姿估计坐标系
- 机器人位姿（`base_link`、`aft_mapped`）相对于 `camera_init` 移动

## TF 树结构

### 建图阶段

```
camera_init (建图开始时的传感器位置，固定)
  └── aft_mapped (动态，FAST-LIVO2 位姿估计)
      └── base_link (机器人基座坐标系)
```

### 重定位阶段

```
map (固定坐标系，PCD地图原点)
  ├── camera_init (初始时与 map 对齐，设置初始位姿后会移动)
  │   └── aft_mapped (动态，FAST-LIVO2 位姿估计)
  │       └── base_link (机器人基座坐标系)
  └── base_link (通过 initial_pose_handler 发布的静态 TF)
```

## 关键特性

### 1. 固定原点

- `camera_init` 的原点在建图时确定，之后不再改变
- 这是 FAST-LIVO2 的"世界坐标系原点"

### 2. 内部坐标系

- `camera_init` 是 FAST-LIVO2 内部使用的坐标系
- 所有 FAST-LIVO2 的位姿估计都相对于 `camera_init`

### 3. 与 ROS 标准坐标系的关系

- 在重定位模式下，`map` 坐标系对应 `camera_init` 的初始位置
- `map` 是标准的 ROS 坐标系，用于与 ROS 生态系统集成

## 代码中的使用

### 1. 位姿发布

```cpp
// LIVMapper.cpp:1337
odomAftMapped.header.frame_id = "camera_init";
odomAftMapped.child_frame_id = "aft_mapped";
```

### 2. 点云发布

```cpp
// LIVMapper.cpp:1232
laserCloudmsg.header.frame_id = "camera_init";
```

### 3. 路径发布

```cpp
// LIVMapper.cpp:45
path.header.frame_id = "camera_init";
```

## 常见问题

### Q: camera_init 和 map 有什么区别？

**A:**
- **`camera_init`**：FAST-LIVO2 内部的地图坐标系，原点在建图时确定
- **`map`**：标准的 ROS 地图坐标系，在重定位模式下与 `camera_init` 对齐
- **关系**：`map` 的原点 = PCD 文件的原点 = 建图时 `camera_init` 的原点

### Q: camera_init 会移动吗？

**A:**
- **建图阶段**：不会移动，`camera_init` 的原点固定
- **重定位阶段**：`map -> camera_init` 的变换会改变（通过 2D Pose Estimate），但 `camera_init` 的原点本身不变

### Q: 为什么叫 camera_init 而不是 map？

**A:**
- FAST-LIVO2 最初设计时使用 `camera_init` 作为内部坐标系
- 在重定位模式下，为了与 ROS 标准集成，引入了 `map` 坐标系
- `camera_init` 仍然保留，作为 FAST-LIVO2 的内部坐标系

### Q: 如何理解 camera_init 和 aft_mapped 的关系？

**A:**
- **`camera_init`**：地图坐标系（固定）
- **`aft_mapped`**：当前传感器位姿（动态）
- **关系**：`camera_init -> aft_mapped` 表示传感器在地图中的位置

## 总结

- ✅ `camera_init` 是 FAST-LIVO2 的内部地图坐标系
- ✅ `camera_init` 的原点在建图时确定，之后固定不变
- ✅ PCD 文件的原点 = 建图时 `camera_init` 的原点
- ✅ 在重定位模式下，`map` 坐标系与 `camera_init` 对齐
- ✅ 所有 FAST-LIVO2 的位姿估计都相对于 `camera_init`

## 相关文档

- [Map 坐标系说明](./map_coordinate_system.md)
- [aft_mapped 坐标变化原因分析](./aft_mapped_coordinate_analysis.md)
- [重定位模式使用说明](./relocalization_usage.md)

