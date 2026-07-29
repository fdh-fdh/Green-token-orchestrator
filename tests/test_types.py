"""类型层边界校验(DFR DEP-1.3/1.4/1.5/1.6/1.7)。断言错误类型与信息内容,不做代理断言。"""

from datetime import datetime, timedelta, timezone

import pytest
from conftest import T0, ts_grid

from greenpulse.errors import (
    DuplicateTimestampError,
    MissingIntervalError,
    NaiveTimestampError,
    ResolutionMismatchError,
    SeriesSchemaError,
)
from greenpulse.types import Accounting, CarbonIntensitySeries, Provenance, Series


def _mk(ts, values, **kw):
    defaults = dict(
        unit="kw", resolution_minutes=15, provenance=Provenance.SYNTHETIC, source="test"
    )
    defaults.update(kw)
    return Series(timestamps=ts, values=values, **defaults)


def test_naive_timestamp_rejected():
    naive = (datetime(2026, 8, 1, 0, 0), datetime(2026, 8, 1, 0, 15))
    with pytest.raises(NaiveTimestampError, match="无时区"):
        _mk(naive, (1.0, 2.0))


def test_duplicate_timestamps_rejected():
    ts = (T0, T0, T0 + timedelta(minutes=15))
    with pytest.raises(DuplicateTimestampError, match="重复时间戳"):
        _mk(ts, (1.0, 2.0, 3.0))


def test_gap_rejected_not_filled():
    """缺失区间必须拒绝并命名区间,禁止零填/插值(DEP-1.3 信号编造之门)。"""
    ts = (T0, T0 + timedelta(minutes=15), T0 + timedelta(minutes=60))
    with pytest.raises(MissingIntervalError, match="缺失区间禁止零填"):
        _mk(ts, (1.0, 2.0, 3.0))


def test_resolution_mismatch_rejected():
    """声明 15 分钟、实际 5 分钟步距 → 拒绝并同时报请求值与实测值(DEP-1.5)。"""
    ts = (T0, T0 + timedelta(minutes=5))
    with pytest.raises(ResolutionMismatchError, match="实测步距"):
        _mk(ts, (1.0, 2.0))


def test_empty_series_rejected():
    with pytest.raises(SeriesSchemaError, match="空序列"):
        _mk((), ())


def test_nan_rejected():
    with pytest.raises(SeriesSchemaError, match="非有限数"):
        _mk((T0,), (float("nan"),))


def test_non_utc_normalized_to_utc():
    """带时区的非 UTC 时间戳被统一为 UTC(边界处统一,DEP-1.7)。"""
    cest = timezone(timedelta(hours=2))
    s = _mk((T0.astimezone(cest),), (1.0,))
    assert s.timestamps[0].tzinfo == timezone.utc
    assert s.timestamps[0] == T0


def test_carbon_requires_accounting_label():
    """无口径标签的碳强度在类型上不可构造(R1.5)。"""
    ts = ts_grid(T0, 4, 15)
    with pytest.raises(TypeError):
        CarbonIntensitySeries(  # noqa: B026  故意缺 accounting
            timestamps=ts, values=(1.0, 2.0, 3.0, 4.0), unit="gco2_per_kwh",
            resolution_minutes=15, provenance=Provenance.SYNTHETIC, source="test",
        )


def test_carbon_negative_value_rejected():
    ts = ts_grid(T0, 2, 15)
    with pytest.raises(SeriesSchemaError, match="负值"):
        CarbonIntensitySeries(
            timestamps=ts, values=(100.0, -1.0), unit="gco2_per_kwh",
            resolution_minutes=15, provenance=Provenance.SYNTHETIC, source="test",
            accounting=Accounting.AVERAGE,
        )


def test_carbon_wrong_unit_rejected():
    ts = ts_grid(T0, 2, 15)
    with pytest.raises(SeriesSchemaError, match="单位"):
        CarbonIntensitySeries(
            timestamps=ts, values=(100.0, 120.0), unit="kg_per_mwh",
            resolution_minutes=15, provenance=Provenance.SYNTHETIC, source="test",
            accounting=Accounting.AVERAGE,
        )


def test_value_at_outside_range_rejected():
    s = _mk(ts_grid(T0, 4, 15), (1.0, 2.0, 3.0, 4.0))
    with pytest.raises(MissingIntervalError, match="覆盖范围"):
        s.value_at(T0 - timedelta(hours=1))
