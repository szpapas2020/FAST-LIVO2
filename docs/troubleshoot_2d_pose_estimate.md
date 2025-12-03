# 2D Pose Estimate 故障排查指南

## 问题描述

在运行 `roslaunch fast_livo mapping_mid360_relocalization.launch` 后，RViz 中的 "2D Pose Estimate" 功能不起作用。

## 排查步骤

### 1. 检查节点是否运行

```bash
# 检查 initial_pose_handler 节点是否运行
rosnode list | grep initial_pose

# 应该看到：/initial_pose_handler
```

如果节点没有运行，检查 launch 文件是否正确启动。

### 2. 检查话题连接

```bash
# 检查 /initialpose 话题
rostopic info /initialpose

# 应该看到：
# Publishers: /rviz (RViz)
# Subscribers: /initial_pose_handler
```

### 3. 检查 RViz 配置

确保 RViz 的 Fixed Frame 设置为 `camera_init`：

1. 在 RViz 中，查看左下角的 "Global Options"
2. 确认 "Fixed Frame" 设置为 `camera_init`
3. 如果不同，请修改为 `camera_init`

### 4. 测试 2D Pose Estimate

1. **在 RViz 中**：
   - 点击工具栏中的 "2D Pose Estimate" 按钮（箭头图标）
   - 在地图上点击并拖动，设置机器人的位置和朝向
   - 应该看到终端输出调试信息

2. **检查终端输出**：
   如果功能正常，应该看到类似以下输出：
   ```
   ============================================================
   Received initial pose from RViz (2D Pose Estimate)
   Message frame_id: camera_init
   Expected map frame: camera_init
   Position: x=1.234, y=2.345, z=0.000
   Orientation: roll=0.000°, pitch=0.000°, yaw=45.000°
   Published static transform: camera_init -> base_link
   Published initial pose to /set_initial_pose
   ============================================================
   ✓ Initial pose set successfully!
   ```

### 5. 使用测试脚本验证

如果 RViz 中的 2D Pose Estimate 不起作用，可以使用测试脚本验证功能：

```bash
# 在另一个终端运行测试脚本
rosrun fast_livo test_initial_pose.py

# 应该看到 initial_pose_handler 节点的输出
```

### 6. 检查 TF 树

设置初始位姿后，检查 TF 树是否正确：

```bash
# 查看静态 TF
rostopic echo /tf_static -n 1 | grep -A 10 "camera_init\|base_link"

# 应该看到 camera_init -> base_link 的变换
```

### 7. 常见问题

#### 问题 1: 点击后没有任何反应

**可能原因**：
- RViz 的 Fixed Frame 设置不正确
- 话题没有正确连接

**解决方法**：
1. 检查 RViz 的 Fixed Frame 是否为 `camera_init`
2. 运行 `rostopic echo /initialpose` 并点击 2D Pose Estimate，看是否有消息发布

#### 问题 2: 看到错误信息 "Message frame_id != expected map frame"

**可能原因**：
- RViz 发布的 frame_id 与配置不匹配

**解决方法**：
- 脚本会自动处理，使用配置的 `map_frame`（`camera_init`）
- 如果仍有问题，检查 launch 文件中的 `map_frame` 参数

#### 问题 3: 设置了初始位姿但机器人位置没有变化

**可能原因**：
- FAST-LIVO2 的重定位功能可能需要其他触发方式
- 静态 TF 可能被其他节点覆盖

**解决方法**：
1. 检查是否有其他节点在发布 `camera_init -> base_link` 的 TF
2. 运行 `rosrun tf view_frames` 查看完整的 TF 树
3. 确保 FAST-LIVO2 的重定位模式已正确启用

### 8. 手动设置初始位姿

如果 2D Pose Estimate 仍然不起作用，可以手动发布初始位姿：

```bash
# 使用 rostopic pub 命令
rostopic pub /initialpose geometry_msgs/PoseWithCovarianceStamped "
{
  header: {
    stamp: {secs: 0, nsecs: 0},
    frame_id: 'camera_init'
  },
  pose: {
    pose: {
      position: {x: 1.0, y: 2.0, z: 0.0},
      orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
    },
    covariance: [0.25, 0.0, 0.0, 0.0, 0.0, 0.0,
                 0.0, 0.25, 0.0, 0.0, 0.0, 0.0,
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.06853891945200942]
  }
}" -1
```

### 9. 检查日志

查看 `initial_pose_handler` 节点的详细日志：

```bash
# 查看节点日志
rosnode info /initial_pose_handler

# 或者查看所有日志
rostopic echo /rosout | grep initial_pose_handler
```

## 预期行为

设置初始位姿后，应该：

1. ✅ 看到终端输出确认消息
2. ✅ 静态 TF `camera_init -> base_link` 被发布
3. ✅ 机器人在地图中的位置更新（在 RViz 中可以看到）
4. ✅ FAST-LIVO2 开始使用预加载的地图进行定位

## 相关文件

- `scripts/initial_pose_handler.py` - 初始位姿处理节点
- `scripts/test_initial_pose.py` - 测试脚本
- `rviz_cfg/fast_livo2_map.rviz` - RViz 配置文件
- `launch/mapping_mid360_relocalization.launch` - 重定位启动文件

## 联系支持

如果以上步骤都无法解决问题，请提供以下信息：

1. `rosnode list` 的输出
2. `rostopic info /initialpose` 的输出
3. `initial_pose_handler` 节点的日志输出
4. RViz 的 Fixed Frame 设置

