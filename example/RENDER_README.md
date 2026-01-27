# 2D到3D第一人称视频渲染Pipeline

这个pipeline用于将NeuPAN的2D模拟环境转换为3D第一人称视频，并生成符合`DATA_FORMAT.md`的navigation格式数据。

## 概述

整个pipeline包含两个主要步骤：

1. **run_exp_for_render.py**: 运行NeuPAN实验，记录所有必要的2D信息
2. **render2Dto3D.py**: 将2D信息渲染为3D第一人称视频，并生成navigation格式数据

## 文件说明

### 输入文件
- `env.yaml`: 环境配置文件（来自example文件夹）
- `planner.yaml`: 规划器配置文件（来自example文件夹）

### 中间文件
- `episode_data.json`: 包含完整的2D轨迹和环境信息

### 输出文件（符合DATA_FORMAT.md格式）
```
navigation_data/
  └── seed_{种子值}/
      └── scene_{场景编号}/
          ├── {编号}.json          # 任务执行结果元数据
          ├── {编号}_info.json     # 每步详细数据
          ├── {编号}.mp4           # 第一人称视频
          └── scene_map.jpg        # 场景地图
```

## 使用方法

### 步骤1: 运行实验并记录2D数据

```bash
cd example
python run_exp_for_render.py -e corridor -d omni -o render_data -m 1000
```

**参数说明:**
- `-e, --example`: 示例名称 (pf, corridor, dyna_obs, dyna_non_obs, etc.)
- `-d, --kinematics`: 运动学类型 (acker, diff, omni)
- `-o, --output_dir`: 输出目录 (默认: render_data)
- `-m, --max_steps`: 最大步数 (默认: 1000)
- `-v, --point_vel`: 使用点速度（可选）

**输出:**
- `render_data/episode_data.json`: 包含所有2D信息的JSON文件

### 步骤2: 渲染3D视频并生成navigation格式数据

```bash
python render2Dto3D.py -i render_data/episode_data.json -o navigation_data --scene_id 0 --episode_id 0
```

**参数说明:**
- `-i, --input`: 输入的episode_data.json文件路径
- `-o, --output_dir`: 输出目录 (默认: navigation_data)
- `-s, --seed`: 随机种子 (默认: 100)
- `--scene_id`: 场景ID (默认: 0)
- `--episode_id`: 任务ID (默认: 0)
- `--fps`: 视频帧率 (默认: 10)
- `--width`: 视频宽度 (默认: 640)
- `--height`: 视频高度 (默认: 480)

**输出:**
- `navigation_data/seed_100/scene_00000/0.json`: 任务元数据
- `navigation_data/seed_100/scene_00000/0_info.json`: 步骤详细信息
- `navigation_data/seed_100/scene_00000/0.mp4`: 第一人称视频
- `navigation_data/seed_100/scene_00000/scene_map.jpg`: 场景俯视图

### 一键运行完整pipeline

```bash
# 使用提供的示例脚本
bash run_full_pipeline.sh
```

## episode_data.json 格式说明

`episode_data.json` 包含以下信息：

```json
{
  "robot_info": {
    "shape": "circle",
    "kinematics": "omni",
    "wheelbase": 0.5,
    "radius": 0.3
  },
  "initial_obstacles": [
    {
      "id": 0,
      "initial_center": [x, y],
      "radius": 0.5,
      "velocity": [vx, vy],
      "vertices": [[x1, y1], [x2, y2], ...]  // 可选，多边形障碍物
    }
  ],
  "robot_trajectory": [
    {"x": 0.0, "y": 0.0, "theta": 0.0},
    {"x": 0.1, "y": 0.0, "theta": 0.0},
    ...
  ],
  "obstacle_trajectories": {
    "0": [
      {"x": 5.0, "y": 5.0, "velocity": [0.0, 0.0]},
      ...
    ]
  },
  "actions": [
    {"linear": 0.2, "angular": 0.0},
    ...
  ],
  "waypoints": [
    [x, y],
    ...
  ],
  "metadata": {
    "finish": true,
    "status": "Normal",
    "success": 1.0,
    "total_step": 100,
    "collision_count": 0,
    "duration": 10.0
  }
}
```

## 输出数据格式 (符合DATA_FORMAT.md)

### {编号}.json - 任务元数据
```json
{
  "finish": true,
  "status": "Normal",
  "success": 1.0,
  "collision_count": 0,
  "total_step": 100,
  "duration": 10.0,
  "instruction": "Navigate in a 10.0m room with 3 obstacles using NeuPAN controller.",
  "controller_type": "neupan",
  "room_size": 10.0,
  "num_obstacles": 3
}
```

### {编号}_info.json - 步骤详细信息
```json
[
  {
    "step": 1,
    "position": {
      "x": 0.0,
      "y": 0.0,
      "theta": 0.0
    },
    "velocity": {
      "linear": 0.2,
      "angular": 0.0
    },
    "collision": false
  },
  ...
]
```

## 注意事项

1. **依赖项**: 确保安装了所有必要的Python包：
   ```bash
   pip install opencv-python matplotlib numpy
   ```

2. **3D渲染**: 当前的`render2Dto3D.py`使用简化的2.5D渲染。如果需要更真实的3D渲染效果，可以集成：
   - PyBullet
   - MuJoCo
   - Unity
   - Unreal Engine

3. **性能**: 渲染视频可能需要一些时间，特别是对于长时间的episode。建议先用较短的max_steps测试。

4. **数据一致性**: 
   - `total_step` 必须等于 `_info.json` 数组的长度
   - `step` 字段必须从1开始连续递增

## 扩展功能

### 批量处理多个场景

```python
# batch_render.py
from pathlib import Path
import json
from render2Dto3D import Renderer2Dto3D

# 批量处理多个episode
episode_files = Path("render_data").glob("**/episode_data.json")

for scene_id, episode_file in enumerate(episode_files):
    with open(episode_file, 'r') as f:
        episode_data = json.load(f)
    
    renderer = Renderer2Dto3D(
        episode_data=episode_data,
        scene_id=scene_id,
        episode_id=0,
    )
    renderer.process()
```

### 自定义3D渲染器

如果要使用更高级的3D渲染引擎，可以继承`Renderer2Dto3D`类并重写`_render_first_person_frame`方法：

```python
class PyBulletRenderer(Renderer2Dto3D):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初始化PyBullet
        import pybullet as p
        self.p = p
        self.physics_client = p.connect(p.DIRECT)
    
    def _render_first_person_frame(self, robot_pos, obstacle_trajs, initial_obstacles, step_idx):
        # 使用PyBullet渲染
        # ...
        pass
```

## 常见问题

**Q: 视频渲染太慢怎么办？**
A: 可以降低fps、分辨率，或者使用更高效的渲染引擎。

**Q: 如何添加更多传感器数据？**
A: 在`run_exp_for_render.py`中修改`step_data`，添加需要的传感器数据（如激光雷达、相机等）。

**Q: 如何使用真实的3D模型？**
A: 集成PyBullet或MuJoCo，加载URDF模型，并在`_render_first_person_frame`中使用它们的渲染API。

**Q: 如何处理碰撞检测？**
A: 在`run_exp_for_render.py`中可以使用`env.done()`或者自定义碰撞检测逻辑，并在`step_info`中记录`collision`字段。

## 开发路线图

- [ ] 集成PyBullet进行真实3D渲染
- [ ] 支持多机器人场景
- [ ] 添加语义标注（物体识别）
- [ ] 支持深度图输出
- [ ] 添加数据增强选项
- [ ] 优化渲染性能

## 参考

- [DATA_FORMAT.md](../DATA_FORMAT.md) - 数据格式规范
- [ir-sim](../ir-sim/) - 2D模拟器
- [NeuPAN](../neupan/) - 导航规划器
