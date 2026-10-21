# 热点研究与回退

搜索当前日期再向前7天，优先72小时。用可用联网搜索/页面读取，不要求付费 API。官方产品更新是功能与日期证据；公开 AI 媒体用于发现线索；公开趋势页仅在能读到日期、指标和范围时计入热度。抖音、视频号数据不可读时记录限制，不假造完整热榜。

每条候选保存 id/title/tool/feature/scenario、business_use、feature_verified、demo_feasible、event_at、sources、heat_signals 和 scores。精确时间用含时区的 ISO8601，展示为 Asia/Shanghai。官方只提供日期时，用 `event_at: null`、`event_date: "YYYY-MM-DD"` 和 `date_precision: "day"`，不要补一个虚构的发布时间。完全未知用 null，不把抓取时间当发布时间。

只有日期而没有来源时区时，排名器按 UTC±14 的可能范围计算事件区间，并在 selection.json 的 event_time_bounds 保留日期精度、最早/最晚北京时间和 timezone_known:false。整个区间都落入过去7天或72小时，才分别得到对应新鲜度；与边界重叠的区间不冒称精确的新鲜程度。确知事件时刻时才改填 event_at。

来源字段：url、kind（official/media/trend）、origin_id（原始事件或报道标识）、published_at、verified、核验摘记。转载同一原始消息统一 origin_id；官方快照保存获取时间、原始值和链接，不能推导没测到的增长率。

热度字段：metric、value、window、observed_at、url、verified。例如72小时新增星标、当日排行；累计 Stars 只有单一快照时不能填写增长 window。旧闻新转载用原事件时间判断，不以新转载日期进入近期池。无独立热度数据的官方新功能标“近期更新”；无近期事件标“常青选题”。

评分由当前会话依据证据填 0—5：fit 业务匹配、reproducibility 复现能力、service_demand 可承接服务需求；每项记录理由。程序加权分别30/30/15分，最近72小时新鲜度15分、4—7天9分，有时间窗口的热度证据10分。它是内部择题分数，不代表预计播放或收入。先淘汰无用途、无官方功能核验或不可演示的题目。热题池为空才选常青池。

去重键 tool|feature|scenario（大小写/首尾空格规范化），同时查项目 history.json 与 ~/.codex/ai-practical-video/history.json（跨制作目录）。30天重复只有 material_change 与 change_source 同时有效才可进入；需要实际核对变化，不能填一段空泛话绕过。样片指定主题可记录 selection_mode，不强行包装成搜索热点。

常备10类（选未重复的具体业务案例）：
1. 客户名单清理/去重 → 模板及规则配置。
2. 报价单/订单表制作 → 表单和自动填表服务。
3. 产品文案整理 → 产品资料包服务。
4. 产品宣传图/短片 → 宣传素材制作。
5. 询盘分类和回复草稿 → 销售工作流配置。
6. 公开客户研究 → 有证据的研究报告。
7. 会议记录变任务清单 → 办公模板和培训。
8. 文档/表格汇总 → 数据清理和报表模板。
9. 内容再利用 → 多平台素材改编服务。
10. 本地可复用自动化/技能 → 流程实施和维护。

服务方向必须和本期输出相关；不能保证收益，不自动发营销消息，不编造课程或商品已经可购买。
