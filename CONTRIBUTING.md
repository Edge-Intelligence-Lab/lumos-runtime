# 贡献

X5 上以 Python 3.10 为部署基线。可在开发机运行以下命令核对安装和只读 CLI：

```bash
python -m pip install -e .
lumos-runtime --help
lumos-runtime inspect
python -m compileall -q src
```

如改变设备发现、命令或配置入口，一起更新 README 和首机联调指南。检查结果应说明用了离线环境还是实机，实机记录注明验证的设备与接口。机器专用校准、采集数据和带凭据的配置保存在仓库之外。
