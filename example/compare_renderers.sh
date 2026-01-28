#!/bin/bash

# 对比两个渲染器版本的脚本

echo "=================================="
echo "渲染器版本对比"
echo "=================================="

echo ""
echo "📊 代码统计："
echo ""

if [ -f "render2Dto3D.py" ]; then
    lines_old=$(wc -l < render2Dto3D.py)
    echo "手写版本 (render2Dto3D.py):"
    echo "  - 总行数: $lines_old"
    echo "  - 渲染函数: _render_first_person_frame (手动投影计算)"
    echo "  - 依赖: OpenCV + NumPy"
else
    echo "❌ 找不到 render2Dto3D.py"
fi

echo ""

if [ -f "render2Dto3D_pyrender.py" ]; then
    lines_new=$(wc -l < render2Dto3D_pyrender.py)
    echo "PyRender版本 (render2Dto3D_pyrender.py):"
    echo "  - 总行数: $lines_new"
    echo "  - 渲染函数: _render_first_person_frame_pyrender (引擎自动处理)"
    echo "  - 依赖: PyRender + Trimesh + OpenCV"
    
    if [ -n "$lines_old" ] && [ -n "$lines_new" ]; then
        reduction=$(( (lines_old - lines_new) * 100 / lines_old ))
        echo "  - 代码减少: ~$reduction%"
    fi
else
    echo "❌ 找不到 render2Dto3D_pyrender.py"
fi

echo ""
echo "=================================="
echo "功能对比："
echo "=================================="
echo ""
echo "| 功能              | 手写版本 | PyRender版本 |"
echo "|-------------------|---------|-------------|"
echo "| 3D投影            | 手动    | 自动        |"
echo "| 光照效果          | 简单    | 真实        |"
echo "| 阴影              | 无      | 自动        |"
echo "| 材质系统          | 基础    | 完整        |"
echo "| 代码可维护性      | 低      | 高          |"
echo "| 扩展性            | 困难    | 容易        |"
echo "| 额外依赖          | 无      | 需要安装    |"
echo ""

echo "=================================="
echo "使用建议："
echo "=================================="
echo ""
echo "✅ 推荐使用 PyRender 版本，如果："
echo "   - 追求高质量渲染效果"
echo "   - 需要扩展功能（纹理、复杂模型等）"
echo "   - 有权限安装额外依赖"
echo ""
echo "✅ 使用手写版本，如果："
echo "   - 在受限环境运行（无法安装PyRender）"
echo "   - 只需要基础的可视化效果"
echo "   - 不想安装额外依赖"
echo ""

echo "=================================="
echo "快速开始："
echo "=================================="
echo ""
echo "1. 安装 PyRender 版本依赖："
echo "   pip install -r requirements_render.txt"
echo ""
echo "2. 运行测试："
echo "   python test_pyrender.py"
echo ""
echo "3. 查看文档："
echo "   cat PYRENDER_README.md"
echo ""
