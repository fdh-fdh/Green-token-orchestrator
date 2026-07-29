"""Provider 契约测试(R1.2/R1.3)。

关键性质:测试体对 Provider 类型无感知——合成与 static-json 走完全相同的断言;
新接入的 Provider 只需加一行参数化即可获得同一套契约覆盖。
"""

import json
from datetime import timedelta

import pytest
from conftest import T0

from greenpulse.config import load_config
from greenpulse.errors import ConfigError, SeriesSchemaError, SignalUnavailableError
from greenpulse.signal.base import create_provider, registered_names
from greenpulse.signal.static_json import StaticJsonCarbonProvider
from greenpulse.types import Accounting, Provenance


def _write_carbon_json(dir_path, site_id="vdc-01", *, accounting="average", n=8):
    points = [
        [(T0 + timedelta(minutes=15 * i)).isoformat(), 500.0 + i] for i in range(n)
    ]
    payload = {
        "unit": "gco2_per_kwh",
        "resolution_minutes": 15,
        "provenance": "real",
        "source": "test-grid",
        "accounting": accounting,
        "points": points,
    }
    if accounting is None:
        del payload["accounting"]
    (dir_path / f"carbon_{site_id}.json").write_text(json.dumps(payload))


@pytest.fixture()
def providers(cfg, tmp_path):
    _write_carbon_json(tmp_path)
    return {
        "synthetic": create_provider("carbon", "synthetic", cfg),
        "static-json": StaticJsonCarbonProvider(cfg, data_dir=str(tmp_path)),
    }


@pytest.mark.parametrize("name", ["synthetic", "static-json"])
def test_carbon_contract(providers, name):
    """契约:窗口覆盖、口径标签、溯源标记、非负值——对 Provider 类型无感知。"""
    p = providers[name]
    end = T0 + timedelta(minutes=15 * 7)
    series = p.carbon_series("vdc-01", T0, end)
    assert series.start == T0
    assert series.end == end
    assert isinstance(series.accounting, Accounting)
    assert isinstance(series.provenance, Provenance)
    assert all(v >= 0 for v in series.values)
    assert series.unit == "gco2_per_kwh"


def test_registry_lists_first_class_providers():
    """static-json/合成 Provider 为一等公民(S-X1)。"""
    for kind in ("carbon", "green_forecast", "price"):
        names = registered_names(kind)
        assert "synthetic" in names and "static-json" in names


def test_unknown_provider_rejected_listing_names(cfg):
    """未知 Provider 名:构造任何对象之前拒绝并列出全部注册名(DEP-6.2)。"""
    with pytest.raises(ConfigError, match="已注册"):
        create_provider("carbon", "watttime-typo", cfg)


def test_static_json_missing_file_is_unavailable_not_synthetic(cfg, tmp_path):
    """文件缺失 → SignalUnavailableError;运行时绝不静默退回合成(DEP-2.1)。"""
    p = StaticJsonCarbonProvider(cfg, data_dir=str(tmp_path / "nowhere"))
    with pytest.raises(SignalUnavailableError, match="不存在"):
        p.carbon_series("vdc-01", T0, T0 + timedelta(minutes=15))


def test_static_json_missing_accounting_rejected(cfg, tmp_path):
    """碳强度缺口径标签 → 边界处拒绝(DEP-1.4)。"""
    _write_carbon_json(tmp_path, accounting=None)
    p = StaticJsonCarbonProvider(cfg, data_dir=str(tmp_path))
    with pytest.raises(SeriesSchemaError, match="口径"):
        p.carbon_series("vdc-01", T0, T0 + timedelta(minutes=15 * 7))


def test_static_json_empty_points_rejected(cfg, tmp_path):
    (tmp_path / "carbon_vdc-01.json").write_text(json.dumps({
        "unit": "gco2_per_kwh", "resolution_minutes": 15, "provenance": "real",
        "source": "t", "accounting": "average", "points": [],
    }))
    p = StaticJsonCarbonProvider(cfg, data_dir=str(tmp_path))
    with pytest.raises(SeriesSchemaError, match="零数据点"):
        p.carbon_series("vdc-01", T0, T0 + timedelta(minutes=15))


def test_synthetic_same_seed_same_curve(cfg):
    """同 seed 双跑 bit 级一致(DEP-3.3),且与请求窗口无关(时刻级确定性)。"""
    p = create_provider("carbon", "synthetic", cfg)
    end = T0 + timedelta(hours=6)
    a = p.carbon_series("vdc-01", T0, end)
    b = p.carbon_series("vdc-01", T0, end)
    assert a.values == b.values
    # 子窗口的值必须与全窗口对应时刻完全一致(值只由时刻决定,不由窗口决定)
    sub = p.carbon_series("vdc-01", T0 + timedelta(hours=1), end)
    assert sub.values == a.values[4:]


def test_synthetic_seed_changes_curve(tmp_path):
    """不同 seed 产生不同曲线——确定性不是常量(防'断言低一层级',R7)。"""
    from conftest import DEFAULT_CONFIG

    other = tmp_path / "cfg.yaml"
    other.write_text(DEFAULT_CONFIG.read_text().replace("seed: 42", "seed: 43"))
    cfg42 = load_config(DEFAULT_CONFIG)
    cfg43 = load_config(other)
    end = T0 + timedelta(hours=6)
    a = create_provider("carbon", "synthetic", cfg42).carbon_series("vdc-01", T0, end)
    b = create_provider("carbon", "synthetic", cfg43).carbon_series("vdc-01", T0, end)
    assert a.values != b.values
