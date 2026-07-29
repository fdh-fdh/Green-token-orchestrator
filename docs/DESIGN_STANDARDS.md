# GreenPulse 设计标准与对标调研

2026-07-29 完成的三路联网调研(评审方法论 / 论文 SOTA / 标杆仓库)的结论记录,用于校准:(a) 竞赛获奖作品怎么构建;(b) 碳感知调度与 LLM 推理编排的学术/工程水位线;(c) 世纪互联工程文化下"像样"意味着什么。**本文件回答"业界怎么做";"我们必须怎么做"在 [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md);"何时做"在 [`PLAN.md`](PLAN.md)。**

> **状态词汇(继承姊妹项目,含双向校验规则)**:**DONE** = 今天在树里验证过;**PARTIAL** = 机制存在但不覆盖其声称(门禁决策中视同未做);**PLANNED** = 未建;**SKIPPED** = 有意不建,附理由。状态列必须双向复核——假 DONE 让人不再看,假 PLANNED 让人重做已完成的事,两者都是"状态列不再追踪树"。本项目零代码起步,今天几乎所有行都是 PLANNED/SKIPPED;**每个 Gate 评审时逐行重核**。

---

## 1. 竞赛评审对标

### 1.1 本大赛已确认的机制

企业真实场景命题、1-3 人学生队、认领命题→提交初步思路→企业教练带教出案例、奖励为校招/实习 Offer [确认: https://diidea.pku.edu.cn/web/programs_details_a.php?id=28 ; https://www.aitop100.cn/infomation/details/34142.html]。**世纪互联赛道的命题原文与评分细则未获取(PLAN P0-X2 的 48 小时任务)。** 其他企业命题风格(蔚来/瑞幸/去哪儿)显示大赛偏"业务场景 AI 应用 + 可展示案例" [推断]。推论:**答辩叙事、可演示性、技术深度三者同等重要;为工程师评审(企业教练来自世纪互联)保留完整技术证据链。**

### 1.2 获奖仓库的可复制配方(GSF CarbonHack 实证)

CarbonHack 22 冠军 Lowcarb 的配方,经拆仓核实 [确认: https://github.com/birnbaum/flwr-lowcarb]:

1. **宿主框架原生插件接口**(Flower Strategy 接口,不 fork 宿主);
2. **独立 SDK 适配层**(carbon_sdk_client/ 单独目录隔离外部依赖);
3. **`backtest/` 回测框架**——用历史数据回放出"-13% 碳排、零精度损失"这一个诚实数字,这是它赢的证据链;
4. 一个有说服力的领域 demo + 可跑通的教程 notebook。

同届亚军(Zeus 碳感知训练,-24% 碳/+3% 时间)与 Most Polished(GreenCourier,K8s scheduler framework 自定义调度器 + 压测工具与结果直接入仓)印证同一模式 [确认: https://greensoftware.foundation/articles/carbonhack22-a-big-leap-in-carbon-aware-computing/ ; https://github.com/thandayuthapani/GreenCourier]。CarbonHack 24 的评判风向进一步转向**可审计、可复算的测算管线**(Impact Framework manifest 生态)[确认: https://greensoftware.foundation/articles/carbon-hack-24-expanding-the-ecosystem-of-software-measurement/]。

**采纳(全部 PLANNED,Gate 评审时核)**:README 顶部一句话价值主张+架构图+从零复现步骤;钉死依赖;Makefile 统一入口(`make demo` 起 kind 集群);`backtest/`+`eval/` 给出量化数字与出图脚本;Grafana dashboard JSON 随仓发布;教程 notebook;MIT/Apache-2.0。

### 1.3 通用获奖仓库惯例(姊妹项目已对标 Kaggle/DrivenData/Zindi,结论直接继承)

精确 pin 依赖、固定 seed 与确定性声明、硬件/OS/运行时长披露、prepare/run/eval 分离入口、指标带容差、每个对外数字可溯源。不再重复论证,执行点在 [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) §2。

---

## 2. 领域水位线(必须清过的杆)

### 2.1 五个旋钮的文献水位(全部核实过一手来源)

> **"关键数字"列仅用于校准水位线:各数字出自不同电网、负载、口径与 SLO,互不可比,且禁止进入任何对外对照表(ENGINEERING_RULES R3.3;对外对照表只对比机制与视角)。**

| 旋钮 | 代表工作 | 关键数字 | 我们的位置 |
|---|---|---|---|
| when(时移) | GreenSlot (SC'11);Google VCC (生产);CarbonScaler (SIGMETRICS'24, arXiv 2023);"Let's Wait Awhile" (Middleware'21) | 节碳 51%(vs carbon-agnostic);对最优静态仅 +8% | MVP 主体;**无新颖性可言,必须做但不要吹** |
| where(空间路由) | CASPER (IGSC'23);SLIT (2025,碳+水四目标) | 节碳最高 70%,零时延退化 | MVP 含多 Pod 版本;多园区是扩展 |
| how(执行方式) | DynamoLLM (HPCA'25);Chase;Perseus (SOSP'24);Zeus (NSDI'23) | 能耗 -53%/碳 -38%;自动调优节能 40%+ | SKIPPED(MVP)——需要真 GPU;记录为扩展路线 |
| which-model(路由) | GAR (2026);RouteLLM (ICLR'25);FrugalGPT;Clover (SC'23) | 0.712 vs 2.750 gCO2/请求(-74%),达 oracle 97% | **MVP 的 token 级旋钮,PLAN O-X2** |
| how-many-tokens(生成控制) | Sprout (EMNLP'24);TALE (ACL Findings'25) | 节碳 40%+ 保质量 | 扩展路线;答辩中引用以兑现 "token" 命名 |

上限与诚实性护栏:EuroSys'24(123 区域,时空平移上限有限、简单策略拿走大部分收益)[确认: https://arxiv.org/abs/2306.06502];e-Energy'24(平均/边际 55.4% 区域负相关,单口径结论可翻转)[确认: https://dl.acm.org/doi/10.1145/3632775.3661953];嵌入碳占比可达 30%+(HotCarbon'24)、EcoServe 旧卡策略总碳 -47%;预测不确定性侵蚀收益(arXiv 2407.02390)。**全部已转化为 ENGINEERING_RULES §3 与 PLAN 的判据。**

### 2.2 公认评估协议(照此设计 `docs/EVAL_PROTOCOL.md`)

- **基线**:carbon-agnostic 性能最优、最优静态、单信号策略(Price-only/Carbon-only)、oracle 上界。强论文全家桶如此,缺一即被评审补刀。
- **指标**:gCO2/token(SCI/ISO-IEC-21031 兼容,功能单元=token,禁止 offset 冲减 [确认: https://www.iso.org/standard/86612.html]);J/token(Zeus/ML.ENERGY 测量口径);SLO 达成率(p95/p99);等 QoS 节碳%;绿电消纳率;峰值功率。
- **数据**:Azure LLM 推理生产 trace(Splitwise 开源)派生负载 [确认:仓库存在,https://github.com/Azure/AzurePublicDataset ;**数据条款待核验,DATA_LICENSES 第 1 行,核验不过则按 PLAN S-E2 走全合成路径**];信号曲线版本化。
- **报告纪律**:碳降与 QoS 代价同表;双口径并列;报"达 oracle 的 x%"。

### 2.3 常见坑(评审会逐个检查的)

平均口径夸大节省;拿批量负载的节碳%外推在线负载;忽略嵌入碳导致"疯狂换新卡"伪最优;FLOPs 推算能耗(实测证明严重低估 [确认: https://arxiv.org/abs/2504.17674]);合成泊松流量替代真实双峰请求分布;忽略 PUE/水/电价耦合。每条在 [`IDEA_REVIEW.md`](IDEA_REVIEW.md) §2-3 有展开与出处。

---

## 3. 工程标准裁决表

| 主题 | 裁决 | 理由(证据) |
|---|---|---|
| 分层:signal / policy / executors / sim / eval / deploy | **PLANNED(P0-X1)** | 每层有形状参照:signal=GSF Carbon Aware SDK 的 DataSources+注册 [确认: https://github.com/Green-Software-Foundation/carbon-aware-sdk];policy=RouteLLM 的基类+注册表 [确认: https://github.com/lm-sys/RouteLLM];executors=llm-d EPP scorer / Kueue AdmissionCheck / KEDA external scaler / scheduler Score 插件 [确认: 各官方仓库];sim=Vessim 的 Actor/Signal/SiL [确认: https://github.com/dos-group/vessim];eval=RouteLLM benchmarks + Lowcarb backtest |
| policy 与 executor 的边界 | **PLANNED(接口先行)** | policy 只产出中性决策(分数/配额/准入/计划),永不直接碰基础设施;每个 executor 把决策翻译成宿主原生扩展点。**orchestrator 本体永不 fork 任何上游** |
| 信号传递介质 | **PLANNED** | Prometheus 指标(前缀 `gto_`,与 Kepler `kepler_` 可 PromQL 相乘)+ K8s ConfigMap 契约(兼容 Azure exporter 的格式即可直接复用其消费端生态)[确认: https://github.com/Azure/kubernetes-carbon-intensity-exporter] |
| mock-first Provider | **PLANNED(S-X1)** | static-json/合成 Provider 为一等公民,无外部账号可跑 demo 与 CI(Carbon Aware SDK `.Json` 源、KEDA operator mock 源的既有惯例) |
| 存储 | **PLANNED:文件优先(CSV/Parquet/SQLite 单文件)经薄接口** | 明文要求"不与数据库过拟合"。换 PostgreSQL/时序库不改调用方为验收;禁 SQL 方言/ORM 泄漏进业务代码(ENGINEERING_RULES R1.4) |
| 调度算法 | **PLANNED:滚动时域 MILP/启发式(HiGHS/OR-Tools)** | 上限研究:简单策略拿走大部分收益;RL 移出 MVP(IDEA_REVIEW Q2.6) |
| RL / 学习型调度器 | **SKIPPED(MVP)** | 同上;三人队工程量;不可解释性与 R1.6 冲突。Gate O 通过后可作为对照实验 |
| Hydra / 复杂配置框架 | **SKIPPED** | 单管线;姊妹项目同裁决(学习曲线+工作目录魔法,评审困惑) |
| MLflow / W&B | **SKIPPED** | 评审无法对账号复现;CSV 实验记录入 git(R3.4) |
| DVC | **SKIPPED** | 数据是合成生成器+一个公开 trace;下载脚本+校验和清单足够 |
| Docker / kind demo | **SKIPPED(本届,2026-07-29 日历压缩)** | 08-16 截止下移出本届;`make demo` = 本地仿真回放+可视化,无外部依赖(这本来就是 DFT 要求);kind 集群与适配器参考实现为 08-16 后回收项 |
| 大屏 | **PLANNED(升级为交付物本体)** | 交付物含"路演 Demo",大屏/时间线可视化是路演主体;仍只消费同一指标源,Grafana JSON 同时发布(A-X2);美化投入受 RISKS R6 Trigger 约束 |
| 双语言(Go executor + Python policy/sim) | **PLANNED,Python 先行** | AIBrix 的 Go 控制面+Python 运行时布局与 VNET 栈同构 [确认: https://github.com/vllm-project/aibrix];但 MVP 阶段只有 Python 是必须的,Go 适配器随 A-X1 的"恰好一个参考实现"决定 |
| 许可证 | **PLANNED:代码 MIT(P0-X1 已裁定,与 README 声明一致)** | 与 CNCF 生态(vLLM/llm-d/Kueue 均 Apache-2.0)兼容;**AGPL(electricitymaps-contrib)零 vendor**;NOTICE 汇总第三方声明。若大赛硬性条款另有许可要求,按 ENGINEERING_RULES §0 优先级让位并记录 |
| CI | **PLANNED(P0-X1)** | ruff+pytest 起步;覆盖率先测量后设门(棘轮);可移植性扫描;发布元数据测试 |
| 实验留痕 | **PLANNED(P0-X5)** | 姊妹项目机制直接移植,含"dirty 行不得进对外材料"的硬教训 |

---

## 4. 世纪互联工程文化画像(评审模拟的依据)

公开证据:GitHub org 21vianet——smarthaven(百万传感器/日均 10TB 的 DC 管理:Flink on K8s、PyTorch on K8s、Prometheus+Grafana、GitOps、K8s CRD;设计原则"开源、基础设施即代码、云原生、技术中立",后解耦为 Meta42 五项目)[确认: https://github.com/21vianet/smarthaven];主要语言 Go/Python/JS,许可 MIT/Apache-2.0 [确认: https://github.com/21Vianet];专职电力交易职能(绿电采购/现货)[推断:调研代理报告招聘信息含电力交易员岗位,所存 URL 为 Java 岗列表页不能作证;P0 补抓 JD 一手证据];运营 Azure 中国主权云十余年(数据驻留/审计/变更管理的流程肌肉)[确认: https://learn.microsoft.com/zh-cn/azure/china/overview-operations]。

推论(评审时的默认标尺,[推断] 标注):新系统必须能以标准接口(Prometheus/CRD/ConfigMap)挂进现有栈而非孤岛;"技术中立、可插拔"会被当作品味问题而不仅是加分项;数据口径与合规敏感度极高;演示数据的真假会被第一个问到。

---

## 5. 来源

评审方法论:[stanford-oval/storm](https://github.com/stanford-oval/storm) · [STORM 论文](https://arxiv.org/abs/2402.14207) · [Co-STORM 论文](https://arxiv.org/abs/2408.15232)

论文(全部核实一手来源,完整列表与逐篇设计启示见 IDEA_REVIEW 及其引用):[Google VCC](https://arxiv.org/abs/2106.11750) · [Let's Wait Awhile](https://arxiv.org/abs/2110.13234) · [CarbonScaler](https://arxiv.org/abs/2302.08681) · [Ecovisor](https://arxiv.org/abs/2210.04951) · [Carbon Explorer](https://arxiv.org/abs/2201.10036) · [CASPER](https://arxiv.org/abs/2403.14792) · [Chase](https://arxiv.org/abs/2303.02508) · [GreenSlot](https://dl.acm.org/doi/abs/10.1145/2063384.2063411) · [上限研究](https://arxiv.org/abs/2306.06502) · [DynamoLLM](https://arxiv.org/abs/2408.00741) · [Sprout](https://arxiv.org/abs/2403.12900) · [Perseus](https://arxiv.org/abs/2312.06902) · [Zeus](https://arxiv.org/abs/2208.06102) · [Splitwise](https://arxiv.org/abs/2311.18677) · [Mélange](https://arxiv.org/abs/2404.14527) · [Clover](https://arxiv.org/abs/2304.09781) · [LLMCarbon](https://arxiv.org/abs/2309.14393) · [EcoServe](https://arxiv.org/abs/2502.05043) · [SLIT](https://arxiv.org/abs/2505.23554) · [GAR](https://arxiv.org/abs/2605.11603) · [HotCarbon'24 GPU 代际](https://hotcarbon.org/assets/2024/pdf/hotcarbon24-final3.pdf) · [FrugalGPT](https://arxiv.org/abs/2305.05176) · [RouteLLM](https://arxiv.org/abs/2406.18665) · [能耗实测](https://arxiv.org/abs/2504.17674) · [From Words to Watts](https://arxiv.org/abs/2310.03003) · [TALE](https://arxiv.org/abs/2412.18547) · [平均vs边际](https://dl.acm.org/doi/10.1145/3632775.3661953) · [24/7 CFE](https://arxiv.org/abs/2403.07876) · [ML.ENERGY](https://arxiv.org/abs/2505.06371) · [MLPerf Power](https://arxiv.org/abs/2410.12032) · [不确定性](https://arxiv.org/abs/2407.02390)

仓库:[carbon-aware-sdk](https://github.com/Green-Software-Foundation/carbon-aware-sdk) · [carbon-aware-keda-operator](https://github.com/Azure/carbon-aware-keda-operator) · [carbon-intensity-exporter](https://github.com/Azure/kubernetes-carbon-intensity-exporter) · [kube-green](https://github.com/kube-green/kube-green) · [Kepler](https://github.com/sustainable-computing-io/kepler) · [Scaphandre](https://github.com/hubblo-org/scaphandre) · [CodeCarbon](https://github.com/mlco2/codecarbon) · [vLLM 插件/调度扩展](https://docs.vllm.ai/en/latest/design/plugin_system/) · [llm-d](https://github.com/llm-d/llm-d) · [llm-d-inference-scheduler](https://github.com/llm-d/llm-d-inference-scheduler) · [AIBrix](https://github.com/vllm-project/aibrix) · [LiteLLM routing](https://docs.litellm.ai/docs/routing) · [RouteLLM](https://github.com/lm-sys/RouteLLM) · [KServe](https://github.com/kserve/kserve) · [scheduler-plugins](https://github.com/kubernetes-sigs/scheduler-plugins) · [KEDA external scaler](https://keda.sh/docs/latest/concepts/external-scalers/) · [Volcano](https://github.com/volcano-sh/volcano) · [Kueue](https://github.com/kubernetes-sigs/kueue) · [Lowcarb](https://github.com/birnbaum/flwr-lowcarb) · [GreenCourier](https://github.com/thandayuthapani/GreenCourier) · [Vessim](https://github.com/dos-group/vessim) · [Impact Framework](https://github.com/Green-Software-Foundation/if) · [Azure LLM trace](https://github.com/Azure/AzurePublicDataset) · [21vianet org](https://github.com/21Vianet)

大赛与世纪互联:[DIIDEA 公告](https://diidea.pku.edu.cn/web/programs_details_a.php?id=28) · [AITOP100 报道](https://www.aitop100.cn/infomation/details/34142.html) · [VNET 环境页](https://www.vnet.com/environment.html) · [10GW 绿色直流](https://www.vnet.com/portal/article/index/cid/14/id/1031.html) · [绿电采购](https://www.vnet.com/portal/article/index/cid/14/id/868.html) · [算电协同(国家数据局)](https://www.nda.gov.cn/sjj/swdt/sjdt/0318/20250318212051776584737_pc.html)
