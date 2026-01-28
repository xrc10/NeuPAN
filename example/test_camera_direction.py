"""
测试相机方向是否正确
生成不同theta角度的测试帧，验证相机朝向
"""

import json
import numpy as np
from pathlib import Path

# 读取原始数据
with open('render_data/episode_data.json', 'r') as f:
    episode_data = json.load(f)

# 创建测试数据，在固定位置但不同朝向
test_data = episode_data.copy()

# 修改轨迹：在原点附近，朝向不同方向
test_positions = []
num_angles = 8
for i in range(num_angles):
    theta = i * (2 * np.pi / num_angles)  # 0, 45, 90, 135, 180, 225, 270, 315度
    test_positions.append({
        'x': 0.0,
        'y': 0.0,
        'theta': theta
    })

test_data['robot_trajectory'] = test_positions
test_data['actions'] = [{'linear': 0.0, 'angular': 0.0} for _ in range(len(test_positions))]

# 保存测试数据
test_file = Path('render_data/test_camera_direction.json')
with open(test_file, 'w', encoding='utf-8') as f:
    json.dump(test_data, f, indent=2)

print(f"测试数据已生成: {test_file}")
print(f"生成了 {num_angles} 个不同朝向的帧：")
for i, pos in enumerate(test_positions):
    theta_deg = np.rad2deg(pos['theta'])
    print(f"  帧 {i}: theta = {theta_deg:6.1f}°")

print("\n运行以下命令进行测试：")
print(f"./render_with_xvfb.sh -i {test_file} --scene_id 1 --clean")
