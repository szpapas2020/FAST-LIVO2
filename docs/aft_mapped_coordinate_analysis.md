# aft_mapped 坐标变化原因分析

## 概述

`aft_mapped` 是 FAST-LIVO2 输出的位姿估计坐标系，其坐标会持续变化。本文档分析所有可能影响 `aft_mapped` 坐标的因素。

## TF 树结构

```
map (固定坐标系，PCD地图原点)
  └── camera_init (FAST-LIVO2的地图坐标系)
      └── aft_mapped (FAST-LIVO2的位姿估计坐标系，动态)
          └── base_link (机器人基座坐标系)
```

## 影响 aft_mapped 坐标的因素

### 1. FAST-LIVO2 内部状态更新（主要因素）

#### 1.1 `_state.pos_end` 的更新

`aft_mapped` 的坐标直接来源于 FAST-LIVO2 的内部状态 `_state.pos_end`（在 `LIVMapper.cpp` 中）：

```cpp
// LIVMapper.cpp:1343
transform.setOrigin(tf::Vector3(_state.pos_end(0), _state.pos_end(1), _state.pos_end(2)));
```

`_state.pos_end` 通过以下方式更新：

#### 1.2 IMU 传播（IMU_Processing.cpp）

- **位置**：`src/IMU_Processing.cpp:211`
- **更新方式**：
  ```cpp
  state_inout.pos_end = state_inout.pos_end + state_inout.vel_end * dt;
  ```
- **影响**：IMU 数据会持续传播位置，导致 `aft_mapped` 移动
- **频率**：IMU 频率（通常 200-400Hz）

#### 1.3 ICP 匹配更新（voxel_map.cpp）

- **位置**：`src/voxel_map.cpp:474`
- **更新方式**：
  ```cpp
  state_ += solution;  // solution 来自 EKF 更新
  ```
- **影响**：ICP 匹配会优化位姿估计，导致 `aft_mapped` 位置调整
- **频率**：LiDAR 频率（通常 10-20Hz）
- **说明**：这是重定位模式的核心功能，通过 ICP 匹配来精确定位

#### 1.4 VIO 更新（vio.cpp）

- **位置**：`src/vio.cpp:1502`
- **更新方式**：
  ```cpp
  (*state) += solution;  // solution 来自视觉-惯性优化
  ```
- **影响**：视觉-惯性融合会更新位姿
- **频率**：相机频率（通常 30-60Hz）

#### 1.5 坐标系变换（LIVMapper.cpp）

- **位置**：`src/LIVMapper.cpp:234`
- **更新方式**：
  ```cpp
  _state.pos_end = G_R_I0 * _state.pos_end;
  ```
- **影响**：坐标系对齐时的变换

### 2. initial_pose_handler 的 TF 发布

#### 2.1 `map -> aft_mapped` TF

- **位置**：`scripts/initial_pose_handler.py:296-299`
- **作用**：设置 `aft_mapped` 在 `map` 坐标系中的位置
- **更新频率**：100Hz（持续发布）
- **时间戳**：+2ms（未来时间戳，提高优先级）

```python
aft_mapped_transform.transform.translation.x = camera_init_transform.transform.translation.x
aft_mapped_transform.transform.translation.y = camera_init_transform.transform.translation.y
aft_mapped_transform.transform.translation.z = camera_init_transform.transform.translation.z
```

#### 2.2 `camera_init -> aft_mapped` TF（单位变换）

- **位置**：`scripts/initial_pose_handler.py:304-316`
- **作用**：覆盖 FAST-LIVO2 发布的 `camera_init -> aft_mapped` 动态 TF
- **更新频率**：100Hz（持续发布）
- **时间戳**：+5ms（未来时间戳，最高优先级）

```python
camera_init_to_aft_mapped_transform.transform.translation.x = 0.0
camera_init_to_aft_mapped_transform.transform.translation.y = 0.0
camera_init_to_aft_mapped_transform.transform.translation.z = 0.0
```

### 3. FAST-LIVO2 的动态 TF 发布

#### 3.1 `camera_init -> aft_mapped` TF

- **位置**：`src/LIVMapper.cpp:1349`
- **发布频率**：约 10Hz（LiDAR 频率）
- **时间戳**：`ros::Time::now()`（当前时间）
- **内容**：基于 `_state.pos_end` 和 `geoQuat`

```cpp
br.sendTransform(tf::StampedTransform(transform, odomAftMapped.header.stamp, "camera_init", "aft_mapped"));
```

### 4. TF 优先级规则

ROS TF 系统使用以下规则确定使用哪个 TF：

1. **时间戳优先级**：时间戳越新（越大），优先级越高
2. **发布频率**：发布频率越高，时间戳越新
3. **发布顺序**：相同时间戳时，后发布的覆盖先发布的

当前设置：
- `initial_pose_handler`：100Hz，时间戳 +2ms 和 +5ms（未来时间戳）
- FAST-LIVO2：约 10Hz，时间戳 `now()`（当前时间）

**结果**：`initial_pose_handler` 的 TF 应该能够覆盖 FAST-LIVO2 的动态 TF，但 FAST-LIVO2 的 `_state.pos_end` 仍在持续更新。

## 为什么 aft_mapped 仍在移动？

### 原因分析

1. **FAST-LIVO2 内部状态持续更新**：
   - `_state.pos_end` 通过 IMU、ICP、VIO 持续更新
   - 即使我们覆盖了 TF，FAST-LIVO2 的内部状态仍在变化

2. **TF 覆盖不完全**：
   - 虽然我们发布了 `camera_init -> aft_mapped` 的单位变换
   - 但 FAST-LIVO2 仍会发布新的 TF，时间戳可能比我们的更新

3. **ICP 匹配的正常行为**：
   - 在重定位模式下，ICP 匹配会持续优化位姿
   - 这是正常的重定位行为，表示系统在工作

### 移动幅度判断

- **正常**：移动幅度 < 1cm（毫米级），表示 ICP 匹配在收敛
- **异常**：移动幅度 > 10cm，可能是：
  - 初始位姿设置不准确
  - 地图与当前环境不匹配
  - ICP 匹配参数需要调整

## 如何固定 aft_mapped？

### 方案 1：提高 TF 发布优先级（当前方案）

- **优点**：简单，不需要修改 FAST-LIVO2 源码
- **缺点**：可能无法完全固定，因为 FAST-LIVO2 内部状态仍在更新
- **实现**：提高发布频率和时间戳优先级

### 方案 2：修改 FAST-LIVO2 源码（不推荐）

- **方法**：在重定位模式下禁用 `_state.pos_end` 的更新
- **缺点**：会破坏重定位功能，ICP 匹配无法工作
- **影响**：系统无法进行重定位

### 方案 3：接受移动（推荐）

- **说明**：在重定位模式下，`aft_mapped` 的移动是正常的
- **原因**：ICP 匹配需要持续优化位姿
- **建议**：只要移动幅度在毫米级，就是正常的

## 监控 aft_mapped 的变化

### 使用监控脚本

```bash
rosrun fast_livo monitor_aft_mapped.py
```

### 使用 tf_echo

```bash
rosrun tf tf_echo map aft_mapped
```

### 检查 TF 树

```bash
rosrun tf view_frames
```

## 调试步骤

### 1. 检查 initial_pose_handler 是否运行

```bash
rosnode list | grep initial_pose_handler
```

### 2. 检查 TF 发布频率

```bash
rostopic hz /tf
```

### 3. 检查 camera_init -> aft_mapped 的 TF

```bash
rosrun tf tf_echo camera_init aft_mapped
```

如果显示为单位变换（0, 0, 0），说明我们的 TF 正在覆盖 FAST-LIVO2 的动态 TF。

### 4. 检查 aft_mapped 的移动幅度

```bash
rosrun fast_livo monitor_aft_mapped.py
```

观察移动幅度：
- < 1cm：正常
- > 10cm：异常，需要检查初始位姿和地图

## 总结

影响 `aft_mapped` 坐标的主要因素：

1. **FAST-LIVO2 内部状态更新**（主要）：
   - IMU 传播
   - ICP 匹配
   - VIO 更新

2. **TF 发布**：
   - `initial_pose_handler` 的 TF（100Hz，未来时间戳）
   - FAST-LIVO2 的动态 TF（10Hz，当前时间戳）

3. **TF 优先级**：
   - 时间戳越新，优先级越高
   - `initial_pose_handler` 的 TF 应该能够覆盖 FAST-LIVO2 的动态 TF

**结论**：`aft_mapped` 的移动是重定位模式的正常行为。只要移动幅度在毫米级，就表示系统正常工作。如果移动幅度很大，需要检查初始位姿设置和地图匹配情况。

