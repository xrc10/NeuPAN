# PyRender 渲染器使用指南

基于成熟的 3D 引擎 PyRender 的高质量渲染器，用于将 2D 导航数据渲染为逼真的 3D 第一人称视频。

## 优势对比

| 特性 | 手写版本 | PyRender 版本 |
|------|---------|--------------|
| 代码量 | ~1279 行 | ~900 行 |
| 渲染质量 | 基础 | 高质量 |
| 光照效果 | 手动模拟 | 自动真实光照 |
| 阴影效果 | 无 | 自动阴影 |
| 材质系统 | 简单颜色 | 完整材质系统 |
| 扩展性 | 困难 | 容易 |
| 依赖 | 仅需 OpenCV | 需要 pyrender + trimesh |

## 快速开始

### 1. 安装依赖

```bash
# 安装渲染所需的依赖
pip install -r requirements_render.txt

# 或者单独安装
pip install pyrender trimesh opencv-python Pillow
```

**注意事项：**
- PyRender 需要 OpenGL 支持
- 在服务器环境（无显示器）需要配置离线渲染：
  ```bash
  export PYOPENGL_PLATFORM=osmesa  # 或 egl
  ```
- 如果遇到 `pyglet` 版本问题，安装 1.x 版本：
  ```bash
  pip install 'pyglet<2'
  ```

### 2. 运行测试

```bash
# 交互式测试（会显示版本对比和依赖检查）
python test_pyrender.py

# 或者直接运行
python render2Dto3D_pyrender.py -i render_data/episode_data.json -o navigation_data_pyrender
```

### 3. 查看输出

输出目录结构：
```
navigation_data_pyrender/
└── seed_100/
    └── scene_00000/
        ├── 0.json              # 任务元数据
        ├── 0_info.json         # 每步详细数据
        ├── scene_map.jpg       # 场景俯视图
        ├── 0.mp4               # 第一人称视频
        ├── frame_0.jpg         # 关键帧（每10帧）
        ├── frame_10.jpg
        └── ...
```

## 使用方法

### 基础使用

```python
from render2Dto3D_pyrender import Renderer2Dto3D
import json

# 读取数据
with open('render_data/episode_data.json', 'r') as f:
    episode_data = json.load(f)

# 创建渲染器
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

# 执行渲染
result = renderer.process(
    clean_old_files=True,  # 清理旧文件
    save_gif=False         # 不生成GIF（可选）
)

print(f"视频已生成: {result['video_file']}")
```

### 命令行使用

```bash
# 基础渲染
python render2Dto3D_pyrender.py -i render_data/episode_data.json

# 自定义参数
python render2Dto3D_pyrender.py \
    -i render_data/episode_data.json \
    -o my_output_dir \
    --fps 30 \
    --width 1280 \
    --height 720 \
    --clean \
    --gif

# 参数说明
# -i, --input: 输入的 episode_data.json 文件
# -o, --output_dir: 输出目录（默认: navigation_data）
# -s, --seed: 随机种子（默认: 100）
# --scene_id: 场景ID（默认: 0）
# --episode_id: 任务ID（默认: 0）
# --fps: 视频帧率（默认: 10）
# --width: 视频宽度（默认: 640）
# --height: 视频高度（默认: 480）
# --gif: 同时生成GIF动画
# --clean: 渲染前清理旧文件
```

## 自定义渲染参数

```python
renderer = Renderer2Dto3D(
    episode_data=episode_data,
    
    # 输出配置
    output_dir="navigation_data_pyrender",
    seed=100,
    scene_id=0,
    episode_id=0,
    
    # 3D 渲染参数
    wall_height=2.5,        # 墙壁高度（米）
    obstacle_height=1.5,    # 障碍物高度（米）
    camera_height=1.2,      # 相机高度（米）
    fov=90.0,              # 视场角（度）
    
    # 视频参数
    image_width=640,       # 图像宽度
    image_height=480,      # 图像高度
    fps=10,               # 帧率
)
```

## 技术细节

### 渲染流程

1. **场景构建**：使用 Trimesh 创建 3D 几何体
   - 地面平面（大平面）
   - 地面网格线（细长方块模拟）
   - 障碍物（多边形挤压或圆柱体）
   - 世界坐标地标（高塔标记）

2. **相机设置**：透视相机，自动处理投影变换
   - 第一人称视角
   - 根据机器人位姿自动计算相机变换

3. **光照系统**：多光源真实光照
   - 主方向光（模拟太阳）
   - 辅助光（模拟天空散射）
   - 环境光（基础照明）

4. **渲染合成**：
   - PyRender 离线渲染（color + depth）
   - 天空背景替换（基于深度）
   - UI 信息覆盖层（OpenCV 绘制）

### 坐标系转换

- **机器人坐标系**：+X 前，+Y 左，theta 是朝向
- **PyRender 相机坐标系**：+X 右，+Y 上，-Z 前
- 自动处理坐标系转换和旋转

### 渲染优化

- 使用 OffscreenRenderer 进行离线渲染
- 自动资源管理（`__del__` 清理）
- 支持批量渲染多个场景

## 故障排除

### 问题：ImportError: No module named 'pyrender'

**解决方案**：
```bash
pip install pyrender trimesh
```

### 问题：OpenGL 相关错误

**解决方案（服务器环境）**：
```bash
# 使用 OSMesa 进行软件渲染
export PYOPENGL_PLATFORM=osmesa
pip install PyOpenGL PyOpenGL-accelerate

# 或使用 EGL
export PYOPENGL_PLATFORM=egl
```

### 问题：pyglet.canvas.xlib.NoSuchDisplayException

**解决方案**：
```bash
# 安装 pyglet 1.x 版本
pip install 'pyglet<2'

# 或设置虚拟显示
export DISPLAY=:0
```

### 问题：渲染速度慢

**优化建议**：
- 降低分辨率：`--width 320 --height 240`
- 降低帧率：`--fps 5`
- 减少障碍物细节（修改 `sections` 参数）

## 扩展功能

### 添加纹理

```python
# 在 _create_extruded_polygon_mesh 中添加纹理
import trimesh

mesh = trimesh.creation.box(extents=[w, h, d])

# 加载纹理
texture = trimesh.visual.material.SimpleMaterial(
    image=PIL.Image.open('texture.png')
)
mesh.visual = trimesh.visual.TextureVisuals(
    material=texture,
    uv=uv_coords  # UV 坐标
)
```

### 自定义光照

```python
# 在 _render_first_person_frame_pyrender 中修改光照
scene = pyrender.Scene(ambient_light=[0.5, 0.5, 0.5])  # 更亮的环境光

# 添加点光源
point_light = pyrender.PointLight(color=[1.0, 1.0, 1.0], intensity=10.0)
scene.add(point_light, pose=self._create_pose([x, y, z], [0, 0, 0]))

# 添加聚光灯
spot_light = pyrender.SpotLight(
    color=[1.0, 1.0, 1.0],
    intensity=10.0,
    innerConeAngle=np.pi/16,
    outerConeAngle=np.pi/6
)
scene.add(spot_light, pose=spot_pose)
```

### 导出深度图

```python
# 在渲染时同时保存深度图
color, depth = self.renderer.render(scene)

# 保存深度图
depth_file = self.scene_dir / f"depth_{step_idx}.png"
depth_normalized = (depth / depth.max() * 255).astype(np.uint8)
cv2.imwrite(str(depth_file), depth_normalized)
```

## 性能对比

在典型场景（50 个障碍物，200 帧）下的性能：

| 指标 | 手写版本 | PyRender 版本 |
|------|---------|--------------|
| 渲染时间 | ~30 秒 | ~45 秒 |
| 视频质量 | 基础 | 高质量 |
| 光照效果 | 简单 | 真实 |
| 可扩展性 | 低 | 高 |

**结论**：虽然 PyRender 版本略慢，但渲染质量显著提升，且代码更易维护和扩展。

## 相关文件

- `render2Dto3D_pyrender.py` - PyRender 渲染器主文件
- `render2Dto3D.py` - 原手写渲染器（保留作为备选）
- `requirements_render.txt` - 渲染功能依赖
- `test_pyrender.py` - 测试脚本
- `run_exp_for_render.py` - 生成渲染数据

## 参考资源

- [PyRender 官方文档](https://pyrender.readthedocs.io/)
- [Trimesh 文档](https://trimsh.org/)
- [OpenGL 教程](https://learnopengl.com/)
