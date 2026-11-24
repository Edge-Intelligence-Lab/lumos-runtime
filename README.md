# Lumos Runtime

面向 Lumos Touch R1 从臂、StarArm102 主臂与 RDK X5 的运行时工程。X5 负责现场硬件连接、遥操作和数据采集。GPU 工作站用于训练和提供推理服务。

当前版本提供可安装的 Python 包、只读接口探测、工作站仿真和首机联调文档。遥操作、校准、采集和推理的现场验收依赖现有合作方工程和实机。

## 快速开始

X5 部署基线为 RDK OS Server（Ubuntu 22.04、aarch64、Python 3.10）。在 X5 上执行：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
lumos-runtime inspect
```

`inspect` 输出 JSON，列出系统架构、Python 版本、视频节点、串口和 SocketCAN 接口。它只枚举系统节点。设备出现后，仍需用现场工程检查视频流和双臂反馈。

## 工作站仿真

MuJoCo 4.0.1 提供带详细外观的 LumosTouch V3 工作台、Studio 网页查看和腕部 RGB 渲染。
使用独立 Python 3.12 环境，按 [仿真与相机说明](docs/simulation.md) 安装。

## 文档

- [架构与模块边界](docs/architecture.md)
- [RDK X5 首机联调与验收](docs/bring-up.md)
- [贡献与本地检查](CONTRIBUTING.md)

项目组织参考实验室的 [OpenArm Runtime](https://github.com/Edge-Intelligence-Lab/openarm-runtime)。
