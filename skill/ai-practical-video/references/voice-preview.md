# 连贯旁白的可选预览适配器

`scripts/voice_edge_preview.py` 使用 [edge-tts](https://github.com/rany2/edge-tts) 的在线语音客户端，把每个语义镜头的完整旁白一次性提交，保留标点和英文。它和默认的本地 Kokoro 适配器相互独立，不会在故障或断网时偷偷切换声线。

这项选择需由调用方明确指定。参考试片的声线为 `zh-CN-XiaoxiaoNeural`、语速 `+3%`。不要因为声线相似就宣称效果或授权完全相同。此工作流没有使用付费 API、API key 或额度消费操作；客户端开源许可不等于服务输出的商用许可，始终写入 `publication_rights: "not_verified"`。该声音用于风格预览，公开发布前需核对适用的服务输出使用条件；不能把预览声线的成片宣称为授权已核实的可商用成片。

在已配置的 Python 环境单独安装可选依赖：

```bash
python -m pip install edge-tts==7.3.1
python skill/ai-practical-video/scripts/voice_edge_preview.py \
  --run /absolute/project/runs/RUN_ID \
  --voice zh-CN-XiaoxiaoNeural --rate=+3%
```

也可以使用 `--config /absolute/voice-preview.json`：

```json
{
  "provider": "edge-online-preview",
  "voice_id": "zh-CN-XiaoxiaoNeural",
  "rate": "+3%",
  "approved_style_change": true,
  "scene_gap": 0.28,
  "tail": 0.6
}
```

配置中的 `approved_style_change` 是调用者已经获得声线选择授权的记录，不能由无人值守的降级逻辑自行设为 true。默认声线配置不变；新声线须通过显式配置或 `--voice` 进入此适配器。

首尾仅裁去低于 −45 dB 的安静片段，并保留 30 ms 余量；镜头内停顿完整保留。镜头之间增加至多 0.28 秒，最后保留 0.6 秒尾音余量。真实时长不在 60–90 秒时，保留已生成的证据并把配音阶段标记失败，要求修改脚本，不用加速、截断或额外静音凑时长。

字幕使用服务返回的 `WordBoundary` 时间。多字词内的字符时刻、未返回的标点做插值；这些不是逐音素测量。词与脚本文字匹配率低于 65% 会停止，保留证据供核对。字幕按语义标点优先切分，每条最多 20 个字符；叙事模板优先在自然标点处分为均衡的两行，避免手机显示时只余一字换行。

每个镜头保留原始 MP3、原始词时间、裁切后 WAV、裁切量和文字对齐记录。缓存键包含全文、声线、语速、客户端和适配器版本、裁切策略；缓存命中前逐文件校验 SHA-256。输出继续使用 `voice/manifest.json`、`voice/measured-scenes.json` 和 `voice/narration.wav`，兼容现有时间线。全部原始声音、时间证据和对齐文件进入阶段校验，中途失败不会伪装为配音完成。

此适配器独立编写，沿用参考试片“完整语义段合成、保留原速、用词时间对齐字幕”的制作方法，没有复制参考项目完整脚本。
