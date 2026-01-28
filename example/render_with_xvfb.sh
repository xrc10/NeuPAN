#!/bin/bash
# 使用 xvfb-run 在无头服务器上运行 PyRender 渲染脚本
# 用法: ./render_with_xvfb.sh [参数...]
# 示例: ./render_with_xvfb.sh -i render_data/episode_data.json --fps 10

# 检查 xvfb-run 是否安装
if ! command -v xvfb-run &> /dev/null; then
    echo "错误: xvfb-run 未安装"
    echo "请安装: sudo apt-get install xvfb"
    exit 1
fi

# 使用虚拟显示器运行渲染脚本
# -a: 自动选择可用的服务器编号
# -s "-screen 0 1024x768x24": 设置虚拟屏幕为 1024x768，24位色深
xvfb-run -a -s "-screen 0 1024x768x24" python render2Dto3D_pyrender.py "$@"
