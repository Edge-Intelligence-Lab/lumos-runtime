# LumosTouch V3 仿真

在独立工作站环境用 Python 3.12 安装。仿真依赖固定为 MuJoCo 4.0.1。

```sh
python3.12 -m pip install -e '.[simulation]'
lumos-runtime sim-assets
lumos-runtime simulate --steps 1000
lumos-runtime simulate --web
MUJOCO_GL=egl lumos-runtime simulate --wrist-image wrist.png
```

`sim-assets` 从华馨京官网获取 9 个 STL 并校验 SHA-256。默认目录是
`${XDG_CACHE_HOME:-$HOME/.cache}/lumos-runtime/touch-v3/meshes`。
可以用两个命令的 `--assets-dir` 指定同一个目录，或把验证过的目录复制到离线机器。
包内携带 MJCF 和资产来源清单。原始 STL 从供应方发布地址获取，仓库无需保存 22 MB 网格。

`simulate --web` 启动官方 Studio WebViewer，浏览器访问 `http://localhost:8080`。
该服务默认监听所有网卡，没有认证。请在可信网络运行。远程工作站可通过 SSH
端口转发，用本机 `localhost` 打开。窗内可选择腕部相机 `wrist`。

Python 可调用 `lumos_runtime.simulation.load_workbench()`，得到已初始化的
`MjModel` 和 `MjData`。工位包含机器人、平面和灯光。机器人 MJCF
`touch_v3.xml` 可作为自定义场景的 include，配套 STL 放在编译器的 meshdir。
控制输入按 J1～J6 的关节目标（rad）以及夹爪两指总开口（m）排列。
X5 数据中的夹爪是归一化位置，接数据前需按实机型号核对其与开口的映射。

## 模型来源和验证范围

- [华馨京 LumosTouch V3 预览](https://fashionstar.com.cn/wiki/software/robot-arm/data/102-web-controller/Browser_SDK/urdf-preview.html)
  提供视觉 STL、六轴运动学、惯量及对称平移夹爪。模型使用其 J2 下限 −0.209 rad，指尖总行程 85 mm。
- X5 交付包内 `FastTouchV2.SLDASM.urdf` 的六轴轴向、关节原点与 V3 一致，J2 下限是 −0.366 rad。
  SDK 配置选用的 TypeLJ 夹爪为 80 mm，工具偏移注释为 173.34 mm。
  V3 预览的工具偏移为 155.84 mm。用真机轨迹前需要确认实装夹爪、TCP 和设备限位。
- 模型使用独立的碰撞几何。臂部胶囊参考交付包 `robot_kinematics.yaml`，
  底座、夹爪基座和指尖盒体是近似。关节控制器和接触参数用于仿真预览，实机动力学与抓取接触仍待验证。

## 腕部相机

交付包的 X5 记录把腕部设备识别为 `USB Camera`，现场采集模式是
640×480 RGB、30 FPS，并写入 LeRobot 的 `observation.images.front`。
Gemini 335L 和 RealSense D435i 是可选的全局视角。

鹿明官网列出可安装到 Touch R1 的
[FastUMI Pro 板载相机模组](https://www.lumosbot.tech/products/fastumi-pro/)，
官方 [FastUMI_Camera](https://github.com/lumos-open/FastUMI_Camera) 给出了
xvsdk 和 SEUCM 标定工具。这两处公开资料未找到模组和支架的 CAD。
现场工程没有记录腕部 VID:PID、镜头型号或支架版本，尚未确认所用配件。

华馨京的另一条线索是 **HQ-1080KDT-01**。供应方将其列为 Star Arm 102-FL 的
选配第一视角相机，给出了 32×32×18 mm 的模组尺寸，以及含相机、卡扣式底座和盖板的
[总成 STEP](https://github.com/servodevelop/Star-Arm-102/blob/70f0de6046b4418c3ecf87a409559fa6062ee80e/hardware/camera-module/step/assembly/camera-module.STEP)。
[工程图](https://github.com/servodevelop/Star-Arm-102/blob/70f0de6046b4418c3ecf87a409559fa6062ee80e/hardware/camera-module/drawings/camera-module1.pdf)
显示总成面宽 38 mm，细长安装片末端有两个 Ø2.8 mm 孔。可用实物侧照和安装面核对。
[选配相机 BOM](https://github.com/servodevelop/Star-Arm-102/blob/70f0de6046b4418c3ecf87a409559fa6062ee80e/hardware/102-fl/README.zh.md#camera-module-bom)

默认 `wrist` 相机固定于 J6 后的 `gripper_base`，使用暂定外参和 58° 垂直视场，
用于检查图像接口。拿到实机标定后，向 `simulate --wrist-calibration wrist.json`
或 `load_workbench(wrist_calibration=Path("wrist.json"))` 传入配置。格式如下，
数值仅为格式示例。

```json
{
  "resolution": [640, 480],
  "intrinsics": [520.0, 520.0, 320.0, 240.0],
  "position_m": [0.07, 0.0, 0.075],
  "quaternion_wxyz": [0.5, -0.5, 0.5, -0.5]
}
```

`intrinsics` 按 `[fx, fy, cx, cy]` 排列，单位是像素，原点是图像左上角。
位置和四元数一起表达 **OpenCV 光学坐标系在 gripper_base 中的位姿**
（光学坐标 X 向右、Y 向下、Z 向前，四元数 WXYZ）。渲染使用标定对应的分辨率。
内参与实机图像应来自同一去畸变、裁剪和缩放流程。如果实机用原始鱼眼画面，
需先确定鱼眼模型和匹配的重投影流程。

在 X5 上可用以下只读命令确认设备身份和采集模式。路径须选实际的腕部 RGB 节点。

```sh
v4l2-ctl --list-devices
udevadm info --query=property --name=/dev/video0
v4l2-ctl --device=/dev/video0 --list-formats-ext
lsusb
```

随后按实际训练分辨率采集 ChArUco 或棋盘格图像，求内参与畸变，
再用同步的从臂位姿和标定板图像做 eye-in-hand 标定。若能拿到配套支架 STEP，
可用它初始化外参并补上外壳和支架的遮挡，最后用同一姿态下的像素重投影和实拍对照验收。

### 复用 OpenArm 标定板

使用 OpenArm 头部标定同款的带索引 ChArUco 板。共有 6×4 格，格长
22.5 mm，标签边长 16.5 mm，字典 `DICT_4X4_50`。开始前量实际印刷尺寸。
把板固定在桌面，图案朝上，整个手眼采样期间保持板和机器人底座的位置固定。
确认相机装在会随 J6 转动的 `gripper_base` 上。

使用同一相机模式，采集 16 张拟合图像和 4 张预先指定的验证图像。每个姿态停稳后，
保存原始图像和同一时间段的六轴真实反馈。覆盖两个方向的倾斜、远近和画面四周。
选择仍能看到足够角点的姿态，保持焦距、分辨率和安装位置一致。
关节反馈用 rad，时间戳用同一时钟的秒。输入要求图像采集和关节反馈时间差不超过
50 ms。采集工具必须保留实际配对的时间依据，LeRobot 的重采样时间轴不能用作
传感器采集时间。X5 工具的 `camera_read_end_ns` 是主机读帧结束时间，
采用它之前需要核实帧获取延迟，并确认反馈在整个采集窗口内保持稳定。

把原始图像和样本清单保存到同一个会话目录。以下 JSON 只展示一个样本的字段，
实跑时填入所有照片、成对反馈和采集时间。

```json
{
  "board": {
    "type": "charuco",
    "squares_x": 6,
    "squares_y": 4,
    "square_size_m": 0.0225,
    "marker_size_m": 0.0165,
    "dictionary": "DICT_4X4_50"
  },
  "joint_state_source": "measured_feedback",
  "samples": [
    {
      "image": "frame-01.png",
      "role": "fit",
      "joints_rad": [0.20, 0.72, -1.10, 0.40, 0.20, 0.10],
      "image_captured_at_s": 10.015,
      "robot_received_at_s": 10.022
    }
  ]
}
```

在工作站上用相邻的 OpenArm Runtime 源码安装它的 calibration extra，复用其中的
ChArUco 内参及手眼求解器。已验证 OpenArm Runtime 0.10.1。
此命令读取图像和反馈，记录每张原始图像的摘要，并生成新的候选文件。

```sh
uv run --no-project --python 3.12 --with-editable '.[simulation]' \
  --with-editable '../openarm-runtime[calibration]' \
  lumos-runtime calibrate-wrist session.json wrist.json
```

结果包含原始畸变、内参重投影误差，以及留出图像变换回基座后相对拟合板位姿的
偏差。留出位置 RMS 超过 5 mm 或旋转 RMS 超过 0.03 rad 时拒绝输出。
内参部分沿用针孔加五参数畸变模型，导出的内参对应**保持同一 K 和分辨率、去畸变且不裁剪**的图像。
用 `simulate --wrist-calibration wrist.json --wrist-image wrist.png` 可检查仿真视角。
实际使用前还需对照真机图像和实装坐标系独立验收。
