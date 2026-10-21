# 运行顺序与产物契约

下面的 `$SKILL` 是当前技能目录，`$PY` 来自 scripts/local.json，`$RUN` 是 init 返回的绝对路径；不要把示例变量当成已设置。

```sh
python3 "$SKILL/scripts/pipeline.py" init --root "$PWD/ai-practical-video-project" --topic "自动选题" --mode auto
python3 "$SKILL/scripts/pipeline.py" select --run "$RUN" --candidates "$RUN/research/candidates.json" --history "$PROJECT/history.json"
python3 "$SKILL/scripts/pipeline.py" seal --run "$RUN" --stage research --outputs research/candidates.json research/selection.json
```

当前会话先执行联网检索，生成 candidates.json；select 是核验后的分类/排名器，不自行联网。保留原始搜索查询与页面证据到 research。指定选题也要保留来源，但无需假造候选竞赛。

候选事件可用精确 `event_at`（含时区），或仅日期的 `event_at: null`、`event_date: "YYYY-MM-DD"`、`date_precision: "day"`；后者按不确定时区区间保守判断时效，详见 research.md，不捏造具体时刻。

实测生成 `demo/files/` 输入、输出、提示词、脚本及数值核对。`demo/evidence.json`：items 数组，每项 id/type/source_file/capture_step；另外保存 input_output_hashes 与 actual_output。`demo/usage.json` 记录素材与声音许可、模拟数据、音乐状态。`capture-plan.json` 有 url（省略则使用本地 demo/viewer.html）和 actions 数组，kind 支持 click/fill/press/observe、selector/value/expect/hold_ms。外部界面先实际读取 DOM，不能猜选择器。

```sh
node "$SKILL/scripts/capture.mjs" --run "$RUN"
# seal demo 时列出所有实际 inputs/outputs，包括源数据、程序、截图、录屏和日志。
python3 "$SKILL/scripts/pipeline.py" check-script --run "$RUN"
# seal script 的 outputs 至少包括 script/script.json、script/platforms.json、script/check.json。
"$PY" "$SKILL/scripts/voice.py" --run "$RUN" --config "$VOICE_CONFIG"
"$PY" "$SKILL/scripts/produce.py" timeline --run "$RUN"
"$PY" "$SKILL/scripts/produce.py" preview --run "$RUN"
node "$SKILL/scripts/audit-layout.mjs" "$RUN"
```

seal 命令 `--inputs`/`--outputs` 接 run 相对路径列表，文件必须真实存在，禁止路径越界。语音按短句合成并测时，每条字幕对应自己的音频段，不使用估计语速生成正式时间码。实际视频映射 `capture_index` 到 capture/log.json 的操作片段。旁白包含连续多个动作时，可设置 `capture_end_index`，首尾索引均包含在片段内；省略时保持单动作映射，必须满足 `0 <= capture_index <= capture_end_index < 动作数`。

检查预览后写 `qa/preview-review.json`：preview_sha256、visual_checked、phone_readable、claims_match、audio_checked、no_clipping、review_method、notes。必须有实际检查依据。音频可用本地 ASR 加信号检测；说明无法替代主观听审。失败时修复原因后重跑对应阶段。

```sh
"$PY" "$SKILL/scripts/produce.py" final --run "$RUN"
"$PY" "$SKILL/scripts/produce.py" qa --run "$RUN"
"$PY" "$SKILL/scripts/produce.py" package --run "$RUN"
python3 "$SKILL/scripts/pipeline.py" status --run "$RUN"
```

`status` 按输入输出 SHA256 与依赖图使过期内容失效。失败用 `fail --stage … --reason …`；外部介入用 `wait`。初次失败后技术步骤再修复2次；demo再修复1次，随后换候选并从 research 开始。录屏损坏应使 demo 及后续步骤过期，不必重新搜索已核验来源。渲染中断从完整 timeline 继续，不能把残留分段文件当成成片。

声音变更也要使 voice 过期：把当前声线配置复制进 run/voice/config.json 作为 voice 输入（模型路径可留本机，交付包含哈希与许可）；不能只根据文件名命中缓存。每次恢复核对 scripts/local.json 指向的运行时是否仍可用。

交付目录 checksums.json 是文件清单，脚本、封面、字幕与示例均对应当前 run 版本。项目 history.json 和跨项目 ~/.codex/ai-practical-video/history.json 只记录本地完成，不代表平台发布记录。ZIP 包含制作源码但不打包浏览器登录状态、API密钥、Python环境或巨大模型；runtime.md 说明依赖复建方式。
