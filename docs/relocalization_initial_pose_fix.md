# 2D Pose Estimate 重定位修复说明

## 问题描述

使用 2D Pose Estimate 设置初始位姿后，`base_link` 动了一下又立即回到原来位置，无法在所选位置开始 ICP 匹配。

## 问题原因

1. `initial_pose_handler` 只发布了 `camera_init -> base_link` 的静态 TF
2. 但 FAST-LIVO2 的位姿估计基于 `aft_mapped` 坐标系
3. FAST-LIVO2 会持续发布 `camera_init -> aft_mapped` 的动态 TF，覆盖静态 TF
4. 因此需要直接设置 `aft_mapped` 的初始位置

## 解决方案

修改 `initial_pose_handler.py` 来：
1. **发布 `camera_init -> aft_mapped` 的静态 TF**（关键！）
   - 这是 FAST-LIVO2 位姿估计的坐标系
   - 设置它会重置 FAST-LIVO2 的初始位姿
   - FAST-LIVO2 会从新的初始位置开始进行 ICP 匹配

2. **考虑物理结构偏移**
   - `aft_mapped` 对应传感器位置（camera）
   - `base_link` 是底盘中心，位于传感器下方 1.8m，后方 0.4m
   - 从 `base_link` 到 `aft_mapped` 的变换：x=0.4, y=0, z=1.8
   - 因此 `aft_mapped` 的位置 = `base_link` 位置 + (0.4, 0, 1.8)

3. **同时发布 `camera_init -> base_link` 的静态 TF**（用于显示）

## 修改内容

### 1. `initial_pose_handler.py`

- 添加 `aft_mapped_frame` 参数
- 发布 `camera_init -> aft_mapped` 的静态 TF（关键）
- 考虑物理结构偏移（+0.4m x, +1.8m z）
- 多次发布 TF 以确保覆盖

### 2. `mapping_mid360_relocalization.launch`

- 添加 `aft_mapped_frame` 参数配置

## 使用方法

1. **重启 launch 文件**：
   ```bash
   roslaunch fast_livo mapping_mid360_relocalization.launch
   ```

2. **在 RViz 中使用 2D Pose Estimate**：
   - 点击工具栏中的 "2D Pose Estimate" 按钮
   - 在地图上点击并拖动，设置机器人的初始位置和朝向

3. **验证效果**：
   - 查看终端输出，应该看到：
     ```
     Published static transform: camera_init -> aft_mapped (关键：重置 FAST-LIVO2 位姿)
     ```
   - `base_link` 应该保持在所选位置
   - FAST-LIVO2 会从新位置开始进行 ICP 匹配

## 技术细节

### TF 树结构

重定位模式下的 TF 树：
```
camera_init (map frame)
  └── aft_mapped (FAST-LIVO2 位姿估计)
      └── base_link (通过 static_transform_publisher: -0.4, 0, -1.8)
```

### 坐标系关系

- **camera_init**: 地图坐标系（固定）
- **aft_mapped**: FAST-LIVO2 位姿估计坐标系（动态，但可以通过静态 TF 重置）
- **base_link**: 机器人底盘中心（通过 `aft_mapped` 计算）

### 物理结构偏移

- 传感器（camera/lidar）位置 = `aft_mapped`
- 底盘中心（base_link）位置 = `aft_mapped` + (-0.4, 0, -1.8)
- 因此：`aft_mapped` = `base_link` + (0.4, 0, 1.8)

## 故障排查

### 问题1: base_link 仍然回到原位置

**可能原因**：
- `aft_mapped` 的静态 TF 被 FAST-LIVO2 的动态 TF 覆盖
- 静态 TF 发布频率不够

**解决方法**：
1. 检查终端输出，确认 "Published static transform: camera_init -> aft_mapped"
2. 运行 `rosrun tf view_frames` 查看 TF 树
3. 检查是否有其他节点在发布 `camera_init -> aft_mapped` 的 TF

### 问题2: 位置偏移不正确

**可能原因**：
- 物理结构参数不匹配

**解决方法**：
1. 检查 launch 文件中的 `aft_mapped_to_base_link` 静态 TF 参数
2. 确认偏移量是否正确（-0.4, 0, -1.8）
3. 根据实际物理结构调整 `initial_pose_handler.py` 中的偏移量

## 相关文件

- `scripts/initial_pose_handler.py` - 初始位姿处理脚本（已修改）
- `launch/mapping_mid360_relocalization.launch` - 重定位启动文件（已修改）
- `docs/troubleshoot_2d_pose_estimate.md` - 2D Pose Estimate 故障排查指南

