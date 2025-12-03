# 时间同步问题快速修复指南

## 🚀 一键修复（最简单！）

### ⭐ 方法1：Python 一键脚本（推荐）

**只需一条命令，自动完成所有步骤！**

```bash
# 1. 启动 FAST-LIVO2
roslaunch fast_livo mapping_mid360.launch

# 2. 在另一个终端运行一键修复（等待30秒，自动完成）
rosrun fast_livo quick_fix_time_sync.py

# 3. 重启 FAST-LIVO2
# 完成！就这么简单！
```

**功能：**
- ✅ 自动采集30秒数据
- ✅ 自动计算最优偏移值
- ✅ 自动更新配置文件
- ✅ 自动备份原配置

### 方法2：Shell 一键脚本

```bash
# 1. 启动 FAST-LIVO2
roslaunch fast_livo mapping_mid360.launch

# 2. 运行一键修复脚本
bash src/FAST-LIVO2/scripts/fix_time_sync.sh

# 3. 重启 FAST-LIVO2
```

---

## 📊 其他方法（如果需要手动控制）

### 方法3：自动校准 + 手动更新

```bash
# 1. 启动 FAST-LIVO2
roslaunch fast_livo mapping_mid360.launch

# 2. 在另一个终端运行自动校准（等待30秒）
rosrun fast_livo auto_calibrate_time_offset.py

# 3. 查看推荐值
cat /tmp/time_offset_calibration_result.txt

# 4. 更新配置文件
vim src/FAST-LIVO2/config/mid360.yaml
# 将 img_time_offset 设置为推荐值

# 5. 重启 FAST-LIVO2
```

### 方法2：实时监控调整

```bash
# 1. 启动 FAST-LIVO2
roslaunch fast_livo mapping_mid360.launch

# 2. 运行实时监控工具
rosrun fast_livo monitor_time_sync_realtime.py

# 3. 观察时间差，手动调整配置
# 如果时间差为 +170344.5 秒，则设置 img_time_offset = -170344.5
```

## 📊 诊断工具

### 检查当前同步状态

```bash
# 简单检查
rosrun fast_livo check_time_sync_simple.py

# 详细检查
rosrun fast_livo check_time_sync.py
```

### 实时监控

```bash
rosrun fast_livo monitor_time_sync_realtime.py
```

## ⚙️ 配置文件位置

- `config/mid360.yaml` - 主配置文件
- `config/mid360_relocalization.yaml` - 重定位配置文件

## 🔧 配置参数

```yaml
time_offset:
  img_time_offset: -170344.5  # 根据校准结果设置（秒）
  imu_time_offset: 0.0
  exposure_time_init: 0.0
```

## ✅ 验证修复

修复后检查：
1. 日志中不再出现 "Waiting for newer data"
2. `/cloud_registered` 和 `/rgb_img` 正常发布
3. 时间差 < 10ms（使用监控工具检查）

## 📚 详细文档

完整解决方案请参考：`docs/time_sync_solution.md`

