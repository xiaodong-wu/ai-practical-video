# 来源与改编范围

- wallstreet-explainer，固定 commit `920ed1d3b3ecb5997d861902e2719dda6688c0b1`，MIT 代码/文档。脚本 render.mjs 从该版本改编，增加竖屏比例、安全路径、编码失败检查、视频录屏支持，默认2个渲染进程。沿用确定性 seek(t) 时间线接口。produce.py 的混音交付流程参考 upstream/mix.py，重新实现为无背景音乐且不截断旁白的 AAC 合成。原版源码与 LICENSE 在 upstream/wallstreet。
- SterlingChin/video-production-skills 的 video-scriptwriter，固定 commit `7c06790e9bc1d83662b749b2fa09e62fe8c2b1ef`，MIT。仅改编写作和镜头交接原则，中文业务实操结构及自动检查由本技能定义。原稿与 LICENSE 在 upstream/scriptwriter。
- Kokoro-82M-v1.1-zh 模型 Apache-2.0，kokoro-onnx MIT。依赖自己的许可仍然有效；不把模型许可套用到任意商标、音乐或客户数据。

未引入上游样片的新闻截图、人物、logo、视频或音乐；这些不在代码 MIT 许可内。未引入非商业许可的脚本技能。实际固定文件哈希见 upstream/pins.json 与model-lock.json。

