# 无头服务器渲染指南

## 问题说明

在没有显示器的服务器上运行 PyRender 时，会遇到以下错误：

```
pyglet.display.xlib.NoSuchDisplayException: Cannot connect to "None"
```

这是因为 PyRender 需要 OpenGL 上下文，而在无头服务器上没有可用的显示器。

## 解决方案

使用 **xvfb-run**（X Virtual FrameBuffer）创建虚拟显示器来运行渲染脚本。

### 方法 1：使用便捷脚本（推荐）

```bash
./render_with_xvfb.sh -i render_data/episode_data.json
```

该脚本会自动使用 xvfb-run 来运行 `render2Dto3D_pyrender.py`，支持所有原始参数。

### 方法 2：直接使用 xvfb-run

```bash
xvfb-run -a -s "-screen 0 1024x768x24" python render2Dto3D_pyrender.py -i render_data/episode_data.json
```

参数说明：
- `-a`：自动选择可用的显示器编号
- `-s "-screen 0 1024x768x24"`：创建一个 1024x768、24位色深的虚拟屏幕

### 方法 3：使用 EGL 后端（高级）

如果系统支持 EGL（无需 X server 的 OpenGL），可以设置环境变量：

```bash
PYOPENGL_PLATFORM=egl python render2Dto3D_pyrender.py -i render_data/episode_data.json
```

**注意**：此方法需要系统安装了 EGL 库（如 `libegl1-mesa`）。

## 安装依赖

### 安装 Python 依赖

```bash
pip install -r requirements_render.txt
```

### 安装系统依赖（如果需要）

#### Ubuntu/Debian

```bash
# 安装 xvfb（虚拟显示器）
sudo apt-get install xvfb

# 或者安装 EGL 支持
sudo apt-get install libegl1-mesa libegl1-mesa-dev
```

#### 其他系统

请根据你的系统包管理器安装相应的包。

## 常见问题

### Q: 渲染速度慢

A: 这是正常的，因为 CPU 渲染比 GPU 渲染慢。可以尝试：
- 降低分辨率：`--width 320 --height 240`
- 降低帧率：`--fps 5`

### Q: 视频编码器错误

A: 如果看到 FFmpeg 编码器错误，通常不影响渲染。脚本会自动尝试多个编码器。如果需要特定编码器，请安装：

```bash
sudo apt-get install ffmpeg libx264-dev
```

### Q: 内存不足

A: 渲染大型场景可能需要较多内存。尝试：
- 分批渲染多个 episode
- 减小图像分辨率

## 验证输出

渲染完成后，检查输出目录：

```bash
ls -lh navigation_data/seed_100/scene_00000/
```

应该包含：
- `0.json` - 任务元数据
- `0_info.json` - 步骤详细信息
- `scene_map.jpg` - 场景俯视图
- `0.mp4` - 第一人称视频
- `frame_*.jpg` - 关键帧图像

## 示例命令

### 基本渲染

```bash
./render_with_xvfb.sh -i render_data/episode_data.json
```

### 指定输出目录和场景参数

```bash
./render_with_xvfb.sh -i render_data/episode_data.json \
    -o my_navigation_data \
    --seed 200 \
    --scene_id 1 \
    --episode_id 0
```

### 自定义视频参数

```bash
./render_with_xvfb.sh -i render_data/episode_data.json \
    --fps 15 \
    --width 1280 \
    --height 720
```

### 同时生成 GIF

```bash
./render_with_xvfb.sh -i render_data/episode_data.json --gif
```

### 清理旧文件后渲染

```bash
./render_with_xvfb.sh -i render_data/episode_data.json --clean
```

## 性能优化建议

1. **使用较低分辨率进行测试**：先用 320x240 测试，确认无误后再用高分辨率
2. **批量处理**：处理多个 episode 时，可以使用循环或并行处理
3. **监控资源**：使用 `htop` 或 `nvidia-smi` 监控 CPU/GPU 使用情况

## 相关文件

- `render2Dto3D_pyrender.py` - 主渲染脚本
- `render_with_xvfb.sh` - 便捷启动脚本
- `requirements_render.txt` - Python 依赖
- `PYRENDER_README.md` - PyRender 详细说明
