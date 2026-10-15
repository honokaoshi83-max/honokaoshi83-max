# 0.2.5 完整安装文件

本机安装：运行`iracing-chinese-assistant-0.2.5-setup.exe`，配套`iracing-chinese-assistant-0.2.5-setup-1.bin`必须放在同一目录。

GitHub下载：下载全部`iracing-chinese-assistant-0.2.5-setup.zip.001`、`.zip.002`分卷，放在同一目录，用7-Zip打开`.001`解压。不要分别解压每一卷。

安装包包含Python、CPU PyTorch、GPT-SoVITS、基础模型和默认芙宁娜／克洛琳德音色，无需云端API密钥。安装结束默认勾选Simulator Controller一键安装引导，需联网下载官方组件；已有组件可复用。

本版修复首次安装缺少组件ID导致自动启动卡住的问题，自动建立本地身份，无需填写iRacing Customer ID。已有身份、个人配置和播报按键保留，首次安装默认无按键绑定。上游首次启动可能显示数据共享等自身提示。

升级前停止播报并从托盘退出界面。安装后启动播报，在首页绑定实时播报按键；进入驾驶会话前可预热固定缓存。

157项后台和16项桌面测试通过。首次安装到组件启动有组合回归；另一台设备实际安装、实体按键、真实语音听感和游戏触发仍需验收。完整变化及限制见`CHANGELOG.md`。

日志入口：左侧“诊断日志”；完整运行日志位于安装目录`work/race-voices`，组件安装日志位于`logs/simulator-install.log`。

下载后可按`SHA256SUMS.txt`核对文件；引用来源见仓库README和`THIRD_PARTY_NOTICES.md`。
