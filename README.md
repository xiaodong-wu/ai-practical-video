# AI 实操视频技能

为小企业老板、外贸业务员和运营人员制作不露脸 AI 实操短片。由 Codex 搜索近期选题、完成真实演示、写中文脚本，再用本地工具录屏、免费配音、渲染和验收。

每次交付一条 **60—90 秒、1080×1920、30fps、H.264/AAC** 竖屏 MP4，以及微信视频号和抖音各自的封面、标题和发布文案。成片由使用者手动上传；本项目不登录账号发布、不创建定时任务。

## 工作方式

```text
近 7 天检索 → 核验与择题 → 实测并保留证据 → 写稿与分镜
→ 真实录屏 → 本地中文女声 → 低清预览 → 成片检查 → 发布素材包
```

- 优先最近 72 小时的变化；有来源的近期更新不自动称为“热门”。缺少可复现热点时记录原因并回退常青案例。
- 每句旁白对应真实操作、输出文件或标注的示意。自建预览器持续标明“本地文件预览”，不冒充第三方软件界面。
- 默认 Kokoro v1.1-zh `zf_001` 女声，本地合成无服务商按次费用；无需语音 API 密钥。文本、声线和模型相同时复用缓存。
- 音频决定字幕和镜头时间，不通过强行加速或截断凑时长。默认无背景音乐；可选纸感叙事模板、原创轻音乐和短音效。
- 可显式选择整段语气的晓晓试听适配器：每个语义段合成后按词时间拆字幕，避免逐逗号合成破坏连贯性。在线声音发布授权未单独核实，不能把客户端开源许可当成音频商用许可；默认本地声线保持不变。见 [试听配置](skill/ai-practical-video/references/voice-preview.md)。
- 输入输出哈希、阶段依赖、重试预算及等待状态支持中断续跑。只有检查与素材包完整时才标记 `completed_local`，从不写成“已发布”。

这是一套 **Codex 技能及本地制作工具**。联网研究、选题判断、写稿和实操仍由当前 Codex 会话及其工具完成；`pipeline.py select` 只是对已核验候选评分，不是独立联网服务。Codex 或所演示第三方产品自身的订阅、账号与地区条件仍适用。

## 安装

已验证环境为 Apple Silicon macOS、Python 3.12。代码使用 POSIX 文件锁；Linux 需要准备中文字体及 Chromium 系统依赖，目前没有完整跨平台验收；Windows 不支持。

准备 Python **3.12**、Node.js **20+**、npm、FFmpeg（含 `ffprobe`）和中文字体。macOS 常用安装方式：

```sh
brew install python@3.12 node ffmpeg
git clone https://github.com/xiaodong-wu/ai-practical-video.git
cd ai-practical-video
python3.12 bootstrap.py --plan
python3.12 bootstrap.py
python3.12 doctor.py
python3.12 install.py
```

`bootstrap.py` 创建仓库内 `.runtime/`，按锁定版本安装 Python/Node 依赖、Playwright Chromium，并下载约 **362 MiB** 模型。首次安装需要网络和额外的依赖/浏览器磁盘空间；下载模型按 SHA256 核验。它不调用付费服务，不改系统 Python 环境。

默认使用系统中文字体；找不到时运行 `python3.12 bootstrap.py --font /path/to/NotoSansCJK-Regular.ttc`。运行时也可放到别处：`--runtime /path/to/ai-video-runtime`。安装后需保留该目录，移动后重新配置并安装。

技能默认安装到 `${CODEX_HOME:-~/.codex}/skills/ai-practical-video`。已有同名技能时安装器会停止；确认替换后用 `python3.12 install.py --replace`，旧目录会备份。可用 `--target /path/to/skills/ai-practical-video` 指定位置。仅先安装指令用 `--instructions-only`；制作视频前仍须配置运行时。

安装或更新后，开启新 Codex 会话，让技能重新被发现。

## 一句话运行

在希望保存视频项目的目录中，向 Codex 发送：

> 使用 $ai-practical-video 搜索最新 AI 选题，制作今天的一条视频。

或指定主题：

> 使用 $ai-practical-video 把 AI 整理客户名单做成一条视频，用模拟数据完成演示。

恢复任务：

> 使用 $ai-practical-video 继续上次未完成的视频任务。

项目默认位于当前目录的 `ai-practical-video-project/runs/<任务编号>/`。完整工具顺序和文件结构见 [工作流契约](skill/ai-practical-video/references/workflow.md)，模型及运行配置见 [运行时说明](skill/ai-practical-video/references/runtime.md)。没有目标工具登录、功能权限或可验证结果的候选会被跳过；免费本地配音可直接执行，新增付费能力需要本次明确批准。

## 交付内容

| 产物 | 内容 |
| --- | --- |
| 成片 | 可上传 MP4、SRT、完整旁白和分镜 |
| 平台素材 | 视频号和抖音各自封面、标题、简介、话题词、AI 内容声明建议 |
| 可复用文件 | 本期模板、模拟输入和真实输出 |
| 证据与编辑 | 选题来源、素材许可、操作证据、QA 报告、手机尺寸联系表、编辑源码、ZIP |

封面和字幕采用保守留白，平台 UI 可能变化，发布前仍应查看平台预览。ASR 和波形检查不能代替主观听审；实际采用的音频检查方式会写进报告。

## 示例与验证

[合成客户表示例](examples/customer-cleanup/)包含 CSV、提示词和可运行的整理程序，可先验证数据规则，不需要登录或模型服务：

```sh
python3.12 examples/customer-cleanup/clean.py
python3.12 -m unittest discover -s tests -v
```

测试覆盖选题时效/独立来源/热度证据、30 天去重、前置依赖、输入变更失效、登录/费用等待、重试预算、路径边界、安装备份、模型校验及实际竖屏编码。渲染回归测试需要完成 `bootstrap.py`。测试不替代每条视频的内容与视听检查。

观感检查单独记录：短开场、完整语义段配音、真实操作的局部放大、动画与操作的交替、手机尺寸文字。技术解码通过不代表语言自然或风格匹配。具体见 [叙事与观感检查](skill/ai-practical-video/references/editorial.md)。

## 开源来源

原创实现与改编部分使用 [MIT](LICENSE)。保留上游代码、固定版本和各自许可证：

- [wallstreet-explainer](https://github.com/HeyChengC/wallstreet-explainer)：时间线/浏览器渲染和混音思路；竖屏画幅、录屏、验证与交付流程在此改编。
- [video-scriptwriter](https://github.com/SterlingChin/video-production-skills/tree/main/skills/video-scriptwriter)：脚本和分镜交接思路。
- [Kokoro 中文模型](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)：Apache-2.0；[kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)：MIT。

详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和 [固定版本记录](skill/ai-practical-video/references/upstream/pins.json)。仓库不包含上游样片的新闻图片、人物素材或音乐，也不包含模型权重、浏览器登录数据或个人制作记录。
