# Map 坐标系定义说明

## 核心定义

**`map` 坐标系是一个固定的全局坐标系，其原点对应 PCD 文件的原点（建图时 `camera_init` 的原点）。**

## 坐标系定义方式

### 1. 通过静态 TF 定义

`map` 坐标系通过发布 `map -> camera_init` 的静态 TF 来定义：

```xml
<!-- 在 launch 文件中 -->
<node pkg="tf" type="static_transform_publisher" name="map_to_camera_init_initial"
    args="0 0 0 0 0 0 map camera_init 100" />
```

**参数说明**：
- `args="x y z qx qy qz qw"` 或 `args="x y z yaw pitch roll"`
- `x y z`: 平移量（米）
- `qw qx qy qz`: 四元数，或 `yaw pitch roll`: 欧拉角（弧度）
- `map`: 父坐标系
- `camera_init`: 子坐标系
- `100`: 发布频率（Hz）

### 2. 初始状态

**初始时**：
- `map -> camera_init` 的变换是**单位变换**（`0 0 0 0 0 0`）
- 这意味着 `map` 和 `camera_init` 在初始时**完全对齐**
- `map` 的原点 = `camera_init` 的原点 = PCD 文件的原点

### 3. 坐标系原点

**`map` 坐标系的原点定义**：
- **位置**：PCD 文件的原点（建图时 `camera_init` 的原点）
- **含义**：建图开始时的传感器位置
- **特点**：固定不变，不会随机器人移动

## 坐标系关系

### 建图阶段

在建图阶段，通常**不使用 `map` 坐标系**，只使用 `camera_init`：

```
camera_init (建图时 FAST-LIVO2 自动创建)
  └── aft_mapped (动态，FAST-LIVO2 位姿估计)
      └── base_link (静态，相对于 aft_mapped)
```

### 重定位阶段

在重定位阶段，引入 `map` 坐标系：

```
map (固定坐标系，原点 = PCD 原点)
  ├── camera_init (初始时与 map 对齐，设置初始位姿后会移动)
  │   └── aft_mapped (动态，FAST-LIVO2 位姿估计)
  │       └── base_link (静态，相对于 aft_mapped)
  └── base_link (通过 initial_pose_handler 发布的静态 TF，用户选择的坐标)
```

## 实现细节

### 1. Launch 文件中的定义

**重定位模式** (`mapping_mid360_relocalization.launch`)：

```xml
<!-- 发布静态 TF：map -> camera_init（初始时单位变换，对齐 PCD 原点） -->
<node pkg="tf" type="static_transform_publisher" name="map_to_camera_init_initial"
    args="0 0 0 0 0 0 map camera_init 100" />
```

**建图模式** (`mapping_mid360.launch`)：

```xml
<!-- 创建 map 坐标系（建图模式下也使用 map 坐标系） -->
<node pkg="tf" type="static_transform_publisher" name="map_to_camera_init_initial"
    args="0 0 0 0 0 0 map camera_init 100" />
```

### 2. PCD 地图发布

PCD 地图使用 `map` 作为 `frame_id`：

```python
# publish_pcd_map_simple.py
header.frame_id = "map"  # 地图固定在 map 坐标系中
```

**关键点**：
- 地图固定在 `map` 坐标系中，不会移动
- 地图的原点就是 `map` 坐标系的原点
- 无论 `camera_init` 如何移动，地图始终固定在 `map` 原点

### 3. 初始位姿设置

当用户通过 2D Pose Estimate 设置初始位姿时：

```python
# initial_pose_handler.py
camera_init_transform.header.frame_id = "map"  # map 原点
camera_init_transform.child_frame_id = "camera_init"
# 更新 map -> camera_init 的变换
```

**关键点**：
- 只改变 `map -> camera_init` 的变换
- 地图仍然固定在 `map` 坐标系的原点，不会移动
- `camera_init` 移动到新位置（用户选择的位姿）

## 坐标系特点

### 1. 固定性

- ✅ `map` 坐标系是**固定的**，不会随机器人移动
- ✅ 地图固定在 `map` 坐标系中，不会移动
- ✅ `map` 的原点就是 PCD 文件的原点

### 2. 与 camera_init 的关系

- **初始时**：`map` 和 `camera_init` 对齐（单位变换）
- **设置初始位姿后**：`map -> camera_init` 的变换会改变，但地图仍然固定在 `map` 原点
- **运行时**：`camera_init -> aft_mapped` 是动态的，但地图始终固定在 `map` 原点

### 3. 与 PCD 文件的关系

- **PCD 文件的原点** = `map` 坐标系的原点 = 建图时 `camera_init` 的原点
- **PCD 文件中的点云坐标**是相对于 `map` 原点的
- **地图显示**时，使用 `map` 作为 `frame_id`

## 验证方法

### 1. 检查 TF 树

```bash
# 查看 TF 树
rosrun tf view_frames
evince frames.pdf

# 应该看到：
# map (固定)
#   └── camera_init (初始时对齐，设置初始位姿后会移动)
```

### 2. 检查 map -> camera_init 的 TF

```bash
# 初始时应该是单位变换
rosrun tf tf_echo map camera_init

# 应该显示：
# Translation: [0.000, 0.000, 0.000]
# Rotation: in Quaternion [0.000, 0.000, 0.000, 1.000]
```

### 3. 检查 PCD 地图 frame_id

```bash
# 检查 PCD 地图的 frame_id
rostopic echo /pcd_map -n 1 | grep frame_id

# 应该显示：frame_id: "map"
```

### 4. 在 RViz 中观察

- Fixed Frame 设置为 `map`
- 地图应该保持静止
- 机器人位姿在地图中移动

## 常见问题

### Q1: map 坐标系是如何创建的？

A: `map` 坐标系通过发布 `map -> camera_init` 的静态 TF 来创建。这个 TF 由 launch 文件中的 `static_transform_publisher` 节点发布。

### Q2: map 坐标系的原点在哪里？

A: `map` 坐标系的原点 = PCD 文件的原点 = 建图时 `camera_init` 的原点。初始时，`map` 和 `camera_init` 对齐（单位变换）。

### Q3: map 坐标系会移动吗？

A: 不会。`map` 坐标系是固定的，不会随机器人移动。只有 `map -> camera_init` 的变换会改变（当设置初始位姿时），但地图始终固定在 `map` 原点。

### Q4: 为什么需要 map 坐标系？

A: `map` 坐标系用于固定地图，确保地图不会随传感器移动。这样，无论机器人如何移动，地图都保持在固定的位置。

### Q5: map 和 camera_init 的区别是什么？

A:
- **`map`**: 固定的全局坐标系，地图固定在其中
- **`camera_init`**: FAST-LIVO2 的内部地图坐标系，初始时与 `map` 对齐，设置初始位姿后会移动

## 总结

- ✅ `map` 坐标系通过静态 TF `map -> camera_init` 定义
- ✅ `map` 坐标系的原点 = PCD 文件的原点 = 建图时 `camera_init` 的原点
- ✅ 初始时，`map` 和 `camera_init` 对齐（单位变换）
- ✅ 地图固定在 `map` 坐标系中，不会移动
- ✅ 设置初始位姿时，只改变 `map -> camera_init` 的变换，地图位置不变

