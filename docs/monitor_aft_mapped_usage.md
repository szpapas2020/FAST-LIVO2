# aft_mapped 坐标监控使用说明

## 概述

监控 `aft_mapped` 坐标系在 `map` 坐标系中的位置和姿态变化，用于验证 2D Pose Estimate 后 `aft_mapped` 是否固定在用户选择的坐标。

## 使用方法

### 方法1: Python 监控脚本（推荐）

功能最完整，显示位置、姿态和变化量。

```bash
rosrun fast_livo monitor_aft_mapped.py
```

**参数**（可选）：
- `map_frame`: 地图坐标系名称（默认: `map`）
- `aft_mapped_frame`: aft_mapped 坐标系名称（默认: `aft_mapped`）
- `update_rate`: 更新频率，Hz（默认: `10.0`）
- `show_delta`: 是否显示变化量（默认: `true`）

**示例**：
```bash
# 使用默认参数
rosrun fast_livo monitor_aft_mapped.py

# 自定义参数
rosrun fast_livo monitor_aft_mapped.py _map_frame:=map _aft_mapped_frame:=aft_mapped _update_rate:=20.0
```

**输出示例**：
```
================================================================================
aft_mapped 坐标监控
================================================================================
时间: 1764661234.567
坐标系: map -> aft_mapped
--------------------------------------------------------------------------------
位置 (m):
  X:    5.0000  [Δ:  +0.0000]
  Y:    2.0000  [Δ:  +0.0000]
  Z:    0.0000  [Δ:  +0.0000]
--------------------------------------------------------------------------------
姿态 (度):
  Roll:     0.00°
  Pitch:    0.00°
  Yaw:     45.00°  [Δ:  +0.00°]
--------------------------------------------------------------------------------
状态: ✓ 静止
================================================================================
按 Ctrl+C 退出
```

### 方法2: Shell 脚本（简单）

使用 `rosrun tf tf_echo` 命令。

```bash
rosrun fast_livo monitor_aft_mapped_simple.sh
```

或直接使用：
```bash
rosrun tf tf_echo map aft_mapped
```

### 方法3: 命令行工具

使用 ROS 命令行工具：

```bash
# 查看 TF 树
rosrun tf view_frames
evince frames.pdf

# 实时查看变换
rosrun tf tf_echo map aft_mapped

# 查看 TF 话题
rostopic echo /tf | grep -A 10 aft_mapped
```

## 监控内容

### 位置信息
- **X, Y, Z**: `aft_mapped` 在 `map` 坐标系中的位置（米）
- **ΔX, ΔY, ΔZ**: 位置变化量（米）

### 姿态信息
- **Roll, Pitch, Yaw**: `aft_mapped` 的姿态（度）
- **ΔYaw**: 姿态变化量（度）

### 状态指示
- **✓ 静止**: 位置变化小于 1mm
- **⚠️ 移动中**: 位置变化大于 1mm

## 验证 2D Pose Estimate

### 预期行为

1. **设置初始位姿前**：
   - 可能无法获取 `map -> aft_mapped` 的变换
   - 或 `aft_mapped` 在 PCD 原点（0, 0, 0）

2. **设置初始位姿后**：
   - `aft_mapped` 应该固定在用户选择的坐标
   - 位置变化量应该为 0（或非常小，< 1mm）
   - 状态显示为 "✓ 静止"

3. **如果 `aft_mapped` 仍在移动**：
   - 检查 `initial_pose_handler` 是否正常运行
   - 检查静态 TF 是否持续发布（10Hz）
   - 检查是否有其他节点在发布 `aft_mapped` 相关的 TF

## 故障排查

### 问题1: 无法获取 TF 变换

**错误信息**：
```
错误: 无法获取 map -> aft_mapped 的变换
```

**解决方法**：
1. 确认 FAST-LIVO2 节点正在运行
2. 确认已设置初始位姿（2D Pose Estimate）
3. 检查 TF 树：
   ```bash
   rosrun tf view_frames
   ```

### 问题2: `aft_mapped` 仍在移动

**症状**：
- 监控显示位置变化量不为 0
- 状态显示为 "⚠️ 移动中"

**可能原因**：
1. `initial_pose_handler` 没有正常运行
2. 静态 TF 没有持续发布
3. FAST-LIVO2 的动态 TF 覆盖了静态 TF

**解决方法**：
1. 检查 `initial_pose_handler` 节点：
   ```bash
   rosnode info /initial_pose_handler
   ```
2. 检查静态 TF 发布：
   ```bash
   rostopic echo /tf_static | grep aft_mapped
   ```
3. 检查动态 TF：
   ```bash
   rostopic echo /tf | grep aft_mapped
   ```
4. 重启系统并重新设置初始位姿

### 问题3: 坐标不正确

**症状**：
- `aft_mapped` 的位置不是用户选择的坐标

**解决方法**：
1. 确认用户选择的坐标是否正确
2. 检查 `initial_pose_handler` 的日志输出
3. 重新设置初始位姿

## 相关文件

- `scripts/monitor_aft_mapped.py` - Python 监控脚本
- `scripts/monitor_aft_mapped_simple.sh` - Shell 监控脚本
- `scripts/initial_pose_handler.py` - 初始位姿处理节点

## 总结

使用监控脚本可以：
- ✅ 实时查看 `aft_mapped` 的位置和姿态
- ✅ 检测 `aft_mapped` 是否在移动
- ✅ 验证 2D Pose Estimate 是否正常工作
- ✅ 调试 TF 相关问题

如果 `aft_mapped` 固定在用户选择的坐标（变化量 < 1mm），说明 2D Pose Estimate 工作正常。

