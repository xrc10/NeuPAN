# 相机方向修复总结

## 问题描述

PyRender 渲染中遇到了两个问题：

### 问题1：地面和天空颠倒（已修复）
- 上半部分显示的是地面网格（应该是天空）
- 下半部分显示的是天空（应该是地面）

### 问题2：图像倾斜（已修复）
- 地面网格线是倾斜的（从右上到左下）
- 应该是水平的（向远处汇聚）

## 原因分析

问题出在 `_robot_pose_to_camera_pose` 函数中的相机姿态矩阵计算错误。

### 坐标系约定

- **世界坐标系**: X-Y 是水平面，Z 是垂直向上
- **机器人坐标系**: 在 XY 平面移动，theta 是朝向角
- **PyRender 相机坐标系**: +X 右，+Y 上，-Z 前（看的方向）

### 修复前的问题

#### 第一版错误代码
旧代码错误地将相机的上方向映射到了 -Y（向下），导致图像上下颠倒：

```python
# 错误版本1：上下颠倒
pose[:3, :3] = np.array([
    [c, -s, 0],
    [s, c, 0],
    [0, 0, 1]
]) @ np.array([
    [0, 0, 1],   # 前
    [-1, 0, 0],  # 右
    [0, -1, 0]   # 上 → 映射到 -Y (错误！)
])
```

#### 第二版错误代码
第一次修复后，虽然天地方向正确了，但相机的"右"方向计算错误，导致图像倾斜：

```python
# 错误版本2：图像倾斜
cam_right = np.array([-forward_y, forward_x, 0])  # 错误的右方向！
```

正确的右方向应该使用右手定则：`right = up × (-forward)`

## 解决方案

### 修复后的代码

正确构建相机坐标系的三个轴：

```python
def _robot_pose_to_camera_pose(self, x, y, theta):
    pose = np.eye(4)
    
    # 相机位置
    pose[0, 3] = x
    pose[1, 3] = y
    pose[2, 3] = self.camera_height
    
    # 计算相机朝向（在世界坐标系中）
    forward_x = np.cos(theta)
    forward_y = np.sin(theta)
    
    # 相机坐标系的三个轴
    cam_forward = np.array([forward_x, forward_y, 0])  # 前方
    cam_up = np.array([0, 0, 1])                        # 上方 = 世界的 +Z
    
    # 右方向使用右手定则：right = up × (-forward)
    # 因为相机看向-Z，所以相机的+Z方向是-forward
    # right = [0,0,1] × [-forward_x, -forward_y, 0]
    #       = [sin(theta), -cos(theta), 0]
    #       = [forward_y, -forward_x, 0]
    cam_right = np.array([forward_y, -forward_x, 0])
    
    # 构建旋转矩阵
    pose[:3, 0] = cam_right      # 相机的 +X（右）
    pose[:3, 1] = cam_up         # 相机的 +Y（上）
    pose[:3, 2] = -cam_forward   # 相机的 +Z（深度方向）
    
    return pose
```

### 关键点

1. **相机的上方向** (+Y) 必须映射到世界的 +Z（垂直向上）
2. **相机的前方向** (-Z，因为相机看向 -Z) 映射到机器人的朝向（由 theta 决定）
3. **相机的右方向** (+X) 必须使用**正确的右手定则**计算：
   - ⚠️ 错误：`right = [-sin(theta), cos(theta), 0]`（导致图像倾斜）
   - ✅ 正确：`right = up × (-forward) = [sin(theta), -cos(theta), 0]`

### 右手坐标系叉积计算

在PyRender的右手坐标系中：
- 相机 +Y = up = [0, 0, 1]
- 相机 +Z = -forward（因为相机看向 -Z）
- 相机 +X = +Y × +Z = up × (-forward)

计算过程：
```
up = [0, 0, 1]
forward = [cos(theta), sin(theta), 0]
-forward = [-cos(theta), -sin(theta), 0]

right = up × (-forward)
      = [0, 0, 1] × [-cos(theta), -sin(theta), 0]
      = [0*0 - 1*(-sin(theta)), 1*(-cos(theta)) - 0*0, 0*(-sin(theta)) - 0*(-cos(theta))]
      = [sin(theta), -cos(theta), 0]
      = [forward_y, -forward_x, 0]
```

## 验证结果

### 测试场景

创建了 8 个不同朝向的测试帧（0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°）

### 验证项目

✅ **地面和天空方向**
- 上半部分：天空（浅色背景）
- 下半部分：地面（绿色网格）

✅ **相机旋转方向**
- Theta=0°：指南针指向 N（北），相机看向前方
- Theta=90°：指南针指向 E（东），相机旋转90度
- Theta=180°：指南针指向 S（南），相机旋转180度
- Theta=270°：指南针指向 W（西），相机旋转270度

✅ **视角一致性**
- 相机视角与俯视图中的障碍物位置完全一致
- 指南针方向与相机朝向完全匹配

## 测试文件

- `test_camera_direction.py` - 生成不同朝向的测试数据
- `navigation_data/seed_100/scene_00001/` - 测试渲染输出

## 对比图像

### 错误版本1 - 天地颠倒
- 天空在下方 ❌
- 地面在上方 ❌
- 图像完全上下颠倒

### 错误版本2 - 图像倾斜
- 天空在上方 ✅
- 地面在下方 ✅
- 但地面网格线倾斜（从右上到左下）❌

### 最终修复版本
- 天空在上方 ✅
- 地面在下方 ✅
- 地面网格线水平（向远处汇聚）✅
- 相机方向完全正确 ✅

## 相关修改

修改文件：
- `example/render2Dto3D_pyrender.py` - `_robot_pose_to_camera_pose()` 函数

新增文件：
- `example/test_camera_direction.py` - 相机方向测试工具
- `example/CAMERA_FIX_SUMMARY.md` - 本文档

## 使用建议

1. 使用修复后的脚本重新渲染所有数据
2. 验证生成的视频和图像
3. 如有问题，可使用 `test_camera_direction.py` 生成测试场景验证

## 技术细节

### PyRender 相机约定

- 相机默认看向 -Z 方向
- +X 是右，+Y 是上，+Z 是深度（远离相机）
- 使用透视投影（视场角 FOV）

### 坐标变换矩阵

4x4 齐次变换矩阵格式：
```
[Rx Ry Rz Tx]
[          ]
[Rx Ry Rz Ty]
[          ]
[Rx Ry Rz Tz]
[          ]
[0  0  0  1 ]
```

其中：
- R 是 3x3 旋转矩阵（列向量是各个轴）
- T 是平移向量 (Tx, Ty, Tz)

## 结论

相机方向问题已完全解决，现在可以正常使用 PyRender 进行第一人称视角渲染。
