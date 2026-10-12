# 引用与第三方许可

本项目是独立集成层，不代表以下项目、iRacing 或游戏角色的官方产品。下载器不捆绑第三方模型、参考录音、Python 或 FFmpeg 二进制。

| 项目 | 使用内容与来源 | 许可说明 |
| --- | --- | --- |
| [Simulator Controller](https://github.com/SeriousOldMan/Simulator-Controller) | Oliver Juwig 开发的赛事助手框架与语法格式；`data/grammars` 为中文语法修订 | 修订材料继续采用 CC BY-NC-SA 4.0；原始许可与其他依赖声明保留在 `licenses/Simulator-Controller.txt` |
| [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | 角色语音推理引擎，固定源码版本见 `config/upstream.json` | MIT；保留 `licenses/GPT-SoVITS-MIT.txt`，安装时从上游下载 |
| [pyirsdk](https://github.com/kutu/pyirsdk) | iRacing 遥测读取 | BSD-3-Clause，随安装依赖保留其许可 |
| [UnlimitedBurst 音色库](https://huggingface.co/UnlimitedBurst/GPT-SoVITS) | 克洛琳德模型与参考音频 | 发布页面标注 MIT；资源与哈希见 `config/assets.json`，原始角色/录音权利另行适用 |
| [芙宁娜音色](https://www.modelscope.cn/models/leletxh/Furina_GPT_SoVITS) | 芙宁娜模型与参考音频 | 未对其权利作额外授权声明；遵守原发布页面条款，资源不随本仓库再分发 |
| [G2PW](https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained) | GPT-SoVITS 使用的中文发音模型包 | 安装时从上游下载，固定版本与哈希见下载清单；各包条款随上游适用 |
| Python、PyTorch、FastAPI、imageio-ffmpeg 等 | 安装时从官方源 / PyPI 下载运行依赖 | 各自许可适用；FFmpeg 具体构建许可随 imageio-ffmpeg 包保留 |

`data/grammars` 的修订日期为 2026-10-12，修改包括中文措辞、角色名称与自然报时。保留来源和上述共享许可；本仓库自编集成程序的 MIT 许可不覆盖这些材料。

`data/tracks_zh.json` 是赛道名称/布局的中文词典；`data/phrasebook.json` 是中文表达校对资料。赛道及品牌名称归原权利人。运行日志、个人配置、API 密钥、缓存与私有录音不进入发行包。

完整依赖版本分别记录在 `requirements.txt` 和 `requirements-roles.txt`。云端 API 对话只列入后续计划，当前运行不发送驾驶数据给对话模型。
