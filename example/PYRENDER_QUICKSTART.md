# PyRender 渲染器快速开始指南

## ✅ 问题已解决！

您在服务器环境（无显示器）下遇到的 OpenGL 错误已经解决了！

### 解决方案

使用 **EGL** 平台进行 GPU 加速渲染（利用您的 NVIDIA A100 GPU）。

## 🚀 快速使用

### 方法 1: 使用包装脚本（推荐）

```bash
cd example
./render_pyrender.sh -i render_data/episode_data.json -o navigation_data_pyrender
```

### 方法 2: 手动设置环境变量

```bash
cd example
export PYOPENGL_PLATFORM=egl
python render2Dto3D_pyrender.py -i render_data/episode_data.json
```

### 方法 3: 添加到 bashrc（永久设置）

```bash
echo 'export PYOPENGL_PLATFORM=egl' >> ~/.bashrc
source ~/.bashrc

# 之后可以直接运行
python render2Dto3D_pyrender.py -i render_data/episode_data.json
```

## 📁 输出文件

渲染完成后，您可以在以下位置找到输出：

```
navigation_data_pyrender/seed_100/scene_00000/
├── 0.mp4              # 第一人称视频 (3.0 MB) ⭐
├── 0.json             # 任务元数据
├── 0_info.json        # 每步详细数据
├── scene_map.jpg      # 场景俯视图
├── frame_0.jpg        # 关键帧
├── frame_10.jpg
└── ...
```

## 🔧 常用命令

### 渲染视频（默认设置）

```bash
./render_pyrender.sh -i render_data/episode_data.json
```

### 自定义分辨率和帧率

```bash
./render_pyrender.sh \
    -i render_data/episode_data.json \
    --width 1280 \
    --height 720 \
    --fps 30
```

### 同时生成 GIF

```bash
./render_pyrender.sh \
    -i render_data/episode_data.json \
    --gif
```

### 清理旧文件后重新渲染

```bash
./render_pyrender.sh \
    -i render_data/episode_data.json \
    --clean
```

## ⚙️ 环境诊断

如果遇到问题，运行诊断脚本：

```bash
./fix_pyrender_rendering.sh
```

这会检测：
- ✓ NVIDIA A100 GPU
- ✓ EGL 库
- ✓ 显示环境
- ✓ 推荐的解决方案

## 📊 性能

在您的系统上（NVIDIA A100）：
- **渲染时间**: ~60-90 秒（244 帧）
- **视频大小**: ~3 MB（640x480, 10 FPS）
- **GPU 加速**: ✓ 启用

## 🔄 与手写版本对比

| 特性 | 手写版本 | PyRender 版本 |
|------|---------|--------------|
| 渲染时间 | ~30 秒 | ~60 秒 |
| 代码行数 | 1285 行 | 932 行 |
| 光照效果 | 手动模拟 | 真实光照 |
| 阴影 | 无 | 自动 |
| 需要设置 | 无 | 需要 `PYOPENGL_PLATFORM=egl` |

### 对比命令

```bash
# 渲染手写版本
python render2Dto3D.py -i render_data/episode_data.json -o navigation_data_manual

# 渲染 PyRender 版本
./render_pyrender.sh -i render_data/episode_data.json -o navigation_data_pyrender

# 对比输出
ls -lh navigation_data_manual/seed_100/scene_00000/
ls -lh navigation_data_pyrender/seed_100/scene_00000/
```

## 🐛 故障排除

### 问题: ImportError: Unable to load OpenGL library

**解决方案**: 使用包装脚本或设置环境变量
```bash
export PYOPENGL_PLATFORM=egl
```

### 问题: 视频编码警告

这些警告是正常的，系统会自动回退到 MPEG-4 编码器：
```
[ERROR] Could not find encoder for codec_id=27
OpenCV: FFMPEG: fallback to use tag 'avc1'
```

视频仍然会正常生成。

### 问题: 渲染速度慢

优化建议：
```bash
# 降低分辨率
./render_pyrender.sh -i ... --width 320 --height 240

# 降低帧率
./render_pyrender.sh -i ... --fps 5
```

## 📚 更多文档

- **完整文档**: `PYRENDER_README.md`
- **迁移指南**: `MIGRATION_TO_PYRENDER.md`
- **对比分析**: `./compare_renderers.sh`

## ✨ 下一步

1. **查看渲染结果**:
   ```bash
   ls -lh navigation_data_pyrender/seed_100/scene_00000/
   ```

2. **播放视频** (如果在本地):
   ```bash
   vlc navigation_data_pyrender/seed_100/scene_00000/0.mp4
   ```

3. **查看关键帧**:
   ```bash
   eog navigation_data_pyrender/seed_100/scene_00000/frame_*.jpg
   ```

## 💡 提示

- ✅ 包装脚本 `render_pyrender.sh` 会自动设置正确的环境变量
- ✅ 可以在任何无显示器的服务器上运行（只要有 EGL 或 OSMesa）
- ✅ 支持 GPU 加速（使用 EGL + NVIDIA GPU）
- ✅ 输出格式与手写版本完全兼容

---

**现在开始使用 PyRender 渲染器吧！** 🎨✨
