# First-Tier Laboratory Fire Guard

基于 ROS2 + RK3588 的实验室巡检机器人系统，集成远程遥控、激光避障、自主巡检与 YOLO26 火焰/烟雾检测。

## 系统架构

```
┌────────────────────────────────────────────────────┐
│                   微信小程序 / Web                   │
│                  (远程遥控 & 监控面板)                 │
└──────────┬──────────────────────────┬──────────────┘
           │ MQTT                     │ HTTP
┌──────────▼──────────────────────────▼──────────────┐
│                    MQTT Broker                      │
│                 (localhost:1883)                    │
└──────────┬──────────────────────────┬──────────────┘
           │                          │
  ┌────────▼────────┐     ┌──────────▼──────────┐
  │  wechat_control │     │   obstacle_alert    │
  │  (MQTT→/cmd_vel)│     │ (/scan→MQTT告警)    │
  └────────┬────────┘     └─────────────────────┘
           │
  ┌────────▼──────────────────────────────────┐
  │              /cmd_vel                      │
  │  ┌─────────────┐  ┌───────────────────┐   │
  │  │lidar_avoider│  │  simple_patrol    │   │
  │  │ (避障拦截)   │  │  (自主巡检+脱困)   │   │
  │  └─────────────┘  └───────────────────┘   │
  └───────────────────────────────────────────┘
                        │
           ┌────────────▼────────────┐
           │     fire_detect.py      │
           │  YOLO26 + RKNN (NPU)    │
           │  火焰/烟雾检测 → MQTT    │
           └─────────────────────────┘
```

## 目录结构

```
开源/
├── ros2_packages/          # ROS2 Python 功能包
│   ├── control/            # MQTT 桥接控制节点 (wechat_control)
│   ├── lidar_avoider/      # 激光雷达避障节点 (lidar_avoider)
│   └── obstacle_alert/     # 障碍物 MQTT 告警节点 (obstacle_alert)
├── scripts/                # 独立运行脚本
│   ├── fire_detect.py      # 火焰/烟雾实时检测
│   ├── simple_patrol.py    # 自主巡检（含脱困逻辑）
│   └── patrol_daemon.py    # 巡检守护进程（MQTT 远程启停）
├── web/                    # Web 监控前端 (uni-app)
├── yolo26_fire/            # YOLO26 火焰检测模型
└── README.md
```

## 功能模块

### 1. ROS2 功能包 (`ros2_packages/`)

#### wechat_control — MQTT 桥接遥控
- 订阅 MQTT Topic `robot/cmd`，接收 JSON 格式的线速度/角速度指令
- 将指令转换为 `geometry_msgs/Twist` 发布到 `/cmd_vel`
- 依赖：`rclpy`, `geometry_msgs`, `paho-mqtt`

#### lidar_avoider — 激光避障
- 订阅 `/scan` (LaserScan)，监测前方 ±30° 扇形区域
- 当障碍物距离 < 0.5m 时急停（发布零速 Twist），遥控模式下起安全拦截作用
- 依赖：`rclpy`, `sensor_msgs`, `geometry_msgs`

#### obstacle_alert — 障碍物告警
- 同避障逻辑，检测到前方 0.5m 内障碍时通过 MQTT `robot/obstacle` 推送告警
- 向前端提供实时障碍物状态

### 2. 火焰检测 (`scripts/fire_detect.py`)
- 基于 YOLO26 模型，运行在 RK3588 NPU 上
- 支持 `fire` 和 `smoke` 两类检测，置信度阈值 0.85
- 检测到火情时保存最优截图，通过 MQTT `robot/alert` 推送告警（含 HTTP 截图链接）
- 告警间隔 5 秒，截图上限 10 张自动轮转

### 3. 自主巡检 (`scripts/simple_patrol.py`)
- 直线前进 + 激光雷达避障，遇障碍物自动转向绕行
- 内置脱困逻辑：连续 3 次检测到障碍 → 后退 → 交替左右转向脱困
- 启动时自动杀死 `lidar_avoider` 避障节点，结束后恢复

### 4. 巡检守护 (`scripts/patrol_daemon.py`)
- 常驻进程，通过 MQTT `robot/patrol` 接收启停指令
- `start_patrol`：停止避障节点、启动巡检
- `stop_patrol`：终止巡检、恢复避障节点

### 5. Web 前端 (`web/`)
- 基于 uni-app 构建的监控面板
- 页面标题：`first-tier-laboratory-fire-guard`
- 包含告警、控制、火情仪表盘、监控、设置等页面模块

### 6. YOLO26 推理 (`yolo26_fire/`)
- `infer_rk3588_yolo26.py`：RK3588 端侧推理脚本，支持单图输入/letterbox预处理/NPU多核选择
- `dataset.yaml`：训练数据集配置（训练集/验证集/测试集路径，1 类 fire）
- `rknn_toolkit2-2.3.2-cp38-*.whl`：RKNN Toolkit2 离线安装包（ARM64）

## 硬件依赖

| 硬件 | 用途 |
|------|------|
| RK3588 开发板 | NPU 推理（火焰检测） |
| 激光雷达 | 避障 & 障碍物检测 |
| 摄像头 | 视频流采集（火焰检测输入） |
| 轮式底盘 | 运动执行（/cmd_vel 控制） |

## 软件依赖

### ROS2 (Humble)
```bash
# 安装 ROS2 Humble，然后构建工作空间
cd ~/astra_ws
colcon build --packages-select wechat_control lidar_avoider obstacle_alert
source install/setup.bash
```

### Python 依赖
```bash
pip install paho-mqtt opencv-python numpy
# RKNN Toolkit2 (RK3588 NPU)
pip install rknn_toolkit2-2.3.2-cp38-cp38-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
```

### MQTT Broker
```bash
# 安装 Mosquitto
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
```

## 快速启动

```bash
# 1. 启动 MQTT Broker（通常已自启）
sudo systemctl start mosquitto

# 2. 启动 ROS2 节点
ros2 run wechat_control mqtt_bridge &
ros2 run lidar_avoider lidar_avoider &
ros2 run obstacle_alert obstacle_alert &

# 3. 启动火焰检测（需连接摄像头视频流）
python3 scripts/fire_detect.py &

# 4. 启动巡检守护
python3 scripts/patrol_daemon.py &

# 5. 部署 Web 前端到 Nginx 或直接打开 index.html
```

## MQTT Topic 速查

| Topic | 方向 | 说明 |
|-------|------|------|
| `robot/cmd` | 小程序 → 机器人 | 遥控指令 `{"x": 0.15, "z": 0.0}` |
| `robot/obstacle` | 机器人 → 前端 | 障碍物告警 `{"obstacle": true}` |
| `robot/alert` | 机器人 → 前端 | 火情告警 `{"type":"fire","confidence":0.92,...}` |
| `robot/patrol` | 前端 → 机器人 | 巡检启停 `{"cmd":"start_patrol"/"stop_patrol"}` |

## 许可证

AGPL License

