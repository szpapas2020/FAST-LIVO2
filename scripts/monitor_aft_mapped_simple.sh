#!/bin/bash
# 简单的 aft_mapped 监控脚本

echo "============================================================"
echo "监控 aft_mapped 坐标变化"
echo "============================================================"
echo ""

# 检查参数
MAP_FRAME=${1:-map}
AFT_MAPPED_FRAME=${2:-aft_mapped}

echo "监控坐标系: $MAP_FRAME -> $AFT_MAPPED_FRAME"
echo "按 Ctrl+C 退出"
echo ""

while true; do
    # 获取当前时间
    TIMESTAMP=$(date +"%H:%M:%S.%3N")
    
    # 尝试获取 TF 变换
    TRANSFORM=$(timeout 0.5 rostopic echo /tf -n 1 2>/dev/null | grep -A 15 "$AFT_MAPPED_FRAME" | head -20)
    
    if [ -n "$TRANSFORM" ]; then
        # 使用 rosrun tf echo 获取变换
        TF_OUTPUT=$(timeout 0.5 rosrun tf tf_echo $MAP_FRAME $AFT_MAPPED_FRAME 2>/dev/null | tail -10)
        
        if [ -n "$TF_OUTPUT" ]; then
            clear
            echo "============================================================"
            echo "aft_mapped 坐标监控 - $TIMESTAMP"
            echo "============================================================"
            echo "$TF_OUTPUT"
            echo "============================================================"
        fi
    else
        echo "等待 TF 变换..."
    fi
    
    sleep 0.1
done

