# Lumos Runtime

面向 Lumos Touch R1 机械臂、StarArm102 遥操作臂与 RDK X5 的 Python 工具。用它检查 X5 设备接口、预览启动对齐，或在工作站运行 MuJoCo 仿真。

| 使用场景 | 入口 | 要求 |
| --- | --- | --- |
| 检查 X5 的串口、CAN 和视频节点 | `lumos-runtime inspect` | Python 3.10，设备从 Linux 系统节点枚举 |
| 计算遥操作臂的起始目标 | `lumos-runtime plan-startup-alignment` | 核心包，输入校准文件和六轴读数 |
| 仿真、腕部 RGB 预览和标定 | `lumos-runtime simulate`、`calibrate-wrist` | 工作站 Python 3.12，按仿真指南安装可选依赖 |
| 真机遥操作和数采 | [X5 首机联调指南](docs/bring-up.md) | 已部署的现场工程和设备 |

## 核心安装

从仓库根目录安装。X5 的部署基线是 RDK OS Server（Ubuntu 22.04、aarch64、Python 3.10）。

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
lumos-runtime inspect
```

`inspect` 输出 JSON，列出系统架构、Python 版本、视频节点、串口和 SocketCAN 接口。它只枚举系统节点。设备出现后，仍需用现场工程检查视频流和双臂反馈。

## 离线对齐预览

可直接用示例校准文件运行。预览读取文件和角度参数，不连接设备。

```bash
lumos-runtime plan-startup-alignment examples/startup-calibration.example.json --operator-deg 2 0 0 0 0 -4
```

## 工作站仿真

用独立 Python 3.12 环境安装可选依赖。MuJoCo 工作台支持 Studio 网页查看和腕部 RGB 渲染。

```bash
python -m pip install '.[simulation]'
lumos-runtime sim-assets
lumos-runtime simulate --steps 100
```

## 文档

- [架构与模块边界](docs/architecture.md)
- [命令与 Python API](docs/reference.md)
- [仿真、网格下载和相机标定](docs/simulation.md)
- [RDK X5 首机联调与验收](docs/bring-up.md)
- [2026-11-24 双臂联调记录](docs/teleoperation-2026-11-24.md)
- [贡献与本地检查](CONTRIBUTING.md)
- [变更记录](CHANGELOG.md)

项目组织参考实验室的 [OpenArm Runtime](https://github.com/Edge-Intelligence-Lab/openarm-runtime)。
