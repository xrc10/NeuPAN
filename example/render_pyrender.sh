#!/bin/bash

# PyRender 渲染脚本（自动配置 EGL 环境）
# 用于在无显示器服务器环境下运行

# 设置 EGL 作为 OpenGL 平台（使用 GPU 加速）
export PYOPENGL_PLATFORM=egl

# 运行 PyRender 渲染器
python render2Dto3D_pyrender.py "$@"
