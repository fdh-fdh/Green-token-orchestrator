"""执行层适配器接口(Stage A:本届只交付接口定义,参考实现移出本届 — PLAN A-X1)。"""

from .base import (  # noqa: F401
    AdmissionCheckAdapter,
    ExternalScalerAdapter,
    InferenceRouterScorer,
    SchedulerScorePlugin,
)
