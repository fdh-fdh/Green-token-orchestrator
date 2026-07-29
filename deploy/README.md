# deploy/ — 执行层适配器(Stage A,接口定义阶段)

按 [`docs/PLAN.md`](../docs/PLAN.md) A-X1(2026-07-29 日历压缩版):本届交付**接口定义 + 架构图**,
参考实现与 kind 集群移出本届。适配器插入点(接口在 `greenpulse/executors/base.py`):

| 宿主 | 插入点 | 状态 |
|---|---|---|
| Kueue | AdmissionCheck | 接口已定义,实现移出本届 |
| KEDA | external scaler | 接口已定义,实现移出本届 |
| kube-scheduler | Score 插件 | 接口已定义,实现移出本届 |
| llm-d | EPP scorer | 接口已定义,实现移出本届 |
| vLLM | scheduler_cls | 接口已定义,实现移出本届 |

约束(ENGINEERING_RULES R1.4):policy 层不感知具体宿主;对外暴露一律走中性介质
(Prometheus 指标前缀 `gto_`、ConfigMap 契约、OpenAI 兼容 API)。
失效契约见 [`docs/DFR.md`](../docs/DFR.md) DEP-7。
