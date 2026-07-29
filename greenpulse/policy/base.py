"""调度器接口与注册表。

共同不变量(所有策略,包括基线,无一豁免):
- 刚性任务到达即启动(SLA 保底铁律)——任何策略不得为节能延迟刚性任务;
- 弹性任务到达最迟启动点(deadline - duration)时强制启动(Deadline 约束);
- 信号降级(view.degraded)时退回 carbon-agnostic 行为(DFR 铁律推论 2)。
这些不变量实现于本基类,子类只回答一个问题:这个可延迟任务,现在启动还是再等?
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import timedelta

from ..config import Config
from ..errors import ConfigError
from ..sim.model import Action, Decision, SimState, Task, TaskKind
from ..sim.view import SignalView


class Scheduler(ABC):
    name: str = "abstract"

    def __init__(self, config: Config):
        self.cfg = config

    # -- 子类唯一需要实现的钩子 --------------------------------------------
    @abstractmethod
    def want_start(self, task: Task, state: SimState, view: SignalView) -> bool:
        """可延迟任务在当前时刻是否应该启动(不含刚性/强制启动逻辑)。"""

    # -- 共同不变量 ----------------------------------------------------------
    def latest_start(self, task: Task):
        return task.deadline - timedelta(minutes=task.duration_minutes)

    def must_start(self, task: Task, state: SimState) -> bool:
        return state.now >= self.latest_start(task)

    def first_fit(self, task: Task, state: SimState) -> str | None:
        for pod in state.pods.values():
            if pod.gpus_free >= task.gpus:
                return pod.name
        return None

    def decide(self, state: SimState, view: SignalView) -> list[Decision]:
        decisions: list[Decision] = []
        free = {name: pod.gpus_free for name, pod in state.pods.items()}

        def fit(task: Task) -> str | None:
            for name, gpus in free.items():
                if gpus >= task.gpus:
                    return name
            return None

        for task in state.queue:
            pod = fit(task)
            rigid = task.kind == TaskKind.RIGID
            forced = self.must_start(task, state)
            degraded_fallback = view.degraded  # 信号断供 → 一律 carbon-agnostic 行为
            if pod is not None and (
                rigid or forced or degraded_fallback or self.want_start(task, state, view)
            ):
                decisions.append(Decision(task_name=task.name, action=Action.START, pod_name=pod))
                free[pod] -= task.gpus
            else:
                decisions.append(Decision(task_name=task.name, action=Action.DELAY))
        return decisions


_POLICIES: dict[str, Callable[[Config], Scheduler]] = {}


def register_policy(name: str):
    def deco(cls):
        cls.name = name
        _POLICIES[name] = cls
        return cls

    return deco


def registered_policies() -> list[str]:
    return sorted(_POLICIES)


def create_scheduler(name: str, config: Config) -> Scheduler:
    """未知策略名在构造之前拒绝并列出全部注册名(与 DEP-6.2 同型)。"""
    if name not in _POLICIES:
        raise ConfigError(f"未知调度策略 {name!r};已注册: {registered_policies()}")
    return _POLICIES[name](config)
