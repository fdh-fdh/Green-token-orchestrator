"""仿真域模型:任务、Pod、状态、决策记录。

决策记录必含字段(PLAN A-X3,缺任一字段即评审不通过):
任务、动作、时窗、决策时刻信号快照、目标函数各项贡献值、被拒的替代动作及其目标值。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskKind(str, Enum):
    RIGID = "rigid"            # 在线推理等:SLA 保护,到达即须服务,不可时移
    SEMI_ELASTIC = "semi"      # 批量推理/评测:小时级可移
    ELASTIC = "elastic"        # 训练/微调/离线推理:日级可移


@dataclass(frozen=True)
class Task:
    name: str
    kind: TaskKind
    gpus: int
    duration_minutes: int
    arrival: datetime
    deadline: datetime
    interruptible: bool        # MVP 中仅作布尔约束(PLAN §7):不可中断任务不得被重排出已分配窗口
    tokens_expected: float     # 合成画像:预计 token 产量


@dataclass
class Pod:
    name: str
    gpu_count: int
    power_budget_kw: float
    gpus_free: int = -1

    def __post_init__(self) -> None:
        if self.gpus_free < 0:
            self.gpus_free = self.gpu_count


class Action(str, Enum):
    START = "start"
    DELAY = "delay"


@dataclass(frozen=True)
class Decision:
    """调度器输出:对单个任务的一个动作。"""

    task_name: str
    action: Action
    pod_name: str | None = None       # START 时必填


@dataclass(frozen=True)
class DecisionRecord:
    """结构化决策记录(A-X3 必含字段全集)。缺任一字段即不通过——字段不允许为 None 以外的缺省。"""

    task: str
    action: str
    window_start: str                  # ISO;DELAY 时为下一评估时刻
    window_end: str
    signal_snapshot: dict              # 决策时刻:碳强度(带口径)、电价、绿电预报、degraded 标志
    objective_contributions: dict      # 目标函数各项贡献值(alpha_cost/beta_carbon/…)
    rejected_alternatives: list        # [{action, pod, objective_total}] 被拒动作及其目标值
    degraded: bool                     # 信号断供降级标志(DFR 铁律推论 2:降级必须可观测)
    oracle: bool                       # oracle 上界运行标志(R3.2:上界数字不得当产品收益)


@dataclass
class SimState:
    """调度器可见的世界状态(不含未来——未来只能经 SignalView 的受控通道)。"""

    now: datetime
    queue: list[Task] = field(default_factory=list)
    running: dict[str, tuple[Task, str, datetime]] = field(default_factory=dict)
    # task_name -> (task, pod_name, end_time)
    pods: dict[str, Pod] = field(default_factory=dict)
