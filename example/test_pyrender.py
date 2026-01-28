#!/usr/bin/env python3
"""
快速测试PyRender渲染器
对比新旧版本的渲染效果
"""

import sys
import json
from pathlib import Path

def test_pyrender():
    """测试PyRender版本渲染器"""
    
    print("=" * 60)
    print("测试 PyRender 渲染器")
    print("=" * 60)
    
    # 检查依赖
    print("\n[1/4] 检查依赖...")
    try:
        import pyrender
        import trimesh
        import cv2
        from PIL import Image
        print("✓ 所有依赖已安装")
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("\n请运行以下命令安装依赖:")
        print("  pip install -r requirements_render.txt")
        print("\n或者单独安装:")
        print("  pip install pyrender trimesh opencv-python Pillow")
        return False
    
    # 检查输入数据
    print("\n[2/4] 检查输入数据...")
    input_file = Path("render_data/episode_data.json")
    if not input_file.exists():
        print(f"✗ 找不到输入文件: {input_file}")
        print("\n请先运行以下命令生成数据:")
        print("  python run_exp_for_render.py")
        return False
    
    print(f"✓ 找到输入文件: {input_file}")
    
    # 读取数据
    with open(input_file, 'r', encoding='utf-8') as f:
        episode_data = json.load(f)
    
    print(f"  - 轨迹长度: {len(episode_data.get('robot_trajectory', []))} 步")
    print(f"  - 障碍物数量: {len(episode_data.get('initial_obstacles', []))}")
    
    # 导入渲染器
    print("\n[3/4] 初始化 PyRender 渲染器...")
    try:
        from render2Dto3D_pyrender import Renderer2Dto3D
        
        renderer = Renderer2Dto3D(
            episode_data=episode_data,
            output_dir="navigation_data_pyrender",
            seed=100,
            scene_id=0,
            episode_id=0,
            fps=10,
            image_width=640,
            image_height=480,
        )
        print("✓ 渲染器初始化成功")
    except Exception as e:
        print(f"✗ 渲染器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 执行渲染
    print("\n[4/4] 开始渲染...")
    try:
        result = renderer.process(clean_old_files=True, save_gif=False)
        print("\n✓ 渲染完成！")
        print(f"\n输出目录: {result['scene_dir']}")
        print(f"视频文件: {result['video_file']}")
        return True
    except Exception as e:
        print(f"\n✗ 渲染失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_versions():
    """对比新旧版本"""
    print("\n" + "=" * 60)
    print("版本对比")
    print("=" * 60)
    
    print("\n手写版本 (render2Dto3D.py):")
    print("  + 优点: 无额外依赖，完全可控")
    print("  - 缺点: 代码复杂（1279行），需要手动处理投影、光照等")
    print("  - 特点: 使用OpenCV和NumPy手动实现3D渲染")
    
    print("\nPyRender版本 (render2Dto3D_pyrender.py):")
    print("  + 优点: 代码简洁（~900行），自动处理投影、光照、阴影")
    print("  + 优点: 更真实的3D渲染效果")
    print("  + 优点: 易于扩展（添加纹理、复杂模型等）")
    print("  - 缺点: 需要安装pyrender和trimesh")
    print("  - 特点: 使用成熟的3D引擎，基于OpenGL")
    
    print("\n推荐:")
    print("  → 如果追求渲染质量和可维护性: 使用 PyRender 版本")
    print("  → 如果需要在受限环境运行: 使用手写版本")


if __name__ == "__main__":
    print("\nPyRender 渲染器测试工具\n")
    
    # 显示版本对比
    compare_versions()
    
    # 询问是否继续测试
    print("\n" + "=" * 60)
    response = input("\n是否运行测试? (y/n): ").strip().lower()
    
    if response in ['y', 'yes', '是']:
        success = test_pyrender()
        
        if success:
            print("\n" + "=" * 60)
            print("测试成功！")
            print("=" * 60)
            print("\n您可以对比以下目录的输出:")
            print("  - 手写版本: navigation_data/")
            print("  - PyRender版本: navigation_data_pyrender/")
            print("\n查看生成的视频:")
            print("  - navigation_data_pyrender/seed_100/scene_00000/0.mp4")
        else:
            print("\n" + "=" * 60)
            print("测试失败，请检查错误信息")
            print("=" * 60)
            sys.exit(1)
    else:
        print("\n取消测试")
