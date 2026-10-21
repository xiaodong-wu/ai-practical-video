# 中文实操脚本与交接

改编自 MIT video-scriptwriter：保留先明确受众与结果、口语写作、可测时长、镜头交接与版本意识。原文及 LICENSE 在 upstream/scriptwriter；它的英文按词数估时不能直接用于中文成片。

先实测，后定稿。写三种差异化开头：实际结果、具体错误、操作前后对比，保留选择理由。避开泛泛的“你知道吗”“颠覆”“必看”。第一句只说一个结果或具体疑问；只教两三个关键动作；例外和结果核对必须可见。结尾自然回扣；相关服务可以放进发布文案，不强塞口播广告、关注/评论/购买多重动作。

先写完整语义段的口语，再做字幕切分。参考短片风格初稿可约 230–280 个汉字，最终以实际配音为准。不要把“原始输入保留、独立程序复算、工具定制和规则维护”等交付报告句子连续念给观众；用“这五天到底是哪五天，一格格核对”表达同一动作，证据保留在交付文件。幽默只能修饰事实，不能改变计算规则或把模拟日期说成官方假期。

script.json：title、business_use、access_conditions、hooks（3项）、selected_hook、hook_reason、pronunciations、scenes。
scene：id、phase（开头 result/hook，中间 problem/steps/verify，结尾 service/takeaway）、heading（建议每行不超过14汉字，两行内）、narration、evidence_id、proof_files、capture_index、visual_kind、disclosure、claim_checked。illustration 必须 disclosure=示意画面；真实文件预览写 local_file_preview。示意镜头不需要虚构 capture_index，实际操作镜头仍必须映射真实录屏。新叙事模板用 visual_style="editorial"，具体字段见 editorial.md。

不要自动把 claim_checked 设为真：比对原输入、实际输出、截图及计算日志。价格/地域/付费方案未知就说明未知。为有依据的英文字母读法提供 pronunciations，仅改变读音不改变含义。字数只供初稿参考，正式时长来自实际生成音频。

每个录屏镜头含真实操作或结果，必要时保留原操作短片段再停帧解释，不制造不存在的点击。屏幕文字太小就缩小所讲区域、放大或减少字段；不能靠旁白掩盖不可读画面。界面拟稿只能清楚标“示意”，不能当实操证据。

platforms.json 包含 wechat/douyin 两个对象：title、description、hashtags、cover_lines（每行最多9字为宜）、cover_subtitle、monetization、ai_disclosure。不同平台各自组织标题与封面，事实范围一致。description 必须写必要账号、费用或访问条件，不能称“完全免费”却省略上游工具订阅。
