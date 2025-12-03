#!/bin/bash
# 一键修复时间同步问题
# 使用方法: ./fix_time_sync.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(dirname "$SCRIPT_DIR")/config"
CONFIG_FILE="$CONFIG_DIR/mid360.yaml"
RELOCALIZATION_CONFIG="$CONFIG_DIR/mid360_relocalization.yaml"

echo "==========================================================="
echo "🚀 FAST-LIVO2 时间同步一键修复工具"
echo "==========================================================="
echo ""

# 检查 ROS 环境
if [ -z "$ROS_DISTRO" ]; then
    echo "❌ 错误: 未检测到 ROS 环境，请先 source setup.bash"
    exit 1
fi

# 检查 FAST-LIVO2 是否在运行
echo "📋 步骤 1/4: 检查 FAST-LIVO2 运行状态..."
if ! pgrep -f "fastlivo_mapping" > /dev/null; then
    echo "⚠️  警告: FAST-LIVO2 未运行"
    echo "   请先启动: roslaunch fast_livo mapping_mid360.launch"
    echo ""
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ FAST-LIVO2 正在运行"
fi

# 检查话题是否可用
echo ""
echo "📋 步骤 2/4: 检查话题可用性..."
if ! timeout 2 rostopic echo /livox/lidar -n 1 > /dev/null 2>&1; then
    echo "❌ 错误: /livox/lidar 话题不可用"
    exit 1
fi
if ! timeout 2 rostopic echo /left_camera/image -n 1 > /dev/null 2>&1; then
    echo "❌ 错误: /left_camera/image 话题不可用"
    exit 1
fi
echo "✅ 话题可用"

# 运行自动校准
echo ""
echo "📋 步骤 3/4: 运行自动校准（需要约30秒）..."
echo "   正在采集数据..."

# 创建临时校准脚本
TEMP_CALIB_SCRIPT=$(mktemp)
cat > "$TEMP_CALIB_SCRIPT" << 'PYTHON_EOF'
#!/usr/bin/env python3
import rospy
import numpy as np
from collections import deque
from sensor_msgs.msg import Image
import sys
import os

try:
    import livox_ros_driver2.msg as livox_msg
    CustomMsg = livox_msg.CustomMsg
except ImportError:
    try:
        import livox_ros_driver.msg as livox_msg
        CustomMsg = livox_msg.CustomMsg
    except ImportError:
        print("ERROR: Cannot import Livox messages")
        sys.exit(1)

class QuickCalibrator:
    def __init__(self):
        rospy.init_node('quick_calibrator', anonymous=True)
        self.lidar_timestamps = deque(maxlen=500)
        self.img_timestamps = deque(maxlen=500)
        self.time_diffs = deque(maxlen=500)
        self.done = False
        
        rospy.Subscriber('/livox/lidar', CustomMsg, self.lidar_cb)
        rospy.Subscriber('/left_camera/image', Image, self.img_cb)
        
        rospy.loginfo("Collecting data for 30 seconds...")
        rospy.sleep(30.0)
        
        if len(self.time_diffs) < 50:
            print("ERROR: Not enough samples")
            sys.exit(1)
        
        time_diffs_array = np.array(self.time_diffs)
        recommended_offset = -np.median(time_diffs_array)
        
        print("SUCCESS")
        print("RECOMMENDED_OFFSET={:.6f}".format(recommended_offset))
        print("SAMPLES={}".format(len(self.time_diffs)))
        print("MEAN_DIFF={:.6f}".format(np.mean(time_diffs_array)))
        print("MEDIAN_DIFF={:.6f}".format(np.median(time_diffs_array)))
        
        self.done = True
    
    def lidar_cb(self, msg):
        self.lidar_timestamps.append(msg.header.stamp.to_sec())
    
    def img_cb(self, msg):
        img_time = msg.header.stamp.to_sec()
        if len(self.lidar_timestamps) > 0:
            diff = img_time - self.lidar_timestamps[-1]
            self.time_diffs.append(diff)

if __name__ == '__main__':
    try:
        calibrator = QuickCalibrator()
    except rospy.ROSInterruptException:
        pass
PYTHON_EOF

chmod +x "$TEMP_CALIB_SCRIPT"

# 运行校准并捕获输出
CALIB_OUTPUT=$(python3 "$TEMP_CALIB_SCRIPT" 2>&1)
rm "$TEMP_CALIB_SCRIPT"

# 检查是否成功
if echo "$CALIB_OUTPUT" | grep -q "ERROR"; then
    echo "❌ 校准失败:"
    echo "$CALIB_OUTPUT"
    exit 1
fi

# 提取推荐值
RECOMMENDED_OFFSET=$(echo "$CALIB_OUTPUT" | grep "RECOMMENDED_OFFSET" | cut -d'=' -f2)
SAMPLES=$(echo "$CALIB_OUTPUT" | grep "SAMPLES" | cut -d'=' -f2)
MEAN_DIFF=$(echo "$CALIB_OUTPUT" | grep "MEAN_DIFF" | cut -d'=' -f2)

if [ -z "$RECOMMENDED_OFFSET" ]; then
    echo "❌ 错误: 无法获取推荐值"
    echo "输出: $CALIB_OUTPUT"
    exit 1
fi

echo "✅ 校准完成"
echo "   样本数: $SAMPLES"
echo "   平均时间差: $MEAN_DIFF 秒"
echo "   推荐偏移: $RECOMMENDED_OFFSET 秒"

# 更新配置文件
echo ""
echo "📋 步骤 4/4: 更新配置文件..."

# 备份原配置
BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo "✅ 已备份原配置: $BACKUP_FILE"

# 更新主配置文件
if grep -q "img_time_offset:" "$CONFIG_FILE"; then
    # 使用 sed 更新（兼容不同系统）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|img_time_offset:.*|img_time_offset: $RECOMMENDED_OFFSET|" "$CONFIG_FILE"
    else
        sed -i "s|img_time_offset:.*|img_time_offset: $RECOMMENDED_OFFSET|" "$CONFIG_FILE"
    fi
    echo "✅ 已更新: $CONFIG_FILE"
else
    echo "⚠️  警告: 未找到 img_time_offset 配置项"
fi

# 更新重定位配置文件
if [ -f "$RELOCALIZATION_CONFIG" ]; then
    if grep -q "img_time_offset:" "$RELOCALIZATION_CONFIG"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|img_time_offset:.*|img_time_offset: $RECOMMENDED_OFFSET|" "$RELOCALIZATION_CONFIG"
        else
            sed -i "s|img_time_offset:.*|img_time_offset: $RECOMMENDED_OFFSET|" "$RELOCALIZATION_CONFIG"
        fi
        echo "✅ 已更新: $RELOCALIZATION_CONFIG"
    fi
fi

echo ""
echo "==========================================================="
echo "✅ 修复完成！"
echo "==========================================================="
echo ""
echo "已更新配置:"
echo "  - img_time_offset: $RECOMMENDED_OFFSET 秒"
echo ""
echo "下一步:"
echo "  1. 重启 FAST-LIVO2 以使配置生效"
echo "  2. 运行监控工具验证: rosrun fast_livo monitor_time_sync_realtime.py"
echo ""
echo "配置文件备份: $BACKUP_FILE"
echo "==========================================================="

