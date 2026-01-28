"""
将2D模拟数据渲染为3D第一人称视频
并生成符合DATA_FORMAT.md的navigation任务格式数据
"""

import json
import numpy as np
from pathlib import Path
import argparse
from typing import Dict, List, Tuple
import cv2


class Renderer2Dto3D:
    """将2D数据渲染为3D第一人称视频的渲染器"""
    
    def __init__(
        self,
        episode_data: Dict,
        output_dir: str = "navigation_data",
        seed: int = 100,
        scene_id: int = 0,
        episode_id: int = 0,
        wall_height: float = 2.5,
        obstacle_height: float = 1.5,
        camera_height: float = 1.2,
        fov: float = 90.0,
        image_width: int = 640,
        image_height: int = 480,
        fps: int = 10,
    ):
        """
        初始化渲染器
        
        Args:
            episode_data: 从run_exp_for_render.py生成的episode数据
            output_dir: 输出目录
            seed: 随机种子
            scene_id: 场景ID
            episode_id: 任务ID
            wall_height: 墙壁高度（米）
            obstacle_height: 障碍物高度（米）
            camera_height: 摄像机高度（米）
            fov: 视场角（度）
            image_width: 图像宽度
            image_height: 图像高度
            fps: 帧率
        """
        self.episode_data = episode_data
        self.output_dir = Path(output_dir)
        self.seed = seed
        self.scene_id = scene_id
        self.episode_id = episode_id
        
        # 3D渲染参数
        self.wall_height = wall_height
        self.obstacle_height = obstacle_height
        self.camera_height = camera_height
        self.fov = fov
        self.image_width = image_width
        self.image_height = image_height
        self.fps = fps
        
        # 创建输出目录结构
        self.scene_dir = self.output_dir / f"seed_{seed}" / f"scene_{scene_id:05d}"
        self.scene_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_navigation_data(self):
        """生成符合DATA_FORMAT.md的navigation任务格式数据"""
        
        # 生成 {编号}.json - 任务元数据
        metadata = self.episode_data.get("metadata", {})
        robot_traj = self.episode_data.get("robot_trajectory", [])
        
        # 计算碰撞次数（简化：从metadata获取）
        collision_count = metadata.get("collision_count", 0)
        
        # 生成任务元数据文件
        task_metadata = {
            "finish": metadata.get("finish", True),
            "status": metadata.get("status", "Normal"),
            "success": metadata.get("success", 1.0),
            "collision_count": collision_count,
            "total_step": metadata.get("total_step", len(robot_traj)),
            "duration": metadata.get("duration", len(robot_traj) * 0.1),
            "instruction": self._generate_instruction(),
            "controller_type": "neupan",
            "room_size": self._estimate_room_size(),
            "num_obstacles": len(self.episode_data.get("initial_obstacles", [])),
        }
        
        # 保存任务元数据
        metadata_file = self.scene_dir / f"{self.episode_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(task_metadata, f, indent=2, ensure_ascii=False)
        
        print(f"任务元数据已保存: {metadata_file}")
        
        # 生成 {编号}_info.json - 每步详细数据
        step_info_list = []
        robot_traj = self.episode_data.get("robot_trajectory", [])
        actions = self.episode_data.get("actions", [])
        
        for step_idx in range(len(robot_traj)):
            position_data = robot_traj[step_idx]
            action_data = actions[step_idx] if step_idx < len(actions) else {"linear": 0.0, "angular": 0.0}
            
            step_info = {
                "step": step_idx + 1,
                "position": {
                    "x": position_data["x"],
                    "y": position_data["y"],
                    "theta": position_data["theta"],
                },
                "velocity": {
                    "linear": action_data["linear"],
                    "angular": action_data["angular"],
                },
                "collision": False,  # 可以根据实际情况设置
            }
            step_info_list.append(step_info)
        
        # 保存步骤信息
        info_file = self.scene_dir / f"{self.episode_id}_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(step_info_list, f, indent=2, ensure_ascii=False)
        
        print(f"步骤信息已保存: {info_file}")
        
        return task_metadata, step_info_list
    
    def generate_scene_map(self):
        """生成场景俯视图 scene_map.jpg（使用OpenCV）"""
        
        robot_traj = self.episode_data.get("robot_trajectory", [])
        obstacle_trajs = self.episode_data.get("obstacle_trajectories", {})
        initial_obstacles = self.episode_data.get("initial_obstacles", [])
        
        # 计算场景范围
        all_x = []
        all_y = []
        
        if robot_traj:
            all_x.extend([pos["x"] for pos in robot_traj])
            all_y.extend([pos["y"] for pos in robot_traj])
        
        for obs in initial_obstacles:
            center = obs.get("initial_center", [0, 0])
            all_x.append(center[0])
            all_y.append(center[1])
        
        if not all_x:
            print("警告: 没有数据可绘制")
            return None
        
        margin = 5.0
        x_min, x_max = min(all_x) - margin, max(all_x) + margin
        y_min, y_max = min(all_y) - margin, max(all_y) + margin
        
        # 创建图像（1000x1000像素）
        img_size = 1000
        map_img = np.ones((img_size, img_size, 3), dtype=np.uint8) * 255
        
        # 坐标转换函数
        def world_to_pixel(x, y):
            px = int((x - x_min) / (x_max - x_min) * (img_size - 100) + 50)
            py = int((y_max - y) / (y_max - y_min) * (img_size - 100) + 50)
            return px, py
        
        # 绘制网格
        grid_color = (220, 220, 220)
        for i in range(10):
            x = x_min + (x_max - x_min) * i / 10
            y = y_min + (y_max - y_min) * i / 10
            px1, py1 = world_to_pixel(x, y_min)
            px2, py2 = world_to_pixel(x, y_max)
            cv2.line(map_img, (px1, py1), (px2, py2), grid_color, 1)
            px1, py1 = world_to_pixel(x_min, y)
            px2, py2 = world_to_pixel(x_max, y)
            cv2.line(map_img, (px1, py1), (px2, py2), grid_color, 1)
        
        # 绘制障碍物
        for obs in initial_obstacles:
            center = obs.get("initial_center", [0, 0])
            vertices = obs.get("vertices", None)
            
            if vertices and len(vertices) == 2:
                # 多边形障碍物
                points = []
                for vx, vy in zip(vertices[0], vertices[1]):
                    px, py = world_to_pixel(vx, vy)
                    points.append([px, py])
                points = np.array(points, dtype=np.int32)
                cv2.fillPoly(map_img, [points], (180, 180, 255))
                cv2.polylines(map_img, [points], True, (150, 150, 200), 2)
            else:
                # 圆形障碍物
                radius = obs.get("radius", 0.5)
                px, py = world_to_pixel(center[0], center[1])
                pr = int(radius / (x_max - x_min) * (img_size - 100))
                cv2.circle(map_img, (px, py), pr, (180, 180, 255), -1)
                cv2.circle(map_img, (px, py), pr, (150, 150, 200), 2)
        
        # 绘制机器人轨迹
        if robot_traj:
            points = []
            for pos in robot_traj:
                px, py = world_to_pixel(pos["x"], pos["y"])
                points.append([px, py])
            points = np.array(points, dtype=np.int32)
            cv2.polylines(map_img, [points], False, (255, 100, 100), 2)
            
            # 标记起点和终点
            start_px, start_py = world_to_pixel(robot_traj[0]["x"], robot_traj[0]["y"])
            end_px, end_py = world_to_pixel(robot_traj[-1]["x"], robot_traj[-1]["y"])
            cv2.circle(map_img, (start_px, start_py), 8, (100, 255, 100), -1)
            cv2.circle(map_img, (end_px, end_py), 8, (100, 100, 255), -1)
        
        # 添加标题和图例
        cv2.putText(map_img, f"Scene {self.scene_id:05d} - Episode {self.episode_id}", 
                   (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(map_img, "Start", (20, img_size - 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 2)
        cv2.putText(map_img, "End", (20, img_size - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 255), 2)
        
        # 保存场景地图
        map_file = self.scene_dir / "scene_map.jpg"
        cv2.imwrite(str(map_file), map_img)
        
        print(f"场景地图已保存: {map_file}")
        
        return map_file
    
    def render_first_person_video(self):
        """渲染第一人称视频"""
        
        print("开始渲染第一人称视频...")
        
        robot_traj = self.episode_data.get("robot_trajectory", [])
        obstacle_trajs = self.episode_data.get("obstacle_trajectories", {})
        initial_obstacles = self.episode_data.get("initial_obstacles", [])
        
        if not robot_traj:
            print("警告: 没有机器人轨迹数据")
            return None
        
        # 创建视频
        video_file = self.scene_dir / f"{self.episode_id}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            str(video_file), 
            fourcc, 
            self.fps, 
            (self.image_width, self.image_height)
        )
        
        # 为每一帧渲染第一人称视图
        for step_idx, robot_pos in enumerate(robot_traj):
            frame = self._render_first_person_frame(
                robot_pos, 
                obstacle_trajs, 
                initial_obstacles,
                step_idx
            )
            
            # 转换为BGR格式（OpenCV格式）
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
            
            if (step_idx + 1) % 10 == 0:
                print(f"已渲染 {step_idx + 1}/{len(robot_traj)} 帧")
        
        out.release()
        print(f"视频已保存: {video_file}")
        
        return video_file
    
    def _render_first_person_frame(
        self, 
        robot_pos: Dict, 
        obstacle_trajs: Dict, 
        initial_obstacles: List,
        step_idx: int
    ) -> np.ndarray:
        """
        渲染单帧第一人称视图（改进版本）
        使用更真实的3D投影和渲染
        """
        
        # 创建黑色背景图像
        frame = np.zeros((self.image_height, self.image_width, 3), dtype=np.uint8)
        
        # 机器人位置和朝向
        robot_x = robot_pos["x"]
        robot_y = robot_pos["y"]
        robot_theta = robot_pos["theta"]
        
        # 设置视角范围
        view_distance = 50.0  # 增加可视距离
        fov_rad = np.deg2rad(self.fov)
        
        # 渲染天空和地面
        sky_color = (135, 206, 235)  # 天蓝色 BGR格式
        ground_color = (100, 120, 90)  # 深绿色
        
        horizon_y = self.image_height // 2
        frame[:horizon_y, :] = sky_color
        frame[horizon_y:, :] = ground_color
        
        # 添加地面网格效果
        self._draw_ground_grid(frame, robot_x, robot_y, robot_theta, horizon_y)
        
        # 收集所有需要渲染的障碍物
        obstacles_to_render = []
        
        for obs_id, traj in obstacle_trajs.items():
            obs_id_int = int(obs_id) if isinstance(obs_id, str) else obs_id
            
            if obs_id_int >= len(initial_obstacles):
                continue
            
            obs_info = initial_obstacles[obs_id_int]
            is_dynamic = obs_info.get('is_dynamic', False)
            
            # 获取当前位置
            if is_dynamic and step_idx < len(traj):
                # 动态障碍物：使用轨迹中的当前位置
                obs_pos = traj[step_idx]
                obs_x = obs_pos["x"]
                obs_y = obs_pos["y"]
            else:
                # 静态障碍物或没有轨迹数据：使用初始位置
                center = obs_info["initial_center"]
                obs_x, obs_y = center[0], center[1]
            
            # 获取障碍物顶点（如果有）
            vertices = obs_info.get("vertices", None)
            
            if vertices and len(vertices) == 2 and len(vertices[0]) >= 3:
                # 多边形障碍物（确保有至少3个顶点）
                vertices_x = np.array(vertices[0])
                vertices_y = np.array(vertices[1])
                
                # 如果是动态障碍物，需要平移顶点
                if is_dynamic:
                    initial_center = obs_info["initial_center"]
                    dx = obs_x - initial_center[0]
                    dy = obs_y - initial_center[1]
                    vertices_x = vertices_x + dx
                    vertices_y = vertices_y + dy
                
                # 将所有顶点转换到相机坐标系
                all_vertices_camera = []
                min_distance = float('inf')
                
                for vx, vy in zip(vertices_x, vertices_y):
                    # 计算相对位置
                    dx = vx - robot_x
                    dy = vy - robot_y
                    distance = np.sqrt(dx**2 + dy**2)
                    
                    # 转换到机器人坐标系（相机坐标系：x向前，y向左）
                    local_x = dx * np.cos(-robot_theta) - dy * np.sin(-robot_theta)
                    local_y = dx * np.sin(-robot_theta) + dy * np.cos(-robot_theta)
                    
                    all_vertices_camera.append({
                        "local_x": local_x,
                        "local_y": local_y,
                        "distance": distance
                    })
                    min_distance = min(min_distance, distance)
                
                # 提取可见的边（至少一个顶点在前方，或边跨越前方）
                visible_edges = []
                num_vertices = len(all_vertices_camera)
                
                for i in range(num_vertices):
                    v1 = all_vertices_camera[i]
                    v2 = all_vertices_camera[(i + 1) % num_vertices]
                    
                    # 检查边是否可见：至少一个端点在前方，或者边跨越前方平面
                    if v1["local_x"] > 0.1 or v2["local_x"] > 0.1 or (v1["local_x"] < 0 and v2["local_x"] > 0):
                        # 如果边跨越相机平面，需要裁剪
                        if v1["local_x"] <= 0.1 and v2["local_x"] > 0.1:
                            # v1在后方，v2在前方，插值找到交点
                            t = (0.1 - v1["local_x"]) / (v2["local_x"] - v1["local_x"])
                            v1_clipped = {
                                "local_x": 0.1,
                                "local_y": v1["local_y"] + t * (v2["local_y"] - v1["local_y"]),
                                "distance": v1["distance"] + t * (v2["distance"] - v1["distance"])
                            }
                            visible_edges.append((v1_clipped, v2))
                        elif v1["local_x"] > 0.1 and v2["local_x"] <= 0.1:
                            # v1在前方，v2在后方
                            t = (0.1 - v1["local_x"]) / (v2["local_x"] - v1["local_x"])
                            v2_clipped = {
                                "local_x": 0.1,
                                "local_y": v1["local_y"] + t * (v2["local_y"] - v1["local_y"]),
                                "distance": v1["distance"] + t * (v2["distance"] - v1["distance"])
                            }
                            visible_edges.append((v1, v2_clipped))
                        else:
                            # 两个端点都在前方
                            visible_edges.append((v1, v2))
                
                # 如果有可见的边，则渲染
                if len(visible_edges) > 0:
                    obstacles_to_render.append({
                        "type": "polygon",
                        "edges": visible_edges,
                        "obs_info": obs_info,
                        "distance": min_distance,
                        "is_dynamic": is_dynamic
                    })
            else:
                # 圆形障碍物或退化的多边形
                dx = obs_x - robot_x
                dy = obs_y - robot_y
                distance = np.sqrt(dx**2 + dy**2)
                
                # 转换到机器人坐标系
                local_x = dx * np.cos(-robot_theta) - dy * np.sin(-robot_theta)
                local_y = dx * np.sin(-robot_theta) + dy * np.cos(-robot_theta)
                
                # 计算相对角度
                angle_to_obs = np.arctan2(dy, dx)
                relative_angle = angle_to_obs - robot_theta
                relative_angle = np.arctan2(np.sin(relative_angle), np.cos(relative_angle))
                
                radius = obs_info.get("radius", 0.5)
                
                # 检查是否在视野内
                if local_x > 0.1 and distance < view_distance and abs(relative_angle) < fov_rad / 2:
                    obstacles_to_render.append({
                        "type": "circle",
                        "local_x": local_x,
                        "local_y": local_y,
                        "distance": distance,
                        "radius": radius,
                        "obs_info": obs_info,
                        "is_dynamic": is_dynamic
                    })
        
        # 按距离排序（远的先绘制）
        obstacles_to_render.sort(key=lambda x: x["distance"], reverse=True)
        
        # 渲染障碍物
        for obs in obstacles_to_render:
            is_dynamic = obs.get("is_dynamic", False)
            if obs["type"] == "polygon":
                self._draw_polygon_obstacle(frame, obs["edges"], obs["obs_info"], horizon_y, is_dynamic)
            else:
                self._draw_circle_obstacle(frame, obs, horizon_y, is_dynamic)
        
        # 添加UI信息
        self._draw_ui_info(frame, step_idx)
        
        return frame
    
    def _draw_ground_grid(self, frame, robot_x, robot_y, robot_theta, horizon_y):
        """绘制地面网格效果（改进版）"""
        grid_size = 2.0  # 网格间距（米）
        grid_color = (70, 90, 60)  # 深绿色 BGR
        
        fov_rad = np.deg2rad(self.fov)
        
        # 绘制横向网格线（深度线）
        for i in range(1, 25):
            z = i * grid_size  # 距离
            if z > 50:
                break
            
            # 左右边界
            left_y = -z * np.tan(fov_rad / 2)
            right_y = z * np.tan(fov_rad / 2)
            
            # 投影到屏幕
            screen_y = self._project_to_screen_y(z, horizon_y)
            
            if horizon_y <= screen_y < self.image_height:
                left_x = self._project_to_screen_x(left_y, z)
                right_x = self._project_to_screen_x(right_y, z)
                
                # 根据距离调整线宽（近粗远细）
                line_width = max(1, 3 - i // 5)
                
                cv2.line(frame, 
                        (max(0, left_x), screen_y), 
                        (min(self.image_width - 1, right_x), screen_y),
                        grid_color, line_width)
        
        # 绘制纵向网格线
        num_vertical_lines = 15
        for i in range(-num_vertical_lines, num_vertical_lines + 1):
            y = i * grid_size
            
            points = []
            for z in np.linspace(grid_size, 50, 30):
                screen_x = self._project_to_screen_x(y, z)
                screen_y = self._project_to_screen_y(z, horizon_y)
                
                if 0 <= screen_x < self.image_width and horizon_y <= screen_y < self.image_height:
                    points.append([screen_x, screen_y])
            
            # 绘制连续的线而不是点
            if len(points) >= 2:
                points = np.array(points, dtype=np.int32)
                cv2.polylines(frame, [points], False, grid_color, 1)
    
    def _draw_polygon_obstacle(self, frame, edges, obs_info, horizon_y, is_dynamic=False):
        """绘制多边形障碍物（改进版 - 基于边）"""
        if not edges or len(edges) == 0:
            return
        
        # 根据障碍物大小和类型判断是墙壁还是小障碍物
        radius = obs_info.get("radius", 0.5)
        if radius > 10:  # 大障碍物，可能是墙壁
            if is_dynamic:
                obstacle_color = (100, 150, 255)  # 浅蓝色（动态墙壁）BGR
                edge_color = (50, 100, 200)
            else:
                obstacle_color = (210, 210, 210)  # 浅灰色（静态墙壁）BGR
                edge_color = (80, 80, 80)
            wall_height = self.wall_height
        else:  # 小障碍物
            if is_dynamic:
                obstacle_color = (0, 165, 255)  # 橙色（动态小障碍物）BGR
                edge_color = (0, 100, 200)
            else:
                obstacle_color = (80, 100, 220)  # 橙红色（静态小障碍物）BGR
                edge_color = (40, 50, 120)
            wall_height = self.obstacle_height
        
        # 绘制每条边作为一个矩形面
        for v1, v2 in edges:
            # 投影边的两个端点
            # 底部点
            screen_x1_bottom = self._project_to_screen_x(v1["local_y"], v1["local_x"])
            screen_y1_bottom = self._project_to_screen_y(v1["local_x"], horizon_y)
            screen_x2_bottom = self._project_to_screen_x(v2["local_y"], v2["local_x"])
            screen_y2_bottom = self._project_to_screen_y(v2["local_x"], horizon_y)
            
            # 顶部点
            screen_x1_top = self._project_to_screen_x(v1["local_y"], v1["local_x"])
            screen_y1_top = self._project_to_screen_y_with_height(v1["local_x"], wall_height, horizon_y)
            screen_x2_top = self._project_to_screen_x(v2["local_y"], v2["local_x"])
            screen_y2_top = self._project_to_screen_y_with_height(v2["local_x"], wall_height, horizon_y)
            
            # 检查是否在屏幕范围内
            if (screen_x1_bottom < 0 and screen_x2_bottom < 0) or \
               (screen_x1_bottom >= self.image_width and screen_x2_bottom >= self.image_width):
                continue
            
            # 创建矩形面的四个顶点
            wall_face = np.array([
                [screen_x1_bottom, screen_y1_bottom],
                [screen_x2_bottom, screen_y2_bottom],
                [screen_x2_top, screen_y2_top],
                [screen_x1_top, screen_y1_top]
            ], dtype=np.int32)
            
            # 计算光照（基于边的方向）
            dx = v2["local_y"] - v1["local_y"]  # 在y方向（左右）的变化
            dy = v2["local_x"] - v1["local_x"]  # 在x方向（前后）的变化
            
            # 根据边的方向调整亮度
            if abs(dx) > abs(dy):  # 主要是左右延伸的边（正面墙）
                brightness = 0.9
            else:  # 主要是前后延伸的边（侧面墙）
                brightness = 0.7
            
            # 根据距离调整亮度
            avg_distance = (v1["distance"] + v2["distance"]) / 2
            distance_factor = max(0.5, min(1.0, 1.0 - avg_distance / 60.0))
            brightness *= distance_factor
            
            # 应用光照
            face_color = tuple(int(c * brightness) for c in obstacle_color)
            
            # 绘制墙面
            cv2.fillPoly(frame, [wall_face], face_color)
            cv2.polylines(frame, [wall_face], True, edge_color, 1)
    
    def _draw_circle_obstacle(self, frame, obs, horizon_y, is_dynamic=False):
        """绘制圆形障碍物（改进版）"""
        local_x = obs["local_x"]
        local_y = obs["local_y"]
        radius = obs["radius"]
        distance = obs["distance"]
        obs_info = obs.get("obs_info", {})
        
        # 投影中心点
        screen_x = self._project_to_screen_x(local_y, local_x)
        screen_y_bottom = self._project_to_screen_y(local_x, horizon_y)
        screen_y_top = self._project_to_screen_y_with_height(local_x, self.obstacle_height, horizon_y)
        
        # 计算屏幕空间的半径
        screen_radius = int(radius * self.image_width / (2 * local_x * np.tan(np.deg2rad(self.fov) / 2)))
        screen_height = screen_y_bottom - screen_y_top
        
        if screen_radius < 2:
            return
        
        # 根据距离调整颜色（近亮远暗）
        brightness = max(0.5, min(1.0, 1.0 - distance / 50.0))
        
        # 根据障碍物大小和类型选择基础颜色
        if radius > 10:  # 大障碍物 - 墙壁
            if is_dynamic:
                base_color = (100, 150, 255)  # 浅蓝色（动态墙壁）BGR
            else:
                base_color = (210, 210, 210)  # 灰色（静态墙壁）BGR
        else:  # 小障碍物
            if is_dynamic:
                base_color = (0, 165, 255)  # 橙色（动态小障碍物）BGR
            else:
                base_color = (80, 100, 220)  # 橙红色（静态小障碍物）BGR
        
        # 绘制圆柱体
        obstacle_color = tuple(int(c * brightness) for c in base_color)
        edge_color = tuple(int(c * brightness * 0.6) for c in base_color)
        shadow_color = tuple(int(c * brightness * 0.7) for c in base_color)
        
        # 绘制阴影（底部）
        cv2.ellipse(frame,
                   (screen_x + 2, screen_y_bottom + 2),
                   (screen_radius, max(1, screen_radius // 6)),
                   0, 0, 360,
                   (40, 50, 40), -1)
        
        # 绘制主体（左侧暗，右侧亮，增加立体感）
        center_y = (screen_y_top + screen_y_bottom) // 2
        
        # 绘制左侧（暗）
        cv2.ellipse(frame, 
                   (screen_x, center_y),
                   (screen_radius, int(screen_height / 2)),
                   0, 90, 270,
                   shadow_color, -1)
        
        # 绘制右侧（亮）
        cv2.ellipse(frame, 
                   (screen_x, center_y),
                   (screen_radius, int(screen_height / 2)),
                   0, 270, 90,
                   obstacle_color, -1)
        
        # 绘制顶部（椭圆）
        top_ellipse_height = max(2, screen_radius // 5)
        cv2.ellipse(frame,
                   (screen_x, screen_y_top),
                   (screen_radius, top_ellipse_height),
                   0, 0, 360,
                   obstacle_color, -1)
        
        # 绘制高光
        highlight_color = tuple(int(c * 1.3) for c in obstacle_color)
        highlight_color = tuple(min(255, c) for c in highlight_color)
        cv2.ellipse(frame,
                   (screen_x - screen_radius // 3, center_y - screen_height // 6),
                   (screen_radius // 3, screen_height // 6),
                   0, 0, 360,
                   highlight_color, -1)
        
        # 绘制边缘
        cv2.ellipse(frame,
                   (screen_x, center_y),
                   (screen_radius, int(screen_height / 2)),
                   0, 0, 360,
                   edge_color, 2)
    
    def _project_to_screen_x(self, y, z):
        """将世界坐标y投影到屏幕x坐标"""
        if z <= 0:
            return self.image_width // 2
        
        fov_rad = np.deg2rad(self.fov)
        screen_x = self.image_width / 2 + (y / z) * (self.image_width / (2 * np.tan(fov_rad / 2)))
        return int(screen_x)
    
    def _project_to_screen_y(self, z, horizon_y):
        """将世界坐标z投影到屏幕y坐标（地面）"""
        if z <= 0:
            return horizon_y
        
        # 简单透视投影
        focal_length = self.image_height / 2
        screen_y = horizon_y + focal_length * self.camera_height / z
        return int(screen_y)
    
    def _project_to_screen_y_with_height(self, z, height, horizon_y):
        """将世界坐标z和高度h投影到屏幕y坐标"""
        if z <= 0:
            return horizon_y
        
        # 透视投影考虑高度
        focal_length = self.image_height / 2
        screen_y = horizon_y + focal_length * (self.camera_height - height) / z
        return int(screen_y)
    
    def _draw_ui_info(self, frame, step_idx):
        """绘制UI信息"""
        # 获取动作信息
        info_text = f"Step: {step_idx + 1}/{len(self.episode_data.get('robot_trajectory', []))}"
        
        if step_idx < len(self.episode_data.get('actions', [])):
            action = self.episode_data['actions'][step_idx]
            info_text2 = f"V: {action['linear']:.2f} m/s"
            info_text3 = f"W: {action['angular']:.2f} rad/s"
        else:
            info_text2 = "V: 0.00 m/s"
            info_text3 = "W: 0.00 rad/s"
        
        # 绘制半透明背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (250, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        # 绘制文字
        cv2.putText(frame, info_text, (20, 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, info_text2, (20, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, info_text3, (20, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def _generate_instruction(self) -> str:
        """生成任务描述指令"""
        metadata = self.episode_data.get("metadata", {})
        num_obstacles = len(self.episode_data.get("initial_obstacles", []))
        room_size = self._estimate_room_size()
        
        instruction = f"Navigate in a {room_size:.1f}m room with {num_obstacles} obstacles using NeuPAN controller."
        return instruction
    
    def _estimate_room_size(self) -> float:
        """估算房间大小"""
        robot_traj = self.episode_data.get("robot_trajectory", [])
        
        if not robot_traj:
            return 10.0
        
        x_coords = [pos["x"] for pos in robot_traj]
        y_coords = [pos["y"] for pos in robot_traj]
        
        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)
        
        room_size = max(x_range, y_range) * 1.2  # 增加20%余量
        
        return room_size
    
    def process(self):
        """执行完整的渲染pipeline"""
        print(f"\n开始处理 Scene {self.scene_id:05d}, Episode {self.episode_id}")
        print("=" * 60)
        
        # 1. 生成导航任务格式数据
        print("\n[1/3] 生成导航任务格式数据...")
        task_metadata, step_info = self.generate_navigation_data()
        
        # 2. 生成场景地图
        print("\n[2/3] 生成场景地图...")
        map_file = self.generate_scene_map()
        
        # 3. 渲染第一人称视频
        print("\n[3/3] 渲染第一人称视频...")
        video_file = self.render_first_person_video()
        
        print("\n" + "=" * 60)
        print("处理完成！")
        print(f"输出目录: {self.scene_dir}")
        print(f"  - 任务元数据: {self.episode_id}.json")
        print(f"  - 步骤信息: {self.episode_id}_info.json")
        print(f"  - 场景地图: scene_map.jpg")
        print(f"  - 第一人称视频: {self.episode_id}.mp4")
        
        return {
            "scene_dir": str(self.scene_dir),
            "metadata_file": str(self.scene_dir / f"{self.episode_id}.json"),
            "info_file": str(self.scene_dir / f"{self.episode_id}_info.json"),
            "map_file": str(map_file),
            "video_file": str(video_file) if video_file else None,
        }


def main():
    parser = argparse.ArgumentParser(description="将2D数据渲染为3D第一人称视频")
    parser.add_argument("-i", "--input", type=str, default="render_data/episode_data.json",
                        help="输入的episode_data.json文件路径")
    parser.add_argument("-o", "--output_dir", type=str, default="navigation_data",
                        help="输出目录")
    parser.add_argument("-s", "--seed", type=int, default=100,
                        help="随机种子")
    parser.add_argument("--scene_id", type=int, default=0,
                        help="场景ID")
    parser.add_argument("--episode_id", type=int, default=0,
                        help="任务ID")
    parser.add_argument("--fps", type=int, default=10,
                        help="视频帧率")
    parser.add_argument("--width", type=int, default=640,
                        help="视频宽度")
    parser.add_argument("--height", type=int, default=480,
                        help="视频高度")
    
    args = parser.parse_args()
    
    # 读取episode数据
    print(f"读取数据: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        episode_data = json.load(f)
    
    # 创建渲染器
    renderer = Renderer2Dto3D(
        episode_data=episode_data,
        output_dir=args.output_dir,
        seed=args.seed,
        scene_id=args.scene_id,
        episode_id=args.episode_id,
        fps=args.fps,
        image_width=args.width,
        image_height=args.height,
    )
    
    # 执行渲染
    result = renderer.process()
    
    print("\n所有文件已生成，符合DATA_FORMAT.md的navigation格式要求")


if __name__ == "__main__":
    main()
