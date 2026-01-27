"""
运行实验并输出用于渲染的2D数据
用于将2D模拟环境转换为3D第一人称视频
"""

from neupan import neupan
import irsim
import numpy as np
import argparse
import json
import os
from pathlib import Path


def main(
    env_file,
    planner_file,
    output_dir="render_data",
    max_steps=1000, 
    point_vel=False,
    reverse=False,
    save_ani=True,
    ani_name="render_2d_animation",
):
    """
    运行实验并记录所有必要的2D数据用于后续渲染
    
    Args:
        env_file: 环境配置文件路径
        planner_file: 规划器配置文件路径
        output_dir: 输出目录
        max_steps: 最大步数
        point_vel: 是否使用点速度
        reverse: 是否反向运动
        save_ani: 是否保存2D动画（默认True）
        ani_name: 保存的动画文件名（不含扩展名）
    """
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 创建环境（不显示GUI）
    env = irsim.make(env_file, save_ani=save_ani, full=False, display=False)
    neupan_planner = neupan.init_from_yaml(planner_file)
    
    # 获取初始环境信息
    robot_info = env.get_robot_info()
    obstacle_info_list = env.get_obstacle_info_list()
    
    # 存储数据
    episode_data = {
        "robot_info": {
            "shape": robot_info.shape,
            "kinematics": robot_info.kinematics,
            "wheelbase": float(robot_info.wheelbase) if (hasattr(robot_info, 'wheelbase') and robot_info.wheelbase is not None) else 0.0,
            "radius": 0.5,  # 默认半径，可以从robot_info中获取
        },
        "initial_obstacles": [],
        "robot_trajectory": [],  # 存储机器人的完整轨迹
        "obstacle_trajectories": {},  # 存储所有障碍物的完整轨迹
        "actions": [],  # 存储每一步的action
        "waypoints": [],  # 存储每一步的中间目标点
        "step_info": [],  # 存储每一步的详细信息
    }
    
    # 记录初始障碍物信息
    for idx, obs_info in enumerate(obstacle_info_list):
        obstacle_data = {
            "id": idx,
            "initial_center": obs_info.center.flatten().tolist(),
            "radius": float(obs_info.radius),
            "velocity": obs_info.velocity.flatten().tolist() if obs_info.velocity is not None else [0.0, 0.0],
        }
        if obs_info.vertex is not None and len(obs_info.vertex) > 0:
            obstacle_data["vertices"] = obs_info.vertex.tolist()
        
        episode_data["initial_obstacles"].append(obstacle_data)
        episode_data["obstacle_trajectories"][idx] = []
    
    # 设置反向运动参数
    if reverse:
        for j in range(len(neupan_planner.initial_path)):
            neupan_planner.initial_path[j][-1, 0] = -1
            neupan_planner.initial_path[j][-2, 0] = neupan_planner.initial_path[j][-2, 0] + 3.14
    
    # 主循环
    step = 0
    success = False
    collision_count = 0
    
    for i in range(max_steps):
        # 获取机器人状态
        robot_state = env.get_robot_state()
        lidar_scan = env.get_lidar_scan()
        
        # 获取点云数据
        if point_vel:
            points, point_velocities = neupan_planner.scan_to_point_velocity(robot_state, lidar_scan)
        else:
            points = neupan_planner.scan_to_point(robot_state, lidar_scan)
            point_velocities = None
        
        # 规划action
        action, info = neupan_planner(robot_state, points, point_velocities)
        
        # 获取当前的waypoint（参考轨迹上最近的点）
        current_waypoint = None
        if hasattr(neupan_planner, 'ref_trajectory') and neupan_planner.ref_trajectory is not None:
            # 从参考轨迹中获取下一个waypoint
            if len(neupan_planner.ref_trajectory) > 0:
                # 找到距离机器人最近但在前方的航点
                ref_traj = neupan_planner.ref_trajectory[0]  # 假设第一条轨迹
                if ref_traj.shape[0] > 0:
                    # 简单取前方几个点作为waypoint
                    lookahead_idx = min(5, ref_traj.shape[0] - 1)  # 向前看5个点
                    current_waypoint = ref_traj[lookahead_idx, :2].tolist()
        
        # 如果没有waypoint，使用目标点
        if current_waypoint is None and hasattr(robot_info, 'goal'):
            current_waypoint = robot_info.goal[:2].flatten().tolist()
        
        # 记录当前步的信息
        step_data = {
            "step": step + 1,
            "robot_state": robot_state.flatten().tolist(),
            "action": action.flatten().tolist(),
            "waypoint": current_waypoint,
            "neupan_info": {
                "stop": bool(info["stop"]),
                "arrive": bool(info["arrive"]),
            }
        }
        
        # 记录机器人轨迹
        episode_data["robot_trajectory"].append({
            "x": float(robot_state[0, 0]),
            "y": float(robot_state[1, 0]),
            "theta": float(robot_state[2, 0]),
        })
        
        # 记录action
        episode_data["actions"].append({
            "linear": float(action[0, 0]) if action.shape[0] > 0 else 0.0,
            "angular": float(action[1, 0]) if action.shape[0] > 1 else 0.0,
        })
        
        # 记录waypoint
        episode_data["waypoints"].append(current_waypoint)
        
        # 记录障碍物当前位置
        current_obstacle_info = env.get_obstacle_info_list()
        for idx, obs_info in enumerate(current_obstacle_info):
            if idx < len(episode_data["obstacle_trajectories"]):
                episode_data["obstacle_trajectories"][idx].append({
                    "x": float(obs_info.center[0, 0]),
                    "y": float(obs_info.center[1, 0]),
                    "velocity": obs_info.velocity.flatten().tolist() if obs_info.velocity is not None else [0.0, 0.0],
                })
        
        # 记录详细步骤信息
        episode_data["step_info"].append(step_data)
        
        # 检查是否到达或停止
        if info["stop"]:
            print(f"步骤 {step + 1}: NeuPAN 因最小距离停止")
            break
        
        if info["arrive"]:
            print(f"步骤 {step + 1}: NeuPAN 到达目标")
            success = True
            break
        
        # 执行action
        env.step(action)
        
        # 如果需要保存动画，必须调用render来收集帧
        if save_ani:
            env.render()
        
        # 检查是否完成（碰撞等）
        if env.done():
            collision_count += 1
            print(f"步骤 {step + 1}: 环境结束 (可能碰撞)")
            break
        
        step += 1
    
    # 记录任务元数据
    episode_data["metadata"] = {
        "finish": success or step >= max_steps,
        "status": "Normal" if success else "Incomplete",
        "success": 1.0 if success else 0.0,
        "total_step": step,
        "collision_count": collision_count,
        "duration": float(step * 0.1),  # 假设每步0.1秒
        "env_file": env_file,
        "planner_file": planner_file,
    }
    
    # 保存数据
    output_file = output_path / "episode_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(episode_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n数据已保存到: {output_file}")
    print(f"总步数: {step}")
    print(f"成功: {success}")
    print(f"碰撞次数: {collision_count}")
    
    # 保存动画（如果启用）
    if save_ani:
        env.end(3, ani_name=ani_name)
        print(f"2D动画已保存为: {ani_name}")
    else:
        env.end(0)
    
    return episode_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行实验并输出用于渲染的2D数据")
    parser.add_argument("-e", "--example", type=str, default="polygon_robot", 
                        help="示例名称: pf, pf_obs, corridor, dyna_obs, dyna_non_obs, convex_obs, non_obs, polygon_robot, reverse")
    parser.add_argument("-d", "--kinematics", type=str, default="diff", 
                        help="运动学类型: acker, diff, omni")
    parser.add_argument("-o", "--output_dir", type=str, default="render_data",
                        help="输出目录")
    parser.add_argument("-v", "--point_vel", action='store_true', 
                        help="使用点速度")
    parser.add_argument("-m", "--max_steps", type=int, default=1000, 
                        help="最大步数")
    parser.add_argument("-a", "--save_ani", action='store_true', default=True,
                        help="保存2D动画mp4（默认开启）")
    parser.add_argument("--no_save_ani", action='store_false', dest='save_ani',
                        help="不保存2D动画mp4")
    
    args = parser.parse_args()
    
    env_path_file = args.example + "/" + args.kinematics + "/env.yaml"
    planner_path_file = args.example + "/" + args.kinematics + "/planner.yaml"
    
    reverse = (args.example == "reverse" and args.kinematics == "diff")
    
    # 生成动画名称
    ani_name = f"{args.example}_{args.kinematics}_render_2d"
    
    main(
        env_path_file, 
        planner_path_file, 
        output_dir=args.output_dir,
        max_steps=args.max_steps,
        point_vel=args.point_vel,
        reverse=reverse,
        save_ani=args.save_ani,
        ani_name=ani_name
    )
