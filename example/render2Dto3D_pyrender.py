"""
使用PyRender将2D模拟数据渲染为3D第一人称视频
相比手写版本，使用成熟的3D引擎大幅简化代码并提升渲染质量

注意：在无头服务器上运行时，请使用 xvfb-run 命令：
    xvfb-run -a -s "-screen 0 1024x768x24" python render2Dto3D_pyrender.py -i render_data/episode_data.json
"""

import json
import numpy as np
from pathlib import Path
import argparse
from typing import Dict, List, Tuple
import cv2

try:
    import pyrender
    import trimesh
except ImportError:
    print("错误: 需要安装 pyrender 和 trimesh")
    print("请运行: pip install pyrender trimesh")
    raise


class Renderer2Dto3D:
    """使用PyRender将2D数据渲染为3D第一人称视频的渲染器"""
    
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
        
        # 初始化PyRender渲染器（离线模式）
        self.renderer = pyrender.OffscreenRenderer(image_width, image_height)
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'renderer'):
            self.renderer.delete()
    
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
        """使用PyRender渲染第一人称视频
        
        Args:
            also_save_gif: 是否同时保存GIF动画
        """
        
        print("开始渲染第一人称视频（使用PyRender）...")
        
        robot_traj = self.episode_data.get("robot_trajectory", [])
        obstacle_trajs = self.episode_data.get("obstacle_trajectories", {})
        initial_obstacles = self.episode_data.get("initial_obstacles", [])
        
        if not robot_traj:
            print("警告: 没有机器人轨迹数据")
            return None
        
        # 创建视频
        video_file = self.scene_dir / f"{self.episode_id}.mp4"
        
        # 尝试多种编码器
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
                
                if out.isOpened():
                    print(f"使用视频编码器: {codec_name}")
                    break
                else:
                    out.release()
                    out = None
            except Exception:
                if out:
                    out.release()
                out = None
                continue
        
        if out is None or not out.isOpened():
            print("警告: 无法初始化视频编码器")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                str(video_file), 
                fourcc, 
                self.fps, 
                (self.image_width, self.image_height)
            )
        
        # 为每一帧渲染第一人称视图
        frames_written = 0
        all_frames_bgr = []
        
        for step_idx, robot_pos in enumerate(robot_traj):
            frame = self._render_first_person_frame_pyrender(
                robot_pos, 
                obstacle_trajs, 
                initial_obstacles,
                step_idx
            )
            
            # 转换为BGR格式（OpenCV格式）
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # 写入视频
            if out and out.isOpened():
                out.write(frame_bgr)
                frames_written += 1
            
            # 保存帧用于GIF
            if also_save_gif and step_idx % 2 == 0:
                all_frames_bgr.append(frame_bgr)
            
            # 保存关键帧的图片
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
            
            if file_size < 1024:
                print("  - 警告: 视频文件过小，可能保存失败")
        else:
            print(f"错误: 视频文件未生成: {video_file}")
            video_file = None
        
        # 保存GIF动画
        gif_file = None
        if also_save_gif and len(all_frames_bgr) > 0:
            print("\n生成GIF动画...")
            gif_file = self.scene_dir / f"{self.episode_id}.gif"
            
            from PIL import Image
            pil_frames = [Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)) for f in all_frames_bgr]
            
            pil_frames[0].save(
                str(gif_file),
                save_all=True,
                append_images=pil_frames[1:],
                duration=int(1000 / (self.fps / 2)),
                loop=0
            )
            
            if gif_file.exists():
                gif_size = gif_file.stat().st_size
                print(f"GIF动画已保存: {gif_file}")
                print(f"  - 总帧数: {len(pil_frames)}")
                print(f"  - 文件大小: {gif_size / 1024:.2f} KB")
        
        return video_file if video_file else gif_file
    
    def _render_first_person_frame_pyrender(
        self, 
        robot_pos: Dict, 
        obstacle_trajs: Dict, 
        initial_obstacles: List,
        step_idx: int
    ) -> np.ndarray:
        """
        使用PyRender渲染单帧第一人称视图
        大幅简化代码，由引擎自动处理投影、光照等
        """
        
        # 创建PyRender场景
        scene = pyrender.Scene(ambient_light=[0.3, 0.3, 0.3])
        
        # 机器人位置和朝向
        robot_x = robot_pos["x"]
        robot_y = robot_pos["y"]
        robot_theta = robot_pos["theta"]
        
        # 添加棋盘格地面（更容易看出移动方向）
        self._add_checkered_floor_to_scene(scene, robot_x, robot_y)
        
        # 添加场景边界墙（带条纹纹理）
        self._add_boundary_walls_to_scene(scene)
        
        # 标记目标终点位置
        self._add_goal_marker_to_scene(scene)
        
        # 添加障碍物
        for obs_id, traj in obstacle_trajs.items():
            obs_id_int = int(obs_id) if isinstance(obs_id, str) else obs_id
            
            if obs_id_int >= len(initial_obstacles):
                continue
            
            obs_info = initial_obstacles[obs_id_int]
            is_dynamic = obs_info.get('is_dynamic', False)
            
            # 获取当前位置
            if is_dynamic and step_idx < len(traj):
                obs_pos = traj[step_idx]
                obs_x = obs_pos["x"]
                obs_y = obs_pos["y"]
            else:
                center = obs_info["initial_center"]
                obs_x, obs_y = center[0], center[1]
            
            # 获取障碍物顶点
            vertices = obs_info.get("vertices", None)
            radius = obs_info.get("radius", 0.5)
            
            # 判断是墙壁还是小障碍物
            is_wall = radius > 10
            height = self.wall_height if is_wall else self.obstacle_height
            
            # 选择颜色
            if is_dynamic:
                color = [100, 180, 255, 255] if is_wall else [255, 180, 0, 255]  # 浅蓝/橙色
            else:
                color = [200, 200, 210, 255] if is_wall else [255, 120, 60, 255]  # 灰/橙红
            
            # 创建障碍物几何体
            if vertices and len(vertices) == 2 and len(vertices[0]) >= 3:
                # 多边形障碍物（挤压成3D）
                mesh = self._create_extruded_polygon_mesh(
                    vertices[0], vertices[1], height, color
                )
                if is_dynamic:
                    # 平移到当前位置
                    initial_center = obs_info["initial_center"]
                    dx = obs_x - initial_center[0]
                    dy = obs_y - initial_center[1]
                    pose = self._create_pose([dx, dy, height/2], [0, 0, 0])
                else:
                    pose = self._create_pose([0, 0, height/2], [0, 0, 0])
            else:
                # 圆柱形障碍物
                mesh = trimesh.creation.cylinder(
                    radius=radius, 
                    height=height,
                    sections=32
                )
                mesh.visual.vertex_colors = color
                pose = self._create_pose([obs_x, obs_y, height/2], [0, 0, 0])
            
            scene.add(pyrender.Mesh.from_trimesh(mesh), pose=pose)
        
        # 设置相机（第一人称视角）
        camera = pyrender.PerspectiveCamera(yfov=np.radians(self.fov))
        
        # 相机姿态：从机器人位置和朝向计算
        # PyRender使用的坐标系：+X右，+Y上，-Z前（相机看向-Z）
        # 我们的2D坐标系：+X前，+Y左，theta是朝向角
        camera_pose = self._robot_pose_to_camera_pose(robot_x, robot_y, robot_theta)
        scene.add(camera, pose=camera_pose)
        
        # 添加光源（模拟天空光和太阳光）
        # 主方向光（太阳）
        sun_light = pyrender.DirectionalLight(color=[1.0, 1.0, 0.95], intensity=3.0)
        sun_pose = self._create_pose([0, 0, 10], [np.pi/4, np.pi/4, 0])
        scene.add(sun_light, pose=sun_pose)
        
        # 辅助光（天空散射光）
        sky_light = pyrender.DirectionalLight(color=[0.7, 0.8, 1.0], intensity=1.5)
        sky_pose = self._create_pose([0, 0, 10], [-np.pi/6, 0, 0])
        scene.add(sky_light, pose=sky_pose)
        
        # 渲染场景
        color, depth = self.renderer.render(scene)
        
        # 添加天空背景（PyRender默认黑色背景，我们需要替换）
        color = self._add_sky_background(color, depth)
        
        # 添加UI信息覆盖层（使用OpenCV绘制）
        frame_with_ui = self._draw_ui_overlay(color, robot_pos, step_idx)
        
        return frame_with_ui
    
    def _create_pose(self, translation, rotation_euler):
        """
        创建4x4变换矩阵
        
        Args:
            translation: [x, y, z]
            rotation_euler: [rx, ry, rz] 欧拉角（弧度）
        """
        pose = np.eye(4)
        
        # 设置平移
        pose[:3, 3] = translation
        
        # 设置旋转（ZYX欧拉角）
        rx, ry, rz = rotation_euler
        
        # 旋转矩阵（ZYX顺序）
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(rx), -np.sin(rx)],
            [0, np.sin(rx), np.cos(rx)]
        ])
        
        Ry = np.array([
            [np.cos(ry), 0, np.sin(ry)],
            [0, 1, 0],
            [-np.sin(ry), 0, np.cos(ry)]
        ])
        
        Rz = np.array([
            [np.cos(rz), -np.sin(rz), 0],
            [np.sin(rz), np.cos(rz), 0],
            [0, 0, 1]
        ])
        
        R = Rz @ Ry @ Rx
        pose[:3, :3] = R
        
        return pose
    
    def _robot_pose_to_camera_pose(self, x, y, theta):
        """
        将机器人位姿转换为相机位姿矩阵
        
        世界坐标系：X-Y是水平面，Z是垂直向上
        机器人坐标系：+X前，+Y左，theta是朝向角（在XY平面）
        PyRender相机坐标系：+X右，+Y上，-Z前（看的方向）
        """
        pose = np.eye(4)
        
        # 相机位置（在机器人位置的垂直高度上）
        pose[0, 3] = x
        pose[1, 3] = y
        pose[2, 3] = self.camera_height
        
        # 构建相机旋转矩阵
        # 相机的 -Z（前）应该指向机器人的朝向（在XY平面上，由theta决定）
        # 相机的 +Y（上）应该指向世界的 +Z（垂直向上）
        # 相机的 +X（右）应该是前×上的叉积
        
        # 计算相机的朝向向量（在世界坐标系中）
        # 机器人theta=0时朝向+X，theta=π/2时朝向+Y
        forward_x = np.cos(theta)
        forward_y = np.sin(theta)
        
        # 相机坐标系的三个轴在世界坐标系中的表示
        # 相机看向的方向（-Z在相机坐标系）= 机器人前方（XY平面）
        cam_forward = np.array([forward_x, forward_y, 0])
        
        # 相机的上方向（+Y在相机坐标系）= 世界的+Z
        cam_up = np.array([0, 0, 1])
        
        # 相机的右方向（+X在相机坐标系）使用右手定则：right = up × (-forward)
        # 因为相机看向-Z，所以+Z方向是-forward
        # right = up × (-forward) = [0,0,1] × [-forward_x,-forward_y,0]
        # = [0*0-1*(-forward_y), 1*(-forward_x)-0*0, 0*(-forward_y)-0*(-forward_x)]
        # = [forward_y, -forward_x, 0]
        cam_right = np.array([forward_y, -forward_x, 0])
        
        # 构建旋转矩阵（列向量是各个轴）
        # 注意：OpenGL/PyRender的相机看向-Z，所以forward对应-Z方向
        pose[:3, 0] = cam_right      # 相机的+X（右）
        pose[:3, 1] = cam_up         # 相机的+Y（上）
        pose[:3, 2] = -cam_forward   # 相机的+Z（注意相机看向-Z，所以这里是-forward）
        
        return pose
    
    def _create_extruded_polygon_mesh(self, vertices_x, vertices_y, height, color):
        """
        创建挤压多边形（2D多边形挤压成3D）
        
        Args:
            vertices_x: 顶点X坐标列表
            vertices_y: 顶点Y坐标列表
            height: 挤压高度
            color: RGBA颜色
        """
        n = len(vertices_x)
        
        # 创建顶点（底部+顶部）
        vertices = []
        for i in range(n):
            vertices.append([vertices_x[i], vertices_y[i], 0])  # 底部
        for i in range(n):
            vertices.append([vertices_x[i], vertices_y[i], height])  # 顶部
        
        vertices = np.array(vertices)
        
        # 创建面（三角形）
        faces = []
        
        # 侧面
        for i in range(n):
            next_i = (i + 1) % n
            # 每个侧面2个三角形
            faces.append([i, next_i, i + n])
            faces.append([next_i, next_i + n, i + n])
        
        # 底面和顶面（三角扇形）
        for i in range(1, n - 1):
            faces.append([0, i, i + 1])  # 底面
            faces.append([n, n + i + 1, n + i])  # 顶面
        
        faces = np.array(faces)
        
        # 创建trimesh
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        mesh.visual.vertex_colors = color
        
        return mesh
    
    def _add_checkered_floor_to_scene(self, scene, robot_x, robot_y):
        """添加棋盘格地面到场景（更容易观察移动方向）"""
        tile_size = 2.0  # 每个方格的大小
        tile_height = 0.01
        render_range = 15  # 渲染范围（方格数量）
        
        # 两种颜色交替
        color_light = [180, 180, 170, 255]  # 浅灰色
        color_dark = [100, 100, 90, 255]    # 深灰色
        
        # 计算机器人所在的网格位置
        robot_grid_x = int(np.floor(robot_x / tile_size))
        robot_grid_y = int(np.floor(robot_y / tile_size))
        
        # 收集浅色和深色方块的位置，然后合并
        light_tiles = []
        dark_tiles = []
        
        for grid_x_idx in range(robot_grid_x - render_range, robot_grid_x + render_range + 1):
            for grid_y_idx in range(robot_grid_y - render_range, robot_grid_y + render_range + 1):
                # 棋盘格模式：根据坐标奇偶性选择颜色
                is_light = (grid_x_idx + grid_y_idx) % 2 == 0
                
                # 计算方格中心的世界坐标
                world_x = grid_x_idx * tile_size + tile_size / 2
                world_y = grid_y_idx * tile_size + tile_size / 2
                
                if is_light:
                    light_tiles.append((world_x, world_y))
                else:
                    dark_tiles.append((world_x, world_y))
        
        # 合并所有浅色方块为一个mesh
        if light_tiles:
            light_meshes = []
            for world_x, world_y in light_tiles:
                tile_mesh = trimesh.creation.box(extents=[tile_size, tile_size, tile_height])
                # 平移到正确位置
                tile_mesh.apply_translation([world_x, world_y, -tile_height/2])
                light_meshes.append(tile_mesh)
            
            combined_light = trimesh.util.concatenate(light_meshes)
            combined_light.visual.vertex_colors = color_light
            scene.add(pyrender.Mesh.from_trimesh(combined_light))
        
        # 合并所有深色方块为一个mesh
        if dark_tiles:
            dark_meshes = []
            for world_x, world_y in dark_tiles:
                tile_mesh = trimesh.creation.box(extents=[tile_size, tile_size, tile_height])
                # 平移到正确位置
                tile_mesh.apply_translation([world_x, world_y, -tile_height/2])
                dark_meshes.append(tile_mesh)
            
            combined_dark = trimesh.util.concatenate(dark_meshes)
            combined_dark.visual.vertex_colors = color_dark
            scene.add(pyrender.Mesh.from_trimesh(combined_dark))
    
    def _add_boundary_walls_to_scene(self, scene):
        """添加场景边界墙（带条纹纹理）"""
        # 计算场景范围
        robot_traj = self.episode_data.get("robot_trajectory", [])
        initial_obstacles = self.episode_data.get("initial_obstacles", [])
        
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
            # 如果没有数据，使用默认范围
            x_min, x_max = -10, 10
            y_min, y_max = -10, 10
        else:
            margin = 8.0  # 边界边距
            x_min, x_max = min(all_x) - margin, max(all_x) + margin
            y_min, y_max = min(all_y) - margin, max(all_y) + margin
        
        wall_thickness = 0.5
        wall_height = 3.0
        
        # 创建四面墙，每面墙用多个竖条纹方块组成
        stripe_width = 1.0  # 条纹宽度
        
        # 北墙和南墙（平行于X轴）
        for y_coord, name in [(y_max, "North"), (y_min, "South")]:
            wall_length = x_max - x_min + 2 * wall_thickness
            num_stripes = int(wall_length / stripe_width) + 1
            
            for i in range(num_stripes):
                # 交替颜色
                is_light = i % 2 == 0
                color = [200, 180, 150, 255] if is_light else [150, 130, 110, 255]
                
                # 计算当前条纹的位置
                stripe_x = x_min - wall_thickness + i * stripe_width + stripe_width / 2
                
                stripe_mesh = trimesh.creation.box(
                    extents=[stripe_width, wall_thickness, wall_height]
                )
                stripe_mesh.visual.vertex_colors = color
                scene.add(pyrender.Mesh.from_trimesh(stripe_mesh),
                         pose=self._create_pose([stripe_x, y_coord, wall_height/2], [0, 0, 0]))
        
        # 东墙和西墙（平行于Y轴）
        for x_coord, name in [(x_max, "East"), (x_min, "West")]:
            wall_length = y_max - y_min + 2 * wall_thickness
            num_stripes = int(wall_length / stripe_width) + 1
            
            for i in range(num_stripes):
                # 交替颜色
                is_light = i % 2 == 0
                color = [200, 180, 150, 255] if is_light else [150, 130, 110, 255]
                
                # 计算当前条纹的位置
                stripe_y = y_min - wall_thickness + i * stripe_width + stripe_width / 2
                
                stripe_mesh = trimesh.creation.box(
                    extents=[wall_thickness, stripe_width, wall_height]
                )
                stripe_mesh.visual.vertex_colors = color
                scene.add(pyrender.Mesh.from_trimesh(stripe_mesh),
                         pose=self._create_pose([x_coord, stripe_y, wall_height/2], [0, 0, 0]))
    
    def _add_goal_marker_to_scene(self, scene):
        """标记目标终点位置"""
        robot_traj = self.episode_data.get("robot_trajectory", [])
        
        if not robot_traj:
            return
        
        # 获取终点位置（轨迹最后一个点）
        goal_pos = robot_traj[-1]
        goal_x = goal_pos["x"]
        goal_y = goal_pos["y"]
        
        # 创建高大的目标标记（金色高塔）
        marker_height = 6.0
        tower_radius = 0.3
        
        # 塔身（金色）
        tower_mesh = trimesh.creation.cylinder(
            radius=tower_radius,
            height=marker_height,
            sections=12
        )
        tower_mesh.visual.vertex_colors = [255, 215, 0, 255]  # 金色
        scene.add(pyrender.Mesh.from_trimesh(tower_mesh),
                 pose=self._create_pose([goal_x, goal_y, marker_height/2], [0, 0, 0]))
        
        # 顶部标记（金色星形，用球体近似）
        star_mesh = trimesh.creation.icosphere(subdivisions=2, radius=0.5)
        star_mesh.visual.vertex_colors = [255, 215, 0, 255]  # 金色
        scene.add(pyrender.Mesh.from_trimesh(star_mesh),
                 pose=self._create_pose([goal_x, goal_y, marker_height + 0.5], [0, 0, 0]))
        
        # 底座（红色圆盘）
        base_mesh = trimesh.creation.cylinder(
            radius=tower_radius * 2,
            height=0.2,
            sections=16
        )
        base_mesh.visual.vertex_colors = [255, 50, 50, 255]  # 红色
        scene.add(pyrender.Mesh.from_trimesh(base_mesh),
                 pose=self._create_pose([goal_x, goal_y, 0.1], [0, 0, 0]))
    
    def _add_landmarks_to_scene(self, scene):
        """添加世界坐标系地标到场景"""
        landmark_positions = [
            (0, 0, [255, 200, 100, 255], "Origin"),
            (20, 0, [100, 200, 255, 255], "East"),
            (-20, 0, [255, 100, 200, 255], "West"),
            (0, 20, [100, 255, 100, 255], "North"),
            (0, -20, [255, 255, 100, 255], "South"),
            (20, 20, [200, 150, 255, 255], "NE"),
            (-20, 20, [150, 255, 200, 255], "NW"),
            (20, -20, [255, 180, 150, 255], "SE"),
            (-20, -20, [200, 200, 200, 255], "SW"),
        ]
        
        for world_x, world_y, color, label in landmark_positions:
            # 创建高塔地标（细长圆柱+顶部标记）
            landmark_height = 5.0
            tower_radius = 0.15
            
            # 塔身
            tower_mesh = trimesh.creation.cylinder(
                radius=tower_radius,
                height=landmark_height,
                sections=8
            )
            tower_mesh.visual.vertex_colors = color
            scene.add(pyrender.Mesh.from_trimesh(tower_mesh),
                     pose=self._create_pose([world_x, world_y, landmark_height/2], [0, 0, 0]))
            
            # 顶部标记（小球）
            marker_mesh = trimesh.creation.icosphere(subdivisions=2, radius=0.3)
            marker_mesh.visual.vertex_colors = color
            scene.add(pyrender.Mesh.from_trimesh(marker_mesh),
                     pose=self._create_pose([world_x, world_y, landmark_height + 0.3], [0, 0, 0]))
    
    def _add_sky_background(self, color_img, depth_img):
        """添加天空背景到渲染图像"""
        # 创建可写副本（PyRender 返回的数组是只读的）
        color_img = color_img.copy()
        
        # 创建天空渐变
        sky_gradient = np.zeros_like(color_img)
        
        for y in range(self.image_height):
            t = y / self.image_height
            # 从顶部深蓝到底部浅蓝
            sky_color = np.array([
                int(200 + (240 - 200) * t),  # R
                int(180 + (220 - 180) * t),  # G
                int(135 + (190 - 135) * t),  # B
            ])
            sky_gradient[y, :] = sky_color
        
        # 在没有深度的地方（背景）使用天空
        # depth为0表示没有物体
        background_mask = (depth_img == 0)
        color_img[background_mask] = sky_gradient[background_mask]
        
        return color_img
    
    def _draw_ui_overlay(self, frame, robot_pos, step_idx):
        """在渲染图像上绘制UI信息覆盖层"""
        # 确保数组是可写的
        if not frame.flags.writeable:
            frame = frame.copy()
        frame_copy = frame.copy()
        
        # 获取机器人轨迹信息
        robot_traj = self.episode_data.get('robot_trajectory', [])
        info_text = f"Frame: {step_idx + 1}/{len(robot_traj)}"
        
        pos_text = f"Pos: ({robot_pos['x']:.2f}, {robot_pos['y']:.2f})"
        theta_text = f"Theta: {np.rad2deg(robot_pos['theta']):.1f} deg"
        
        if step_idx < len(self.episode_data.get('actions', [])):
            action = self.episode_data['actions'][step_idx]
            vel_text = f"Linear: {action['linear']:.2f} m/s"
            ang_text = f"Angular: {action['angular']:.2f} rad/s"
        else:
            vel_text = "Linear: 0.00 m/s"
            ang_text = "Angular: 0.00 rad/s"
        
        # 转换为BGR用于OpenCV绘制
        frame_bgr = cv2.cvtColor(frame_copy, cv2.COLOR_RGB2BGR)
        
        # 绘制半透明背景
        overlay = frame_bgr.copy()
        cv2.rectangle(overlay, (10, 10), (300, 130), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame_bgr, 0.4, 0, frame_bgr)
        
        # 绘制边框
        cv2.rectangle(frame_bgr, (10, 10), (300, 130), (100, 150, 200), 2)
        
        # 绘制文字
        texts = [info_text, pos_text, theta_text, vel_text, ang_text]
        y_positions = [35, 55, 75, 95, 115]
        
        for text, y_pos in zip(texts, y_positions):
            cv2.putText(frame_bgr, text, (21, y_pos + 1), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
            cv2.putText(frame_bgr, text, (20, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        
        # 绘制指南针
        self._draw_compass(frame_bgr, robot_pos['theta'])
        
        # 转换回RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        
        return frame_rgb
    
    def _draw_compass(self, frame, theta):
        """绘制指南针"""
        compass_x = self.image_width - 70
        compass_y = 50
        compass_radius = 30
        
        # 背景圆
        overlay = frame.copy()
        cv2.circle(overlay, (compass_x, compass_y), compass_radius, (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.circle(frame, (compass_x, compass_y), compass_radius, (100, 150, 200), 2)
        
        # 方向箭头
        arrow_length = compass_radius - 8
        arrow_end_x = int(compass_x + arrow_length * np.cos(theta - np.pi/2))
        arrow_end_y = int(compass_y + arrow_length * np.sin(theta - np.pi/2))
        
        cv2.arrowedLine(frame, (compass_x, compass_y), (arrow_end_x, arrow_end_y),
                       (100, 255, 100), 3, tipLength=0.4)
        
        # N标记
        cv2.putText(frame, "N", (compass_x - 5, compass_y - compass_radius - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def _generate_instruction(self) -> str:
        """生成任务描述指令"""
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
        
        room_size = max(x_range, y_range) * 1.2
        
        return room_size
    
    def process(self, clean_old_files=False, save_gif=False):
        """执行完整的渲染pipeline
        
        Args:
            clean_old_files: 是否清理旧文件
            save_gif: 是否同时保存GIF动画
        """
        print(f"\n开始处理 Scene {self.scene_id:05d}, Episode {self.episode_id}")
        print("=" * 60)
        
        # 清理旧文件
        if clean_old_files and self.scene_dir.exists():
            print("\n[0/3] 清理旧文件...")
            import shutil
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
        print("\n[3/3] 渲染第一人称视频（使用PyRender）...")
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
    parser = argparse.ArgumentParser(description="使用PyRender将2D数据渲染为3D第一人称视频")
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
