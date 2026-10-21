# 本地运行配置

验证使用 Python3.12、Node20+、ffmpeg/ffprobe、Playwright Chromium 和中文字体，支持 POSIX 文件锁。macOS 已走通成片；Linux 需补齐 Chromium 系统依赖，尚未完整验收；Windows 暂不支持。机器配置在 scripts/local.json：python、playwright_from（可定位 playwright 的 package.json）、voice_config、cover_font。不要拷贝其他用户的浏览器 cookies 或凭据。

公开仓库根目录的 bootstrap.py 创建独立运行时、安装锁定依赖、下载并校验模型，doctor.py 检查可用性，install.py 安装技能。先运行 `python3.12 bootstrap.py --plan` 可查看无副作用安装计划，再执行 bootstrap、doctor、install。可以指定 --runtime 与 --font；既有技能需要 --replace 且会保留备份。技能目录内仅保留 local.example.json 作为结构示例；不要把其他机器的绝对路径直接拿来使用。

免费声音运行在独立 venv，避免改系统依赖：kokoro-onnx==0.6.0、misaki[zh]==0.9.4、soundfile、pillow、pyyaml。实际环境的精确版本留存 requirements-lock.txt；模型固定身份在 model-lock.json，Node 锁定版本在 node-package-lock.json。本地合成不要求登录，也没有服务商按次费用；首次模型下载约362MiB，下载后缓存使用。首次选择 zf_001，speed=1.0；不靠变速凑时长。

中文 G2P 不会自动读英文工具名。script.json 的 pronunciations 映射应给 AI、Codex、ChatGPT、Excel 等本期出现的词提供经过核对的中文读法；没有映射的英文会在合成前明确报错，不把漏读音频当成成功。显示字幕仍保留原文本。

模型文件来自维护者 [model-files-v1.1](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1)：kokoro-v1.1-zh.onnx 与 voices-v1.1-zh.bin。下载后记录来源、大小与 SHA256，恢复时核验。若上游改动，不默默替换固定模型。模型许可与训练数据说明见 [Kokoro中文模型卡](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)。这不是对所有第三方素材的授权。

voice 配置 JSON：provider="kokoro-local"、voice_id="zf_001"、speed=1.0、engine_version、model/voices/cache 绝对路径、model_sha256、voices_sha256、cost_per_generation=0、license。每次合成前核对模型字节与预期 SHA256，变化时拒绝续跑；旧配置没有哈希字段时使用随技能附带的 model-lock.json。配置缺失报告具体缺项；不能偷偷调用付费 TTS。voice.py 的免费适配器会拒绝其他 provider，付费服务须另写适配器并在实际调用前核对本次报价与用户批准记录。

可用 Python 与文件录屏足够制作本地示例。真实外部 AI 工具的登录、可用地区、会员、导出限制必须逐次核验，不因已经安装本技能就认为全部可用。默认不自动调用其他模型 API、不创建计划任务、不代发平台。
