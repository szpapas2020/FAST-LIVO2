#!/bin/bash
# 快速修复 RViz 地图晃动问题

echo "============================================================"
echo "修复 RViz 地图晃动问题"
echo "============================================================"
echo ""

echo "1. 检查 PCD 地图的 frame_id..."
rostopic echo /pcd_map -n 1 2>&1 | grep -A 3 "header:" | grep frame_id
echo ""

echo "2. 检查 map -> camera_init 的静态 TF..."
rostopic echo /tf_static -n 1 2>&1 | grep -A 10 "map\|camera_init" | head -15
echo ""

echo "3. 检查 RViz 的 Fixed Frame 设置..."
echo "   请在 RViz 中检查："
echo "   - 左下角 'Global Options' → 'Fixed Frame'"
echo "   - 应该显示为 'map'"
echo "   - 如果显示为其他值，请改为 'map'"
echo ""

echo "4. 如果 Fixed Frame 下拉菜单中没有 'map'，说明 map 坐标系不存在"
echo "   请重启 launch 文件："
echo "   roslaunch fast_livo mapping_mid360_relocalization.launch"
echo ""

echo "5. 重新加载 RViz 配置："
echo "   - File → Open Config → 选择 fast_livo2_map.rviz"
echo ""

echo "============================================================"
echo "如果问题仍然存在，请运行诊断脚本："
echo "rosrun fast_livo diagnose_map_shaking.py"
echo "============================================================"

