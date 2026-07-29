"""执行层适配器接口定义(PLAN A-X1,2026-07-29 日历压缩版:接口 + 架构图,实现移出本届)。

约束(R1.4):policy 层不感知具体宿主;适配器是唯一允许出现宿主概念的地方。
失效契约见 docs/DFR.md DEP-7:K8s API 不可达时报错并保持现状(不振荡);
ConfigMap 信号过期同 DEP-1.2 降级;ecoModeOff 时行为与 carbon-agnostic 基线 bit 级一致。

插入点对照(deploy/README.md 有架构图指引):
    Kueue AdmissionCheck   → AdmissionCheckAdapter
    KEDA external scaler   → ExternalScalerAdapter
    kube-scheduler Score   → SchedulerScorePlugin
    llm-d EPP scorer /
    vLLM scheduler_cls     → InferenceRouterScorer
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class AdmissionCheckAdapter(ABC):
    """Kueue AdmissionCheck:批处理任务是否此刻准入(否则排队等待更绿窗口)。"""

    @abstractmethod
    def should_admit(self, workload_name: str, gpus: int, duration_minutes: int,
                     deadline: datetime) -> bool: ...


class ExternalScalerAdapter(ABC):
    """KEDA external scaler:按碳/绿电信号给出目标副本数(0 = 暂停弹性负载)。"""

    @abstractmethod
    def desired_replicas(self, deployment: str, min_replicas: int, max_replicas: int) -> int: ...


class SchedulerScorePlugin(ABC):
    """kube-scheduler Score 插件:按节点/站点碳效为放置打分(0-100)。"""

    @abstractmethod
    def score(self, pod_name: str, node_name: str) -> int: ...


class InferenceRouterScorer(ABC):
    """llm-d EPP scorer / vLLM scheduler_cls:token 级路由打分(O-X2 最小可信版的落点)。"""

    @abstractmethod
    def score_backend(self, request_id: str, backend: str, model_tier: str) -> float: ...
