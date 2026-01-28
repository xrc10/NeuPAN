#!/bin/bash

# 修复 PyRender 在服务器环境下的渲染问题

echo "=================================="
echo "PyRender 环境诊断与修复"
echo "=================================="
echo ""

# 检查是否有显示器
echo "🔍 检查显示环境..."
if [ -z "$DISPLAY" ]; then
    echo "  ❌ 无显示器环境（DISPLAY 未设置）"
    NO_DISPLAY=1
else
    echo "  ✓ DISPLAY = $DISPLAY"
    NO_DISPLAY=0
fi

echo ""
echo "🔍 检查 GPU 和渲染库..."

# 检查 GPU
if command -v nvidia-smi &> /dev/null; then
    echo "  ✓ 检测到 NVIDIA GPU"
    nvidia-smi --query-gpu=name --format=csv,noheader | head -1
    HAS_GPU=1
else
    echo "  ℹ️  未检测到 NVIDIA GPU"
    HAS_GPU=0
fi

# 检查 EGL
if ldconfig -p | grep -q libEGL.so; then
    echo "  ✓ 检测到 EGL 库"
    HAS_EGL=1
else
    echo "  ❌ 未检测到 EGL 库"
    HAS_EGL=0
fi

# 检查 OSMesa
if ldconfig -p | grep -q libOSMesa.so; then
    echo "  ✓ 检测到 OSMesa 库"
    HAS_OSMESA=1
else
    echo "  ❌ 未检测到 OSMesa 库"
    HAS_OSMESA=0
fi

echo ""
echo "=================================="
echo "推荐解决方案："
echo "=================================="
echo ""

# 根据环境推荐解决方案
if [ $NO_DISPLAY -eq 1 ]; then
    echo "您在无显示器环境下运行，需要配置离线渲染。"
    echo ""
    
    if [ $HAS_GPU -eq 1 ] && [ $HAS_EGL -eq 1 ]; then
        echo "✅ 方案 1: 使用 EGL (GPU 加速，推荐)"
        echo ""
        echo "运行以下命令："
        echo "  export PYOPENGL_PLATFORM=egl"
        echo "  python render2Dto3D_pyrender.py -i render_data/episode_data.json"
        echo ""
        echo "或者将环境变量添加到脚本："
        echo "  echo 'export PYOPENGL_PLATFORM=egl' >> ~/.bashrc"
        echo "  source ~/.bashrc"
        echo ""
    elif [ $HAS_OSMESA -eq 1 ]; then
        echo "✅ 方案 2: 使用 OSMesa (CPU 渲染)"
        echo ""
        echo "运行以下命令："
        echo "  export PYOPENGL_PLATFORM=osmesa"
        echo "  python render2Dto3D_pyrender.py -i render_data/episode_data.json"
        echo ""
    else
        echo "❌ 需要安装渲染库"
        echo ""
        echo "选项 A: 安装 OSMesa (CPU 渲染，适用于所有系统)"
        echo "  Ubuntu/Debian:"
        echo "    sudo apt-get update"
        echo "    sudo apt-get install -y libosmesa6-dev freeglut3-dev"
        echo ""
        echo "  CentOS/RHEL:"
        echo "    sudo yum install -y mesa-libOSMesa-devel freeglut-devel"
        echo ""
        echo "  Conda 环境:"
        echo "    conda install -c conda-forge mesalib"
        echo ""
        echo "选项 B: 安装 EGL (GPU 渲染，需要 NVIDIA GPU)"
        echo "  Ubuntu/Debian:"
        echo "    sudo apt-get install -y libegl1-mesa-dev"
        echo ""
    fi
    
    echo "选项 C: 使用虚拟显示 (xvfb)"
    echo "  sudo apt-get install -y xvfb"
    echo "  xvfb-run -a python render2Dto3D_pyrender.py -i render_data/episode_data.json"
    echo ""
    
    echo "选项 D: 使用手写渲染器（无需额外依赖）"
    echo "  python render2Dto3D.py -i render_data/episode_data.json"
    echo ""
    
else
    echo "✓ 您有显示器环境，应该可以直接运行"
    echo ""
    echo "如果仍然遇到问题，尝试："
    echo "  pip install PyOpenGL PyOpenGL-accelerate"
    echo ""
fi

echo "=================================="
echo "快速测试："
echo "=================================="
echo ""
echo "测试 PyRender 是否可用："
echo "  python -c 'import pyrender; print(\"✓ PyRender 导入成功\")'"
echo ""
