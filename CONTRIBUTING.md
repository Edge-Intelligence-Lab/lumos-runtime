# 贡献

X5 的部署基线是 Python 3.10。工作站仿真使用独立的 Python 3.12 环境。修改核心包时，在仓库根目录运行：

```bash
python -m pip install -e .
lumos-runtime --help
lumos-runtime inspect
lumos-runtime plan-startup-alignment examples/startup-calibration.example.json --operator-deg 2 0 0 0 0 -4
python -m unittest discover -s tests -v
```

核心变更请分别在 Python 3.10 和 3.12 上运行同一批离线检查。仿真和腕部标定测试依赖可选包、模型资产或图形后端，请按 [仿真说明](docs/simulation.md) 准备环境，再运行测试。

修改命令或配置字段时同步更新 [命令与 Python API](docs/reference.md) 和示例。报告中注明测试环境，实机记录附上验证的设备和接口。机器专用校准、采集数据和凭据保存在仓库之外。
