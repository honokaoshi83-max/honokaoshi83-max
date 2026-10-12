# iRacing AI Race Engineer

一个基于 Simulator Controller、pyirsdk、GPT-SoVITS 与 DeepSeek API 的中文车内赛事工程师，使用芙宁娜音色。

A Chinese-speaking in-car race assistant for iRacing, built with Simulator Controller, pyirsdk, GPT-SoVITS, and DeepSeek API integration, with a Furina voice.

## 最新更新 | Latest Updates — 2026-10-12

- 圈速采用“本圈一分零九秒七”等自然表达，赛道中文词典包含 533 条赛道与布局记录。 / Natural Chinese lap-time announcements and 533 track/layout entries.
- 开场只介绍一次“芙宁娜”，其他助手只报告监控就绪。 / One named introduction with short readiness messages.
- Clear 提示改为“左侧已无车”“右侧已无车”“两侧已无车”。 / Clear messages use natural, side-specific Chinese wording.
- 新增事故记录、维修需求、发动机告警、维修倒计时和维修完成提示。 / Added incident, repair, engine warning, timer, and completion messages.
- 37 项自动检查通过；基础语音和圈速已完成游戏测试，最新事故、维修与开场修改仍待游戏验收。 / 37 automated checks pass; recent incident, repair, and greeting changes still need in-game validation.

详细记录 / Details: [项目进度与后续计划](docs/iracing-ai-engineer/PROGRESS_AND_PLAN.md)

## 项目简介 | Overview

面向个人驾驶场景，在比赛中提供中文圈速、交通、旗号、油量和进站相关提醒。Simulator Controller 提供赛事助手框架，Python 遥测模块补充圈速、赛道识别与维修事件，GPT-SoVITS 在本机生成芙宁娜语音。

基础提醒根据遥测与规则触发。DeepSeek 用于云端对话与策略解释，目前对话和云端增强暂时关闭，优先完善基础自动播报与长时间运行稳定性。

Simulator Controller supplies the assistant framework, Python adds telemetry-based announcements, and GPT-SoVITS generates speech locally. DeepSeek dialogue and cloud enhancements are currently paused while basic announcements and endurance reliability are improved.

## 主要能力 | Features

| 能力 / Feature | 当前状态 / Status |
| --- | --- |
| 芙宁娜纯净音色、响度处理与短句缓存 / Clean Furina voice and phrase caching | 已部署，基础游戏测试正常 / Deployed and tested in-game |
| 每圈报时与中文赛道识别 / Lap times and Chinese track names | 已运行，部分赛道已验证 / Working; selected tracks verified |
| 并排赛车与旗号提醒 / Spotting and flags | 框架已使用，最新 clear 措辞待验收 / Framework in use; revised clear wording pending validation |
| 开场名字去重 / Single named introduction | 本地检查通过 / Locally tested |
| 事故、维修需求与发动机告警 / Incident, repair, and engine alerts | 本地规则检查通过，待游戏验收 / Rule tests pass; in-game validation pending |
| 维修倒计时与维修完成 / Repair timer and completion | 本地检查通过，待游戏验收 / Locally tested; in-game validation pending |
| 油量与进站策略 / Fuel and pit strategy | 已配置，完整比赛验收待完成 / Configured; full-race validation pending |
| DeepSeek 云端对话 / Cloud dialogue | 接入已配置，当前暂停 / Configured; currently paused |

## 技术架构 | Architecture

```text
iRacing SDK telemetry
          │
          ├── Simulator Controller
          │      ├── Race Engineer
          │      ├── Race Strategist
          │      └── Race Spotter
          │
          └── Python telemetry monitor
                 ├── Lap times and Chinese track names
                 └── Incident and repair events
                          │
                          ▼
                Local speech bridge + cache
                          │
                          ▼
                GPT-SoVITS → Furina speech

DeepSeek API → cloud dialogue / explanation (paused)
```

本地只启用一个音色，使用 CPU 合成，不运行本地大语言模型。常用短句预缓存，未缓存内容仍需要合成时间。

One voice model runs with CPU synthesis. No local LLM runs. Cached phrases reduce latency; uncached speech still requires synthesis time.

核心本地组件 / Local components:

| 文件 / File | 用途 / Role |
| --- | --- |
| `work/race-voices/bridge.py` | 语音接口、合成与缓存 / Speech API and caching |
| `work/race-voices/telemetry_announcer.py` | 圈速、赛道名称与播报队列 / Lap times, track names, and queue |
| `work/race-voices/damage_monitor.py` | 事故、维修及发动机事件 / Incident, repair, and engine rules |
| `work/race-voices/start.ps1` / `stop.ps1` | 服务启动与停止 / Service lifecycle |
| `outputs/Race_Voices/track_catalog/` | 中文赛道词典 / Chinese track catalog |
| `outputs/Race_Voices/基础表达校对.json` | 中文表达校对 / Chinese phrase corrections |

这些是现有本机部署的路径；当前公开仓库仅提供介绍与计划，尚未包含程序文件。

These paths describe the local deployment. The public repository currently contains documentation, not the application files.

## 播报示例 | Announcement Examples

| 场景 / Event | 中文播报 / Announcement |
| --- | --- |
| 开场 / Introduction | 我是芙宁娜，会帮你留意周围的赛车。 |
| 圈速 / Lap time | 本圈一分零九秒七。 |
| 左侧解除并排 / Clear left | 左侧已无车。 |
| 两侧解除并排 / All clear | 两侧已无车。 |
| 维修完成 / Repair complete | 本次维修已完成。出站前留意维修区交通，回到赛道后先确认车辆状态。 |

“已无车”表示该侧赛车已解除并排，不表示整条赛道安全。损伤提示依据实际维修要求与告警，不推测具体车身部位或损伤百分比。

Clear messages describe the end of alongside traffic. Damage alerts use available warnings and repair requirements rather than guessing component damage or percentages.

## 安装与运行 | Installation and Run

当前为个人本机部署，尚未发布完整安装包。以下命令用于已有部署，不能仅克隆本仓库后直接运行。

No complete installer is published. These commands apply to the existing local deployment, not a fresh clone.

前置条件 / Prerequisites:

- Windows 与 iRacing / Windows and iRacing
- Simulator Controller
- Python 3.10 项目环境及依赖 / Project Python environment and dependencies
- GPT-SoVITS、兼容的音色模型与参考音频 / Compatible voice weights and reference audio
- DeepSeek API 凭据，仅云端功能需要 / Credentials only for cloud features

在现有项目根目录启动服务 / Start services from the existing project root:

```powershell
.\work\race-voices\start.ps1
```

检查语音服务 / Check speech service:

```powershell
Invoke-RestMethod 'http://127.0.0.1:9881/health'
```

随后启动 Simulator Controller 并进入 iRacing。语音接口为本机 `http://127.0.0.1:9881/v1/audio/speech`，使用 OpenAI 兼容协议，由本地 GPT-SoVITS 合成。

Then start Simulator Controller and enter iRacing. The OpenAI-compatible speech endpoint uses local GPT-SoVITS synthesis.

停止本地语音与遥测服务 / Stop services:

```powershell
.\work\race-voices\stop.ps1
```

## 测试 | Tests

在现有本机部署中运行 / Run within the existing deployment:

```powershell
.\work\race-voices\venv\Scripts\python.exe -X utf8 -m unittest discover -s work/race-voices -p 'test_*.py'
```

2026-10-12 验证为 **37 项通过**，覆盖中文表达、圈速转换、遥测事件与维修条件。自动测试不能替代游戏中的触发、延迟与听感验收。

**37 checks passed on 2026-10-12.** Automated checks do not replace in-game trigger, latency, and listening validation.

## 后续计划 | Roadmap

- **P0**：服务健康检查、故障自动恢复、播报优先级与事故/维修游戏验收。 / Service recovery, announcement priorities, and in-game validation.
- **P1**：耐力赛油耗与进站策略、多组别交通提醒、赛道与表达校对。 / Endurance strategy validation, multiclass traffic, and Chinese proofreading.
- **P2**：恢复 DeepSeek 对话、复核方向盘语音按键、整理部署与依赖授权。 / Cloud dialogue, wheel controls, deployment, and licensing.

[查看完整任务与验收条件 / Full plan](docs/iracing-ai-engineer/PROGRESS_AND_PLAN.md#后续计划)

## 引用与参考 | Credits and References

| 项目 / Project | 使用与参考内容 / Contribution |
| --- | --- |
| [Simulator Controller](https://github.com/SeriousOldMan/Simulator-Controller) | 赛事助手及配置框架 / Assistant framework |
| [AI Race Engineer 文档](https://github.com/SeriousOldMan/Simulator-Controller/wiki/AI-Race-Engineer) | 工程师功能与数据限制 / Capabilities and limitations |
| [pyirsdk](https://github.com/kutu/pyirsdk) | 遥测读取、告警与维修字段 / SDK telemetry and field definitions |
| [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | 本地角色音色语音合成 / Local voice synthesis |
| [Furina_GPT_SoVITS](https://www.modelscope.cn/models/leletxh/Furina_GPT_SoVITS) | 芙宁娜音色来源 / Furina voice source |
| [UnlimitedBurst/GPT-SoVITS](https://huggingface.co/UnlimitedBurst/GPT-SoVITS) | 克洛琳德、甘雨候选音色，目前不同时启用 / Alternative voice sources |
| [DeepSeek API](https://api-docs.deepseek.com/) | 云端模型服务，当前对话暂停 / Cloud model service |

本项目定制部分为中文赛道与表达校对、圈速口语化、开场去重、事故与维修规则、语音桥接和部署脚本。上游作者权利与许可证保持独立；本项目不代表上游官方合作，不默认获得模型再分发授权。

Custom work includes Chinese catalogs, phrase corrections, lap-time formatting, greeting deduplication, event rules, the speech bridge, and deployment scripts. Upstream rights and licenses remain independent; this is not an official upstream collaboration.

## 配置与隐私 | Configuration and Privacy

公开仓库不包含密钥、私人配置、运行日志、音频或模型。启用 DeepSeek 云端功能时，相关请求会发送到该服务；当前基础播报由本地遥测规则和语音服务执行。

No credentials, private configuration, logs, audio, or model weights are published. Cloud features send relevant requests to DeepSeek; current basic announcements run locally.
