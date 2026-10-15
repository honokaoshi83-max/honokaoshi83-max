# 完整离线安装版

运行 `iracing-chinese-assistant-0.2.5-setup.exe`，选择安装位置，完成后从桌面快捷方式启动。安装器与同名数据 `.bin` 必须放在同一文件夹，复制到其他电脑时一并复制。

安装包包含桌面应用、独立 Python 3.10.11、CPU 版 PyTorch 2.5.1、GPT-SoVITS 推理源码与基础模型、中文发音组件、FFmpeg、克洛琳德和芙宁娜权重与参考录音。首次运行无需下载默认音色，不需要打开 GPT-SoVITS 网页界面。

工程师默认使用克洛琳德，负责车辆、油量、轮胎、维修和按键状态摘要。观察员／策略师默认使用芙宁娜，负责圈速、周围赛车、天气、旗号和策略；邻车、旗号和策略播报依赖 Simulator Controller。安装完成页默认勾选“一键安装并接入 Simulator Controller”，需要联网获取官方发布包和组件，并自动创建 iRacing 中文基础配置、接入本地语音。取消勾选会缺少邻车、旗号和策略播报；本地车辆、轮胎、油量与按键状态播报仍可使用。

一键安装从上游官方 VERSION 清单获取正式发布包及配套组件，使用 HTTPS 官方镜像，校验 ZIP 和必需程序，完整下载后再提交到当前用户的 `AppData\Local\Programs\SimulatorController`。程序仍独立放置，个人数据仍位于 Windows“文档”的 Simulator Controller 目录。已有安装直接复用，已有配置先备份，保留原有 iRacing 进站按键；不会重复覆盖程序目录。下载来源、版本和文件 SHA256 保存在组件目录的 `chinese-assistant-install.json`。后续更新由上游维护。官方安装器保留为手动备用入口。请参阅[官方安装与配置指引](https://github.com/SeriousOldMan/Simulator-Controller/wiki/Installation-%26-Configuration)。

首页的“Simulator Controller 安装引导”会检测组件、基础配置和中文语音接入状态。优先点击“一键安装并接入”，无需手动填写基础向导；安装和配置失败时可以使用下方的官方安装器、已有目录选择、Simulator Setup 和单独接入按钮。接入前关闭组件各模块。完成后启动 Simulator Controller、启动助手播报，再进游戏验证。上游初次启动时仍可能显示自身的数据共享选择等提示。

## 音色管理

在“音色管理”中分别选择两个角色的音色。保存后运行中的播报服务会重新启动。默认两套音色不可删除。

“添加音色”支持 Hugging Face 仓库或目录链接，以及本地配套 `.ckpt`、`.pth` 和参考录音。参考录音为 3～10 秒，须填写对应中文台词。当前支持 v1、v2、v2Pro 和 v2ProPlus 中文音色；其他版本尚未适配。下载固定到仓库提交版本，并检查已提供的文件大小和 SHA256。

新增音色尚不会自动替换角色。删除正在使用的自定义音色时，该角色恢复默认音色。不要在模型导入或语音合成时手动修改模型文件。

## 运行与保留数据

默认服务仅监听本机 9881 端口。另一套部署占用该端口时，先停止原部署，或修改 `config/local.json` 的 `port`。安装升级保留本地设置、自定义音色和缓存。卸载不自动清除安装器未创建的自定义音色或缓存；如需彻底删除，先备份后自行删除残留安装目录。

固定提示建议预热缓存。首次模型加载与生成新句子仍需要 CPU 计算；两角色共享一个推理引擎，串行切换模型。

## 引用与分发

应用源码引用来源见 `README.md` 和 `licenses`。默认音色来自 UnlimitedBurst/GPT-SoVITS 的克洛琳德目录以及 leletxh/Furina_GPT_SoVITS；下载地址和哈希见 `config/assets.json`，GPT-SoVITS 源码版本见 `config/upstream.json`。

源码仓库不存放模型二进制；完整安装版的发布附件包含默认模型和参考音频，各来源条款分别适用，见[第三方说明](../THIRD_PARTY.md)。

## 0.2.5 首次安装与日志

安装阶段与自动启动前补齐组件本地GUID，已有身份原样保留，无需填写iRacing Customer ID。先初始化身份与150米慢车范围，再启动组件。另一台设备实际安装仍待验证。

左侧“诊断日志”提供查看入口；运行日志在安装目录`work/race-voices`，组件安装日志在`logs/simulator-install.log`。
