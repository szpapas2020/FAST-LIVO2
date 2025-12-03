# Map 坐标系说明

## 核心概念

**`map` 坐标系的原点对应 PCD 文件的原点（建图时 `camera_init` 的原点）**

## 坐标系关系

### 建图阶段

1. **`camera_init` 坐标系**：
   - FAST-LIVO2 在建图开始时创建 `camera_init` 坐标系
   - `camera_init` 的原点就是建图开始时的传感器位置
   - 所有点云数据都相对于 `camera_init` 的原点保存

2. **PCD 文件**：
   - PCD 文件中的点云坐标是相对于 `camera_init` 的原点的
   - PCD 文件的原点就是建图时 `camera_init` 的原点

### 重定位阶段

1. **`map` 坐标系**：
   - `map` 坐标系的原点 = PCD 文件的原点 = 建图时 `camera_init` 的原点
   - 初始时，`map -> camera_init` 是单位变换（对齐）
   - PCD 地图固定在 `map` 坐标系中，不会移动

2. **初始位姿设置**：
   - 当用户通过 2D Pose Estimate 设置初始位姿时：
     - `initial_pose_handler` 更新 `map -> camera_init` 的静态 TF
     - `camera_init` 移动到新位置（用户选择的位姿）
     - **地图仍然固定在 `map` 坐标系的原点，不会移动**

3. **运行时**：
   - FAST-LIVO2 持续发布 `camera_init -> aft_mapped` 的动态 TF
   - 机器人位姿（`base_link`、`aft_mapped`）在地图中移动
   - **地图保持静止，固定在 `map` 坐标系的原点**

## TF 树结构

```
map (固定坐标系，原点 = PCD 原点)
  ├── camera_init (初始时与 map 对齐，设置初始位姿后会移动)
  │   └── aft_mapped (动态，FAST-LIVO2 位姿估计)
  │       └── base_link (静态，-0.4, 0, -1.8)
  └── base_link (通过 initial_pose_handler 发布的静态 TF，用户选择的坐标)
```

## 关键点

1. **地图固定**：
   - PCD 地图使用 `map` 坐标系
   - 地图固定在 `map` 坐标系的原点（PCD 原点）
   - 地图不会随传感器移动

2. **初始位姿**：
   - 设置初始位姿时，只改变 `map -> camera_init` 的变换
   - 地图位置不变，仍然固定在 `map` 原点

3. **RViz 显示**：
   - Fixed Frame 应该设置为 `map`
   - 地图应该保持静止
   - 机器人位姿在地图中移动

## 实现细节

### Launch 文件

```xml
<!-- map -> camera_init 初始为单位变换（对齐） -->
<node pkg="tf" type="static_transform_publisher" name="map_to_camera_init"
    args="0 0 0 0 0 0 map camera_init 100" />
```

### PCD 地图发布

```python
# 地图使用 map 坐标系，固定在 map 原点
header.frame_id = "map"  # 对应 PCD 原点
```

### 初始位姿处理

```python
# 更新 map -> camera_init 的变换
# camera_init 移动到新位置，但地图保持在 map 原点
camera_init_transform.header.frame_id = "map"  # map 原点
camera_init_transform.child_frame_id = "camera_init"
```

## 验证方法

1. **检查 PCD 地图 frame_id**：
   ```bash
   rostopic echo /pcd_map -n 1 | grep frame_id
   # 应该显示：frame_id: "map"
   ```

2. **检查 TF 树**：
   ```bash
   rosrun tf view_frames
   evince frames.pdf
   # 应该看到 map -> camera_init 的变换
   ```

3. **在 RViz 中观察**：
   - Fixed Frame 设置为 `map`
   - 地图应该保持静止
   - 机器人位姿在地图中移动

## 常见问题

### Q: 地图为什么在晃动？

A: 检查：
1. RViz 的 Fixed Frame 是否为 `map`
2. PCDMap 显示项的 "Use Fixed Frame" 是否为 `true`
3. 是否有其他显示项干扰

### Q: 设置初始位姿后地图移动了？

A: 不应该移动。如果移动了，检查：
1. `initial_pose_handler` 是否正确更新了 `map -> camera_init` 的变换
2. PCD 地图的 frame_id 是否为 `map`
3. RViz 的 Fixed Frame 是否为 `map`

### Q: map 和 camera_init 的关系是什么？

A:
- **初始时**：`map` 和 `camera_init` 对齐（单位变换）
- **设置初始位姿后**：`map -> camera_init` 的变换会改变，但地图仍然固定在 `map` 原点
- **运行时**：`camera_init -> aft_mapped` 是动态的，但地图始终固定在 `map` 原点

## 总结

- ✅ `map` 坐标系的原点 = PCD 文件的原点 = 建图时 `camera_init` 的原点
- ✅ PCD 地图固定在 `map` 坐标系中，不会移动
- ✅ 设置初始位姿时，只改变 `map -> camera_init` 的变换，地图位置不变
- ✅ 运行时，机器人位姿在地图中移动，地图保持静止

