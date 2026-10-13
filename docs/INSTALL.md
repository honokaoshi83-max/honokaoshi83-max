# 在另一台电脑上安装

支持 Windows 10 / 11 的 x64 设备。需要联网下载依赖，安装目录须可写。无需提前安装 Python，也无需配置云端 API。

## 三步开始

1. 从[发行页面](https://github.com/honokaoshi83-max/iracing-chinese-assistant/releases/latest)下载 `windows-x64.zip` 安装包，完整解压到一个独立目录，例如 `D:\iRacing助手`，不要放在 Program Files 中。
2. 双击 **安装.cmd**，等待显示“安装完成”。它只在本目录的 `.runtime` 内安装 Python 和依赖，创建桌面快捷方式，不修改系统 Python。
3. 双击 **启动.cmd** 或桌面“iracing中文播报助手”，先点击“启动”和“测试中文声音”。进入 iRacing 后，本地遥测模块会等待连接并触发圈速、车辆、燃油、轮胎等提醒。

默认使用 **Windows 中文系统语音**。它保留两个角色的分工，但不模仿芙宁娜或克洛琳德。若提示没有中文声音，请在 Windows 的语言设置中安装中文语音组件，再运行安装。

## 接入邻车与赛事提醒

桌面应用首页提供“Simulator Controller 安装引导”。推荐点击“一键安装并接入”：从官方发布清单下载完整便携组件，自动生成 iRacing 中文基础配置并接入语音。已有安装直接复用，配置自动备份；接入前关闭 Simulator Controller 各模块。手动安装、选择已有目录与基础配置向导保留为备用入口。

邻车、旗号和框架策略提醒依赖 [Simulator Controller](https://github.com/SeriousOldMan/Simulator-Controller)。桌面安装器完成页默认勾选一键安装组件；取消勾选后，邻车、旗号和策略播报不可用。若使用没有桌面界面的便携包，请按[官方安装说明](https://github.com/SeriousOldMan/Simulator-Controller/wiki/Installation-%26-Configuration)单独安装。Simulator Controller 使用独立程序目录与 Windows“文档”配置目录，不合并进本应用安装目录。

1. 在官方页面下载并运行自动安装器，或按官方说明安装便携版。默认程序目录为 `C:\Program Files\Simulator Controller`。
2. 运行 Simulator Setup，选择 iRacing 和简体中文，启用赛事工程师、赛事策略师、赛事观察员，保存基础配置。暂不需要赛车教练员。
3. 关闭 Simulator Controller 各模块，在本项目管理界面点击“接入 Simulator Controller”。程序备份原配置和三份语法文件，然后接入本地语音接口，关闭旧的麦克风/云端对话配置。
4. 重新启动 Simulator Controller，再进入游戏验证。确认外部邻车提示正常后，可关闭游戏自带语音，避免双重播报。

配置默认位于 Windows 的“文档”目录，支持文档目录被 OneDrive 重定向。非默认安装路径可以在 `config/local.json` 设置 `simulator_controller` 和 `documents`；字段说明见 `config/default.json`。不要把个人配置提交到仓库。

## 可选：角色音色

双击 **安装角色音色.cmd**，或在管理界面点击角色音色安装。将下载 CPU 版 PyTorch、GPT-SoVITS 和两组模型/参考音频，逐个校验文件大小与 SHA256。下载来源和固定版本见 `config/assets.json`、`config/upstream.json`。

首次安装需要数 GB 的下载和磁盘空间，建议预留 **10 GB 磁盘、6 GB 可用内存**。合成负载会与游戏竞争 CPU；两个角色共用一个引擎，按需切换，不同时启动两个模型服务。较长的首次状态播报可能等待二十多秒，缓存命中会更快。管理界面可预热固定提示缓存，也可切回系统声音。

角色模型是可选第三方资源，未打入仓库或安装包。使用时遵守发布者条款；模型页面的许可不能替代角色和录音本身的权利。参考与许可见 [第三方说明](../THIRD_PARTY.md)。

## 方向盘状态按键

管理界面先检测控制器，再设置设备编号和按键编号。默认设备 1、按键 25 是原设备的 PS 按键，**其他方向盘不保证相同**。

单次按下播报车辆告警、油量、可用的进站估算及已设置的进站服务。长按不重复，冷却期间不重复排队。当前不接入语音对话。按键不是在这里绑定的游戏功能，若游戏也使用同一按键，需自行调整以避免冲突。

## 日常使用与故障处理

- “诊断”检查中文系统声音、FFmpeg、可选模型、Simulator Controller 配置。
- “停止”或根目录的 `停止.cmd` 只停止本安装目录的服务。服务默认端口 9881；已有其他服务占用时不会强行结束它。修改端口后重新接入 Simulator Controller。
- 日志位于 `work/race-voices` 和 `.runtime`，个人配置位于 `config/local.json`，均被 Git 忽略。
- GPT 依赖加载出现 DLL 错误时，检查 [Microsoft Visual C++ x64 运行库](https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist)。安装失败可重新执行安装，已通过校验的资源会重用。
- 移动整个目录后重新执行安装以更新快捷方式。若已接入 Simulator Controller，再重新接入一次。
- 更新时先停止，解压到新目录再安装，保留旧目录便于回退。不要把不同版本的 Python 环境互相覆盖。
- 卸载：先停止服务，手动恢复接入前的 Simulator Controller 配置备份（文件旁有时间戳），再删除本项目目录和桌面快捷方式。不会要求删除游戏或 Simulator Controller 的其他资料。

## 数据与验证边界

轮胎温度和磨损往往是进站更新值，不是每辆车都能提供实时胎压；未知数据不会伪装为实时读数。规则阈值可调，不等于官方最佳胎压。燃油计划需要足够完整圈样本，不能代替人工制定耐力赛计划。

此版做了独立中文目录、全新内置 Python 的安装和音频接口验证。另一台电脑上的实体方向盘、扬声器、Simulator Controller 联动及游戏内触发仍须按上面的步骤现场验证。
