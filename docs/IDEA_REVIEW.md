# GreenPulse Idea 评审报告(STORM 式多视角评审)

飞书「2026 AI 先锋未来人才大赛」世纪互联赛道。评审日期 2026-07-29。
评审对象:`Green-token-orchestrator` 仓库 README(GreenPulse;快照 sha256 前 16 位 `7068c1dbca1890f6`,经对话上传获取于 2026-07-29;桥接恢复后补 commit SHA)。
**评审时仓库桥接离线,只有 README 可读;凡涉及"仓库里有没有代码"的判断均标注为待验证。**

方法论:采用 [stanford-oval/storm](https://github.com/stanford-oval/storm)(Shao et al., NAACL 2024, [arXiv:2402.14207](https://arxiv.org/abs/2402.14207))的核心流程改造而成 —— 视角发现 → 多视角尖锐提问 → 有据攻防(所有结论必须落在检索证据上,证据带 URL)→ 魔鬼代言人(Co-STORM Moderator 机制:专挑已检索但未被讨论的证据追问盲区)→ 结构化成文。评分卡在证据库建完之后才填写(STORM 的 pre-writing/writing 分离原则)。每个判断标注 [确认](有一手来源)、[推断],或 [未检出](检索未发现,受限于检索范围与日期——否定性声明的证据上限只能到这一档,不得标 [确认])。

---

## 0. 执行摘要

**裁决:GO,但有三个必须执行的 PIVOT 条件。** 方向压中世纪互联"10GW 绿色直流 AIDC + 2030 年 100% 可再生能源"双主线与国家"算电协同"政策窗口,文献上也存在真实空白;但 README 目前的 MVP 范围恰好落在文献**最拥挤、最不新颖**的角落,且项目名承诺的"token 级"编排在 MVP 里不存在。

三个 PIVOT 条件(不满足则该项目只是重做 CarbonScaler(SIGMETRICS'24, arXiv 2023)):

1. **把 "token" 做实。** MVP 必须至少包含一个 token 级旋钮(碳感知模型路由,或 Sprout 式生成指令/token 预算),而不只是作业级时移。作业级时移是 2011 年 GreenSlot 以来最拥挤的赛道;token 级调碳 2024 年才出现(Sprout, EMNLP 2024),2026 年才有直接竞品(GAR),这才是名字里 "Green-token" 兑现的地方,也是发表/答辩空间所在。
2. **把评审口径做诚实。** 单一"预计降碳 28%"式数字不可再出现;所有节碳声明必须双口径(平均+边际碳强度)、带 SLO 代价、带与 carbon-agnostic / static-optimal / oracle 三级基线的对照(§2.2 的 Q2.3、Q2.4)。
3. **把运营商身份做成护城河。** 世纪互联的独有资产是园区级分时绿电/储能/电价/PUE 数据与功率预算权 —— 评审(尤其企业教练)会用这个标准挑剔任何"租户视角也能做"的方案(§2.3)。信号层必须为"园区自有信号"留出一等公民的 Provider 位置,而不是绑死 Electricity Maps。

| 视角 | 评分(1-5) | 一句话 |
|---|---|---|
| 赛道/商业评委 | 4.0 | 命题契合度极高,叙事(虚拟储能/绿色 Token 产能)出色;交付物形态需向"可演示案例"校准 |
| 技术评委/学术 SOTA | 2.5 | MVP 落在文献最拥挤处;token 级承诺未兑现;评测协议有硬伤(基线弱、单口径、无不确定性) |
| 世纪互联资深工程师 | 3.0 | 架构分层方向对;但中国碳信号数据、分时 PUE 耦合、与 K8s/Prometheus 栈的对接均未回答 |
| 竞品/相邻项目 | 3.0 | 五个旋钮各自都有开源实现;差异化=运营商信号+多时间尺度统一编排,须明说并证明 |
| 运维/SRE·合规 | 2.5 | 信号丢失降级、SLA 保底开关、合成数据标注纪律均未设计;README 里已出现一个捏造味道的数字 |
| 基本事实核查 | 3.5 | README 自洽、定位诚实(自称 Prototype/合成数据起步);个别示例数字有被误读为实测的风险 |

三大关键风险(全量见 [`RISKS.md`](RISKS.md)):中国区碳强度/绿电公开数据粒度不足(R1);节碳收益被时空平移上限研究证伪或大幅缩水(R2);大赛交付物形态与工程投入错配(R3)。

---

## 1. 视角发现(Step 1)

从同类项目的评审记录与失败案例(GSF CarbonHack 获奖配方、SIGMETRICS/EuroSys/HPCA 论文的评审共识、世纪互联开源项目的设计原则)归纳出 5+1 个视角:

| 视角 | 职责 | 证据基础 |
|---|---|---|
| P0 基本事实核查员 | README 的每个数字、每个声明是否属实/自洽 | README 本身 |
| P1 赛道/商业评委 | 与大赛机制、世纪互联命题、企业价值的契合 | 大赛公开资料 + VNET 战略公开信息 |
| P2 技术评委(学术 SOTA) | 相对文献的新颖性、评测协议有效性 | 25+ 篇核实过的论文 |
| P3 世纪互联资深工程师 | 数据可得性、与现有栈集成、可维护性 | VNET GitHub org、招聘、ESG 披露 |
| P4 竞品/相邻开源项目 | "这个轮子是不是已经有了" | 20+ 个核实过的仓库 |
| P5 运维/SRE·合规 | 失效行为、SLA 保护、口径合规 | 生产系统论文 + 运营商惯例 |

---

## 2. 有据攻防:各视角最尖锐的问题与项目现状(Steps 2-3)

### 2.0 基本事实核查员

**Q0.1 — README 里 `"expected_carbon_reduction": "28%"` 这个数字从哪来的?**
现状:这是调度决策 JSON 示例里的字段值。项目还没有代码、没有仿真、没有任何实验,28% 无出处。作为示例字段无罪,但它长得像一个实测结果,答辩 PPT 里一旦被复制就变成捏造数据。姊妹项目的教训(ENGINEERING_RULES R3.2:任何对外数字必须标注性质与协议)在这里必须继承。**裁定:立即在 README 中把该值改为 `"<模拟输出,无实测含义>"` 或删除。**

**Q0.2 — README 声称 MIT License,LICENSE 文件存在吗?建议仓库结构里没有列 LICENSE。**
待验证(桥接离线)。若不存在,是 5 分钟工作量;竞赛评审对"README 声称的东西 tree 里没有"极其敏感。

**Q0.3 — 三张核心图(SVG)是否与文字架构一致?** 待验证。

### 2.1 赛道/商业评委(P1)

**Q1.1 — 这个题和世纪互联的真实业务钩子在哪?**
答(有据):契合度是本项目最强的一面。世纪互联正处于"10GW 绿色直流 Hyperscale 2.0"部署期(2026-2036,乌兰察布/怀来/苏州三个 GW 级集群,源网荷储协同与园区间能量互济)[确认: https://www.vnet.com/portal/article/index/cid/14/id/1031.html],官方目标 2030 年 100% 可再生能源、2025 年绿电占比约 36%、乌兰察布基地绿电超 80% [确认: https://www.vnet.com/environment.html];"算电协同"已写入政府工作报告并由国家数据局体系化推进 [确认: https://www.nda.gov.cn/sjj/swdt/sjdt/0318/20250318212051776584737_pc.html]。乌兰察布 80% 而非 100% 的缺口,正是"时间不匹配"——让 AI 负荷跟随绿电窗口正面回答这个缺口。另一个真实钩子:公司于 2025-11 前后发行数据中心行业首单绿色持有型不动产 ABS(8.6 亿元)[确认: http://cn.chinadaily.com.cn/a/202511/21/WS692010f6a310942cc4992abf.html],可信的分时绿电消纳账本对绿色融资披露有直接价值。**本段全部世纪互联事实将当着世纪互联评委复述,进对外材料前逐条重开 URL 核验并注明"截至日期"(P0-X4)。****"虚拟储能"与"从售卖 GPU 到经营绿色 Token 产能"的叙事,是能让商业评委记住的那种句子。**

**Q1.2 — 大赛要的到底是什么交付物?**
答(部分有据):大赛机制是"企业真实场景命题 + 1-3 人学生队 + 认领命题提交初步思路 + 企业教练带教产出案例",奖励为校招/实习 Offer [确认: https://diidea.pku.edu.cn/web/programs_details_a.php?id=28 ; https://www.aitop100.cn/infomation/details/34142.html]。**世纪互联赛道的具体命题与评分细则未能从公开渠道获取**(赛道详情页为 JS 渲染,无公开转载)[未检出:2026-07-29,中英文十余组关键词]。参照其他企业命题的风格(蔚来/瑞幸/去哪儿均为业务场景 AI 应用),交付物大概率偏"可演示的业务方案 + 量化收益案例",而非纯学术复现 [推断]。**行动项(见 PLAN P0-X2):队内必须有人登录赛事页面,把世纪互联命题原文、交付物要求、评审标准、关键日期抄录进 `docs/COMPETITION_BRIEF.md`,这是当前全项目最高优先级的信息缺口。**

**Q1.3 — 三人学生队,这个架构图的野心是不是太大了?**
答:README 的能力架构含五层平台 + 数字孪生大屏 + 四个时间尺度。按 CarbonHack 冠军配方(Lowcarb:宿主框架原生插件 + 独立 SDK 适配层 + 回测出一个数字 + 一个领域 demo + notebook)[确认: https://github.com/birnbaum/flwr-lowcarb],获奖作品的共性是**窄而深、一条命令可复现、一个诚实的量化数字**,不是宽而全。README 自我定位为 Prototype 是对的;风险在执行时被架构图牵着走。裁定:MVP 砍到"一个仿真环境 + 一个调度器 + 一套诚实评测 + 一个大屏",四层以外全部推迟(见 PLAN)。

### 2.2 技术评委/学术 SOTA(P2)

**Q2.1 — 你的 MVP(作业级时移+扩缩容)相对 2011-2024 的文献,新在哪里?**
现状:不新。逐条对照:绿电窗口批作业调度 = GreenSlot(SC 2011,绿电消纳 +13~117%)[确认: https://dl.acm.org/doi/abs/10.1145/2063384.2063411];"日内保总量、小时限峰"的容量调制 = Google VCC(生产部署)[确认: https://arxiv.org/abs/2106.11750];随碳强度增减弹性作业副本 = CarbonScaler(SIGMETRICS'24, arXiv 2023,节碳 51%,已集成 K8s autoscaler)[确认: https://arxiv.org/abs/2302.08681];跨园区交互式请求碳路由 = CASPER(节碳最高 70%、零时延退化)[确认: https://arxiv.org/abs/2403.14792]。**README 的 MVP 范围与上述工作的交集接近 100%。** 项目必须回答"统一编排五个旋钮 + 运营商侧信号"这个组合命题,而不是重做其中任何单一旋钮 —— 文献综述的结论恰好是:when(51%↓)/where(70%↓)/how(53% 能耗↓)/which-model(74% 请求碳↓)/how-many-tokens(40%↓)五个旋钮各自被证明有效(各数字出自不同电网/负载/口径,仅为水位线,禁止并列比较),但**把它们统一在运营商多园区环境、一个 SCI 口径的 token 级编排器里的工作**[未检出:截至 2026-07-29 的三路检索]——这是本项目新颖性声明的根基,其证据等级只能到"未检出",答辩前由 P0-X4 复核一遍,措辞保持"据我们所知(to our knowledge)"。

**Q2.2 — 项目叫 Green-**token**-orchestrator,MVP 里 token 在哪?**
现状:不在。MVP 调度的是作业(微调/离线推理),token 只出现在指标(Token/Joule)里。token 级调碳已有两条被证实的路线:(a) Sprout 的生成指令——高碳时段注入指令让模型少生成 token,节碳 40%+ 且保质量(EMNLP 2024,有开源代码)[确认: https://arxiv.org/abs/2403.12900 ; https://github.com/boringlee24/EMNLP24_Sprout];(b) GAR 的碳感知模型路由——三预测器+可行集+碳预算对偶价,0.712 vs 2.750 gCO2/请求(2026)[确认: https://arxiv.org/abs/2605.11603 ;**注意:此文晚近且承重(PIVOT 1 的竞品论据、O-X2 的方案参照都压在它上面),P0-X4 必须重开链接逐一核对题目与三个数字,任一对不上即改写本裁定的论据**]。**裁定(PIVOT 条件 1):MVP 必须纳入至少一条,建议 (b) 路由(与调度器同构、工程量低),(a) 作为扩展。**

**Q2.3 — 你的四个 baseline(FIFO/Price-only/Carbon-only/GreenPulse)够吗?**
不够,且缺的正是强论文的共同做法:**carbon-agnostic 性能最优**(不是 FIFO——FIFO 是稻草人)、**最优静态策略**(证明"动态"有增量:CarbonScaler 对静态最优只 +8%,这个数字才是诚实的)[确认: https://arxiv.org/abs/2302.08681]、**oracle**(事后完美预测上界,报告"达 oracle 的 x%",GAR 报 97%)[确认: https://arxiv.org/abs/2605.11603]。同时必须报"等 QoS 下节碳%"——只报碳降不报 SLO 代价的结果不可信。完整评测协议要点进 [`DESIGN_STANDARDS.md`](DESIGN_STANDARDS.md) §2.2,冻结版为 `docs/EVAL_PROTOCOL.md`(PLAN S-X4)。

**Q2.4 — 用什么碳强度口径?平均还是边际?**
README 未提。这不是细节:e-Energy 2024 实测 65 个电网区域中 **55.4% 平均/边际信号负相关**,按平均信号调度得出的"18% 节碳"按边际口径核算可能为负 [确认: https://dl.acm.org/doi/10.1145/3632775.3661953 ;55.4% 的确切口径(区域占比的统计方式)P0-X4 复核原文回填——该数字是双口径纪律的唯一实证依据,承重]。**单口径结论既不可发表也不可售卖。裁定(PIVOT 条件 2):双口径成为评测协议的硬性要求。**

**Q2.5 — 节碳潜力的上限算过吗?**
没有。EuroSys 2024 用 123 个电网区域证明:时空平移的实际上限"有限且远非理想",**简单策略就能拿走大部分收益**,电网越绿收益越小 [确认: https://arxiv.org/abs/2306.06502];Let's Wait Awhile 证明收益强依赖电网、预测误差会侵蚀收益 [确认: https://arxiv.org/abs/2110.13234]。**裁定:PLAN 的 Stage S 必须先跑"上限分析"——在目标电网曲线下,oracle 调度器最多能省多少。上限如果只有 8%,整个项目的叙事要改写;这必须在写调度器之前知道,而不是答辩前一天。** 这同时是防"AI 大脑"过度工程的护栏:上限研究说简单策略拿走大部分收益,所以 MVP 用 MILP/启发式,不用 RL(见 Q2.6)。

**Q2.6 — "AI 协同调度大脑"具体是什么算法?α-ε 五个权重怎么定?**
README 未定义。裁定:MVP 用**滚动时域 MILP(或贪心启发式)**——目标函数即 README 的五项加权,求解器用开源(HiGHS/OR-Tools);权重不拍脑袋,扫参后报 Pareto 前沿而非单点。RL/学习型调度器明确移出 MVP(依据 Q2.5 的上限证据 + 三人队工程量)。"AI"体现在预测层(绿电/负载预测)与 token 路由层,不体现在把优化器换成黑盒。

### 2.3 世纪互联资深工程师(P3)

**Q3.1 — 你的碳强度和绿电数据,在中国,从哪来?**
这是全项目最被低估的风险。Electricity Maps 对中国只有粗粒度分区,WattTime 的 5 分钟边际信号不覆盖中国大陆 [确认: https://app.electricitymaps.com/developer-hub/api/reference ; https://www.watttime.org]。可用的现实组合:(a) 公开的省级电网分时数据与研究数据集;(b) **园区侧自有信号**——绿电直连曲线、电力交易结算、光伏/储能 SOC(世纪互联设有专职电力交易职能、相应数据在企业内真实存在 [推断:调研代理报告招聘信息中存在电力交易员岗位,但所存 URL 指向 Java 岗列表页,不能作为一手证据;P0 期间补抓 JD 截图,补不到则此点整体降级]);(c) 合成数据(标注为合成)。**裁定:信号层的 Provider 抽象必须把"园区自有信号"和"static-json/合成"做成一等公民(mock-first,参照 GSF Carbon Aware SDK 的 `.Json` 数据源与 carbon-aware-keda-operator 的 mock 源 [确认: https://github.com/Green-Software-Foundation/carbon-aware-sdk ; https://github.com/Azure/carbon-aware-keda-operator]),不绑死任何外部数据商。**

**Q3.2 — 为什么你的调度只看电,不看 PUE?**
运营商相对云租户的独家优势恰好在这:CUE = 电网碳强度 × PUE(The Green Grid WP#32)[确认: https://www.thegreengrid.org/en/resources/library-and-tools/241-WP%2332---Carbon-Usage-Effectiveness-(CUE):-A-Green-Grid-Data-Center-Sustainability-Metric],而 PUE 分时变化(夜间/冬季更低),时移决策应当用 CI(t)×PUE(t) 联合信号。租户看不到分时 PUE,世纪互联看得到(全年平均 1.24 已披露 [确认: https://www.vnet.com/environment.html])。**裁定:仿真环境加入分时 PUE 曲线,这是差异化,不是负担。**

**Q3.3 — 怎么接进我们的栈?我们是 K8s/Go/Python/Flink/Prometheus 世家。**
世纪互联 GitHub org 的 smarthaven(超大规模 DC 管理:Flink on K8s + Prometheus/Grafana + GitOps + K8s CRD,设计原则"开源、技术中立")就是这个问题的标准答案模板 [确认: https://github.com/21vianet/smarthaven]。裁定:执行层适配器全部走宿主原生扩展点——Kueue AdmissionCheck 做批任务绿电闸门、KEDA external scaler(gRPC 四方法)做弹性伸缩、K8s scheduler framework Score 插件做放置打分、llm-d EPP scorer 做推理路由 [确认: https://github.com/kubernetes-sigs/kueue ; https://keda.sh/docs/latest/concepts/external-scalers/ ; https://github.com/kubernetes-sigs/scheduler-plugins ; https://github.com/llm-d/llm-d-inference-scheduler];指标全部以 Prometheus exporter 约定输出(与 CNCF Kepler 的 `kepler_` 指标可在 PromQL 里直接相乘 [确认: https://github.com/sustainable-computing-io/kepler])。**绝不 fork 任何上游;MVP 阶段这些适配器只需要接口定义 + 一个参考实现,但接口必须从第一天就在。**

**Q3.4 — 大屏又一个信息孤岛?**
惯例是 Grafana dashboard JSON 随仓发布(carbon-aware-keda-operator 的 `hack/grafana/` [确认: https://github.com/Azure/carbon-aware-keda-operator])。自研大屏可以作为竞赛演示层存在,但数据必须同时以 Prometheus 指标暴露,让企业侧用自己的 Grafana 消费。

### 2.4 竞品/相邻开源项目(P4)

**Q4.1 — 哪些轮子已经存在,你打算重造哪个?**
已存在且必须复用而非重造:碳信号 Provider 抽象(GSF Carbon Aware SDK,MIT)、碳强度→ConfigMap 的 K8s 契约(Azure exporter)、碳感知 KEDA 上限调制(Azure operator)、能耗测量(Zeus/ML.ENERGY [确认: https://ml.energy/zeus/])、微电网协同仿真(Vessim:Actor/Signal/SiL 抽象,MIT [确认: https://github.com/dos-group/vessim])、模型路由框架(RouteLLM,Apache-2.0 [确认: https://github.com/lm-sys/RouteLLM])。**GreenPulse 的自研边界 = 多时间尺度滚动决策引擎 + 任务画像 + 统一评测协议 + 运营商信号整合;其余全部作为依赖或形状参照。**

**Q4.2 — 和 GAR/DynamoLLM/CASPER 摆在一张桌上,你的差异化一句话是什么?**
建议的答案:"**它们各管一个旋钮、站在租户/云商视角;GreenPulse 站在数据中心运营商视角,把园区级绿电信号(含分时 PUE 与功率预算)和从作业到 token 的多级旋钮统一在一个滚动编排器和一个 SCI 口径里。**" 这句话必须写进 README 首屏,并配"相关工作对照表"(逐项:旋钮/视角/信号/我们的差异)。没有这张表,技术评委的默认假设就是"学生队重做了 CarbonScaler"。

### 2.5 运维/SRE·合规(P5)

**Q5.1 — 碳信号断了/预测错了,调度器做什么?**
README 未回答。姊妹项目的核心规则(真实数据源不可用必须报错,绝不静默替换合成数据)在这里的对应物是:**信号丢失时降级为 carbon-agnostic 模式并显式告警,绝不拿过期/编造的碳强度继续"绿色"调度**——后者会把假绿证据写进对外报告。完整失效矩阵见 [`DFR.md`](DFR.md)。

**Q5.2 — 业务方说"这周别给我玩碳了",有开关吗?**
carbon-aware-keda-operator 的 `ecoModeOff`(按时段/时长关闭碳感知)是生产必备的逃生门 [确认: https://github.com/Azure/carbon-aware-keda-operator]。裁定:进 MVP 配置。

**Q5.3 — 合成数据纪律?**
README 的能源侧数据(绿电/电价/碳强度)自称合成数据集;负载侧未声明来源,按 §5 第 3 条决定(Azure trace 派生或全合成)。无论哪种组合,继承姊妹项目 R3.2:每张图、每个数字标注 synthetic/real/derived-from-real;合成收益数字旁必须写"合成场景,非实测"。答辩场景下这条纪律的违约成本极高(企业教练一句"你这数据哪来的"就足以出局)。

---

## 3. 魔鬼代言人(Step 4:已检索、未被 README 讨论的证据)

1. **嵌入碳(embodied carbon)。** 低碳电网中嵌入碳占总碳 30%+;新卡小 batch 反而比旧卡多耗 28% 能量 [确认: https://hotcarbon.org/assets/2024/pdf/hotcarbon24-final3.pdf];EcoServe 证明"旧卡跑 decode/批量"总碳最高降 47% [确认: https://arxiv.org/abs/2502.05043]。GreenPulse 的任务画像里有 GPU 类型,但目标函数只算运行碳。**建议:MVP 至少在核算里报告嵌入碳摊销(LLMCarbon 的边界 [确认: https://arxiv.org/abs/2309.14393]),旋钮可以后置。**
2. **水足迹。** 北方园区(乌兰察布/怀来)水资源敏感;SLIT 已把碳+水+电价+QoS 做成四目标 [确认: https://arxiv.org/abs/2505.23554]。目标函数的 β 项旁边留一个 WUE 扩展位,答辩时这是免费加分项。
3. **24/7 CFE 逐小时匹配。** 绿色声明的国际趋势是逐小时匹配(EnergyTag/Google;CFE 逼近 100% 时成本急升,90-95% 是甜点区)[确认: https://arxiv.org/abs/2403.07876]。"绿色 Token"的定义应锚定逐小时匹配口径——年度净匹配的 token 不应标绿。这直接服务于世纪互联乌兰察布 80%→100% 的叙事。
4. **预测不确定性。** 碳/绿电预测误差直接侵蚀调度收益 [确认: https://arxiv.org/abs/2407.02390];README 的感知模块输出里有"预测置信度"字段,但调度目标函数没有消费它。建议:滚动重规划频率与置信度挂钩,或在 MILP 里用鲁棒/场景法,并在评测里报告"预测误差敏感性"。

---

## 4. OPEN RISKS(攻防中无人能答、查证也无法关闭的问题)

| # | 问题 | 状态 |
|---|---|---|
| OR-1 | 世纪互联赛道命题原文、交付物要求、评审标准、关键日期 | **信息缺口,PLAN P0-X2 强制关闭** |
| OR-2 | 中国目标电网的公开分时碳强度/绿电数据,粒度与许可 | RISKS R1,Stage S 期间探明 |
| OR-3 | 大赛是否要求/允许提交代码仓库,是否有开源许可要求 | 随 OR-1 关闭 |
| OR-4 | 仓库当前是否已有代码(桥接离线,只见 README) | 桥接恢复后核实 |

---

## 5. 评审结论对 PLAN 的直接输入

1. MVP 四层:仿真环境(含分时 PUE、储能、合成绿电曲线,SiL 接口参照 Vessim)→ 调度器(滚动 MILP + token 路由旋钮)→ 评测协议(三级基线 + oracle + 双口径 + SLO 代价)→ 演示层(大屏 + Grafana JSON)。
2. 上限分析先行:oracle 节碳上限是 Stage S 的出口判据之一;上限 <15% 时触发叙事重构(RISKS R2)。
3. 负载不用纯合成:Azure LLM 推理生产 trace 已开源(Splitwise 团队)[确认: https://github.com/Azure/AzurePublicDataset],MVP 的任务队列应从中派生,合成部分明确标注。
4. 执行层适配器只做接口 + 单参考实现;宿主原生扩展点清单固定(Kueue AdmissionCheck / KEDA external scaler / scheduler Score 插件 / llm-d EPP scorer / vLLM scheduler_cls)。
5. 指标北极星:gCO2/token,声明为 SCI(ISO/IEC 21031)兼容,功能单元 = token [确认: https://www.iso.org/standard/86612.html];J/token 用 Zeus 系工具测量口径。

---

*证据库:本报告所有 URL 均由三个独立检索代理于 2026-07-29 核实存在;论文结论的转述以 arXiv/会议页为准。未能核实的内容(世纪互联赛道命题细节)已明确标注为信息缺口而非事实。*
