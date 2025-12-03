# PCD 地图彩色显示配置指南

## 问题描述

PCD 地图在 RViz 中显示为灰白色，而不是彩色。

## 解决方案

### 1. 检查 PCD 文件是否有颜色信息

```bash
# 运行颜色检查脚本
python3 /home/fsy/ros_ws/src/FAST-LIVO2/scripts/check_pcd_colors.py
```

如果输出显示 `有颜色: True`，说明 PCD 文件包含颜色信息。

### 2. 检查点云话题格式

```bash
# 检查 /pcd_map 话题的点云格式
rosrun fast_livo check_pcd_map_topic.py
```

应该看到：
- ✓ 找到 'rgb' 字段
- 或 ✓ 找到 'r', 'g', 'b' 字段

### 3. 确保 RViz 配置正确

在 RViz 中：
1. 找到 "PCDMap" 显示项
2. 检查 `Color Transformer` 设置为 `RGB8`
3. 如果设置为其他值（如 `FlatColor`, `Intensity`），请改为 `RGB8`

### 4. 重启节点

修改代码后，需要重启 `pcd_map_publisher` 节点：

```bash
# 方法1: 重启整个 launch 文件
# Ctrl+C 停止当前 launch，然后重新运行
roslaunch fast_livo mapping_mid360_relocalization.launch

# 方法2: 只重启 pcd_map_publisher 节点
rosnode kill /pcd_map_publisher
# 节点会自动重启（如果 launch 文件中有 respawn 参数）
```

### 5. 验证颜色显示

重启后，在 RViz 中应该看到：
- 点云显示为彩色（而不是灰白色）
- 不同区域有不同的颜色
- 颜色与建图时的相机图像颜色一致

## 技术细节

### RGB 格式说明

点云发布脚本使用两种 RGB 格式之一：

1. **打包格式**（推荐）：
   - 字段名：`rgb`
   - 数据类型：`UINT32`
   - 格式：`0xAABBGGRR`（A=透明度，B=蓝色，G=绿色，R=红色）
   - RViz RGB8 转换器可以直接识别

2. **分离格式**：
   - 字段名：`r`, `g`, `b`
   - 数据类型：`UINT8`
   - RViz RGB8 转换器也可以识别，但可能需要额外配置

### 代码修改

`publish_pcd_map_simple.py` 已更新为使用打包的 RGB 格式：

```python
# 打包 RGB 为 UINT32 格式：0xAABBGGRR
rgb_packed = (255 << 24) | (int(b) << 16) | (int(g) << 8) | int(r)
points_list.append([x, y, z, rgb_packed])

fields = [
    point_cloud2.PointField('x', 0, point_cloud2.PointField.FLOAT32, 1),
    point_cloud2.PointField('y', 4, point_cloud2.PointField.FLOAT32, 1),
    point_cloud2.PointField('z', 8, point_cloud2.PointField.FLOAT32, 1),
    point_cloud2.PointField('rgb', 12, point_cloud2.PointField.UINT32, 1),
]
```

## 故障排查

### 问题1: 点云仍然显示为灰白色

**可能原因**：
- RViz 的 Color Transformer 设置不正确
- 点云节点没有重新发布

**解决方法**：
1. 在 RViz 中手动将 Color Transformer 改为 `RGB8`
2. 重启 `pcd_map_publisher` 节点
3. 检查节点日志，确认 "Point cloud has RGB color information"

### 问题2: 只有部分点云显示为彩色

**可能原因**：
- 多个点云话题同时显示
- 不同点云话题使用了不同的颜色设置

**解决方法**：
1. 检查 RViz 中有哪些 PointCloud2 显示项
2. 确认 `/pcd_map` 话题的显示项使用 `RGB8`
3. 其他点云话题（如 `/cloud_registered`）可能使用不同的颜色设置

### 问题3: 颜色显示不正确

**可能原因**：
- RGB 通道顺序错误
- 颜色值范围不正确

**解决方法**：
1. 检查 PCD 文件的颜色值范围（应该是 [0, 1]）
2. 确认颜色转换代码正确（乘以 255 转换为 [0, 255]）
3. 检查 RGB 打包顺序是否正确

## 相关文件

- `scripts/publish_pcd_map_simple.py` - PCD 地图发布脚本
- `scripts/check_pcd_colors.py` - PCD 颜色检查脚本
- `scripts/check_pcd_map_topic.py` - 点云话题格式检查脚本
- `rviz_cfg/fast_livo2_map.rviz` - RViz 配置文件

