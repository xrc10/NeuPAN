#!/bin/bash
# 完整的2D到3D渲染pipeline示例脚本

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}2D到3D渲染Pipeline${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 默认参数
EXAMPLE="corridor"
KINEMATICS="omni"
MAX_STEPS=1000
SEED=100
SCENE_ID=0
EPISODE_ID=0

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--example)
            EXAMPLE="$2"
            shift 2
            ;;
        -d|--kinematics)
            KINEMATICS="$2"
            shift 2
            ;;
        -m|--max_steps)
            MAX_STEPS="$2"
            shift 2
            ;;
        -s|--seed)
            SEED="$2"
            shift 2
            ;;
        --scene_id)
            SCENE_ID="$2"
            shift 2
            ;;
        --episode_id)
            EPISODE_ID="$2"
            shift 2
            ;;
        -h|--help)
            echo "使用方法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  -e, --example EXAMPLE       示例名称 (默认: corridor)"
            echo "  -d, --kinematics TYPE       运动学类型 (默认: omni)"
            echo "  -m, --max_steps STEPS       最大步数 (默认: 1000)"
            echo "  -s, --seed SEED             随机种子 (默认: 100)"
            echo "  --scene_id ID               场景ID (默认: 0)"
            echo "  --episode_id ID             任务ID (默认: 0)"
            echo "  -h, --help                  显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 -e corridor -d omni -m 500"
            echo "  $0 -e dyna_non_obs -d diff --scene_id 1"
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            echo "使用 -h 或 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 显示配置
echo -e "${YELLOW}配置:${NC}"
echo "  示例: $EXAMPLE"
echo "  运动学: $KINEMATICS"
echo "  最大步数: $MAX_STEPS"
echo "  种子: $SEED"
echo "  场景ID: $SCENE_ID"
echo "  任务ID: $EPISODE_ID"
echo ""

# 步骤1: 运行实验并记录2D数据
echo -e "${GREEN}[步骤 1/2] 运行实验并记录2D数据...${NC}"
echo "----------------------------------------"

python run_exp_for_render.py \
    -e "$EXAMPLE" \
    -d "$KINEMATICS" \
    -o "render_data/${EXAMPLE}_${KINEMATICS}" \
    -m "$MAX_STEPS"

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 步骤1失败${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}步骤1完成！${NC}"
echo ""

# 步骤2: 渲染3D视频并生成navigation格式数据
echo -e "${GREEN}[步骤 2/2] 渲染3D视频并生成navigation格式数据...${NC}"
echo "----------------------------------------"

python render2Dto3D.py \
    -i "render_data/${EXAMPLE}_${KINEMATICS}/episode_data.json" \
    -o "navigation_data" \
    -s "$SEED" \
    --scene_id "$SCENE_ID" \
    --episode_id "$EPISODE_ID" \
    --fps 10 \
    --width 640 \
    --height 480

if [ $? -ne 0 ]; then
    echo -e "${RED}错误: 步骤2失败${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}步骤2完成！${NC}"
echo ""

# 显示输出文件
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Pipeline完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}输出文件:${NC}"
echo "  中间数据:"
echo "    - render_data/${EXAMPLE}_${KINEMATICS}/episode_data.json"
echo ""
echo "  最终数据 (符合DATA_FORMAT.md):"
SCENE_DIR="navigation_data/seed_${SEED}/scene_$(printf '%05d' $SCENE_ID)"
echo "    - ${SCENE_DIR}/${EPISODE_ID}.json"
echo "    - ${SCENE_DIR}/${EPISODE_ID}_info.json"
echo "    - ${SCENE_DIR}/${EPISODE_ID}.mp4"
echo "    - ${SCENE_DIR}/scene_map.jpg"
echo ""
echo -e "${GREEN}数据已准备就绪，可用于训练第一人称视觉local planner！${NC}"
