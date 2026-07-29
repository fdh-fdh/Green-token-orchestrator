# 数据与依赖许可记录

GreenPulse。本文件是数据源、外部数据集与关键上游依赖的**逐源许可记录**:来源、条款、署名要求、使用边界、消费模块。对外材料引用许可信息时从本文件抄录,不得各自转述。

**核验状态说明(诚实起见,分三档)**:

- **已核验(2026-07-29)** — 由本次调研代理直接从发布方页面/仓库读取;
- **待核验** — 有较强间接证据但未读到条款原文,P0-X4 期间必须补核;
- **未探明** — 只知道可能存在,P0-X4 的探源对象。

许可会变。每次 Gate 评审与材料冻结前重核验并更新本头部日期。

## 仓库 LICENSE 的边界

README 声明 MIT;LICENSE 文件本身待 P0-X1 落地。它只覆盖**本仓库源代码**,对下列任何数据集与上游依赖不授予任何权利;再分发数据、派生表或图,须在 MIT 之外满足对应源的条款。

## 总表

| # | 源/依赖 | 用途 | 许可 | 核验状态 | 使用边界要点 |
|---|---|---|---|---|---|
| 1 | Azure Public Dataset(LLM 推理 trace) | 派生评测负载 | 仓库存在已核验;**数据条款待核验** | 待核验 | 派生脚本入库、原始 trace 不入库;引用其论文(Splitwise, ISCA'24) |
| 2 | Electricity Maps API | (可选)碳强度信号 | 数据受商业条款;**contrib 仓库 AGPL-3.0** | 已核验(AGPL 部分) | **代码零 vendor;数据快照零入库**;仅 API 边界调用;中国区粒度粗(RISKS R1) |
| 3 | WattTime API | (可选)边际碳强度 | 客户端 MIT;**数据受单独商业授权** | 已核验(客户端) | 不覆盖中国大陆;数据快照零入库 |
| 4 | 中国省级电网分时数据/绿电交易公开数据 | 目标区域信号 | — | **未探明(P0-X4)** | 逐源记录粒度、许可、样例;拉不到或条款不清 → 弃用该源,合成兜底(RISKS R9 预案) |
| 5 | Open-Meteo(天气,用于合成曲线标定,可选) | 合成风光出力标定 | 数据 CC BY 4.0;免费档**非商业限定** | **待核验**(姊妹项目 2026-07-26 读过条款页原文,可作佐证;按本项目规则"转述他人核查结论=待核实",P0-X4 重核) | 竞赛参赛是否算非商业未定——姊妹项目同款未决问题;若使用,先问组织方或换源 |
| 6 | 合成生成器(本项目) | MVP 主数据 | 仓库 MIT | n/a | 合规义务反向:所有产物带 `synthetic` 溯源标记(DFR DEP-3.2),对外数字标注"合成场景" |
| 7 | GSF Carbon Aware SDK | 形状参照/可选依赖 | MIT | 已核验 | — |
| 8 | carbon-aware-keda-operator / carbon-intensity-exporter | ConfigMap 契约参照 | MIT | 已核验 | — |
| 9 | Kepler / Scaphandre / Zeus | 能耗测量口径 | Apache-2.0 | 已核验 | — |
| 10 | RouteLLM / vLLM / llm-d / AIBrix / Kueue / KEDA / Volcano / scheduler-plugins / KServe | 路由与执行层依赖/扩展点 | Apache-2.0 | 已核验 | 派生插件代码保留 license header;KEDA proto 可 vendor(Apache-2.0) |
| 11 | Vessim / Lowcarb / CodeCarbon / Impact Framework | 仿真与核算形状参照 | MIT | 已核验 | — |
| 12 | HiGHS / OR-Tools(求解器,二选一) | MILP 求解 | MIT / Apache-2.0 | 待核验(版本级确认) | — |
| 13 | LiteLLM(如用作网关) | OpenAI 兼容路由 | 仓库含 `enterprise/` 商业目录 | 已核验(存在商业目录) | 仅作依赖调用;不 vendor、不深改 |

## 三条红线(从总表中提级,评审必查)

1. **AGPL 隔离**:electricitymaps-contrib 的任何代码不进仓库(包括"参考着抄"的 parser)。走 API 就不触发 AGPL;抄代码就触发。
2. **数据许可 ≠ 代码许可**:WattTime/Electricity Maps 客户端是 MIT,不代表拉下来的数据可以入库或再分发。CI 与 demo 必须在 mock/static-json Provider 上完整运行(ENGINEERING_RULES §5、DFX)。
3. **企业内部数据隔离**:教练提供的任何非公开材料按 RISKS R10 处理——本地私有目录、`.gitignore` 全覆盖、仓库只放经确认可公开的合成标定版。

## 对外材料署名块(占位,数字与日期在使用时替换)

> **数据来源。** 〔二选一,按 P0-X4 核验结果:〕评测负载派生自 Azure Public Dataset LLM 推理 trace(Patel et al., *Splitwise*, ISCA 2024;派生脚本见 `eval/`,原始数据依其条款获取)〔或〕评测负载为合成任务流,统计特征标定方法见 `docs/EVAL_PROTOCOL.md`。碳强度/绿电/电价曲线为合成数据,标定方法见 `docs/EVAL_PROTOCOL.md`;〔如启用真实源:逐源列出并附条款与获取日期〕。能耗与碳核算口径:SCI(ISO/IEC 21031)兼容,功能单元 = token;测量方法参照 Zeus / ML.ENERGY。所有修改(重采样、聚合、派生指标)由作者完成。

## 交付前检查清单

- [ ] 重核验每一行许可;更新头部核验日期(日期不动 = 核验没发生,日期就是控制点)。
- [ ] P0-X4 的"未探明"行全部升级为已核验或已弃用,不留中间态。
- [ ] Azure trace 数据条款读原文并回填第 1 行。
- [ ] Open-Meteo 非商业问题:若用了,取得组织方书面口径或换源(§总表 5)。
- [ ] 仓库全树扫描:无 AGPL 代码、无受限数据快照、无内部材料。
- [ ] 每张图表标注 synthetic / real / derived-from-real(与 ENGINEERING_RULES R3.2 联动)。
- [ ] LICENSE 文件与 README 声明一致。
