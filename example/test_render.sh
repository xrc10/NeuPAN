#!/bin/bash

# 测试渲染优化脚本
# 使用方法: bash example/test_render.sh

echo "========================================"
echo "测试2D到3D渲染（优化版）"
echo "========================================"

# 设置路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 检查输入文件
INPUT_FILE="${SCRIPT_DIR}/render_data/episode_data.json"
if [ ! -f "$INPUT_FILE" ]; then
    echo "错误: 找不到输入文件 $INPUT_FILE"
    echo "请先运行 run_exp_for_render.py 生成episode数据"
    exit 1
fi

# 运行渲染（标准分辨率）
OUTPUT_DIR="${SCRIPT_DIR}/navigation_data"
echo ""
echo "开始渲染（640x480）..."
python "${SCRIPT_DIR}/render2Dto3D.py" \
    -i "$INPUT_FILE" \
    -o "$OUTPUT_DIR" \
    --seed 100 \
    --scene_id 0 \
    --episode_id 0 \
    --fps 10 \
    --width 640 \
    --height 480 \
    --clean

# 检查输出
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "渲染完成！"
    echo "========================================"
    echo "输出目录: $OUTPUT_DIR/seed_100/scene_00000/"
    echo ""
    echo "生成的文件："
    ls -lh "$OUTPUT_DIR/seed_100/scene_00000/"
    echo ""
    echo "关键帧图片："
    ls -lh "$OUTPUT_DIR/seed_100/scene_00000/frame_"*.jpg 2>/dev/null | head -5
    echo ""
    echo "可以使用以下命令查看视频："
    echo "  ffplay $OUTPUT_DIR/seed_100/scene_00000/0.mp4"
    echo "  或"
    echo "  vlc $OUTPUT_DIR/seed_100/scene_00000/0.mp4"
else
    echo "错误: 渲染失败"
    exit 1
fi

# 如果需要高分辨率版本，取消下面的注释
# echo ""
# echo "开始渲染高分辨率版本（1280x960）..."
# python "${SCRIPT_DIR}/render2Dto3D.py" \
#     -i "$INPUT_FILE" \
#     -o "${OUTPUT_DIR}_hd" \
#     --seed 100 \
#     --scene_id 0 \
#     --episode_id 0 \
#     --fps 10 \
#     --width 1280 \
#     --height 960
