"""
从episode_data.json还原2D动画
用于验证run_exp_for_render.py的输出是否正确
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation, PillowWriter
import argparse
from pathlib import Path


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
        
    def setup_figure(self):
        """设置图形窗口"""
        self.fig, self.ax = plt.subplots(figsize=(12, 10))
        
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
        
    def draw_robot(self, x, y, theta, color='blue', alpha=1.0):
        """绘制机器人"""
        radius = self.robot_info.get('radius', 0.5)
        
        if self.robot_info['shape'] == 'circle':
            # 圆形机器人
            circle = patches.Circle((x, y), radius, 
                                   color=color, alpha=alpha, zorder=10)
            self.ax.add_patch(circle)
            
            # 方向指示线
            dx = radius * np.cos(theta)
            dy = radius * np.sin(theta)
            self.ax.plot([x, x + dx], [y, y + dy], 
                        color='red', linewidth=2, alpha=alpha, zorder=11)
        else:
            # 矩形机器人（简化表示为圆）
            circle = patches.Circle((x, y), radius, 
                                   color=color, alpha=alpha, zorder=10)
            self.ax.add_patch(circle)
            
            # 方向指示线
            dx = radius * np.cos(theta)
            dy = radius * np.sin(theta)
            self.ax.plot([x, x + dx], [y, y + dy], 
                        color='red', linewidth=2, alpha=alpha, zorder=11)
    
    def draw_obstacle(self, obs_data, step_idx=None):
        """绘制障碍物"""
        # 获取障碍物在当前步的位置
        if step_idx is not None and obs_data['id'] < len(self.obstacle_trajectories):
            obs_id = str(obs_data['id'])
            if obs_id in self.obstacle_trajectories:
                traj = self.obstacle_trajectories[obs_id]
                if step_idx < len(traj):
                    center_x = traj[step_idx]['x']
                    center_y = traj[step_idx]['y']
                else:
                    center_x, center_y = obs_data['initial_center']
            else:
                center_x, center_y = obs_data['initial_center']
        else:
            center_x, center_y = obs_data['initial_center']
        
        # 如果有顶点，绘制多边形
        if 'vertices' in obs_data and obs_data['vertices']:
            vertices = np.array(obs_data['vertices'])
            if vertices.ndim == 2 and vertices.shape[0] == 2:
                # 顶点格式: [[x1, x2, ...], [y1, y2, ...]]
                polygon_points = list(zip(vertices[0, :], vertices[1, :]))
                polygon = patches.Polygon(polygon_points, 
                                         facecolor='red', alpha=0.3, 
                                         edgecolor='darkred', linewidth=2,
                                         zorder=5)
                self.ax.add_patch(polygon)
        else:
            # 绘制圆形障碍物
            radius = obs_data.get('radius', 0.5)
            circle = patches.Circle((center_x, center_y), radius,
                                   color='red', alpha=0.3,
                                   edgecolor='darkred', linewidth=2,
                                   zorder=5)
            self.ax.add_patch(circle)
        
        # 如果障碍物有速度，绘制速度箭头
        velocity = obs_data.get('velocity', [0, 0])
        if abs(velocity[0]) > 0.01 or abs(velocity[1]) > 0.01:
            self.ax.arrow(center_x, center_y, velocity[0], velocity[1],
                         head_width=0.3, head_length=0.2, 
                         fc='orange', ec='darkorange', 
                         linewidth=2, alpha=0.7, zorder=6)
    
    def init_animation(self):
        """初始化动画"""
        # 清空当前图形
        self.ax.clear()
        
        # 重新设置坐标轴
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
        
        # 绘制完整轨迹（淡色）
        trajectory_x = [pos['x'] for pos in self.robot_trajectory]
        trajectory_y = [pos['y'] for pos in self.robot_trajectory]
        self.ax.plot(trajectory_x, trajectory_y, 'b--', 
                    alpha=0.3, linewidth=1, label='Planned Path')
        
        # 绘制起点
        if len(self.robot_trajectory) > 0:
            start_pos = self.robot_trajectory[0]
            self.ax.plot(start_pos['x'], start_pos['y'], 
                        'go', markersize=15, label='Start', zorder=15)
        
        # 绘制终点
        if len(self.robot_trajectory) > 0:
            end_pos = self.robot_trajectory[-1]
            self.ax.plot(end_pos['x'], end_pos['y'], 
                        'r*', markersize=20, label='End', zorder=15)
        
        # 绘制初始障碍物
        for obs in self.initial_obstacles:
            self.draw_obstacle(obs, step_idx=0)
        
        self.ax.legend(loc='upper right', fontsize=10)
        
        return []
    
    def update_animation(self, frame):
        """更新动画帧"""
        # 清除之前的机器人和动态元素
        # 保留轨迹和障碍物
        patches_to_remove = []
        for p in self.ax.patches:
            # 只移除机器人（蓝色圆圈）
            if isinstance(p, patches.Circle) and p.get_facecolor()[2] > 0.5:  # 蓝色
                patches_to_remove.append(p)
        
        for p in patches_to_remove:
            p.remove()
        
        # 移除之前的线条（方向指示）
        lines_to_remove = []
        for line in self.ax.lines:
            if line.get_color() == 'red' and line.get_linewidth() == 2:
                lines_to_remove.append(line)
        
        for line in lines_to_remove:
            line.remove()
        
        # 绘制当前位置的机器人
        if frame < len(self.robot_trajectory):
            pos = self.robot_trajectory[frame]
            self.draw_robot(pos['x'], pos['y'], pos['theta'], color='blue', alpha=1.0)
            
            # 绘制已走过的轨迹（加粗）
            trajectory_x = [self.robot_trajectory[i]['x'] for i in range(frame + 1)]
            trajectory_y = [self.robot_trajectory[i]['y'] for i in range(frame + 1)]
            self.ax.plot(trajectory_x, trajectory_y, 'b-', 
                        linewidth=2, alpha=0.8, zorder=9)
            
            # 显示当前步数和信息
            info_text = f"Step: {frame + 1}/{len(self.robot_trajectory)}\n"
            if frame < len(self.actions):
                action = self.actions[frame]
                info_text += f"Linear: {action['linear']:.3f} m/s\n"
                info_text += f"Angular: {action['angular']:.3f} rad/s"
            
            self.ax.text(0.02, 0.98, info_text,
                        transform=self.ax.transAxes,
                        fontsize=10,
                        verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # 绘制当前waypoint（如果有）
            if frame < len(self.waypoints) and self.waypoints[frame] is not None:
                waypoint = self.waypoints[frame]
                # 检查waypoint是否有效（不是空列表且有两个坐标）
                if isinstance(waypoint, (list, tuple)) and len(waypoint) >= 2:
                    self.ax.plot(waypoint[0], waypoint[1], 
                               'g^', markersize=10, alpha=0.6, zorder=12)
        
        return []
    
    def create_animation(self, save=True, show=False):
        """创建动画"""
        print("创建动画...")
        
        # 创建figure和axis
        self.fig, self.ax = plt.subplots(figsize=(12, 10))
        
        # 设置动画
        num_frames = len(self.robot_trajectory)
        anim = FuncAnimation(self.fig, self.update_animation, 
                           init_func=self.init_animation,
                           frames=num_frames,
                           interval=1000/self.fps,
                           blit=False,
                           repeat=True)
        
        # 保存动画
        if save and self.output_path:
            print(f"保存动画到: {self.output_path}")
            
            if self.output_path.endswith('.gif'):
                writer = PillowWriter(fps=self.fps)
                anim.save(self.output_path, writer=writer)
            elif self.output_path.endswith('.mp4'):
                # 需要ffmpeg
                try:
                    from matplotlib.animation import FFMpegWriter
                    writer = FFMpegWriter(fps=self.fps, bitrate=1800)
                    anim.save(self.output_path, writer=writer)
                except Exception as e:
                    print(f"警告: 无法保存为mp4格式，请安装ffmpeg。错误: {e}")
                    print("尝试保存为gif格式...")
                    gif_path = self.output_path.replace('.mp4', '.gif')
                    writer = PillowWriter(fps=self.fps)
                    anim.save(gif_path, writer=writer)
                    print(f"已保存为: {gif_path}")
            
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
        
        # 绘制障碍物
        for obs in self.initial_obstacles:
            if 'vertices' in obs and obs['vertices']:
                vertices = np.array(obs['vertices'])
                if vertices.ndim == 2 and vertices.shape[0] == 2:
                    polygon_points = list(zip(vertices[0, :], vertices[1, :]))
                    polygon = patches.Polygon(polygon_points, 
                                             facecolor='red', alpha=0.3, 
                                             edgecolor='darkred', linewidth=2,
                                             label='Obstacles' if obs['id'] == 0 else '')
                    ax.add_patch(polygon)
            else:
                radius = obs.get('radius', 0.5)
                center = obs['initial_center']
                circle = patches.Circle((center[0], center[1]), radius,
                                       color='red', alpha=0.3,
                                       edgecolor='darkred', linewidth=2,
                                       label='Obstacles' if obs['id'] == 0 else '')
                ax.add_patch(circle)
        
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
