"""五基线全家桶 + 碳感知调度器(MVP 启发式版)。

基线集(R3.5,FIFO 单基线是稻草人对照——IDEA_REVIEW Q2.3 裁定):
    carbon_agnostic  性能最优:有资源即启动(对照组,也是 ecoModeOff 的行为定义)
    best_static      最优静态:弹性任务固定运行窗
    price_only       只看电价(因果历史分位数,不偷看未来)
    carbon_only      只看碳强度(同上)
    oracle           事后完美预测上界——产出数字永远是 "oracle 上界",不是产品收益(R3.2)
碳感知调度器 carbon_aware 是被评测对象;其相对基线的收益必须按 R3.1 四件套报告。
"""

from __future__ import annotations

from datetime import timedelta

from ..config import Config
from ..errors import GreenPulseError
from ..sim.model import SimState, Task
from ..sim.view import SignalView
from .base import Scheduler, register_policy


def _history_quantile_ok(
    view: SignalView, site_id: str, sim_start, kind: str, quantile: float
) -> bool:
    """当前值是否低于因果历史(sim_start → now)的给定分位。只用过去,不越 DEP-4.4。"""
    getter = view.carbon_series if kind == "carbon" else view.price_series
    series = getter(site_id, sim_start, view.now)
    if series is None:  # 信号断供:降级由基类处理,这里保守返回 True(即刻启动)
        return True
    values = sorted(series.values)
    cut = values[max(0, int(len(values) * quantile) - 1)]
    return series.values[-1] <= cut


@register_policy("carbon_agnostic")
class CarbonAgnosticScheduler(Scheduler):
    """性能最优基线:有资源即启动。ecoModeOff 的行为等价物(DEP-7.3)。"""

    def want_start(self, task: Task, state: SimState, view: SignalView) -> bool:
        return True


@register_policy("best_static")
class BestStaticScheduler(Scheduler):
    """最优静态基线:弹性任务只在固定日内窗运行(窗参数来自 config,不扫描未来)。"""

    def want_start(self, task: Task, state: SimState, view: SignalView) -> bool:
        h = view.now.hour
        start_h = self.cfg.scheduler.static_window_start_hour
        end_h = (start_h + self.cfg.scheduler.static_window_hours) % 24
        if start_h <= end_h:
            return start_h <= h < end_h
        return h >= start_h or h < end_h


@register_policy("price_only")
class PriceOnlyScheduler(Scheduler):
    def __init__(self, config: Config):
        super().__init__(config)
        self.sim_start = None  # 引擎注入

    def want_start(self, task: Task, state: SimState, view: SignalView) -> bool:
        return _history_quantile_ok(
            view, self.cfg.datacenter.site_id, self.sim_start, "price",
            self.cfg.scheduler.defer_quantile,
        )


@register_policy("carbon_only")
class CarbonOnlyScheduler(Scheduler):
    def __init__(self, config: Config):
        super().__init__(config)
        self.sim_start = None

    def want_start(self, task: Task, state: SimState, view: SignalView) -> bool:
        return _history_quantile_ok(
            view, self.cfg.datacenter.site_id, self.sim_start, "carbon",
            self.cfg.scheduler.defer_quantile,
        )


@register_policy("oracle")
class OracleScheduler(Scheduler):
    """oracle 上界:看到未来已实现碳强度,把弹性任务放到可行窗内最低碳时段。

    仅与 oracle=True 的 SignalView 配合;其结果是上限分析(S-X3)的输入,
    出现在任何材料中必须带 "oracle 上界" 前缀,禁止当作产品收益(R3.2/R8)。
    """

    def want_start(self, task: Task, state: SimState, view: SignalView) -> bool:
        site = self.cfg.datacenter.site_id
        dur = timedelta(minutes=task.duration_minutes)
        future = view.carbon_future(site, view.now, self.latest_start(task) + dur)
        step = timedelta(minutes=self.cfg.time.resolution_minutes)
        n_dur = max(1, int(dur / step))
        # 当前启动窗的平均碳强度 vs 未来任一可行启动点:当前已是最优才启动
        windows = [
            sum(future.values[i : i + n_dur]) / n_dur
            for i in range(0, max(1, len(future.values) - n_dur + 1))
        ]
        return windows[0] <= min(windows)


@register_policy("carbon_aware")
class CarbonAwareScheduler(Scheduler):
    """GreenPulse 碳感知调度器(MVP 启发式):绿电预报驱动的等待/启动决策。

    ecoModeOff 开关(O-X5):开启时行为与 carbon_agnostic 基线 bit 级一致。
    Stage O 将替换为滚动时域 MILP/启发式的加权多目标版本(O-X1)。
    """

    def want_start(self, task: Task, state: SimState, view: SignalView) -> bool:
        if self.cfg.scheduler.eco_mode_off:
            return True
        site = self.cfg.datacenter.site_id
        slack = self.latest_start(task) - view.now
        horizon_end = min(
            view.now + slack,
            view.now + timedelta(hours=self.cfg.time.horizon_hours),
        )
        if horizon_end <= view.now:
            return True
        try:
            fc = view.green_power_forecast(site, view.now, horizon_end)
        except GreenPulseError:
            return True  # 预报不可用/过期:显式降级为即刻启动(carbon-agnostic 行为)
        if fc is None:
            return True
        current_kw = fc.series.values[0]
        best_future_kw = max(fc.series.values)
        margin = self.cfg.scheduler.green_improvement_margin
        # 未来绿电显著更高且还有等待余量 → 等;否则现在就跑
        return best_future_kw <= current_kw * (1.0 + margin)
