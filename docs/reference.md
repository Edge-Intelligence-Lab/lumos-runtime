# 命令与 Python API

| 命令 | 用途 | 结果 |
| --- | --- | --- |
| `inspect` | 查 Linux 主机可见的设备节点 | 主机架构、Python 版本、串口、视频设备和 SocketCAN 接口的 JSON |
| `plan-startup-alignment` | 从机械臂参考姿态反算遥操作臂目标 | 六轴当前角、目标角、角度差和校准范围判断的 JSON |
| `sim-assets` | 准备工作站仿真资产 | 下载网格并校验 SHA-256 |
| `simulate` | 加载 MuJoCo 工作台 | 仿真步进、Studio 网页或腕部图像 |
| `calibrate-wrist` | 用配对图像和关节反馈求腕部相机标定 | 新的标定候选 JSON，详见 [仿真指南](simulation.md) |

每个命令的选项可通过 `lumos-runtime <命令> --help` 查看。设备枚举只说明操作系统看到了哪些节点。总线连通性、电机反馈和摄像头帧率按 [首机联调指南](bring-up.md) 验收。

## 调用对齐预览

```python
import json
from pathlib import Path

from lumos_runtime.startup_alignment import plan_startup_alignment

calibration = json.loads(
    Path("examples/startup-calibration.example.json").read_text(encoding="utf-8")
)
for joint in plan_startup_alignment(calibration, [2, 0, 0, 0, 0, -4]):
    print(joint.operator_servo_id, joint.operator_delta_deg, joint.within_calibrated_range)
```

示例使用合成角度。传给 `operator_deg_by_id` 的六个读数按舵机 ID 0–5 排列，单位是度。可选的 `mechanical_rad` 按机械臂 J1–J6 排列，单位是弧度，省略时采用已保存的机械臂参考姿态。输出列表按机械臂关节顺序排列，每项都带对应的遥操作臂舵机 ID。`within_calibrated_range` 只判断反算目标是否在输入标定区间内。

## 调用其他模块

- `lumos_runtime.inspection.inspect_host()` 枚举主机上的设备节点。测试可以传入独立的 `dev_root` 和 `network_root`。
- `lumos_runtime.simulation.load_workbench()` 返回 MuJoCo 模型及状态，支持外部网格目录和腕部相机标定。见 [仿真指南](simulation.md)。
