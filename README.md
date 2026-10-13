# iracing中文播报助手

面向个人驾驶的中文车内播报助手，基于 Simulator Controller、pyirsdk 和 GPT-SoVITS，提供圈速、旗号、邻车、油量、轮胎及维修提醒。

默认双角色音色中，**克洛琳德负责车辆状态、油量和维修；芙宁娜负责周围赛车和策略提醒。** 两个音色共用一个本地语音引擎，基础提醒由遥测与规则触发。

## 最新进度

更新日期：2026-10-13。

- **0.2.2 播报键确认提示**：请求被接受后，立即播放本地缓存的“正在整理具体数据，即将开始播报”，随后播放状态摘要；完整安装包自带音频，重复按键不连播。

- **桌面应用 0.2.1**：首页集中显示运行状态、播报音量、角色试听、实时播报按键与固定缓存预热；精简说明和卡片布局，组件安装保留首页中部整行入口。
- **Simulator Controller 一键安装引导**：本程序一些重要功能依赖Simulator Controller组件，请务必安装。本程序内提供了一键安装功能。
- 默认双音色保护、自定义 GPT-SoVITS 音色导入／删除、方向盘按钮学习绑定已提供；完整安装版包含本地运行环境与默认模型。

[下载完整安装版 0.2.2](https://github.com/honokaoshi83-max/iracing-chinese-assistant/releases/tag/v0.2.2) · [桌面使用说明](docs/DESKTOP_APP.md) · [本次更新](docs/CHANGELOG_0.2.2.md)

- 中文赛道词典包含 **533 条赛道与布局记录**，圈速采用“本圈一分零九秒七”等自然表达。
- 邻车解除并排提示采用“左侧已无车”“右侧已无车”“两侧已无车”，开场介绍按角色分工，减少重复。
- 加入事故记录、强制与可选维修、发动机告警、维修倒计时和维修完成提示。
- 加入胎压、胎温和胎纹余量检查，明确区分冷胎压设置与进站更新的轮胎数据。
- 固定提示已补齐 **200 条缓存组合**；加入服务自动恢复、手动停止保护和端口冲突保护。
- 接入平稳、警告、鼓励三档路由。目前实际效果主要是小幅节奏调整，真实情绪仍需补充合适的参考录音。
- **PS 键改为单次状态摘要**：车辆告警、燃油、燃油进站估算及游戏已设置的进站服务；长按不重复。
- **云端 API 对话已从当前运行配置移除**，仅作为后续计划保留。
- 自动检查与本机 EXE 启动持续验证；实体按键、听感、全场景游戏触发和另一台设备安装仍需现场验收。

[项目进度与后续计划](docs/iracing-ai-engineer/PROGRESS_AND_PLAN.md)

## 功能与验证状态

| 功能 | 当前状态 |
| --- | --- |
| 双音色与纯净音量处理 | 本地接口与切换已检查；先前基础播报已获游戏测试确认，双音色游戏验收待完成 |
| 每圈报时与中文赛道识别 | 基础测试正常；部分赛道已验证，全部名称持续校对 |
| 邻车与旗号提醒 | 使用 Simulator Controller 框架；修订措辞待完整场景验收 |
| 事故、发动机与维修提醒 | 规则测试通过，新增场景待游戏验收 |
| 轮胎检查 | 胎压设置、可用实测胎压、进站更新的胎温与胎纹余量；车型字段与触发待验收 |
| 缓存与自动恢复 | 已通过本地服务退出、手动停止、端口冲突和缓存重用检查 |
| 三档播报表达 | 路由与音频检查通过；目前主要调整节奏，真实情绪和听感待验收 |
| 状态摘要 | 防连发及数据规则已检查；实体按键与游戏验收待完成 |

## 工作方式

```text
iRacing 遥测
    ├── Simulator Controller：工程师、策略师、观察员
    └── 本地遥测模块：圈速、赛道、损伤、轮胎、PS 状态摘要
                          ↓
                   播报队列与语音缓存
                          ↓
                 GPT-SoVITS 双音色串行合成
                          ↓
                   克洛琳德／芙宁娜播报
```

语音服务只监听本机地址，使用 CPU 合成。常用提示预缓存，未缓存的动态内容仍需要合成时间；完整状态摘要首次合成实测约 **22.5 秒**，延迟仍需优化。

## 播报示例

| 场景 | 示例 |
| --- | --- |
| 工程师开场 | 我是克洛琳德，负责赛车状态、油量和维修提醒。 |
| 观察员开场 | 我是芙宁娜，会帮你留意周围的赛车。 |
| 圈速 | 本圈一分零九秒七。 |
| 解除并排 | 左侧已无车。 |
| 维修完成 | 本次维修已完成。出站前留意维修区交通，回到赛道后先确认车辆状态。 |
| 轮胎损耗 | 进站更新的胎纹余量较低，请确认换胎安排。 |
| 状态摘要 | 车辆告警与维修需求、剩余燃油、预计可跑圈数、燃油进站建议和已选进站服务。 |

状态摘要不启动麦克风、不调用云端模型，也不自动修改进站选项。油耗至少取得两份有效完整圈样本后才估算续航；不足时明确说明无法估算。

## 数据边界

- 损伤提示以实际维修要求、发动机告警及维修倒计时为依据，不推测车身部位或损伤百分比。
- 胎温与磨损依赖进站更新。缺少实测胎压字段时仅检查冷胎压设置，不能实时判断漏气。
- 初始胎纹余量提醒线为 70%／40%，可调整；胎压与胎温范围是检查阈值，不是各车型官方最优值。
- 燃油进站建议与游戏已选进站服务分别报告；当前不求解交通、天气、轮胎和换手的综合最优策略。
- 自动测试不能代替实体按键、完整比赛与听感验收。

## 安装与运行

推荐下载 **[v0.2.2 完整桌面安装版](https://github.com/honokaoshi83-max/iracing-chinese-assistant/releases/tag/v0.2.2)**。下载 `.7z.001` 和 `.7z.002` 两个分卷，放在同一文件夹，用 [7-Zip](https://www.7-zip.org/download.html) 打开 `.001` 解压，再运行其中的 **iracing-chinese-assistant-0.2.2-setup.exe**。不要逐卷分别解压，解压后的 `.exe` 与 `.bin` 保持同目录。分卷校验文件和中文安装说明均在发行页面。

[下载安装包](https://github.com/honokaoshi83-max/iracing-chinese-assistant/releases/latest) · [完整安装说明](docs/INSTALL.md) · [验证记录](docs/PORTABLE_VALIDATION.md)

完整桌面安装版包含 Python、CPU PyTorch、GPT-SoVITS、基础模型与默认芙宁娜和克洛琳德音色，不需要另开语音网页。安装完成页默认勾选 Simulator Controller 一键安装并接入；需要联网获取官方组件，已有配置先备份。也可从应用首页打开安装引导。

桌面版提供音量设置、实时播报按键绑定、音色管理、缓存预热和诊断日志。已修复测试声音只响提示音的问题，两套中文试听获用户确认；其他设备的实体按键与游戏内联动仍需现场验收。当前不需要云端 API 密钥，首次未缓存的角色语音仍需要本地合成。

较早的源码移植版仍可从 [v0.1.0](https://github.com/honokaoshi83-max/iracing-chinese-assistant/releases/tag/v0.1.0) 下载，使用 `安装.cmd` 和 `启动.cmd`，默认采用 Windows 中文系统语音。

开发验证：安装后执行 `.runtime/python/python.exe -m pip install -r requirements-test.txt`，再执行 `.runtime/python/python.exe -X utf8 -m unittest discover -s work/race-voices -p 'test_*.py'`。

## 详细说明与计划

- [项目进度与计划](docs/iracing-ai-engineer/PROGRESS_AND_PLAN.md)
- [PS 状态提示](docs/iracing-ai-engineer/PS_STATUS.md)
- [轮胎检测](docs/iracing-ai-engineer/TIRES.md)
- [播报节奏与情绪配置](docs/iracing-ai-engineer/EMOTIONS.md)
- [缓存与自动恢复](docs/iracing-ai-engineer/RECOVERY.md)
- [API 对话后续计划](docs/iracing-ai-engineer/API_PLAN.md)

优先完成新增功能的游戏验收与动态摘要延迟优化，再验证耐力赛燃油估算、多组别交通和长时间稳定性。云端对话保留为可选后续项目，不复用 PS 状态键。

## 引用与参考

| 项目 | 使用或参考内容 |
| --- | --- |
| [Simulator Controller](https://github.com/SeriousOldMan/Simulator-Controller) | 赛事助手框架、配置系统、工程师与策略提醒 |
| [赛事工程师文档](https://github.com/SeriousOldMan/Simulator-Controller/wiki/AI-Race-Engineer) | 工程师能力与数据限制 |
| [pyirsdk](https://github.com/kutu/pyirsdk) | 遥测读取、告警、维修与进站字段 |
| [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | 本地角色音色合成 |
| [芙宁娜音色模型](https://www.modelscope.cn/models/leletxh/Furina_GPT_SoVITS) | 芙宁娜音色来源 |
| [角色音色模型集合](https://huggingface.co/UnlimitedBurst/GPT-SoVITS) | 克洛琳德及备用甘雨音色来源；当前启用克洛琳德与芙宁娜 |
| [DeepSeek API 文档](https://api-docs.deepseek.com/) | 仅用于后续对话规划，当前未启用 |

定制内容包括中文赛道与表达校对、圈速口语化、角色介绍、事故与维修规则、轮胎检查、状态按键、语音桥接、缓存和服务恢复。上游作者权利及许可证保持独立，不默认获得模型或角色音频的再分发授权。

GitHub 源码不包含密钥、私人配置、运行日志、参考录音或模型文件。完整安装版的发布附件包含默认模型与参考录音，来源见上表，各来源许可与使用条件分别适用。
