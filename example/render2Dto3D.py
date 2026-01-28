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
    
    def render_first_person_video(self, also_save_gif=False):
        """渲染第一人称视频
        
        Args:
            also_save_gif: 是否同时保存GIF动画
        """
        
        print("开始渲染第一人称视频...")
        
        robot_traj = self.episode_data.get("robot_trajectory", [])
        obstacle_trajs = self.episode_data.get("obstacle_trajectories", {})
        initial_obstacles = self.episode_data.get("initial_obstacles", [])
        
        if not robot_traj:
            print("警告: 没有机器人轨迹数据")
            return None
        
        # 创建视频（使用更好的编码器）
        video_file = self.scene_dir / f"{self.episode_id}.mp4"
        
        # 尝试多种编码器，按优先级使用
        codecs_to_try = [
            ('avc1', 'H.264 (avc1)'),
            ('H264', 'H.264 (H264)'),
            ('X264', 'H.264 (X264)'),
            ('mp4v', 'MPEG-4'),
        ]
        
        out = None
        for codec, codec_name in codecs_to_try:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                out = cv2.VideoWriter(
                    str(video_file), 
                    fourcc, 
                    self.fps, 
                    (self.image_width, self.image_height)
                )
                
                # 测试是否真的可以打开
                if out.isOpened():
                    print(f"使用视频编码器: {codec_name}")
                    break
                else:
                    out.release()
                    out = None
            except Exception as e:
                if out:
                    out.release()
                out = None
                continue
        
        if out is None or not out.isOpened():
            print("警告: 无法初始化视频编码器，视频可能无法正常保存")
            # 最后尝试使用默认编码器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                str(video_file), 
                fourcc, 
                self.fps, 
                (self.image_width, self.image_height)
            )
        
        # 为每一帧渲染第一人称视图
        frames_written = 0
        all_frames_bgr = []  # 保存所有帧用于GIF生成
        
        for step_idx, robot_pos in enumerate(robot_traj):
            frame = self._render_first_person_frame(
                robot_pos, 
                obstacle_trajs, 
                initial_obstacles,
                step_idx
            )
            
            # 应用轻微的平滑滤波以改善视觉质量
            frame = cv2.GaussianBlur(frame, (3, 3), 0.5)
            
            # 转换为BGR格式（OpenCV格式）
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # 写入视频
            if out and out.isOpened():
                out.write(frame_bgr)
                frames_written += 1
            
            # 保存帧用于GIF（每隔一帧保存以减小文件大小）
            if also_save_gif and step_idx % 2 == 0:
                all_frames_bgr.append(frame_bgr)
            
            # 保存关键帧的图片（每10帧保存一次）
            if step_idx % 10 == 0:
                frame_file = self.scene_dir / f"frame_{step_idx}.jpg"
                cv2.imwrite(str(frame_file), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            if (step_idx + 1) % 10 == 0:
                print(f"已渲染 {step_idx + 1}/{len(robot_traj)} 帧")
        
        # 释放视频写入器
        if out:
            out.release()
        
        # 验证视频文件
        if video_file.exists():
            file_size = video_file.stat().st_size
            print(f"视频已保存: {video_file}")
            print(f"  - 总帧数: {frames_written}/{len(robot_traj)}")
            print(f"  - 文件大小: {file_size / 1024:.2f} KB")
            
            if file_size < 1024:  # 小于1KB可能有问题
                print("  - 警告: 视频文件过小，可能保存失败")
        else:
            print(f"错误: 视频文件未生成: {video_file}")
            video_file = None
        
        # 保存GIF动画（如果需要）
        gif_file = None
        if also_save_gif and len(all_frames_bgr) > 0:
            print("\n生成GIF动画...")
            gif_file = self.scene_dir / f"{self.episode_id}.gif"
            
            # 转换为PIL格式
            from PIL import Image
            pil_frames = [Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)) for f in all_frames_bgr]
            
            # 保存为GIF
            pil_frames[0].save(
                str(gif_file),
                save_all=True,
                append_images=pil_frames[1:],
                duration=int(1000 / (self.fps / 2)),  # 因为我们只保存了每隔一帧
                loop=0
            )
            
            if gif_file.exists():
                gif_size = gif_file.stat().st_size
                print(f"GIF动画已保存: {gif_file}")
                print(f"  - 总帧数: {len(pil_frames)}")
                print(f"  - 文件大小: {gif_size / 1024:.2f} KB")
        
        return video_file if video_file else gif_file
    
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
        
        # 计算地平线位置（考虑相机高度和俯仰角）
        # 相机略微向下倾斜，以便更好地看到地面
        pitch_angle = -5.0  # 向下倾斜5度
        pitch_rad = np.deg2rad(pitch_angle)
        horizon_y = int(self.image_height / 2 - self.image_height * pitch_rad / fov_rad)
        
        # 天空渐变（顶部深蓝，地平线浅蓝）- BGR格式
        for y in range(max(0, horizon_y)):
            t = y / max(1, horizon_y)
            # 从深蓝到浅蓝
            sky_color = (
                int(135 + (190 - 135) * t),  # B: 135->190
                int(180 + (220 - 180) * t),  # G: 180->220
                int(200 + (240 - 200) * t)   # R: 200->240
            )
            frame[y, :] = sky_color
        
        # 地面渐变（近处亮，远处暗）
        for y in range(horizon_y, self.image_height):
            t = (y - horizon_y) / max(1, self.image_height - horizon_y)
            # 从浅绿棕色到深绿色（更像道路/地面）
            ground_color = (
                int(60 + (100 - 60) * t),     # B: 60->100
                int(80 + (115 - 80) * t),     # G: 80->115
                int(70 + (100 - 70) * t)      # R: 70->100
            )
            frame[y, :] = ground_color
        
        # 添加地面网格效果
        self._draw_ground_grid(frame, robot_x, robot_y, robot_theta, horizon_y)
        
        # 添加远处的世界坐标参考标记（地标）
        self._draw_world_landmarks(frame, robot_x, robot_y, robot_theta, horizon_y)
        
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
                    
                    # 转换到机器人坐标系（相机坐标系：x向前，y向右）
                    local_x = dx * np.cos(-robot_theta) - dy * np.sin(-robot_theta)
                    local_y = -(dx * np.sin(-robot_theta) + dy * np.cos(-robot_theta))
                    
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
                
                # 转换到机器人坐标系（相机坐标系：x向前，y向右）
                local_x = dx * np.cos(-robot_theta) - dy * np.sin(-robot_theta)
                local_y = -(dx * np.sin(-robot_theta) + dy * np.cos(-robot_theta))
                
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
        """绘制地面网格效果（基于世界坐标系 - 显示绝对移动）"""
        grid_size = 2.0  # 网格间距（米）
        grid_color = (50, 70, 40)  # 深绿色 BGR
        grid_color_bright = (80, 110, 70)  # 亮绿色（用于主网格线）
        
        fov_rad = np.deg2rad(self.fov)
        view_distance = 50.0
        
        # 将世界坐标转换为相机坐标
        def world_to_camera(world_x, world_y):
            """将世界坐标转换为相机坐标系（相机坐标系：x向前，y向右）"""
            dx = world_x - robot_x
            dy = world_y - robot_y
            # 转换到相机坐标系
            local_x = dx * np.cos(-robot_theta) - dy * np.sin(-robot_theta)
            local_y = -(dx * np.sin(-robot_theta) + dy * np.cos(-robot_theta))
            return local_x, local_y
        
        # 计算世界坐标系中需要绘制的网格范围
        # 找出机器人周围的网格线
        robot_grid_x = int(np.floor(robot_x / grid_size))
        robot_grid_y = int(np.floor(robot_y / grid_size))
        
        grid_range = 30  # 搜索范围（格子数）
        
        # 绘制横向网格线（平行于世界坐标系的X轴）
        for grid_y_idx in range(robot_grid_y - grid_range, robot_grid_y + grid_range + 1):
            world_y = grid_y_idx * grid_size
            
            # 在这条线上采样多个点
            points = []
            for grid_x_idx in range(robot_grid_x - grid_range, robot_grid_x + grid_range + 1):
                world_x = grid_x_idx * grid_size
                
                # 转换到相机坐标
                local_x, local_y = world_to_camera(world_x, world_y)
                
                # 检查是否在视野内
                if local_x > 0.1 and local_x < view_distance:
                    distance = np.sqrt(local_x**2 + local_y**2)
                    if distance < view_distance:
                        angle = np.arctan2(local_y, local_x)
                        if abs(angle) < fov_rad / 2:
                            screen_x = self._project_to_screen_x(local_y, local_x)
                            screen_y = self._project_to_screen_y(local_x, horizon_y)
                            if 0 <= screen_x < self.image_width and horizon_y <= screen_y < self.image_height:
                                points.append([screen_x, screen_y, local_x])
            
            # 按照z坐标排序并绘制线段
            if len(points) >= 2:
                points = sorted(points, key=lambda p: p[2])
                
                # 判断是否是主网格线（每5条）
                is_major = (grid_y_idx % 5 == 0)
                color = grid_color_bright if is_major else grid_color
                thickness = 2 if is_major else 1
                
                # 绘制连续线段
                for i in range(len(points) - 1):
                    x1, y1, z1 = points[i]
                    x2, y2, z2 = points[i + 1]
                    
                    # 根据距离调整颜色亮度
                    avg_z = (z1 + z2) / 2
                    fade = max(0.3, 1.0 - avg_z / 60.0)
                    line_color = tuple(int(c * fade) for c in color)
                    
                    cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), line_color, thickness)
        
        # 绘制纵向网格线（平行于世界坐标系的Y轴）
        for grid_x_idx in range(robot_grid_x - grid_range, robot_grid_x + grid_range + 1):
            world_x = grid_x_idx * grid_size
            
            # 在这条线上采样多个点
            points = []
            for grid_y_idx in range(robot_grid_y - grid_range, robot_grid_y + grid_range + 1):
                world_y = grid_y_idx * grid_size
                
                # 转换到相机坐标
                local_x, local_y = world_to_camera(world_x, world_y)
                
                # 检查是否在视野内
                if local_x > 0.1 and local_x < view_distance:
                    distance = np.sqrt(local_x**2 + local_y**2)
                    if distance < view_distance:
                        angle = np.arctan2(local_y, local_x)
                        if abs(angle) < fov_rad / 2:
                            screen_x = self._project_to_screen_x(local_y, local_x)
                            screen_y = self._project_to_screen_y(local_x, horizon_y)
                            if 0 <= screen_x < self.image_width and horizon_y <= screen_y < self.image_height:
                                points.append([screen_x, screen_y, local_x])
            
            # 按照z坐标排序并绘制线段
            if len(points) >= 2:
                points = sorted(points, key=lambda p: p[2])
                
                # 判断是否是主网格线（每5条）
                is_major = (grid_x_idx % 5 == 0)
                color = grid_color_bright if is_major else grid_color
                thickness = 2 if is_major else 1
                
                # 绘制连续线段
                for i in range(len(points) - 1):
                    x1, y1, z1 = points[i]
                    x2, y2, z2 = points[i + 1]
                    
                    # 根据距离调整颜色亮度
                    avg_z = (z1 + z2) / 2
                    fade = max(0.3, 1.0 - avg_z / 60.0)
                    line_color = tuple(int(c * fade) for c in color)
                    
                    cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), line_color, thickness)
    
    def _draw_world_landmarks(self, frame, robot_x, robot_y, robot_theta, horizon_y):
        """绘制世界坐标系中的固定参考标记（远处地标）"""
        fov_rad = np.deg2rad(self.fov)
        view_distance = 100.0  # 远距离视野
        
        # 将世界坐标转换为相机坐标
        def world_to_camera(world_x, world_y):
            dx = world_x - robot_x
            dy = world_y - robot_y
            local_x = dx * np.cos(-robot_theta) - dy * np.sin(-robot_theta)
            local_y = -(dx * np.sin(-robot_theta) + dy * np.cos(-robot_theta))
            return local_x, local_y
        
        # 在世界坐标系中放置一些固定的参考点（地标塔）
        # 这些地标分布在世界坐标系的固定位置
        landmark_positions = [
            (0, 0, (255, 200, 100), "Origin"),      # 世界原点 - 金色
            (20, 0, (100, 200, 255), "East"),       # 东方 - 蓝色
            (-20, 0, (255, 100, 200), "West"),      # 西方 - 粉色
            (0, 20, (100, 255, 100), "North"),      # 北方 - 绿色
            (0, -20, (255, 255, 100), "South"),     # 南方 - 黄色
            (20, 20, (200, 150, 255), "NE"),        # 东北 - 紫色
            (-20, 20, (150, 255, 200), "NW"),       # 西北 - 青色
            (20, -20, (255, 180, 150), "SE"),       # 东南 - 橙色
            (-20, -20, (200, 200, 200), "SW"),      # 西南 - 灰色
        ]
        
        for world_x, world_y, color_bgr, label in landmark_positions:
            # 转换到相机坐标
            local_x, local_y = world_to_camera(world_x, world_y)
            
            # 检查是否在视野内
            if local_x > 5.0 and local_x < view_distance:  # 至少5米远
                distance = np.sqrt(local_x**2 + local_y**2)
                angle = np.arctan2(local_y, local_x)
                
                if abs(angle) < fov_rad / 2:
                    # 计算地标在地面上的位置
                    screen_x = self._project_to_screen_x(local_y, local_x)
                    screen_y_base = self._project_to_screen_y(local_x, horizon_y)
                    
                    # 地标高度（高塔）
                    landmark_height = 5.0
                    screen_y_top = self._project_to_screen_y_with_height(local_x, landmark_height, horizon_y)
                    
                    if 0 <= screen_x < self.image_width and screen_y_top >= 0:
                        # 根据距离调整地标大小和亮度
                        size_factor = max(0.3, min(1.0, 30.0 / distance))
                        brightness = max(0.5, min(1.0, 1.0 - distance / 150.0))
                        landmark_color = tuple(int(c * brightness) for c in color_bgr)
                        
                        # 地标宽度
                        landmark_width = max(2, int(8 * size_factor))
                        
                        # 绘制地标塔（垂直线）
                        if screen_y_base < self.image_height:
                            cv2.line(frame, 
                                    (screen_x, min(screen_y_base, self.image_height - 1)), 
                                    (screen_x, max(0, screen_y_top)),
                                    landmark_color, landmark_width)
                            
                            # 在顶部绘制标记（菱形或圆形）
                            marker_size = max(3, int(12 * size_factor))
                            if distance < 50:  # 近距离显示更多细节
                                # 绘制菱形标记
                                diamond_points = np.array([
                                    [screen_x, screen_y_top - marker_size],
                                    [screen_x + marker_size//2, screen_y_top],
                                    [screen_x, screen_y_top + marker_size],
                                    [screen_x - marker_size//2, screen_y_top]
                                ], dtype=np.int32)
                                cv2.fillPoly(frame, [diamond_points], landmark_color)
                                cv2.polylines(frame, [diamond_points], True, 
                                            tuple(int(c * 0.6) for c in landmark_color), 2)
                            else:
                                # 远距离只绘制圆形
                                cv2.circle(frame, (screen_x, screen_y_top), 
                                         max(2, marker_size//2), landmark_color, -1)
                            
                            # 如果足够近，显示标签
                            if distance < 40 and size_factor > 0.4:
                                label_y = max(20, screen_y_top - 15)
                                # 半透明背景
                                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 
                                                          0.4 * size_factor, 1)[0]
                                overlay = frame.copy()
                                cv2.rectangle(overlay, 
                                            (screen_x - text_size[0]//2 - 2, label_y - text_size[1] - 2),
                                            (screen_x + text_size[0]//2 + 2, label_y + 2),
                                            (0, 0, 0), -1)
                                cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
                                
                                # 标签文字
                                cv2.putText(frame, label,
                                          (screen_x - text_size[0]//2, label_y),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.4 * size_factor,
                                          (255, 255, 255), 1)
        
        # 在天空中添加固定的"太阳"位置（相对于世界坐标系的固定方向）
        # 太阳在世界坐标系的东南方向（45度）
        sun_world_angle = np.deg2rad(45)  # 世界坐标系中的角度
        sun_camera_angle = sun_world_angle - robot_theta  # 转换到相机坐标系
        
        # 归一化角度到[-π, π]
        sun_camera_angle = np.arctan2(np.sin(sun_camera_angle), np.cos(sun_camera_angle))
        
        # 如果太阳在视野内
        if abs(sun_camera_angle) < fov_rad / 2:
            sun_screen_x = int(self.image_width / 2 + 
                             np.tan(sun_camera_angle) * self.image_width / (2 * np.tan(fov_rad / 2)))
            sun_screen_y = int(horizon_y * 0.3)  # 在天空的上方
            
            if 0 <= sun_screen_x < self.image_width and 0 <= sun_screen_y < horizon_y:
                # 绘制太阳光晕
                for radius in [35, 28, 20, 12]:
                    alpha = 0.15 if radius > 20 else 0.3
                    overlay = frame.copy()
                    cv2.circle(overlay, (sun_screen_x, sun_screen_y), radius, 
                             (180, 220, 255), -1)  # 淡黄色
                    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
                
                # 绘制太阳核心
                cv2.circle(frame, (sun_screen_x, sun_screen_y), 8, 
                         (200, 240, 255), -1)
                cv2.circle(frame, (sun_screen_x, sun_screen_y), 8, 
                         (150, 200, 255), 2)
    
    def _draw_polygon_obstacle(self, frame, edges, obs_info, horizon_y, is_dynamic=False):
        """绘制多边形障碍物（改进版 - 更好的光照和细节）"""
        if not edges or len(edges) == 0:
            return
        
        # 根据障碍物大小和类型判断是墙壁还是小障碍物
        radius = obs_info.get("radius", 0.5)
        if radius > 10:  # 大障碍物，可能是墙壁
            if is_dynamic:
                obstacle_color = (100, 150, 255)  # 浅蓝色（动态墙壁）BGR
                edge_color = (50, 100, 200)
            else:
                obstacle_color = (200, 200, 210)  # 浅灰色（静态墙壁）BGR
                edge_color = (60, 60, 70)
            wall_height = self.wall_height
        else:  # 小障碍物
            if is_dynamic:
                obstacle_color = (0, 180, 255)  # 橙色（动态小障碍物）BGR
                edge_color = (0, 120, 200)
            else:
                obstacle_color = (60, 120, 255)  # 橙红色（静态小障碍物）BGR
                edge_color = (30, 60, 150)
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
            
            # 计算法向量（改进的光照计算）
            edge_dx = v2["local_y"] - v1["local_y"]  # 边在y方向（左右）的变化
            edge_dz = v2["local_x"] - v1["local_x"]  # 边在x方向（前后）的变化
            
            # 计算边的法向量（垂直于边，指向相机）
            normal_y = -edge_dz
            normal_z = edge_dx
            norm = np.sqrt(normal_y**2 + normal_z**2)
            if norm > 0:
                normal_y /= norm
                normal_z /= norm
            
            # 光源方向（从相机上方前方照射）
            light_dir = np.array([0.3, -0.5, 0.8])  # (y, height, z)
            light_dir = light_dir / np.linalg.norm(light_dir)
            
            # 计算法向量与光源的点积
            dot = abs(normal_y * light_dir[0] + normal_z * light_dir[2])
            
            # 基础亮度（0.4-1.0）
            brightness = 0.4 + 0.6 * dot
            
            # 根据距离调整亮度
            avg_distance = (v1["distance"] + v2["distance"]) / 2
            distance_factor = max(0.4, min(1.0, 1.0 - avg_distance / 70.0))
            brightness *= distance_factor
            
            # 应用光照
            face_color = tuple(int(c * brightness) for c in obstacle_color)
            edge_final_color = tuple(int(c * brightness * 0.5) for c in edge_color)
            
            # 绘制墙面
            cv2.fillPoly(frame, [wall_face], face_color)
            
            # 绘制边缘（更粗以增强立体感）
            cv2.polylines(frame, [wall_face], True, edge_final_color, 2)
            
            # 添加阴影效果（底部边缘）
            shadow_color = tuple(int(c * 0.3) for c in obstacle_color)
            shadow_line = np.array([
                [screen_x1_bottom, screen_y1_bottom],
                [screen_x2_bottom, screen_y2_bottom]
            ], dtype=np.int32)
            cv2.polylines(frame, [shadow_line], False, shadow_color, 3)
    
    def _draw_circle_obstacle(self, frame, obs, horizon_y, is_dynamic=False):
        """绘制圆形障碍物（改进版 - 更好的3D效果）"""
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
        
        # 根据距离调整亮度
        brightness = max(0.4, min(1.0, 1.0 - distance / 60.0))
        
        # 根据障碍物大小和类型选择基础颜色
        if radius > 10:  # 大障碍物 - 墙壁
            if is_dynamic:
                base_color = (100, 150, 255)  # 浅蓝色（动态墙壁）BGR
            else:
                base_color = (200, 200, 210)  # 灰色（静态墙壁）BGR
        else:  # 小障碍物
            if is_dynamic:
                base_color = (0, 180, 255)  # 橙色（动态小障碍物）BGR
            else:
                base_color = (60, 120, 255)  # 橙红色（静态小障碍物）BGR
        
        # 绘制圆柱体
        obstacle_color = tuple(int(c * brightness) for c in base_color)
        edge_color = tuple(int(c * brightness * 0.4) for c in base_color)
        
        # 绘制地面阴影（更柔和）
        shadow_offset = 3
        shadow_radius = int(screen_radius * 0.8)
        cv2.ellipse(frame,
                   (screen_x + shadow_offset, screen_y_bottom + shadow_offset),
                   (shadow_radius, max(1, shadow_radius // 5)),
                   0, 0, 360,
                   (30, 40, 30), -1)
        
        # 绘制主体（使用更细致的光照模型）
        center_y = (screen_y_top + screen_y_bottom) // 2
        
        # 绘制多层渐变以增强立体感
        num_segments = 36
        for i in range(num_segments):
            angle_start = i * 10
            angle_end = (i + 1) * 10
            
            # 根据角度计算光照强度（左侧暗，右侧亮）
            mid_angle = (angle_start + angle_end) / 2
            angle_rad = np.deg2rad(mid_angle)
            
            # 光照计算：假设光源在右上方
            normal_x = np.cos(angle_rad)
            normal_z = np.sin(angle_rad)
            light_dir = np.array([0.7, 0.3])  # 右上方光源
            light_intensity = max(0.3, np.dot([normal_x, 0], light_dir))
            
            segment_color = tuple(int(c * light_intensity) for c in obstacle_color)
            
            cv2.ellipse(frame, 
                       (screen_x, center_y),
                       (screen_radius, int(screen_height / 2)),
                       0, angle_start, angle_end,
                       segment_color, -1)
        
        # 绘制顶部（椭圆）- 更明显
        top_ellipse_height = max(3, screen_radius // 4)
        top_color = tuple(int(c * 1.1) for c in obstacle_color)
        top_color = tuple(min(255, c) for c in top_color)
        cv2.ellipse(frame,
                   (screen_x, screen_y_top),
                   (screen_radius, top_ellipse_height),
                   0, 0, 360,
                   top_color, -1)
        cv2.ellipse(frame,
                   (screen_x, screen_y_top),
                   (screen_radius, top_ellipse_height),
                   0, 0, 360,
                   edge_color, 2)
        
        # 绘制高光（更自然的位置）
        highlight_offset_x = -int(screen_radius * 0.35)
        highlight_offset_y = -int(screen_height * 0.25)
        highlight_size_x = max(2, screen_radius // 4)
        highlight_size_y = max(2, screen_height // 8)
        
        highlight_color = tuple(int(c * 1.4) for c in obstacle_color)
        highlight_color = tuple(min(255, c) for c in highlight_color)
        cv2.ellipse(frame,
                   (screen_x + highlight_offset_x, center_y + highlight_offset_y),
                   (highlight_size_x, highlight_size_y),
                   0, 0, 360,
                   highlight_color, -1)
        
        # 绘制边缘轮廓（增强立体感）
        cv2.ellipse(frame,
                   (screen_x, center_y),
                   (screen_radius, int(screen_height / 2)),
                   0, 0, 360,
                   edge_color, 2)
        
        # 绘制底部边缘
        cv2.ellipse(frame,
                   (screen_x, screen_y_bottom),
                   (screen_radius, max(1, screen_radius // 6)),
                   0, 0, 180,
                   edge_color, 2)
    
    def _project_to_screen_x(self, y, z):
        """将相机坐标y投影到屏幕x坐标（y>0在右侧，映射到屏幕右侧）"""
        if z <= 0:
            return self.image_width // 2
        
        fov_rad = np.deg2rad(self.fov)
        # y为正（右侧）映射到屏幕右侧（screen_x增大）
        screen_x = self.image_width / 2 + (y / z) * (self.image_width / (2 * np.tan(fov_rad / 2)))
        return int(screen_x)
    
    def _project_to_screen_y(self, z, horizon_y):
        """将世界坐标z投影到屏幕y坐标（地面）"""
        if z <= 0.01:
            return horizon_y
        
        # 改进的透视投影（考虑FOV）
        fov_rad = np.deg2rad(self.fov)
        focal_length = self.image_height / (2 * np.tan(fov_rad / 2))
        screen_y = horizon_y + focal_length * self.camera_height / z
        return int(min(self.image_height - 1, screen_y))
    
    def _project_to_screen_y_with_height(self, z, height, horizon_y):
        """将世界坐标z和高度h投影到屏幕y坐标"""
        if z <= 0.01:
            return horizon_y
        
        # 改进的透视投影（考虑高度和FOV）
        fov_rad = np.deg2rad(self.fov)
        focal_length = self.image_height / (2 * np.tan(fov_rad / 2))
        screen_y = horizon_y + focal_length * (self.camera_height - height) / z
        return int(max(0, min(self.image_height - 1, screen_y)))
    
    def _draw_direction_indicator(self, frame, step_idx):
        """绘制方向指示器（小地图指南针）"""
        robot_traj = self.episode_data.get('robot_trajectory', [])
        if step_idx >= len(robot_traj):
            return
        
        pos = robot_traj[step_idx]
        theta = pos['theta']
        
        # 指南针位置（右上角）
        compass_x = self.image_width - 70
        compass_y = 50
        compass_radius = 30
        
        # 绘制背景圆
        overlay = frame.copy()
        cv2.circle(overlay, (compass_x, compass_y), compass_radius, (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.circle(frame, (compass_x, compass_y), compass_radius, (100, 150, 200), 2)
        
        # 绘制方向箭头
        arrow_length = compass_radius - 8
        arrow_end_x = int(compass_x + arrow_length * np.cos(theta - np.pi/2))
        arrow_end_y = int(compass_y + arrow_length * np.sin(theta - np.pi/2))
        
        # 箭头主体
        cv2.arrowedLine(frame, (compass_x, compass_y), (arrow_end_x, arrow_end_y),
                       (100, 255, 100), 3, tipLength=0.4)
        
        # 绘制N/S/E/W标记
        cv2.putText(frame, "N", (compass_x - 5, compass_y - compass_radius - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def _draw_ui_info(self, frame, step_idx):
        """绘制UI信息（改进版 - 更清晰的显示）"""
        # 获取机器人位置和动作信息
        robot_traj = self.episode_data.get('robot_trajectory', [])
        info_text = f"Frame: {step_idx + 1}/{len(robot_traj)}"
        
        if step_idx < len(robot_traj):
            pos = robot_traj[step_idx]
            pos_text = f"Pos: ({pos['x']:.2f}, {pos['y']:.2f})"
            theta_text = f"Theta: {np.rad2deg(pos['theta']):.1f} deg"
        else:
            pos_text = "Pos: (0.00, 0.00)"
            theta_text = "Theta: 0.0 deg"
        
        if step_idx < len(self.episode_data.get('actions', [])):
            action = self.episode_data['actions'][step_idx]
            vel_text = f"Linear: {action['linear']:.2f} m/s"
            ang_text = f"Angular: {action['angular']:.2f} rad/s"
        else:
            vel_text = "Linear: 0.00 m/s"
            ang_text = "Angular: 0.00 rad/s"
        
        # 绘制半透明背景（更大的区域）
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (300, 130), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # 绘制边框
        cv2.rectangle(frame, (10, 10), (300, 130), (100, 150, 200), 2)
        
        # 绘制文字（带阴影效果）
        texts = [info_text, pos_text, theta_text, vel_text, ang_text]
        y_positions = [35, 55, 75, 95, 115]
        
        for text, y_pos in zip(texts, y_positions):
            # 阴影
            cv2.putText(frame, text, (21, y_pos + 1), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            # 主文字
            cv2.putText(frame, text, (20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        
        # 添加方向指示器（右上角）
        self._draw_direction_indicator(frame, step_idx)
    
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
    
    def process(self, clean_old_files=False, save_gif=False):
        """执行完整的渲染pipeline
        
        Args:
            clean_old_files: 是否清理旧文件
            save_gif: 是否同时保存GIF动画
        """
        print(f"\n开始处理 Scene {self.scene_id:05d}, Episode {self.episode_id}")
        print("=" * 60)
        
        # 清理旧文件（如果需要）
        if clean_old_files and self.scene_dir.exists():
            print("\n[0/3] 清理旧文件...")
            import shutil
            # 只删除输出文件，保留目录结构
            for pattern in ['*.mp4', '*.gif', 'frame_*.jpg']:
                for file in self.scene_dir.glob(pattern):
                    try:
                        file.unlink()
                        print(f"  已删除: {file.name}")
                    except Exception as e:
                        print(f"  删除失败: {file.name} - {e}")
        
        # 1. 生成导航任务格式数据
        print("\n[1/3] 生成导航任务格式数据...")
        task_metadata, step_info = self.generate_navigation_data()
        
        # 2. 生成场景地图
        print("\n[2/3] 生成场景地图...")
        map_file = self.generate_scene_map()
        
        # 3. 渲染第一人称视频
        print("\n[3/3] 渲染第一人称视频...")
        video_file = self.render_first_person_video(also_save_gif=save_gif)
        
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
    parser.add_argument("--gif", action="store_true",
                        help="同时生成GIF动画")
    parser.add_argument("--clean", action="store_true",
                        help="渲染前清理旧文件")
    
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
    result = renderer.process(
        clean_old_files=args.clean,
        save_gif=args.gif
    )
    
    print("\n所有文件已生成，符合DATA_FORMAT.md的navigation格式要求")


if __name__ == "__main__":
    main()
