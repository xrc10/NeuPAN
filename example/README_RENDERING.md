# 3D 渲染器使用指南

将 2D 导航模拟数据渲染为逼真的 3D 第一人称视频。

## 🎯 快速开始

### 最简单的方式（推荐）

```bash
cd example

# 使用 PyRender 渲染器（高质量，GPU 加速）
./render_pyrender.sh -i render_data/episode_data.json

# 或使用手写渲染器（无需额外依赖）
python render2Dto3D.py -i render_data/episode_data.json
```

## 📚 文档导航

根据您的情况选择相应文档：

### 🆕 新用户

1. **从这里开始** → [`SETUP_COMPLETE.md`](SETUP_COMPLETE.md)
   - 完整的设置说明
   - 问题解决方案
   - 已完成的工作总结

2. **快速开始** → [`PYRENDER_QUICKSTART.md`](PYRENDER_QUICKSTART.md)
   - 3 分钟上手
   - 常用命令
   - 快速故障排除

### 📖 深度学习

3. **完整文档** → [`PYRENDER_README.md`](PYRENDER_README.md)
   - API 详细说明
   - 自定义参数
   - 扩展功能（纹理、材质等）

4. **迁移指南** → [`MIGRATION_TO_PYRENDER.md`](MIGRATION_TO_PYRENDER.md)
   - 从手写版本迁移
   - 代码对比
   - 性能分析

### 🔧 工具脚本

5. **环境诊断** → `./fix_pyrender_rendering.sh`
   - 自动检测系统配置
   - 推荐解决方案
   - GPU/渲染库检测

6. **版本对比** → `./compare_renderers.sh`
   - 代码统计
   - 功能对比
   - 性能分析

## 🎨 渲染器选择

### PyRender 版本（推荐）

**优点**：
- ✅ 高质量渲染（真实光照和阴影）
- ✅ 代码更简洁（减少 27%）
- ✅ GPU 加速（NVIDIA A100）
- ✅ 易于扩展

**使用**：
```bash
./render_pyrender.sh -i render_data/episode_data.json
```

**要求**：
- 需要设置 `PYOPENGL_PLATFORM=egl`（脚本自动设置）
- 需要 EGL 或 OSMesa 库

### 手写版本（备选）

**优点**：
- ✅ 无额外依赖
- ✅ 无需环境配置
- ✅ 渲染速度更快

**使用**：
```bash
python render2Dto3D.py -i render_data/episode_data.json
```

## 📁 输出格式

两个版本输出完全相同的文件结构：

```
navigation_data/
└── seed_100/
    └── scene_00000/
        ├── 0.mp4              # 第一人称视频
        ├── 0.json             # 任务元数据
        ├── 0_info.json        # 每步详细数据
        ├── scene_map.jpg      # 场景俯视图
        ├── frame_0.jpg        # 关键帧（每 10 帧）
        ├── frame_10.jpg
        └── ...
```

## 🚀 常用命令

### 基础渲染

```bash
# PyRender 版本
./render_pyrender.sh -i render_data/episode_data.json

# 手写版本
python render2Dto3D.py -i render_data/episode_data.json
```

### 自定义参数

```bash
./render_pyrender.sh \
    -i render_data/episode_data.json \
    -o custom_output_dir \
    --width 1280 \
    --height 720 \
    --fps 30 \
    --clean
```

### 生成 GIF 动画

```bash
./render_pyrender.sh \
    -i render_data/episode_data.json \
    --gif
```

### 批量渲染

```bash
for data_file in render_data/*.json; do
    ./render_pyrender.sh -i "$data_file"
done
```

## 🔍 环境检查

### 检查 PyRender 是否可用

```bash
./fix_pyrender_rendering.sh
```

输出示例：
```
✓ 检测到 NVIDIA GPU: A100
✓ 检测到 EGL 库
✅ 推荐使用 EGL (GPU 加速)
```

### 测试 PyRender 导入

```bash
PYOPENGL_PLATFORM=egl python -c "import pyrender; print('✓ OK')"
```

## 🐛 常见问题

### 问题 1: ImportError: Unable to load OpenGL library

**解决方案**：使用包装脚本
```bash
./render_pyrender.sh -i render_data/episode_data.json
```

或手动设置环境变量：
```bash
export PYOPENGL_PLATFORM=egl
python render2Dto3D_pyrender.py -i render_data/episode_data.json
```

### 问题 2: 视频编码警告

```
[ERROR] Could not find encoder for codec_id=27
```

**说明**：这是正常的，系统会自动回退到 MPEG-4 编码器，视频仍会正常生成。

### 问题 3: 需要回到手写版本

```bash
python render2Dto3D.py -i render_data/episode_data.json
```

手写版本无需任何额外配置，可作为备选方案。

## 📊 性能对比

在您的系统上（NVIDIA A100）：

| 指标 | 手写版本 | PyRender 版本 |
|------|---------|--------------|
| 渲染时间 | ~30 秒 | ~60 秒 |
| 代码行数 | 1285 行 | 932 行 |
| 渲染质量 | 基础 | 高质量 |
| GPU 加速 | ❌ | ✅ |
| 光照/阴影 | 简单 | 真实 |
| 配置需求 | 无 | 需要 EGL |

## 🔗 相关文件

### 渲染器文件
- `render2Dto3D_pyrender.py` - PyRender 渲染器
- `render2Dto3D.py` - 手写渲染器
- `render_pyrender.sh` - PyRender 包装脚本 ⭐

### 工具脚本
- `fix_pyrender_rendering.sh` - 环境诊断
- `compare_renderers.sh` - 版本对比
- `test_pyrender.py` - 测试脚本

### 文档
- `SETUP_COMPLETE.md` - 设置完成总结 ⭐
- `PYRENDER_QUICKSTART.md` - 快速开始
- `PYRENDER_README.md` - 完整文档
- `MIGRATION_TO_PYRENDER.md` - 迁移指南

### 依赖
- `requirements_render.txt` - 渲染功能依赖

## 💡 最佳实践

### 1. 永久设置环境变量

```bash
echo 'export PYOPENGL_PLATFORM=egl' >> ~/.bashrc
source ~/.bashrc
```

之后可以直接运行：
```bash
python render2Dto3D_pyrender.py -i render_data/episode_data.json
```

### 2. 使用包装脚本

推荐始终使用 `render_pyrender.sh`，它会自动配置环境：
```bash
./render_pyrender.sh -i render_data/episode_data.json
```

### 3. 选择合适的版本

- **开发/测试**: 使用手写版本（快速）
- **生产/展示**: 使用 PyRender 版本（高质量）
- **CI/CD**: 根据环境选择

## 🆘 获取帮助

1. **查看快速开始指南**: `PYRENDER_QUICKSTART.md`
2. **运行环境诊断**: `./fix_pyrender_rendering.sh`
3. **查看完整文档**: `PYRENDER_README.md`
4. **对比两个版本**: `./compare_renderers.sh`

## 🎊 开始使用

```bash
# 1. 确保在正确的目录
cd /data23/xu_ruochen/NeuPAN/example

# 2. 运行渲染（选择一个）
./render_pyrender.sh -i render_data/episode_data.json    # PyRender 版本
python render2Dto3D.py -i render_data/episode_data.json  # 手写版本

# 3. 查看输出
ls -lh navigation_data*/seed_100/scene_00000/
```

**祝您渲染愉快！** 🎨✨

---

**文档更新**: 2026-01-28  
**系统**: Linux + NVIDIA A100 + EGL  
**状态**: ✅ 完全可用
