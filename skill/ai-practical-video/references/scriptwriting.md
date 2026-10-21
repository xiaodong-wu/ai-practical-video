# 中文实操脚本与交接

改编自 MIT video-scriptwriter：保留先明确受众与结果、口语写作、可测时长、镜头交接与版本意识。原文及 LICENSE 在 upstream/scriptwriter；它的英文按词数估时不能直接用于中文成片。

先实测，后定稿。写三种差异化开头：实际结果、具体错误、操作前后对比，保留选择理由。避开泛泛的“你知道吗”“颠覆”“必看”。第一句说清一个结果；只教两三个关键动作；例外和结果核对必须可见。结尾一条相关服务，不强塞关注/评论/购买多重动作。

script.json：title、business_use、access_conditions、hooks（3项）、selected_hook、hook_reason、pronunciations、scenes。
scene：id、phase（result/problem/steps/verify/service）、heading（建议每行不超过14汉字，两行内）、narration、evidence_id、proof_files、capture_index、visual_kind、disclosure、claim_checked。illustration 必须 disclosure=示意画面；真实文件预览写 local_file_preview。

不要自动把 claim_checked 设为真：比对原输入、实际输出、截图及计算日志。价格/地域/付费方案未知就说明未知。为有依据的英文字母读法提供 pronunciations，仅改变读音不改变含义。字数只供初稿参考，正式时长来自实际生成音频。

每个录屏镜头含真实操作或结果，必要时保留原操作短片段再停帧解释，不制造不存在的点击。屏幕文字太小就缩小所讲区域、放大或减少字段；不能靠旁白掩盖不可读画面。界面拟稿只能清楚标“示意”，不能当实操证据。

platforms.json 包含 wechat/douyin 两个对象：title、description、hashtags、cover_lines（每行最多9字为宜）、cover_subtitle、monetization、ai_disclosure。不同平台各自组织标题与封面，事实范围一致。description 必须写必要账号、费用或访问条件，不能称“完全免费”却省略上游工具订阅。
