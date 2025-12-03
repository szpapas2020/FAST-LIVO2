# 修复地图晃动问题

## 问题描述

在运行 `roslaunch fast_livo mapping_mid360_relocalization.launch` 后，PCD 地图随着激光雷达和摄像头晃动，地图应该是静止的。

## 问题原因

地图晃动通常是由以下原因造成的：

1. **RViz 的 Fixed Frame 设置错误**
   - 如果 Fixed Frame 设置为 `base_link` 或其他动态坐标系，地图会随着机器人移动
   - 应该设置为 `camera_init`（固定坐标系）

2. **PCD 地图的 frame_id 设置错误**
   - 地图的 frame_id 应该是 `camera_init`（固定坐标系）
   - 不应该使用 `base_link`、`aft_mapped` 等动态坐标系

3. **RViz 显示项的 Use Fixed Frame 设置**
   - PCDMap 显示项的 "Use Fixed Frame" 应该为 `true`

## 解决方案

### 1. 检查并设置 RViz 的 Fixed Frame

在 RViz 中：
1. 查看左下角的 "Global Options"
2. 确认 "Fixed Frame" 设置为 `camera_init`
3. 如果设置为其他值（如 `base_link`、`aft_mapped`），请改为 `camera_init`

### 2. 检查 PCD 地图的 frame_id

```bash
# 检查 /pcd_map 话题的 frame_id
rostopic echo /pcd_map -n 1 | grep frame_id

# 应该显示：frame_id: "camera_init"
```

如果 frame_id 不是 `camera_init`，检查 launch 文件中的配置：
```xml
<node pkg="fast_livo" type="publish_pcd_map_simple.py" name="pcd_map_publisher">
    <param name="frame_id" value="camera_init" />  <!-- 必须是 camera_init -->
    ...
</node>
```

### 3. 检查 RViz 显示项设置

在 RViz 中：
1. 找到 "PCDMap" 显示项
2. 确认 "Use Fixed Frame" 设置为 `true`
3. 如果为 `false`，请改为 `true`

### 4. 重新加载 RViz 配置

如果修改了 RViz 设置：
1. File → Save Config As → 保存配置
2. 或者重新加载配置文件：
   ```bash
   roslaunch fast_livo mapping_mid360_relocalization.launch
   ```

## 坐标系说明

### 固定坐标系（地图应该使用）

- **camera_init**: 地图坐标系，固定不变
  - PCD 地图应该使用此坐标系
  - RViz 的 Fixed Frame 应该设置为 `camera_init`

### 动态坐标系（地图不应该使用）

- **base_link**: 机器人底盘坐标系，随机器人移动
- **aft_mapped**: FAST-LIVO2 位姿估计坐标系，随机器人移动
- **camera**: 相机坐标系，随机器人移动
- **livox**: 激光雷达坐标系，随机器人移动

## 验证方法

### 方法1: 检查 TF 树

```bash
# 查看 TF 树
rosrun tf view_frames
evince frames.pdf

# 应该看到：
# camera_init (固定)
#   ├── aft_mapped (动态)
#   │   └── base_link (动态)
#   └── (PCD 地图固定在 camera_init)
```

### 方法2: 检查话题 frame_id

```bash
# 检查 PCD 地图的 frame_id
rostopic echo /pcd_map -n 1 | grep frame_id

# 应该显示：frame_id: "camera_init"
```

### 方法3: 在 RViz 中观察

1. 设置 Fixed Frame 为 `camera_init`
2. 观察 PCD 地图是否静止
3. 移动机器人时，地图应该保持静止，只有机器人位姿在移动

## 常见问题

### 问题1: 地图仍然晃动

**可能原因**：
- RViz 的 Fixed Frame 没有正确设置
- 有其他显示项使用了错误的坐标系

**解决方法**：
1. 确认 Fixed Frame 为 `camera_init`
2. 检查所有 PointCloud2 显示项的 frame_id
3. 重启 RViz

### 问题2: 地图位置不正确

**可能原因**：
- 地图坐标系与机器人坐标系不匹配
- 初始位姿设置不正确

**解决方法**：
1. 使用 2D Pose Estimate 设置正确的初始位姿
2. 确保地图坐标系与建图时一致

## 相关文件

- `scripts/publish_pcd_map_simple.py` - PCD 地图发布脚本
- `rviz_cfg/fast_livo2_map.rviz` - RViz 配置文件
- `launch/mapping_mid360_relocalization.launch` - 重定位启动文件

## 总结

地图应该固定在 `camera_init` 坐标系中，不应该随传感器移动。如果地图晃动：

1. ✅ 检查 RViz 的 Fixed Frame 是否为 `camera_init`
2. ✅ 检查 PCD 地图的 frame_id 是否为 `camera_init`
3. ✅ 检查 PCDMap 显示项的 "Use Fixed Frame" 是否为 `true`
4. ✅ 重启系统并重新加载配置

