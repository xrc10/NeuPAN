"""
从episode_data.json还原2D动画（优化版）
用于验证run_exp_for_render.py的输出是否正确
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation, PillowWriter
import argparse
from pathlib import Path
from tqdm import tqdm


class EpisodeVisualizer:
    """从episode_data.json可视化2D导航过程"""
    
    def __init__(self, episode_data_path, output_path=None, fps=10):
        """
        初始化可视化器
        
        Args:
            episode_data_path: episode_data.json文件路径
            output_path: 输出gif/mp4文件路径（可选）
            fps: 动画帧率
        """
        self.fps = fps
        self.output_path = output_path
        
        # 加载数据
        print(f"加载数据: {episode_data_path}")
        with open(episode_data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # 提取数据
        self.robot_info = self.data['robot_info']
        self.robot_trajectory = self.data['robot_trajectory']
        self.initial_obstacles = self.data['initial_obstacles']
        self.obstacle_trajectories = self.data.get('obstacle_trajectories', {})
        self.actions = self.data.get('actions', [])
        self.waypoints = self.data.get('waypoints', [])
        self.metadata = self.data.get('metadata', {})
        
        print(f"机器人轨迹点数: {len(self.robot_trajectory)}")
        print(f"障碍物数量: {len(self.initial_obstacles)}")
        print(f"总步数: {self.metadata.get('total_step', len(self.robot_trajectory))}")
        print(f"任务状态: {self.metadata.get('status', 'Unknown')}")
        
        # 用于动画的对象引用
        self.robot_patch = None
        self.robot_direction_line = None
        self.robot_trail_line = None
        self.info_text = None
        self.waypoint_marker = None
        self.dynamic_obstacle_patches = []  # 存储动态障碍物的patch对象
        self.static_obstacle_patches = []   # 存储静态障碍物的patch对象
        
    def setup_figure(self):
        """设置图形窗口"""
        # 计算场景范围
        all_x = [pos['x'] for pos in self.robot_trajectory]
        all_y = [pos['y'] for pos in self.robot_trajectory]
        
        # 添加障碍物位置
        for obs in self.initial_obstacles:
            center = obs['initial_center']
            all_x.append(center[0])
            all_y.append(center[1])
            
            # 如果有顶点，也加入范围计算
            if 'vertices' in obs and obs['vertices']:
                vertices = np.array(obs['vertices'])
                if vertices.ndim == 2 and vertices.shape[0] == 2:
                    all_x.extend(vertices[0, :].tolist())
                    all_y.extend(vertices[1, :].tolist())
        
        # 设置坐标轴范围
        margin = 5.0
        x_min, x_max = min(all_x) - margin, max(all_x) + margin
        y_min, y_max = min(all_y) - margin, max(all_y) + margin
        
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('X (m)', fontsize=12)
        self.ax.set_ylabel('Y (m)', fontsize=12)
        
        # 标题
        title = f"Episode Visualization - {self.metadata.get('status', 'Unknown')}"
        if self.metadata.get('success', 0) > 0.5:
            title += " ✓"
        self.ax.set_title(title, fontsize=14, fontweight='bold')
        
    def draw_obstacles(self):
        """绘制障碍物（静态障碍物只绘制一次，动态障碍物创建可更新的patch）"""
        self.dynamic_obstacle_patches = []
        self.static_obstacle_patches = []
        
        for obs in self.initial_obstacles:
            center_x, center_y = obs['initial_center']
            # 检查是否真的是动态障碍物（通过轨迹数据判断）
            is_dynamic = obs.get('is_dynamic', False)
            
            # 如果没有明确标记，通过轨迹数据自动判断
            if not is_dynamic and str(obs['id']) in self.obstacle_trajectories:
                obs_traj = self.obstacle_trajectories[str(obs['id'])]
                if len(obs_traj) > 1:
                    # 检查起始和结束位置是否有显著变化
                    start_pos = obs_traj[0]
                    end_pos = obs_traj[-1]
                    distance_moved = np.sqrt(
                        (end_pos['x'] - start_pos['x'])**2 + 
                        (end_pos['y'] - start_pos['y'])**2
                    )
                    # 如果移动距离超过0.1米，认为是动态障碍物
                    if distance_moved > 0.1:
                        is_dynamic = True
                        print(f"检测到障碍物 {obs['id']} 是动态的（移动了 {distance_moved:.2f}m）")
            
            # 如果有顶点，绘制多边形
            if 'vertices' in obs and obs['vertices']:
                vertices = np.array(obs['vertices'])
                if vertices.ndim == 2 and vertices.shape[0] == 2:
                    polygon_points = list(zip(vertices[0, :], vertices[1, :]))
                    
                    if is_dynamic:
                        # 动态障碍物使用橙色
                        polygon = patches.Polygon(polygon_points, 
                                                 facecolor='orange', alpha=0.5, 
                                                 edgecolor='darkorange', linewidth=2,
                                                 zorder=5)
                        self.ax.add_patch(polygon)
                        self.dynamic_obstacle_patches.append({
                            'patch': polygon,
                            'obs_id': obs['id'],
                            'type': 'polygon',
                            'initial_vertices': vertices
                        })
                    else:
                        # 静态障碍物使用红色
                        polygon = patches.Polygon(polygon_points, 
                                                 facecolor='red', alpha=0.3, 
                                                 edgecolor='darkred', linewidth=2,
                                                 zorder=5)
                        self.ax.add_patch(polygon)
                        self.static_obstacle_patches.append(polygon)
            else:
                # 绘制圆形障碍物
                radius = obs.get('radius', 0.5)
                
                if is_dynamic:
                    # 动态障碍物使用橙色
                    circle = patches.Circle((center_x, center_y), radius,
                                           facecolor='orange', alpha=0.5,
                                           edgecolor='darkorange', linewidth=2,
                                           zorder=5)
                    self.ax.add_patch(circle)
                    self.dynamic_obstacle_patches.append({
                        'patch': circle,
                        'obs_id': obs['id'],
                        'type': 'circle',
                        'radius': radius
                    })
                else:
                    # 静态障碍物使用红色
                    circle = patches.Circle((center_x, center_y), radius,
                                           facecolor='red', alpha=0.3,
                                           edgecolor='darkred', linewidth=2,
                                           zorder=5)
                    self.ax.add_patch(circle)
                    self.static_obstacle_patches.append(circle)
    
    def init_animation(self):
        """初始化动画（只调用一次）"""
        self.ax.clear()
        self.setup_figure()
        
        # 绘制完整轨迹（淡色）
        trajectory_x = [pos['x'] for pos in self.robot_trajectory]
        trajectory_y = [pos['y'] for pos in self.robot_trajectory]
        self.ax.plot(trajectory_x, trajectory_y, 'b--', 
                    alpha=0.3, linewidth=1, label='Planned Path', zorder=3)
        
        # 绘制起点和终点
        if len(self.robot_trajectory) > 0:
            start_pos = self.robot_trajectory[0]
            self.ax.plot(start_pos['x'], start_pos['y'], 
                        'go', markersize=15, label='Start', zorder=15)
            
            end_pos = self.robot_trajectory[-1]
            self.ax.plot(end_pos['x'], end_pos['y'], 
                        'r*', markersize=20, label='End', zorder=15)
        
        # 绘制静态障碍物
        self.draw_obstacles()
        
        self.ax.legend(loc='upper right', fontsize=10)
        
        # 创建机器人patch（初始位置）
        radius = self.robot_info.get('radius', 0.5)
        pos = self.robot_trajectory[0]
        self.robot_patch = patches.Circle((pos['x'], pos['y']), radius,
                                         facecolor='blue', alpha=1.0, zorder=10)
        self.ax.add_patch(self.robot_patch)
        
        # 创建方向指示线
        dx = radius * np.cos(pos['theta'])
        dy = radius * np.sin(pos['theta'])
        self.robot_direction_line, = self.ax.plot([pos['x'], pos['x'] + dx], 
                                                   [pos['y'], pos['y'] + dy],
                                                   'r-', linewidth=2, zorder=11)
        
        # 创建机器人轨迹线（动态更新）
        self.robot_trail_line, = self.ax.plot([], [], 'b-', linewidth=2, alpha=0.8, zorder=9)
        
        # 创建信息文本
        self.info_text = self.ax.text(0.02, 0.98, '',
                                      transform=self.ax.transAxes,
                                      fontsize=10,
                                      verticalalignment='top',
                                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                                      zorder=20)
        
        # 创建waypoint标记（初始不可见）
        self.waypoint_marker, = self.ax.plot([], [], 'g^', markersize=10, alpha=0.6, zorder=12)
        
        # 返回所有需要更新的对象
        artists = [self.robot_patch, self.robot_direction_line, self.robot_trail_line, 
                   self.info_text, self.waypoint_marker]
        
        # 添加动态障碍物patches
        for dyn_obs in self.dynamic_obstacle_patches:
            artists.append(dyn_obs['patch'])
        
        return artists
    
    def update_animation(self, frame):
        """更新动画帧（高效版本，只更新变化的部分，包括动态障碍物）"""
        if frame >= len(self.robot_trajectory):
            artists = [self.robot_patch, self.robot_direction_line, self.robot_trail_line,
                       self.info_text, self.waypoint_marker]
            for dyn_obs in self.dynamic_obstacle_patches:
                artists.append(dyn_obs['patch'])
            return artists
        
        pos = self.robot_trajectory[frame]
        radius = self.robot_info.get('radius', 0.5)
        
        # 更新机器人位置
        self.robot_patch.center = (pos['x'], pos['y'])
        
        # 更新方向指示线
        dx = radius * np.cos(pos['theta'])
        dy = radius * np.sin(pos['theta'])
        self.robot_direction_line.set_data([pos['x'], pos['x'] + dx],
                                           [pos['y'], pos['y'] + dy])
        
        # 更新已走过的轨迹
        trajectory_x = [self.robot_trajectory[i]['x'] for i in range(frame + 1)]
        trajectory_y = [self.robot_trajectory[i]['y'] for i in range(frame + 1)]
        self.robot_trail_line.set_data(trajectory_x, trajectory_y)
        
        # 更新动态障碍物位置
        for dyn_obs in self.dynamic_obstacle_patches:
            obs_id = dyn_obs['obs_id']
            if str(obs_id) in self.obstacle_trajectories:
                obs_traj = self.obstacle_trajectories[str(obs_id)]
                if frame < len(obs_traj):
                    obs_pos = obs_traj[frame]
                    
                    if dyn_obs['type'] == 'circle':
                        # 更新圆形障碍物中心
                        dyn_obs['patch'].center = (obs_pos['x'], obs_pos['y'])
                    elif dyn_obs['type'] == 'polygon':
                        # 更新多边形障碍物位置
                        # 计算位移
                        initial_obs = self.initial_obstacles[obs_id]
                        initial_center = initial_obs['initial_center']
                        dx = obs_pos['x'] - initial_center[0]
                        dy = obs_pos['y'] - initial_center[1]
                        
                        # 移动所有顶点
                        initial_vertices = dyn_obs['initial_vertices']
                        new_vertices_x = initial_vertices[0, :] + dx
                        new_vertices_y = initial_vertices[1, :] + dy
                        new_polygon_points = list(zip(new_vertices_x, new_vertices_y))
                        dyn_obs['patch'].set_xy(new_polygon_points)
        
        # 更新信息文本
        info_text = f"Step: {frame + 1}/{len(self.robot_trajectory)}\n"
        if frame < len(self.actions):
            action = self.actions[frame]
            info_text += f"Linear: {action['linear']:.3f} m/s\n"
            info_text += f"Angular: {action['angular']:.3f} rad/s"
        self.info_text.set_text(info_text)
        
        # 更新waypoint标记
        if frame < len(self.waypoints) and self.waypoints[frame] is not None:
            waypoint = self.waypoints[frame]
            if isinstance(waypoint, (list, tuple)) and len(waypoint) >= 2:
                self.waypoint_marker.set_data([waypoint[0]], [waypoint[1]])
            else:
                self.waypoint_marker.set_data([], [])
        else:
            self.waypoint_marker.set_data([], [])
        
        # 返回所有更新的对象
        artists = [self.robot_patch, self.robot_direction_line, self.robot_trail_line,
                   self.info_text, self.waypoint_marker]
        
        for dyn_obs in self.dynamic_obstacle_patches:
            artists.append(dyn_obs['patch'])
        
        return artists
    
    def create_animation(self, save=True, show=False):
        """创建动画"""
        print("创建动画...")
        
        # 创建figure和axis
        self.fig, self.ax = plt.subplots(figsize=(12, 10))
        
        # 设置动画（使用blit=True加速）
        num_frames = len(self.robot_trajectory)
        anim = FuncAnimation(self.fig, self.update_animation, 
                           init_func=self.init_animation,
                           frames=num_frames,
                           interval=1000/self.fps,
                           blit=True,  # 启用blit加速
                           repeat=True)
        
        # 保存动画
        if save and self.output_path:
            print(f"保存动画到: {self.output_path}")
            
            # 创建进度条
            pbar = tqdm(total=num_frames, desc="生成动画", unit="帧", ncols=80)
            
            # 进度回调函数
            def progress_callback(current_frame, total_frames):
                pbar.update(1)
            
            if self.output_path.endswith('.gif'):
                writer = PillowWriter(fps=self.fps)
                try:
                    anim.save(self.output_path, writer=writer, dpi=80, 
                             progress_callback=progress_callback)
                except TypeError:
                    # 旧版本matplotlib不支持progress_callback
                    pbar.close()
                    pbar = tqdm(total=num_frames, desc="生成动画 (无法显示精确进度)", 
                               unit="帧", ncols=80, disable=True)
                    print(f"正在处理 {num_frames} 帧...")
                    anim.save(self.output_path, writer=writer, dpi=80)
            elif self.output_path.endswith('.mp4'):
                try:
                    from matplotlib.animation import FFMpegWriter
                    writer = FFMpegWriter(fps=self.fps, bitrate=1800)
                    try:
                        anim.save(self.output_path, writer=writer, dpi=80,
                                 progress_callback=progress_callback)
                    except TypeError:
                        pbar.close()
                        pbar = tqdm(total=num_frames, desc="生成动画 (无法显示精确进度)", 
                                   unit="帧", ncols=80, disable=True)
                        print(f"正在处理 {num_frames} 帧...")
                        anim.save(self.output_path, writer=writer, dpi=80)
                except Exception as e:
                    pbar.close()
                    print(f"警告: 无法保存为mp4格式，请安装ffmpeg。错误: {e}")
                    print("尝试保存为gif格式...")
                    gif_path = self.output_path.replace('.mp4', '.gif')
                    
                    # 重新创建进度条
                    pbar = tqdm(total=num_frames, desc="生成GIF", unit="帧", ncols=80)
                    writer = PillowWriter(fps=self.fps)
                    try:
                        anim.save(gif_path, writer=writer, dpi=80,
                                 progress_callback=progress_callback)
                    except TypeError:
                        pbar.close()
                        print(f"正在处理 {num_frames} 帧...")
                        anim.save(gif_path, writer=writer, dpi=80)
                    print(f"已保存为: {gif_path}")
            
            pbar.close()
            print("动画保存完成!")
        
        # 显示动画
        if show:
            plt.show()
        else:
            plt.close()
        
        return anim
    
    def create_static_plot(self, output_path=None):
        """创建静态图（显示完整轨迹）"""
        print("创建静态图...")
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 计算场景范围
        all_x = [pos['x'] for pos in self.robot_trajectory]
        all_y = [pos['y'] for pos in self.robot_trajectory]
        
        for obs in self.initial_obstacles:
            center = obs['initial_center']
            all_x.append(center[0])
            all_y.append(center[1])
        
        margin = 5.0
        x_min, x_max = min(all_x) - margin, max(all_x) + margin
        y_min, y_max = min(all_y) - margin, max(all_y) + margin
        
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('X (m)', fontsize=12)
        ax.set_ylabel('Y (m)', fontsize=12)
        
        title = f"Complete Trajectory - {self.metadata.get('status', 'Unknown')}"
        if self.metadata.get('success', 0) > 0.5:
            title += " ✓"
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # 绘制障碍物（区分静态和动态）
        static_label_added = False
        dynamic_label_added = False
        
        for obs in self.initial_obstacles:
            # 检查是否真的是动态障碍物（通过轨迹数据判断）
            is_dynamic = obs.get('is_dynamic', False)
            
            # 如果没有明确标记，通过轨迹数据自动判断
            if not is_dynamic and str(obs['id']) in self.obstacle_trajectories:
                obs_traj = self.obstacle_trajectories[str(obs['id'])]
                if len(obs_traj) > 1:
                    # 检查起始和结束位置是否有显著变化
                    start_pos = obs_traj[0]
                    end_pos = obs_traj[-1]
                    distance_moved = np.sqrt(
                        (end_pos['x'] - start_pos['x'])**2 + 
                        (end_pos['y'] - start_pos['y'])**2
                    )
                    # 如果移动距离超过0.1米，认为是动态障碍物
                    if distance_moved > 0.1:
                        is_dynamic = True
            
            if 'vertices' in obs and obs['vertices']:
                vertices = np.array(obs['vertices'])
                if vertices.ndim == 2 and vertices.shape[0] == 2:
                    polygon_points = list(zip(vertices[0, :], vertices[1, :]))
                    
                    if is_dynamic:
                        # 动态障碍物 - 绘制初始和最终位置
                        # 初始位置（淡橙色）
                        polygon = patches.Polygon(polygon_points, 
                                                 facecolor='orange', alpha=0.2, 
                                                 edgecolor='darkorange', linewidth=1, linestyle='--',
                                                 label='Dynamic Obstacles' if not dynamic_label_added else '')
                        ax.add_patch(polygon)
                        
                        # 如果有轨迹，绘制最终位置（深橙色）
                        if str(obs['id']) in self.obstacle_trajectories:
                            obs_traj = self.obstacle_trajectories[str(obs['id'])]
                            if len(obs_traj) > 0:
                                final_pos = obs_traj[-1]
                                initial_center = obs['initial_center']
                                dx = final_pos['x'] - initial_center[0]
                                dy = final_pos['y'] - initial_center[1]
                                
                                final_vertices_x = vertices[0, :] + dx
                                final_vertices_y = vertices[1, :] + dy
                                final_polygon_points = list(zip(final_vertices_x, final_vertices_y))
                                
                                final_polygon = patches.Polygon(final_polygon_points, 
                                                               facecolor='orange', alpha=0.4, 
                                                               edgecolor='darkorange', linewidth=2)
                                ax.add_patch(final_polygon)
                        
                        dynamic_label_added = True
                    else:
                        # 静态障碍物（红色）
                        polygon = patches.Polygon(polygon_points, 
                                                 facecolor='red', alpha=0.3, 
                                                 edgecolor='darkred', linewidth=2,
                                                 label='Static Obstacles' if not static_label_added else '')
                        ax.add_patch(polygon)
                        static_label_added = True
            else:
                # 圆形障碍物
                radius = obs.get('radius', 0.5)
                center = obs['initial_center']
                
                if is_dynamic:
                    # 动态障碍物 - 绘制初始和最终位置
                    # 初始位置（淡橙色）
                    circle = patches.Circle((center[0], center[1]), radius,
                                           facecolor='orange', alpha=0.2,
                                           edgecolor='darkorange', linewidth=1, linestyle='--',
                                           label='Dynamic Obstacles' if not dynamic_label_added else '')
                    ax.add_patch(circle)
                    
                    # 如果有轨迹，绘制最终位置和运动轨迹
                    if str(obs['id']) in self.obstacle_trajectories:
                        obs_traj = self.obstacle_trajectories[str(obs['id'])]
                        if len(obs_traj) > 0:
                            # 绘制运动轨迹
                            traj_x = [p['x'] for p in obs_traj]
                            traj_y = [p['y'] for p in obs_traj]
                            ax.plot(traj_x, traj_y, 'orange', linewidth=1, alpha=0.5, linestyle=':')
                            
                            # 最终位置（深橙色）
                            final_pos = obs_traj[-1]
                            final_circle = patches.Circle((final_pos['x'], final_pos['y']), radius,
                                                         facecolor='orange', alpha=0.4,
                                                         edgecolor='darkorange', linewidth=2)
                            ax.add_patch(final_circle)
                    
                    dynamic_label_added = True
                else:
                    # 静态障碍物（红色）
                    circle = patches.Circle((center[0], center[1]), radius,
                                           facecolor='red', alpha=0.3,
                                           edgecolor='darkred', linewidth=2,
                                           label='Static Obstacles' if not static_label_added else '')
                    ax.add_patch(circle)
                    static_label_added = True
        
        # 绘制完整轨迹
        trajectory_x = [pos['x'] for pos in self.robot_trajectory]
        trajectory_y = [pos['y'] for pos in self.robot_trajectory]
        ax.plot(trajectory_x, trajectory_y, 'b-', 
                linewidth=2, alpha=0.8, label='Robot Path')
        
        # 绘制起点和终点
        start_pos = self.robot_trajectory[0]
        end_pos = self.robot_trajectory[-1]
        ax.plot(start_pos['x'], start_pos['y'], 
                'go', markersize=15, label='Start')
        ax.plot(end_pos['x'], end_pos['y'], 
                'r*', markersize=20, label='End')
        
        # 添加信息文本
        info_text = f"Total Steps: {len(self.robot_trajectory)}\n"
        info_text += f"Duration: {self.metadata.get('duration', 0):.2f}s\n"
        info_text += f"Success: {self.metadata.get('success', 0):.1f}\n"
        info_text += f"Collisions: {self.metadata.get('collision_count', 0)}"
        
        ax.text(0.02, 0.98, info_text,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        ax.legend(loc='upper right', fontsize=10)
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"静态图已保存到: {output_path}")
        
        plt.close()


def main():
    parser = argparse.ArgumentParser(description="从episode_data.json还原2D动画")
    parser.add_argument("-i", "--input", type=str, required=True,
                       help="输入的episode_data.json文件路径")
    parser.add_argument("-o", "--output", type=str, default=None,
                       help="输出动画文件路径（支持.gif或.mp4）")
    parser.add_argument("-s", "--static", type=str, default=None,
                       help="输出静态轨迹图路径（.png/.jpg）")
    parser.add_argument("--fps", type=int, default=10,
                       help="动画帧率（默认10）")
    parser.add_argument("--show", action='store_true',
                       help="显示动画窗口")
    parser.add_argument("--no_save", action='store_true',
                       help="不保存动画文件")
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not Path(args.input).exists():
        print(f"错误: 文件不存在: {args.input}")
        return
    
    # 创建可视化器
    output_path = args.output
    if output_path is None and not args.no_save:
        # 自动生成输出文件名
        input_path = Path(args.input)
        output_path = str(input_path.parent / "episode_animation.gif")
    
    visualizer = EpisodeVisualizer(
        episode_data_path=args.input,
        output_path=output_path,
        fps=args.fps
    )
    
    # 创建动画
    if not args.no_save or args.show:
        visualizer.create_animation(save=not args.no_save, show=args.show)
    
    # 创建静态图
    if args.static:
        visualizer.create_static_plot(output_path=args.static)
    
    print("\n验证完成!")
    print(f"机器人轨迹点数: {len(visualizer.robot_trajectory)}")
    print(f"障碍物数量: {len(visualizer.initial_obstacles)}")
    print(f"任务状态: {visualizer.metadata.get('status', 'Unknown')}")
    print(f"成功: {visualizer.metadata.get('success', 0)}")


if __name__ == "__main__":
    main()
