# OpenTrackVLA 数据格式说明

本文档详细说明了 OpenTrackVLA 项目的数据格式规范，用于生成相同格式的数据。本文档包含两种任务类型的数据格式：
1. **跟随任务（Following Task）**：机器人跟随目标人物
2. **导航任务（Navigation Task）**：机器人在环境中自主导航避障

## 任务类型对比

| 特性 | 跟随任务 | 导航任务 |
|------|---------|---------|
| **场景命名** | 场景ID（如 `17DRP5sb8fy`） | `scene_{编号}`（如 `scene_00000`） |
| **场景图片** | `track_object.jpg`（跟踪目标） | `scene_map.jpg`（场景地图） |
| **任务目标** | 跟随指定的目标人物 | 在环境中自主导航避障 |
| **关键指标** | `following_rate`、`following_step` | `collision_count`、`duration` |
| **步骤数据** | `dis_to_human`、`facing`、`base_velocity` | `position`、`velocity`、`collision` |
| **速度表示** | 3D向量 `[x, y, z]` | 线速度+角速度 |
| **任务参数** | `instruction`（跟随指令） | `controller_type`、`room_size`、`num_obstacles` |

## 目录结构

### 跟随任务（Following Task）

```
sim_data/
  └── sample/
      └── seed_{种子值}/
          └── {场景ID}/
              ├── {编号}.json          # 任务执行结果元数据
              ├── {编号}_info.json     # 每步详细数据
              ├── {编号}.mp4           # 视频文件
              └── track_object.jpg     # 跟踪目标图片
```

**示例**：
```
seed_100/
  └── 17DRP5sb8fy/
      ├── 4.json
      ├── 4_info.json
      ├── 4.mp4
      ├── 9.json
      ├── 9_info.json
      ├── 9.mp4
      └── track_object.jpg
```

### 导航任务（Navigation Task）

```
data/
  └── test_json_format/
      └── seed_{种子值}/
          └── scene_{场景编号}/
              ├── {编号}.json          # 任务执行结果元数据
              ├── {编号}_info.json     # 每步详细数据
              ├── {编号}.mp4           # 视频文件
              └── scene_map.jpg        # 场景地图图片
```

**示例**：
```
seed_100/
  ├── scene_00000/
  │   ├── 0.json
  │   ├── 0_info.json
  │   ├── 0.mp4
  │   └── scene_map.jpg
  └── scene_00001/
      ├── 1.json
      ├── 1_info.json
      ├── 1.mp4
      └── scene_map.jpg
```

## 文件格式详解

## 一、跟随任务（Following Task）格式

### 1. `{编号}.json` - 任务执行结果元数据

**文件说明**：包含任务执行的汇总信息和统计结果。

**JSON 结构**：
```json
{
  "finish": true,
  "status": "Normal",
  "success": 1.0,
  "following_rate": 0.47619047619047616,
  "following_step": 40,
  "total_step": 84,
  "collision": 0.0,
  "instruction": "Follow the person wearing a brown armored outfit and green sleeves."
}
```

**字段说明**：

| 字段名 | 类型 | 说明 | 取值范围/示例 |
|--------|------|------|--------------|
| `finish` | boolean | 任务是否完成 | `true` / `false` |
| `status` | string | 任务执行状态 | `"Normal"` 等 |
| `success` | float | 任务成功率 | `0.0` - `1.0` |
| `following_rate` | float | 跟随率 | `0.0` - `1.0` |
| `following_step` | integer | 成功跟随的步数 | 非负整数 |
| `total_step` | integer | 任务总步数 | 正整数，需与 `_info.json` 数组长度一致 |
| `collision` | float | 碰撞次数/值 | 非负浮点数 |
| `instruction` | string | 任务指令描述 | 自然语言字符串 |

### 2. `{编号}_info.json` - 每步详细数据

**文件说明**：包含任务执行过程中每个时间步的详细数据，是一个对象数组。

**JSON 结构**：
```json
[
  {
    "step": 1,
    "dis_to_human": 2.100193500518799,
    "facing": 0.0,
    "base_velocity": [
      1.5,
      0.11610042303800583,
      0.0638256873935461
    ]
  },
  {
    "step": 2,
    "dis_to_human": 1.8293745517730713,
    "facing": 0.0,
    "base_velocity": [
      0.7333487272262573,
      0.08077968843281269,
      0.12380489148199558
    ]
  }
  // ... 更多步骤
]
```

**数组元素字段说明**：

| 字段名 | 类型 | 说明 | 取值范围/示例 |
|--------|------|------|--------------|
| `step` | integer | 当前步数 | 从 `1` 开始，连续递增 |
| `dis_to_human` | float | 到目标人物的距离（米） | 非负浮点数 |
| `facing` | float | 面向状态 | `0.0`（未面向）或 `1.0`（面向） |
| `base_velocity` | array[float] | 3D 速度向量 | `[x, y, z]`，三个浮点数 |

**重要约束**：
- 数组长度必须等于对应 `{编号}.json` 中的 `total_step` 值
- `step` 字段必须从 1 开始，连续递增到 `total_step`
- 数组中的元素顺序必须按照 `step` 值从小到大排列

### 3. `{编号}.mp4` - 视频文件

**文件说明**：记录任务执行过程的视频文件。

**格式要求**：
- 文件格式：MP4
- 内容：任务执行过程的视频记录
- 命名：与对应的 JSON 文件编号一致

### 4. `track_object.jpg` - 跟踪目标图片

**文件说明**：显示被跟踪的目标对象的图片。

**格式要求**：
- 文件格式：JPG/JPEG
- 内容：目标对象的图像
- 命名：固定为 `track_object.jpg`（每个场景一个）

---

## 二、导航任务（Navigation Task）格式

### 1. `{编号}.json` - 任务执行结果元数据

**文件说明**：包含导航任务执行的汇总信息和统计结果。

**JSON 结构**：
```json
{
  "finish": true,
  "status": "Normal",
  "success": 1.0,
  "collision_count": 0,
  "total_step": 50,
  "duration": 5.0,
  "instruction": "Navigate in a 10.0m room with 3 obstacles using avoidance controller.",
  "controller_type": "avoidance",
  "room_size": 10.0,
  "num_obstacles": 3
}
```

**字段说明**：

| 字段名 | 类型 | 说明 | 取值范围/示例 |
|--------|------|------|--------------|
| `finish` | boolean | 任务是否完成 | `true` / `false` |
| `status` | string | 任务执行状态 | `"Normal"` 等 |
| `success` | float | 任务成功率 | `0.0` - `1.0` |
| `collision_count` | integer | 碰撞次数 | 非负整数 |
| `total_step` | integer | 任务总步数 | 正整数，需与 `_info.json` 数组长度一致 |
| `duration` | float | 任务持续时间（秒） | 正浮点数 |
| `instruction` | string | 任务指令描述 | 自然语言字符串 |
| `controller_type` | string | 控制器类型 | `"avoidance"` 等 |
| `room_size` | float | 房间大小（米） | 正浮点数 |
| `num_obstacles` | integer | 障碍物数量 | 非负整数 |

### 2. `{编号}_info.json` - 每步详细数据

**文件说明**：包含导航任务执行过程中每个时间步的详细数据，是一个对象数组。

**JSON 结构**：
```json
[
  {
    "step": 1,
    "position": {
      "x": 5.019999980926514,
      "y": 5.0,
      "theta": -0.08999999612569809
    },
    "velocity": {
      "linear": 0.20000000298023224,
      "angular": -0.8999999761581421
    },
    "collision": false
  },
  {
    "step": 2,
    "position": {
      "x": 5.039918899536133,
      "y": 4.998202323913574,
      "theta": -0.18000000715255737
    },
    "velocity": {
      "linear": 0.20000000298023224,
      "angular": -0.8999999761581421
    },
    "collision": false
  }
  // ... 更多步骤
]
```

**数组元素字段说明**：

| 字段名 | 类型 | 说明 | 取值范围/示例 |
|--------|------|------|--------------|
| `step` | integer | 当前步数 | 从 `1` 开始，连续递增 |
| `position` | object | 机器人位置信息 | 包含 x, y, theta 三个字段 |
| `position.x` | float | X 轴坐标（米） | 浮点数 |
| `position.y` | float | Y 轴坐标（米） | 浮点数 |
| `position.theta` | float | 朝向角度（弧度） | `-π` 到 `π` 之间 |
| `velocity` | object | 机器人速度信息 | 包含 linear 和 angular 两个字段 |
| `velocity.linear` | float | 线速度（米/秒） | 浮点数 |
| `velocity.angular` | float | 角速度（弧度/秒） | 浮点数 |
| `collision` | boolean | 该步是否发生碰撞 | `true` / `false` |

**重要约束**：
- 数组长度必须等于对应 `{编号}.json` 中的 `total_step` 值
- `step` 字段必须从 1 开始，连续递增到 `total_step`
- 数组中的元素顺序必须按照 `step` 值从小到大排列

### 3. `{编号}.mp4` - 视频文件

**文件说明**：记录导航任务执行过程的视频文件。

**格式要求**：
- 文件格式：MP4
- 内容：导航任务执行过程的视频记录
- 命名：与对应的 JSON 文件编号一致

### 4. `scene_map.jpg` - 场景地图图片

**文件说明**：显示导航场景的俯视图地图。

**格式要求**：
- 文件格式：JPG/JPEG
- 内容：场景的俯视图，包含障碍物分布
- 命名：固定为 `scene_map.jpg`（每个场景一个）

---

## 数据一致性要求

### 通用要求（两种任务类型都适用）

1. **编号对应**：同一编号的 `.json`、`_info.json` 和 `.mp4` 文件必须属于同一个任务
2. **步数一致**：`{编号}.json` 中的 `total_step` 必须等于 `{编号}_info.json` 数组的长度
3. **步数连续**：`_info.json` 中的 `step` 字段必须从 1 开始，连续递增，无缺失
4. **场景唯一**：每个场景ID对应一个唯一的场景环境

### 跟随任务特定要求

- 每个场景ID（如 `17DRP5sb8fy`）对应一个唯一的场景环境
- 必须包含 `track_object.jpg` 文件
- `following_step` 应小于等于 `total_step`

### 导航任务特定要求

- 场景编号格式：`scene_{编号}`（如 `scene_00000`）
- 必须包含 `scene_map.jpg` 文件
- `collision_count` 应与 `_info.json` 中 `collision: true` 的步数一致

## 数据生成流程建议

### 跟随任务生成流程

1. **确定场景信息**
   - 选择或生成场景ID（如 `17DRP5sb8fy`）
   - 确定种子值（如 `seed_100`）

2. **生成任务元数据** (`{编号}.json`)
   - 根据任务执行结果填写汇总信息
   - 确保 `total_step` 与实际步数一致
   - 计算 `following_rate` = `following_step` / `total_step`

3. **生成步骤数据** (`{编号}_info.json`)
   - 为每个时间步生成一个对象
   - 记录 `dis_to_human`、`facing`、`base_velocity`
   - 确保数组长度 = `total_step`
   - 确保 `step` 字段连续递增

4. **生成媒体文件**
   - 生成对应的 `.mp4` 视频文件
   - 生成 `track_object.jpg` 图片文件

5. **验证数据一致性**
   - 检查所有编号对应的文件是否存在
   - 验证 `total_step` 与 `_info.json` 数组长度一致
   - 验证 `step` 字段的连续性

### 导航任务生成流程

1. **确定场景信息**
   - 选择或生成场景编号（如 `scene_00000`）
   - 确定种子值（如 `seed_100`）
   - 设置房间大小和障碍物数量

2. **生成任务元数据** (`{编号}.json`)
   - 根据任务执行结果填写汇总信息
   - 确保 `total_step` 与实际步数一致
   - 记录 `collision_count`、`duration`
   - 填写控制器类型和环境参数

3. **生成步骤数据** (`{编号}_info.json`)
   - 为每个时间步生成一个对象
   - 记录 `position`（x, y, theta）
   - 记录 `velocity`（linear, angular）
   - 记录 `collision` 状态
   - 确保数组长度 = `total_step`
   - 确保 `step` 字段连续递增

4. **生成媒体文件**
   - 生成对应的 `.mp4` 视频文件
   - 生成 `scene_map.jpg` 场景地图

5. **验证数据一致性**
   - 检查所有编号对应的文件是否存在
   - 验证 `total_step` 与 `_info.json` 数组长度一致
   - 验证 `step` 字段的连续性
   - 验证 `collision_count` 与 `_info.json` 中碰撞步数一致

## 示例数据

### 跟随任务示例

#### 示例 1：任务 4

**4.json**:
```json
{
  "finish": true,
  "status": "Normal",
  "success": 1.0,
  "following_rate": 0.5573770491803278,
  "following_step": 34,
  "total_step": 61,
  "collision": 0.0,
  "instruction": "Follow the person wearing a brown armored outfit and green sleeves."
}
```

**4_info.json**:
- 数组长度为 61（与 `total_step` 一致）
- 第一个元素 `step: 1`，最后一个元素 `step: 61`
- 每个元素包含 `dis_to_human`、`facing`、`base_velocity`

#### 示例 2：任务 9

**9.json**:
```json
{
  "finish": true,
  "status": "Normal",
  "success": 1.0,
  "following_rate": 0.47619047619047616,
  "following_step": 40,
  "total_step": 84,
  "collision": 0.0,
  "instruction": "Follow the person wearing a brown armored outfit and green sleeves."
}
```

**9_info.json**:
- 数组长度为 84（与 `total_step` 一致）
- 第一个元素 `step: 1`，最后一个元素 `step: 84`

### 导航任务示例

#### 示例 1：scene_00000/任务 0

**0.json**:
```json
{
  "finish": true,
  "status": "Normal",
  "success": 1.0,
  "collision_count": 0,
  "total_step": 50,
  "duration": 5.0,
  "instruction": "Navigate in a 10.0m room with 3 obstacles using avoidance controller.",
  "controller_type": "avoidance",
  "room_size": 10.0,
  "num_obstacles": 3
}
```

**0_info.json**:
- 数组长度为 50（与 `total_step` 一致）
- 第一个元素 `step: 1`，最后一个元素 `step: 50`
- 每个元素包含 `position`（x, y, theta）、`velocity`（linear, angular）、`collision`
- 示例元素：
```json
{
  "step": 1,
  "position": {
    "x": 5.019999980926514,
    "y": 5.0,
    "theta": -0.08999999612569809
  },
  "velocity": {
    "linear": 0.20000000298023224,
    "angular": -0.8999999761581421
  },
  "collision": false
}
```

## 注意事项

### 通用注意事项

1. **数据类型**：严格按照字段类型要求，不要混淆整数和浮点数
2. **精度**：浮点数保持足够的精度（建议至少保留 10 位小数）
3. **编码**：所有 JSON 文件使用 UTF-8 编码
4. **格式**：JSON 文件应格式化良好，便于阅读和调试
5. **文件命名**：严格按照命名规范，确保编号一致性

### 跟随任务特定注意事项

1. **跟随率计算**：`following_rate` = `following_step` / `total_step`，确保计算正确
2. **距离单位**：`dis_to_human` 的单位是米（m）
3. **面向判断**：`facing` 只能是 `0.0` 或 `1.0`

### 导航任务特定注意事项

1. **角度范围**：`theta` 应在 `-π` 到 `π` 范围内
2. **碰撞一致性**：`collision_count` 必须与 `_info.json` 中 `collision: true` 的次数一致
3. **时间单位**：`duration` 的单位是秒（s）
4. **速度合理性**：线速度和角速度应符合实际物理约束
5. **场景编号**：导航任务使用 `scene_` 前缀加5位数字的格式

## 常见问题

### 跟随任务相关问题

**Q: `following_step` 和 `total_step` 的区别？**  
A: `total_step` 是任务执行的总步数，`following_step` 是成功跟随目标的步数。通常 `following_step ≤ total_step`。

**Q: `facing` 字段的含义？**  
A: `facing` 表示机器人是否面向目标，`1.0` 表示面向，`0.0` 表示未面向。

**Q: `base_velocity` 的单位是什么？**  
A: 速度向量的单位通常是米/秒（m/s），三个分量分别对应 x、y、z 轴方向的速度。

**Q: 一个场景可以有多个任务吗？**  
A: 可以。一个场景文件夹下可以有多个编号的任务（如 `4.json`、`9.json` 等），它们共享同一个 `track_object.jpg`。

### 导航任务相关问题

**Q: `position.theta` 的取值范围是什么？**  
A: `theta` 是朝向角度，以弧度表示，取值范围通常在 `-π` 到 `π` 之间（约 -3.14 到 3.14）。

**Q: `collision_count` 如何计算？**  
A: `collision_count` 是整个任务过程中发生碰撞的总次数，应该等于 `_info.json` 中 `collision: true` 的步数。

**Q: `velocity.linear` 和 `velocity.angular` 的单位是什么？**  
A: `linear` 的单位是米/秒（m/s），表示线速度；`angular` 的单位是弧度/秒（rad/s），表示角速度。

**Q: 导航任务的场景编号格式有要求吗？**  
A: 是的，导航任务的场景编号格式为 `scene_{编号}`，编号使用5位数字补零，如 `scene_00000`、`scene_00001`。

**Q: 导航任务和跟随任务的主要区别是什么？**  
A: 
- **导航任务**：机器人在环境中自主导航避障，关注位置、速度和碰撞
- **跟随任务**：机器人跟随目标人物，关注与目标的距离和面向状态
- 数据格式不同：导航任务使用 `position`、`velocity`、`collision`；跟随任务使用 `dis_to_human`、`facing`、`base_velocity`
