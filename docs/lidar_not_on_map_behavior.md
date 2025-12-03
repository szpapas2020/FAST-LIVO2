# 激光雷达实时数据不在 PCD 地图上时的行为分析

## 概述

当激光雷达实时数据不在 PCD 地图上时（例如：机器人移动到了地图范围外，或初始位姿设置错误），FAST-LIVO2 的重定位系统会表现出特定的行为。本文档详细分析这种情况下的系统行为。

## 可能的原因

1. **初始位姿设置错误**：2D Pose Estimate 设置的初始位置与实际位置不符
2. **机器人移动出地图范围**：机器人移动到了 PCD 地图覆盖范围之外
3. **地图与当前环境不匹配**：PCD 地图是旧环境，当前环境已发生变化
4. **地图加载失败**：PCD 地图文件损坏或格式不正确

## 系统行为分析

### 1. ICP 匹配失败或效果很差

#### 1.1 有效特征点数量减少

**代码位置**：`src/voxel_map.cpp:403-405`

```cpp
effct_feat_num_ = ptpl_list_.size();
cout << "[ LIO ] Raw feature num: " << feats_undistort_->size() 
     << ", downsampled feature num:" << feats_down_size_ 
     << " effective feature num: " << effct_feat_num_ 
     << " average residual: " << total_residual / effct_feat_num_ << endl;
```

**行为**：
- `effct_feat_num_`（有效特征点数量）会显著减少
- 正常情况下应该有数百到数千个有效特征点
- 当数据不在地图上时，可能只有几十个或更少的有效特征点
- 甚至可能为 0（完全无法匹配）

#### 1.2 残差（Residual）增大

**代码位置**：`src/voxel_map.cpp:399-402`

```cpp
for (int i = 0; i < ptpl_list_.size(); i++)
{
    total_residual += fabs(ptpl_list_[i].dis_to_plane_);
}
```

**行为**：
- 平均残差（average residual）会显著增大
- 正常情况下应该在 0.01-0.1 米范围内
- 当数据不在地图上时，残差可能达到 0.5 米或更大
- 这表示点云与地图平面的距离很大

#### 1.3 ICP 匹配无法收敛

**代码位置**：`src/voxel_map.cpp:477`

```cpp
if ((rot_add.norm() * 57.3 < 0.01) && (t_add.norm() * 100 < 0.015)) 
{ 
    flg_EKF_converged = true; 
}
```

**行为**：
- EKF 迭代可能无法收敛（`flg_EKF_converged` 保持为 `false`）
- 即使达到最大迭代次数（`max_iterations`），位姿更新仍然很大
- 系统会继续运行，但位姿估计质量很差

### 2. 位姿估计主要依赖 IMU 传播

#### 2.1 IMU 传播成为主要位置更新源

**代码位置**：`src/IMU_Processing.cpp:211`

```cpp
state_inout.pos_end = state_inout.pos_end + state_inout.vel_end * dt;
```

**行为**：
- 当 ICP 匹配失败时，位姿更新主要来自 IMU 传播
- IMU 传播会持续更新位置，但会累积误差（漂移）
- 位姿估计会逐渐偏离真实位置

#### 2.2 位姿估计会漂移

**行为**：
- `aft_mapped` 的坐标会持续移动（漂移）
- 移动方向取决于 IMU 测量的速度和加速度
- 漂移速度取决于机器人的实际运动状态
- 如果机器人静止，位姿仍可能因为 IMU 噪声而漂移

### 3. 系统继续运行但质量下降

#### 3.1 系统不会崩溃

**代码位置**：`src/LIVMapper.cpp:343-347`

```cpp
if (feats_undistort->empty() || (feats_undistort == nullptr)) 
{
    std::cout << "[ LIO ]: No point!!!" << std::endl;
    return;
}
```

**行为**：
- 系统会继续运行，不会崩溃
- 即使没有有效特征点，系统也会继续处理下一帧
- 但位姿估计质量会显著下降

#### 3.2 位姿发布频率正常

**代码位置**：`src/LIVMapper.cpp:409`

```cpp
publish_odometry(pubOdomAftMapped);
```

**行为**：
- `/aft_mapped_to_init` 话题仍会正常发布
- 发布频率保持正常（约 10Hz）
- 但位姿数据质量很差，不可靠

### 4. 可能出现的警告和错误

#### 4.1 终端输出示例

**正常情况**：
```
[ LIO ] Raw feature num: 10000, downsampled feature num: 5000 
effective feature num: 2000 average residual: 0.05
```

**数据不在地图上时**：
```
[ LIO ] Raw feature num: 10000, downsampled feature num: 5000 
effective feature num: 50 average residual: 0.8
```

或更严重的情况：
```
[ LIO ] Raw feature num: 10000, downsampled feature num: 5000 
effective feature num: 0 average residual: nan
```

#### 4.2 可能的警告信息

- `effective feature num` 很小（< 100）
- `average residual` 很大（> 0.5 米）
- 位姿估计会持续漂移

## 诊断方法

### 1. 检查有效特征点数量

**方法**：查看终端输出中的 `effective feature num`

```bash
# 查看 FAST-LIVO2 节点的输出
rosnode info /laserMapping | grep -A 5 "Publications"
```

**判断标准**：
- **正常**：`effective feature num` > 500
- **警告**：`effective feature num` < 100
- **严重**：`effective feature num` = 0

### 2. 检查平均残差

**方法**：查看终端输出中的 `average residual`

**判断标准**：
- **正常**：`average residual` < 0.1 米
- **警告**：`average residual` > 0.3 米
- **严重**：`average residual` > 1.0 米

### 3. 监控 aft_mapped 的移动

**方法**：使用监控脚本

```bash
rosrun fast_livo monitor_aft_mapped.py
```

**判断标准**：
- **正常**：移动幅度 < 1cm（毫米级）
- **警告**：移动幅度 1-10cm
- **严重**：移动幅度 > 10cm（可能不在地图上）

### 4. 检查实时点云与地图的重叠

**方法**：在 RViz 中同时显示：
- `/pcd_map`：PCD 地图点云
- `/cloud_registered`：实时激光雷达点云

**判断标准**：
- **正常**：实时点云与地图点云重叠良好
- **警告**：实时点云与地图点云部分重叠
- **严重**：实时点云与地图点云完全不重叠

## 解决方案

### 方案 1：重新设置初始位姿（推荐）

**适用场景**：初始位姿设置错误

**步骤**：
1. 在 RViz 中使用 2D Pose Estimate 重新设置初始位姿
2. 确保初始位姿尽可能准确
3. 观察 `effective feature num` 是否增加

### 方案 2：检查地图范围

**适用场景**：机器人移动出地图范围

**步骤**：
1. 检查 PCD 地图的覆盖范围
2. 确保机器人在地图范围内
3. 如果超出范围，需要扩展地图或重新建图

### 方案 3：重新建图

**适用场景**：地图与当前环境不匹配

**步骤**：
1. 使用建图模式重新生成地图
2. 确保地图覆盖当前环境
3. 使用新地图进行重定位

### 方案 4：调整 ICP 匹配参数

**适用场景**：地图匹配困难但仍有部分重叠

**配置文件**：`config/mid360_relocalization.yaml`

**可调整参数**：
```yaml
lio:
  max_iterations: 5        # 增加迭代次数
  dept_err: 0.02          # 调整深度误差阈值
  beam_err: 0.15          # 调整光束误差阈值
  min_eigen_value: 0.005  # 调整最小特征值
  voxel_size: 0.5         # 调整体素大小
  max_layer: 2            # 调整最大层数
  max_points_num: 50      # 调整最大点数
```

**注意**：调整参数需要谨慎，建议先尝试方案 1-3。

## 预防措施

### 1. 准确设置初始位姿

- 使用 2D Pose Estimate 时，确保位置和朝向尽可能准确
- 初始位姿误差应 < 1 米，角度误差应 < 30 度

### 2. 确保地图覆盖范围足够

- 建图时确保地图覆盖所有可能的工作区域
- 在地图边界处留出足够的缓冲区

### 3. 定期更新地图

- 如果环境发生变化，及时更新地图
- 使用最新的地图进行重定位

### 4. 监控系统状态

- 定期检查 `effective feature num` 和 `average residual`
- 使用监控脚本持续监控 `aft_mapped` 的移动

## 总结

当激光雷达实时数据不在 PCD 地图上时：

1. **ICP 匹配失败**：有效特征点数量减少，残差增大
2. **位姿估计漂移**：主要依赖 IMU 传播，会累积误差
3. **系统继续运行**：不会崩溃，但位姿估计质量很差
4. **需要及时处理**：重新设置初始位姿或更新地图

**关键指标**：
- `effective feature num`：应该 > 500
- `average residual`：应该 < 0.1 米
- `aft_mapped` 移动幅度：应该 < 1cm

**建议**：定期监控这些指标，及时发现问题并采取相应措施。

