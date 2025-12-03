#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始位姿处理节点
功能：订阅 RViz 的 /initialpose 话题，设置机器人的初始位姿
在重定位模式下，用于设置机器人在地图中的初始位置
"""

import rospy
import tf2_ros
import tf2_geometry_msgs
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped
from nav_msgs.msg import Odometry
import math

class InitialPoseHandler:
    def __init__(self):
        rospy.init_node('initial_pose_handler', anonymous=True)
        
        # 获取参数
        self.map_frame = rospy.get_param('~map_frame', 'camera_init')
        self.base_frame = rospy.get_param('~base_frame', 'base_link')
        self.aft_mapped_frame = rospy.get_param('~aft_mapped_frame', 'aft_mapped')  # FAST-LIVO2 的位姿坐标系
        self.odom_frame = rospy.get_param('~odom_frame', 'odom')
        self.initial_pose_topic = rospy.get_param('~initial_pose_topic', '/initialpose')
        
        # 机器人物理结构参数（相机相对于 base_link 的偏移）
        # 默认值：相机在 base_link 前方 0.4m，上方 0.8m
        self.camera_offset_x = rospy.get_param('~camera_offset_x', 0.4)  # 前方（米）
        self.camera_offset_y = rospy.get_param('~camera_offset_y', 0.0)  # 左右（米）
        self.camera_offset_z = rospy.get_param('~camera_offset_z', 0.8)  # 上方（米）
        
        # base_link 距离地面的高度（默认 0.25m）
        self.base_link_height = rospy.get_param('~base_link_height', 0.25)  # 米
        
        # TF 相关
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.tf_broadcaster = tf2_ros.StaticTransformBroadcaster()  # 用于初始发布
        self.tf_dynamic_broadcaster = tf2_ros.TransformBroadcaster()  # 用于持续发布，覆盖动态 TF
        
        # 订阅初始位姿话题（RViz 2D Pose Estimate）
        self.sub_initial_pose = rospy.Subscriber(
            self.initial_pose_topic,
            PoseWithCovarianceStamped,
            self.initial_pose_callback
        )
        
        # 发布初始位姿到 odom 帧
        self.pub_initial_odom = rospy.Publisher(
            '/set_initial_pose',
            Odometry,
            queue_size=1
        )
        
        # 发布空点云用于清除原坐标系的点云
        from sensor_msgs.msg import PointCloud2
        self.pub_clear_cloud = rospy.Publisher(
            '/cloud_registered',
            PointCloud2,
            queue_size=1,
            latch=True
        )
        
        rospy.loginfo("Initial pose handler started")
        rospy.loginfo("Subscribing to: %s", self.initial_pose_topic)
        rospy.loginfo("Map frame: %s", self.map_frame)
        rospy.loginfo("Base frame: %s", self.base_frame)
        rospy.loginfo("Aft_mapped frame: %s", self.aft_mapped_frame)
        rospy.loginfo("注意：map 和 camera_init 初始时都对应 PCD 原点（对齐）")
        rospy.loginfo("     设置初始位姿后会更新 map -> camera_init 的变换")
        
        # 等待 TF 树建立
        rospy.sleep(1.0)
        
        # 存储初始位姿，用于后续重置
        self.initial_pose_set = False
        self.initial_pose = None
        self.camera_init_transform = None
        self.aft_mapped_transform = None
        self.base_link_transform = None
        self.camera_init_to_aft_mapped_transform = None
        
        # 创建定时器，持续发布 TF（防止被 FAST-LIVO2 的动态 TF 覆盖）
        # 使用更高的频率（100Hz）以确保时间戳始终最新，能够覆盖 FAST-LIVO2 的动态 TF
        self.tf_timer = rospy.Timer(rospy.Duration(0.01), self.publish_static_tf_callback)  # 100Hz
    
    def quaternion_to_euler(self, q):
        """将四元数转换为欧拉角 (roll, pitch, yaw)"""
        roll = math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x * q.x + q.y * q.y))
        pitch = math.asin(2 * (q.w * q.y - q.z * q.x))
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return roll, pitch, yaw
    
    def clear_point_clouds(self):
        """清除原坐标系的点云"""
        try:
            from sensor_msgs.msg import PointCloud2
            import sensor_msgs.point_cloud2 as pc2
            
            # 创建空点云消息
            empty_cloud = PointCloud2()
            empty_cloud.header.stamp = rospy.Time.now()
            empty_cloud.header.frame_id = "camera_init"  # 使用 camera_init 坐标系
            empty_cloud.height = 1
            empty_cloud.width = 0  # 空点云
            empty_cloud.is_dense = True
            
            # 发布空点云到相关话题，清除原坐标系的点云显示
            # 注意：这不会清除 FAST-LIVO2 内部的地图数据，只是清除显示
            rospy.loginfo("Clearing point clouds from old coordinate system...")
            
            # 发布空点云到 /cloud_registered（实时点云）
            self.pub_clear_cloud.publish(empty_cloud)
            rospy.sleep(0.1)  # 等待发布完成
            self.pub_clear_cloud.publish(empty_cloud)  # 再次发布确保清除
            
            rospy.loginfo("✓ Point clouds cleared (published empty cloud to /cloud_registered)")
            
        except Exception as e:
            rospy.logwarn("Failed to clear point clouds: %s", str(e))
    
    def publish_static_tf_callback(self, event):
        """定时器回调：持续发布 TF（防止被 FAST-LIVO2 的动态 TF 覆盖）"""
        if self.initial_pose_set:
            # 使用稍微未来的时间戳，确保优先级最高
            # 使用纳秒精度避免时间戳冲突
            import time
            now_ns = time.time_ns()
            # 为不同的 TF 使用不同的时间偏移，避免冲突
            time1 = rospy.Time(now_ns // 1000000000, (now_ns % 1000000000) + 1000000)  # +1ms
            time2 = rospy.Time(now_ns // 1000000000, (now_ns % 1000000000) + 2000000)  # +2ms
            
            # 更新时间戳并使用 TransformBroadcaster 持续发布（动态 TF，但值固定）
            # 使用未来的时间戳可以确保优先级最高，覆盖 FAST-LIVO2 发布的动态 TF
            if self.camera_init_transform is not None:
                self.camera_init_transform.header.stamp = time1
                self.tf_dynamic_broadcaster.sendTransform(self.camera_init_transform)
            
            # 关键：base_link 必须在指定高度（base_link_height），确保时间戳最新以覆盖其他 TF
            if self.base_link_transform is not None:
                # 强制确保 base_link.z = base_link_height（距离地面的高度），无论之前的值是什么
                self.base_link_transform.transform.translation.z = self.base_link_height
                self.base_link_transform.header.stamp = time1  # 使用相同时间戳，确保一致性
                self.tf_dynamic_broadcaster.sendTransform(self.base_link_transform)
                # 每10秒输出一次调试信息（避免日志过多）
                if rospy.get_time() % 10 < 0.01:
                    rospy.logdebug("发布 map -> base_link TF: z=%.3f (应该为0.0)", 
                                 self.base_link_transform.transform.translation.z)
            
            if self.aft_mapped_transform is not None:
                self.aft_mapped_transform.header.stamp = time2
                self.tf_dynamic_broadcaster.sendTransform(self.aft_mapped_transform)
            
            # 关键：持续发布 camera_init -> aft_mapped 的动态 TF（单位变换，但时间戳最新）
            # 使用未来的时间戳确保优先级最高，覆盖 FAST-LIVO2 发布的动态 TF
            # 注意：在重定位模式下，FAST-LIVO2 的 ICP 匹配会持续更新 aft_mapped，这是正常的
            # 如果希望 aft_mapped 固定，需要更频繁地发布 TF（当前 100Hz）
            if self.camera_init_to_aft_mapped_transform is not None:
                # 使用稍微不同的时间戳避免冲突，使用更未来的时间戳（+5ms）确保优先级最高
                aft_mapped_time = rospy.Time(now_ns // 1000000000, (now_ns % 1000000000) + 5000000)  # +5ms，提高优先级
                self.camera_init_to_aft_mapped_transform.header.stamp = aft_mapped_time
                self.tf_dynamic_broadcaster.sendTransform(self.camera_init_to_aft_mapped_transform)
    
    def initial_pose_callback(self, msg):
        """处理初始位姿消息"""
        rospy.loginfo("=" * 60)
        rospy.loginfo("Received initial pose from RViz (2D Pose Estimate)")
        rospy.loginfo("Message frame_id: %s", msg.header.frame_id)
        rospy.loginfo("Expected map frame: %s", self.map_frame)
        rospy.loginfo("用户选择的位姿:")
        rospy.loginfo("  Position: x=%.3f, y=%.3f, z=%.3f (注意：z 将被忽略)", 
                     msg.pose.pose.position.x,
                     msg.pose.pose.position.y,
                     msg.pose.pose.position.z)
        
        # 获取四元数
        q = msg.pose.pose.orientation
        roll, pitch, yaw = self.quaternion_to_euler(q)
        rospy.loginfo("  Orientation: roll=%.3f° (将被忽略), pitch=%.3f° (将被忽略), yaw=%.3f° (使用)", 
                     math.degrees(roll),
                     math.degrees(pitch),
                     math.degrees(yaw))
        rospy.loginfo("2D Pose Estimate: 只使用 xy 和 yaw，z、roll、pitch 保持不变")
        
        # 检查 frame_id 是否匹配
        if msg.header.frame_id != self.map_frame:
            rospy.logwarn("Warning: Message frame_id (%s) != expected map frame (%s)", 
                         msg.header.frame_id, self.map_frame)
            rospy.logwarn("Will use expected map frame: %s", self.map_frame)
        
        # 关键：设置初始位姿并重置 FAST-LIVO2 的位姿估计
        # 由于 FAST-LIVO2 内部使用 camera_init，我们需要：
        # 1. 发布 map -> camera_init 的静态 TF（根据用户选择的位姿）
        # 2. FAST-LIVO2 会从新的 camera_init 位置开始进行 ICP 匹配
        try:
            import geometry_msgs.msg
            
            # 1. 更新 map -> camera_init 的静态 TF（关键！）
            # 注意：map 坐标系的原点 = PCD 文件的原点 = 建图时 camera_init 的原点
            # 初始时，map 和 camera_init 对齐（都是 PCD 原点），通过 launch 文件中的静态 TF 实现
            # PCD 地图固定在 map 坐标系中，不会移动
            # 当用户设置初始位姿时，我们更新 map -> camera_init 的变换
            # 用户在地图上选择的点坐标直接赋值给 camera_init
            camera_init_transform = geometry_msgs.msg.TransformStamped()
            camera_init_transform.header.stamp = rospy.Time.now()
            camera_init_transform.header.frame_id = self.map_frame  # map（PCD 原点）
            camera_init_transform.child_frame_id = "camera_init"  # FAST-LIVO2 的地图坐标系（初始时也是 PCD 原点）
            
            # camera_init 的高度应该始终是 base_link_height + camera_offset_z
            # 不需要获取当前的 z 坐标，因为应该始终使用计算出的正确高度
            camera_init_z_correct = self.base_link_height + self.camera_offset_z
            
            # 2D Pose Estimate：用户选择的坐标是 base_link 的位置（在地图上）
            # 注意：map 坐标系是固定的（PCD 原点），地图固定在 map 中不会移动
            # 用户选择的坐标是相对于 map 的 base_link 位置
            # 2D Pose Estimate 只使用 X、Y 和 Yaw，Z、Roll、Pitch 应该被忽略
            user_selected_x = msg.pose.pose.position.x
            user_selected_y = msg.pose.pose.position.y
            user_selected_z_raw = msg.pose.pose.position.z  # 原始 Z 值（会被忽略）
            
            # 方向：只使用 yaw，roll 和 pitch 保持为 0
            user_q = msg.pose.pose.orientation
            _, _, user_yaw = self.quaternion_to_euler(user_q)
            
            # 创建新的四元数：roll=0, pitch=0, yaw=用户选择的 yaw
            import tf.transformations
            quat = tf.transformations.quaternion_from_euler(0.0, 0.0, user_yaw)
            
            # 1. 设置 base_link 的位置（用户选择的坐标）
            base_link_transform = geometry_msgs.msg.TransformStamped()
            base_link_transform.header.stamp = rospy.Time.now()
            base_link_transform.header.frame_id = self.map_frame  # map（固定坐标系）
            base_link_transform.child_frame_id = self.base_frame  # base_link
            
            # base_link 位置 = 用户选择的 X、Y 坐标（相对于 map）
            # Z 坐标：忽略用户选择的 Z，固定为 base_link_height（距离地面的高度）
            base_link_transform.transform.translation.x = user_selected_x
            base_link_transform.transform.translation.y = user_selected_y
            base_link_transform.transform.translation.z = self.base_link_height  # 固定高度，忽略用户选择的 Z
            base_link_transform.transform.rotation.x = quat[0]
            base_link_transform.transform.rotation.y = quat[1]
            base_link_transform.transform.rotation.z = quat[2]
            base_link_transform.transform.rotation.w = quat[3]
            
            # 2. 根据 base_link 的位置计算 camera_init 的位置
            # camera_init 位置 = base_link 位置 + (camera_offset_x, camera_offset_y, camera_offset_z)
            camera_init_z = self.base_link_height + self.camera_offset_z
            camera_init_transform.transform.translation.x = user_selected_x + self.camera_offset_x
            camera_init_transform.transform.translation.y = user_selected_y + self.camera_offset_y
            camera_init_transform.transform.translation.z = camera_init_z
            camera_init_transform.transform.rotation = base_link_transform.transform.rotation
            
            rospy.loginfo("=" * 60)
            rospy.loginfo("2D Pose Estimate: 用户选择的坐标是 base_link 的位置（相对于 map）")
            rospy.loginfo("  用户选择位置: (%.3f, %.3f, %.3f) - Z 值将被忽略", user_selected_x, user_selected_y, user_selected_z_raw)
            rospy.loginfo("  用户选择 yaw: %.3f°", math.degrees(user_yaw))
            rospy.loginfo("")
            rospy.loginfo("机器人物理结构参数:")
            rospy.loginfo("  base_link 高度: %.3f m（距离地面）", self.base_link_height)
            rospy.loginfo("  相机偏移: (%.3f, %.3f, %.3f) m（相对于 base_link）", 
                         self.camera_offset_x, self.camera_offset_y, self.camera_offset_z)
            rospy.loginfo("")
            rospy.loginfo("计算结果:")
            rospy.loginfo("  base_link 位置: (%.3f, %.3f, %.3f) - 用户选择的位置", 
                         base_link_transform.transform.translation.x,
                         base_link_transform.transform.translation.y,
                         base_link_transform.transform.translation.z)
            rospy.loginfo("  camera_init 位置: (%.3f, %.3f, %.3f) - base_link + 相机偏移", 
                         camera_init_transform.transform.translation.x,
                         camera_init_transform.transform.translation.y,
                         camera_init_transform.transform.translation.z)
            rospy.loginfo("")
            rospy.loginfo("重要：map 坐标系是固定的（PCD 原点），地图固定在 map 中不会移动")
            rospy.loginfo("     只有 base_link 和 camera_init 会移动到用户选择的位置")
            rospy.loginfo("=" * 60)
            
            # 3. 发布 map -> aft_mapped 的静态 TF（关键！）
            # aft_mapped 应该和 camera_init 对齐（都是用户选择的坐标）
            # 由于 FAST-LIVO2 会持续发布 camera_init -> aft_mapped 的动态 TF，
            # 我们需要持续发布 map -> aft_mapped 的静态 TF 来覆盖它
            # 这样 aft_mapped 就会固定在用户选择的坐标，不会移动
            aft_mapped_transform = geometry_msgs.msg.TransformStamped()
            aft_mapped_transform.header.stamp = rospy.Time.now()
            aft_mapped_transform.header.frame_id = self.map_frame  # map
            aft_mapped_transform.child_frame_id = self.aft_mapped_frame  # aft_mapped
            
            # aft_mapped 和 camera_init 应该对齐（都是用户选择的坐标）
            # 所以 aft_mapped 的位置 = camera_init 的位置
            aft_mapped_transform.transform.translation.x = camera_init_transform.transform.translation.x
            aft_mapped_transform.transform.translation.y = camera_init_transform.transform.translation.y
            aft_mapped_transform.transform.translation.z = camera_init_transform.transform.translation.z
            aft_mapped_transform.transform.rotation = camera_init_transform.transform.rotation
            
            # 4. 发布 camera_init -> aft_mapped 的静态 TF（单位变换，关键！）
            # 这样可以覆盖 FAST-LIVO2 发布的 camera_init -> aft_mapped 动态 TF
            # 由于 aft_mapped 和 camera_init 对齐，所以是单位变换
            camera_init_to_aft_mapped_transform = geometry_msgs.msg.TransformStamped()
            camera_init_to_aft_mapped_transform.header.stamp = rospy.Time.now()
            camera_init_to_aft_mapped_transform.header.frame_id = "camera_init"
            camera_init_to_aft_mapped_transform.child_frame_id = self.aft_mapped_frame  # aft_mapped
            
            # 单位变换（aft_mapped 和 camera_init 对齐）
            camera_init_to_aft_mapped_transform.transform.translation.x = 0.0
            camera_init_to_aft_mapped_transform.transform.translation.y = 0.0
            camera_init_to_aft_mapped_transform.transform.translation.z = 0.0
            camera_init_to_aft_mapped_transform.transform.rotation.x = 0.0
            camera_init_to_aft_mapped_transform.transform.rotation.y = 0.0
            camera_init_to_aft_mapped_transform.transform.rotation.z = 0.0
            camera_init_to_aft_mapped_transform.transform.rotation.w = 1.0
            
            # 保存变换，用于持续发布（防止被 FAST-LIVO2 的动态 TF 覆盖）
            self.camera_init_transform = camera_init_transform
            self.base_link_transform = base_link_transform
            self.aft_mapped_transform = aft_mapped_transform
            self.camera_init_to_aft_mapped_transform = camera_init_to_aft_mapped_transform
            
            # 立即发布一次（使用未来时间戳确保优先级）
            import time
            now_ns = time.time_ns()
            # 使用纳秒精度，避免时间戳冲突
            future_time1 = rospy.Time(now_ns // 1000000000, (now_ns % 1000000000) + 1000000)  # +1ms
            future_time2 = rospy.Time(now_ns // 1000000000, (now_ns % 1000000000) + 2000000)  # +2ms
            future_time3 = rospy.Time(now_ns // 1000000000, (now_ns % 1000000000) + 3000000)  # +3ms
            
            camera_init_transform.header.stamp = future_time1
            base_link_transform.header.stamp = future_time1
            aft_mapped_transform.header.stamp = future_time2
            camera_init_to_aft_mapped_transform.header.stamp = future_time3  # 使用不同的时间戳避免冲突
            
            # 使用 TransformBroadcaster 发布（动态 TF，优先级更高）
            self.tf_dynamic_broadcaster.sendTransform(camera_init_transform)
            self.tf_dynamic_broadcaster.sendTransform(base_link_transform)
            self.tf_dynamic_broadcaster.sendTransform(aft_mapped_transform)
            self.tf_dynamic_broadcaster.sendTransform(camera_init_to_aft_mapped_transform)  # 关键：覆盖动态 TF
            
            # 也发布静态 TF 作为备份（使用当前时间）
            current_time = rospy.Time.now()
            camera_init_transform.header.stamp = current_time
            base_link_transform.header.stamp = current_time
            aft_mapped_transform.header.stamp = current_time
            camera_init_to_aft_mapped_transform.header.stamp = current_time
            self.tf_broadcaster.sendTransform(camera_init_transform)
            self.tf_broadcaster.sendTransform(base_link_transform)
            self.tf_broadcaster.sendTransform(aft_mapped_transform)
            self.tf_broadcaster.sendTransform(camera_init_to_aft_mapped_transform)
            
            rospy.loginfo("Camera_init transform (用户选择的坐标直接赋值): translation=(%.3f, %.3f, %.3f), rotation=(%.3f, %.3f, %.3f, %.3f)",
                         camera_init_transform.transform.translation.x,
                         camera_init_transform.transform.translation.y,
                         camera_init_transform.transform.translation.z,
                         camera_init_transform.transform.rotation.x,
                         camera_init_transform.transform.rotation.y,
                         camera_init_transform.transform.rotation.z,
                         camera_init_transform.transform.rotation.w)
            
            rospy.loginfo("Published static transform: %s -> camera_init (关键：用户选择的坐标直接赋值给 camera_init)", 
                         self.map_frame)
            
            rospy.loginfo("Base_link transform (根据 camera_init - 偏移计算): translation=(%.3f, %.3f, %.3f), rotation=(%.3f, %.3f, %.3f, %.3f)",
                         base_link_transform.transform.translation.x,
                         base_link_transform.transform.translation.y,
                         base_link_transform.transform.translation.z,
                         base_link_transform.transform.rotation.x,
                         base_link_transform.transform.rotation.y,
                         base_link_transform.transform.rotation.z,
                         base_link_transform.transform.rotation.w)
            
            rospy.loginfo("Published static transform: %s -> %s (根据 camera_init 位置计算)", 
                         self.map_frame, self.base_frame)
            
            rospy.loginfo("Aft_mapped transform (与 camera_init 对齐): translation=(%.3f, %.3f, %.3f), rotation=(%.3f, %.3f, %.3f, %.3f)",
                         aft_mapped_transform.transform.translation.x,
                         aft_mapped_transform.transform.translation.y,
                         aft_mapped_transform.transform.translation.z,
                         aft_mapped_transform.transform.rotation.x,
                         aft_mapped_transform.transform.rotation.y,
                         aft_mapped_transform.transform.rotation.z,
                         aft_mapped_transform.transform.rotation.w)
            
            rospy.loginfo("Published static transform: %s -> %s (关键：aft_mapped 固定在用户选择的坐标)", 
                         self.map_frame, self.aft_mapped_frame)
            
            rospy.loginfo("Published static transform: camera_init -> %s (关键：单位变换，覆盖 FAST-LIVO2 的动态 TF)", 
                         self.aft_mapped_frame)
            
            rospy.loginfo("注意：map -> camera_init 和 map -> aft_mapped 的变换已更新")
            rospy.loginfo("     camera_init 和 aft_mapped 都移动到用户选择的位置")
            rospy.loginfo("     同时发布 camera_init -> aft_mapped 的动态 TF（单位变换，但时间戳最新）")
            rospy.loginfo("     使用 TransformBroadcaster 持续发布（50Hz），确保时间戳始终最新")
            rospy.loginfo("     这样可以覆盖 FAST-LIVO2 发布的 camera_init -> aft_mapped 动态 TF")
            rospy.loginfo("     地图仍然固定在 map 坐标系的原点（PCD 原点），不会移动")
            
            # 保存初始位姿
            self.initial_pose_set = True
            self.initial_pose = msg.pose.pose
            
            # 发布初始位姿到 odometry
            odom_msg = Odometry()
            odom_msg.header.stamp = rospy.Time.now()
            odom_msg.header.frame_id = self.map_frame
            odom_msg.child_frame_id = self.base_frame
            odom_msg.pose.pose = msg.pose.pose
            odom_msg.pose.covariance = msg.pose.covariance
            
            self.pub_initial_odom.publish(odom_msg)
            rospy.loginfo("Published initial pose to /set_initial_pose")
            
            # 清除原坐标系的点云（发布空点云到相关话题）
            self.clear_point_clouds()
            
            rospy.loginfo("=" * 60)
            rospy.loginfo("✓ Initial pose set successfully!")
            rospy.loginfo("✓ Point clouds from old coordinate system cleared")
            rospy.loginfo("You can now start moving the robot for relocalization")
            rospy.loginfo("=" * 60)
            
        except Exception as e:
            rospy.logerr("=" * 60)
            rospy.logerr("✗ Error setting initial pose: %s", str(e))
            import traceback
            rospy.logerr(traceback.format_exc())
            rospy.logerr("=" * 60)

if __name__ == '__main__':
    try:
        handler = InitialPoseHandler()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

