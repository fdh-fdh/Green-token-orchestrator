"""故障注入测试 — DFR 矩阵落地(docs/DFR.md)。

已实现的所需行为 = PINNED(断言实测行为);尚未实现的 = strict xfail 挂账
(唯一自带过期机制的豁免形状:行为实现后 xfail 变 XPASS,strict 模式强制摘标)。
Gate 评审清点:PINNED 数 / xfail 数进 Gate 记录。
"""

from datetime import datetime, timedelta

import pytest
from conftest import T0

from greenpulse.errors import LookaheadError, SignalUnavailableError, StaleForecastError
from greenpulse.signal.base import (
    CarbonSignalProvider,
    GreenPowerForecastProvider,
    PriceProvider,
)
from greenpulse.sim.view import SignalView
from greenpulse.types import Forecast, Provenance, Series


class DownCarbonProvider(CarbonSignalProvider):
    """模拟 DEP-1.1:Provider 完全不可达。"""

    def carbon_series(self, site_id, start, end):
        raise SignalUnavailableError("模拟断供")


class StaleGreenProvider(GreenPowerForecastProvider):
    """模拟 DEP-1.2:返回的预报生成时间早于最大时龄。"""

    def __init__(self, resolution_minutes: int):
        self._res = resolution_minutes

    def green_power_forecast(self, site_id, issued_at, start, end):
        n = int((end - start) / timedelta(minutes=self._res)) + 1
        series = Series(
            timestamps=tuple(start + timedelta(minutes=self._res * i) for i in range(n)),
            values=tuple(1.0 for _ in range(n)),
            unit="kw", resolution_minutes=self._res,
            provenance=Provenance.SYNTHETIC, source="stale-test",
        )
        return Forecast(series=series, issued_at=issued_at - timedelta(hours=5))


class OkPriceProvider(PriceProvider):
    def price_series(self, site_id, start, end):
        res = 15
        n = int((end - start) / timedelta(minutes=res)) + 1
        return Series(
            timestamps=tuple(start + timedelta(minutes=res * i) for i in range(n)),
            values=tuple(0.5 for _ in range(n)),
            unit="per_kwh", resolution_minutes=res,
            provenance=Provenance.SYNTHETIC, source="ok-price",
        )


@pytest.fixture()
def degraded_view(cfg):
    view = SignalView(
        cfg,
        DownCarbonProvider(),
        StaleGreenProvider(cfg.time.resolution_minutes),
        OkPriceProvider(),
    )
    view.set_now(T0 + timedelta(hours=2))
    return view


# ---- PINNED:所需行为已实现并被断言 -----------------------------------------

def test_dep_1_1_outage_degrades_explicitly_never_fabricates(degraded_view):
    """DEP-1.1(PINNED):断供 → 返回 None + degraded 置位;绝不返回编造/旧曲线。"""
    result = degraded_view.carbon_series("vdc-01", T0, T0 + timedelta(hours=1))
    assert result is None
    assert degraded_view.degraded is True


def test_dep_1_2_stale_forecast_rejected_with_age(degraded_view):
    """DEP-1.2(PINNED):过期预报被拒,错误信息含预报时间戳与时龄阈值。"""
    with pytest.raises(StaleForecastError, match="时龄"):
        degraded_view.green_power_forecast("vdc-01", degraded_view.now, degraded_view.now)
    assert degraded_view.degraded is True


def test_dep_4_4_lookahead_rejected(cfg):
    """DEP-4.4(PINNED,最高优先):实时信号窗口终点 > 决策时刻即拒绝。"""
    from greenpulse.signal.base import create_provider

    view = SignalView(
        cfg,
        create_provider("carbon", "synthetic", cfg),
        create_provider("green_forecast", "synthetic", cfg),
        create_provider("price", "synthetic", cfg),
    )
    view.set_now(T0 + timedelta(hours=1))
    with pytest.raises(LookaheadError, match="前视泄漏"):
        view.carbon_series("vdc-01", T0, T0 + timedelta(hours=1, minutes=15))
    # oracle 通道在非 oracle 视图上同样封死
    with pytest.raises(LookaheadError, match="oracle"):
        view.carbon_future("vdc-01", T0, T0 + timedelta(hours=2))


def test_dep_4_4_unset_clock_rejected(cfg):
    from greenpulse.signal.base import create_provider

    view = SignalView(
        cfg,
        create_provider("carbon", "synthetic", cfg),
        create_provider("green_forecast", "synthetic", cfg),
        create_provider("price", "synthetic", cfg),
    )
    with pytest.raises(LookaheadError, match="set_now"):
        view.carbon_series("vdc-01", T0, T0)


def test_dep_1_7_naive_now_rejected(cfg, degraded_view):
    with pytest.raises(Exception, match="无时区"):
        degraded_view.set_now(datetime(2026, 8, 1, 3, 0))  # naive


def test_degraded_scheduler_falls_back_to_carbon_agnostic(cfg, degraded_view):
    """DFR 铁律推论 2(PINNED):降级时碳感知策略退回 carbon-agnostic 行为(即刻启动)。"""
    from greenpulse.policy.base import create_scheduler
    from greenpulse.sim.model import Action, Pod, SimState, Task, TaskKind

    degraded_view.carbon_series("vdc-01", T0, degraded_view.now)  # 触发降级
    assert degraded_view.degraded
    task = Task(
        name="ft-0", kind=TaskKind.ELASTIC, gpus=8, duration_minutes=60,
        arrival=degraded_view.now, deadline=degraded_view.now + timedelta(hours=20),
        interruptible=False, tokens_expected=1.0,
    )
    state = SimState(
        now=degraded_view.now,
        queue=[task],
        pods={"pod-a": Pod(name="pod-a", gpu_count=128, power_budget_kw=900.0)},
    )
    decisions = create_scheduler("carbon_aware", cfg).decide(state, degraded_view)
    assert decisions[0].action == Action.START  # 降级 → 不再为绿色而等待


# ---- strict xfail:契约已定,行为未实现(挂账,实现即强制摘标) ----------------

@pytest.mark.xfail(strict=True, reason="DEP-1.1 重试 N 次后才降级:重试机制未实现(挂账)")
def test_dep_1_1_retries_before_degrade(cfg):
    calls = []

    class CountingDown(CarbonSignalProvider):
        def carbon_series(self, site_id, start, end):
            calls.append(1)
            raise SignalUnavailableError("down")

    view = SignalView(cfg, CountingDown(), StaleGreenProvider(15), OkPriceProvider())
    view.set_now(T0)
    view.carbon_series("vdc-01", T0, T0)
    assert len(calls) >= 2, "应重试 N 次后才降级"


@pytest.mark.xfail(
    strict=True, reason="DEP-5.1/5.2 求解器未引入(Stage O):不可行报 IIS、超时回退启发式"
)
def test_dep_5_solver_infeasible_reports_constraints():
    from greenpulse.policy import milp  # noqa: F401  Stage O 落地

    raise AssertionError("unreachable")


@pytest.mark.xfail(
    strict=True, reason="DEP-8.3 并发写实验记录的文件锁未实现(已知限制,做了再改契约)"
)
def test_dep_8_3_concurrent_writers_locked():
    from greenpulse.eval.records import acquire_record_lock  # noqa: F401

    raise AssertionError("unreachable")
