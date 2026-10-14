# 0.2.4 完整安装文件

本机安装：运行 `iracing-chinese-assistant-0.2.4-setup.exe`，同名 `setup-1.bin` 必须放在同一目录。

GitHub下载：下载全部 `iracing-chinese-assistant-0.2.4-setup.zip.001`、`.zip.002` 分卷，放在同一目录，用7-Zip打开 `.001` 解压。不要分别解压每卷；解压后保持安装器与bin同目录。

安装包包含Python、CPU PyTorch、GPT-SoVITS、基础模型和默认芙宁娜／克洛琳德音色，无需云端API密钥。安装完成页默认勾选Simulator Controller引导，需联网下载官方组件；已有组件可复用。

升级前停止播报，并从托盘菜单退出界面。升级保留已有通讯按键绑定，首次安装默认无绑定。安装后重新启动，在进入驾驶会话前可以预热固定缓存。

本版本发布前通过143项后台及16项桌面测试。开场同时间戳排序、角色路由、参赛编号读法和旗号变化有自动回归；长正赛、全部真实旗号触发和另一台设备安装仍需实测。完整限制见 `CHANGELOG.md`。

下载后可按 `SHA256SUMS.txt` 检查校验码。项目与上游引用见仓库README及 `THIRD_PARTY_NOTICES.md`。
