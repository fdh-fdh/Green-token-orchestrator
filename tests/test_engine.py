"""引擎端到端:确定性、SLA 保底、ecoModeOff、决策记录必含字段。"""

import json

import pytest
from conftest import DEFAULT_CONFIG

from greenpulse.config import load_config
from greenpulse.demo import SIM_START
from greenpulse.policy.base import create_scheduler
from greenpulse.signal.base import create_provider
from greenpulse.sim.engine import SimulationEngine
from greenpulse.sim.view import SignalView
from greenpulse.sim.workload import synthetic_workload

A_X3_REQUIRED_FIELDS = {
    "task", "action", "window_start", "window_end",
    "signal_snapshot", "objective_contributions", "rejected_alternatives",
    "degraded", "oracle",
}


def _run(cfg, policy: str):
    carbon = create_provider("carbon", cfg.signals.carbon_provider, cfg)
    green = create_provider("green_forecast", cfg.signals.green_forecast_provider, cfg)
    price = create_provider("price", cfg.signals.price_provider, cfg)
    view = SignalView(cfg, carbon, green, price, oracle=(policy == "oracle"))
    world = SignalView(cfg, carbon, green, price, oracle=True)
    engine = SimulationEngine(cfg, view, world)
    tasks = synthetic_workload(cfg, SIM_START)
    return engine.run(create_scheduler(policy, cfg), tasks, SIM_START)


@pytest.fixture(scope="module")
def cfg_module():
    return load_config(DEFAULT_CONFIG)


def test_same_seed_bitwise_identical(cfg_module):
    """确定性门禁:同 seed 双跑,指标与决策记录序列化后逐字节一致(DEP-3.3/S-X2)。"""
    r1 = _run(cfg_module, "carbon_aware")
    r2 = _run(cfg_module, "carbon_aware")
    assert json.dumps(r1.metrics, sort_keys=True) == json.dumps(r2.metrics, sort_keys=True)
    d1 = [json.dumps(d.__dict__, sort_keys=True) for d in r1.decisions]
    d2 = [json.dumps(d.__dict__, sort_keys=True) for d in r2.decisions]
    assert d1 == d2


def test_rigid_slo_never_below_carbon_agnostic(cfg_module):
    """SLA 保底(O-X5 雏形):碳感知策略的刚性 SLO 达成率不得低于 carbon-agnostic 基线。

    断言落在指标本身,而非"调度器输出了计划"(R0.2 高危点 a 的免疫)。
    """
    baseline = _run(cfg_module, "carbon_agnostic").metrics["rigid_slo_rate"]
    aware = _run(cfg_module, "carbon_aware").metrics["rigid_slo_rate"]
    assert aware >= baseline


def test_eco_mode_off_bitwise_equals_carbon_agnostic(tmp_path, cfg_module):
    """ecoModeOff(DEP-7.3):开关关闭碳感知后,行为与 carbon-agnostic 基线 bit 级一致。"""
    text = DEFAULT_CONFIG.read_text().replace("eco_mode_off: false", "eco_mode_off: true")
    p = tmp_path / "eco_off.yaml"
    p.write_text(text)
    cfg_off = load_config(p)
    off = _run(cfg_off, "carbon_aware")
    agnostic = _run(cfg_off, "carbon_agnostic")
    d_off = [
        json.dumps({**d.__dict__}, sort_keys=True).replace('"carbon_aware"', '"x"')
        for d in off.decisions
    ]
    d_agn = [
        json.dumps({**d.__dict__}, sort_keys=True).replace('"carbon_agnostic"', '"x"')
        for d in agnostic.decisions
    ]
    assert d_off == d_agn
    assert off.metrics == agnostic.metrics


def test_decision_records_contain_a_x3_fields(cfg_module):
    """决策记录必含字段(A-X3):缺任一字段即不通过。抽查全部而非 3 条——机器不用省。"""
    result = _run(cfg_module, "carbon_aware")
    assert result.decisions, "至少应有一条决策记录"
    for d in result.decisions:
        missing = A_X3_REQUIRED_FIELDS - set(d.__dict__)
        assert not missing, f"缺字段: {missing}"
        assert "carbon_accounting" in d.signal_snapshot  # 口径进快照,不是注释
        assert "degraded" in d.signal_snapshot
        assert isinstance(d.rejected_alternatives, list) and d.rejected_alternatives


def test_oracle_decisions_flagged(cfg_module):
    """oracle 运行的每条记录必须带 oracle 标志(R3.2:上界数字可溯源地区别于产品收益)。"""
    result = _run(cfg_module, "oracle")
    assert all(d.oracle for d in result.decisions)
    nonoracle = _run(cfg_module, "carbon_agnostic")
    assert not any(d.oracle for d in nonoracle.decisions)


def test_metrics_carry_accounting_and_provenance(cfg_module):
    """每个指标集必须携带口径与数据性质(R3.1/R3.2)——四件套的机器可查部分。"""
    m = _run(cfg_module, "carbon_agnostic").metrics
    assert m["carbon_accounting"] in ("average", "marginal")
    assert m["data_provenance"] == "synthetic"
    assert m["energy_kwh"] > 0
    assert m["tasks_completed"] > 0
