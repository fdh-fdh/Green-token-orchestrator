"""物理量与时间序列类型。

规则来源 ENGINEERING_RULES R1.5:
- 单位显式:字段名后缀强制(`_kw` / `_kwh` / `_gco2_per_kwh`);
- 碳强度必须携带口径标签(average/marginal)与来源——无口径标签的碳强度在类型上不可构造;
- 时间戳一律 tz-aware UTC;步距在边界处校验(DFR DEP-1.5/1.6/1.7)。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from .errors import (
    DuplicateTimestampError,
    MissingIntervalError,
    NaiveTimestampError,
    ResolutionMismatchError,
    SeriesSchemaError,
)


class Accounting(str, Enum):
    """碳强度口径。平均/边际结论可翻转,双口径纪律见 ENGINEERING_RULES R3.1。"""

    AVERAGE = "average"
    MARGINAL = "marginal"


class Provenance(str, Enum):
    """数据性质标注(R3.2):每条曲线必须声明来源性质。"""

    SYNTHETIC = "synthetic"
    REAL = "real"
    DERIVED_FROM_REAL = "derived-from-real"


def ensure_utc(ts: datetime, context: str) -> datetime:
    """边界处统一 UTC(DEP-1.7):无时区信息的时间戳直接拒绝。"""
    if ts.tzinfo is None:
        raise NaiveTimestampError(
            f"{context}: 时间戳 {ts.isoformat()} 无时区信息;要求 tz-aware UTC"
        )
    return ts.astimezone(timezone.utc)


@dataclass(frozen=True)
class Series:
    """等步距时间序列。构造即校验;校验失败在边界处拒绝而非静默修补。"""

    timestamps: tuple[datetime, ...]
    values: tuple[float, ...]
    unit: str
    resolution_minutes: int
    provenance: Provenance
    source: str

    def __post_init__(self) -> None:
        name = f"Series(source={self.source!r}, unit={self.unit!r})"
        if len(self.timestamps) == 0:
            raise SeriesSchemaError(f"{name}: 空序列被拒绝(DEP-2.3/4.3)")
        if len(self.timestamps) != len(self.values):
            raise SeriesSchemaError(
                f"{name}: 时间戳数 {len(self.timestamps)} != 值数 {len(self.values)}"
            )
        utc = tuple(ensure_utc(ts, name) for ts in self.timestamps)
        object.__setattr__(self, "timestamps", utc)
        if len(set(utc)) != len(utc):
            dup = len(utc) - len(set(utc))
            raise DuplicateTimestampError(f"{name}: 存在 {dup} 个重复时间戳(DEP-1.6)")
        step = timedelta(minutes=self.resolution_minutes)
        for a, b in zip(utc, utc[1:], strict=False):
            actual = b - a
            if actual != step:
                raise (
                    MissingIntervalError(
                        f"{name}: {a.isoformat()} → {b.isoformat()} 间隔 {actual} "
                        f"> 声明步距 {step};缺失区间禁止零填/插值(DEP-1.3)"
                    )
                    if actual > step
                    else ResolutionMismatchError(
                        f"{name}: 实测步距 {actual} != 声明分辨率 {step}(DEP-1.5)"
                    )
                )
        for v in self.values:
            if not math.isfinite(v):
                raise SeriesSchemaError(f"{name}: 值 {v} 非有限数(DEP-1.4)")

    @property
    def start(self) -> datetime:
        return self.timestamps[0]

    @property
    def end(self) -> datetime:
        return self.timestamps[-1]

    def value_at(self, ts: datetime) -> float:
        """取 ts 所在步的值(要求 ts 落在序列覆盖范围内)。"""
        ts = ensure_utc(ts, "value_at")
        if ts < self.start or ts > self.end + timedelta(minutes=self.resolution_minutes):
            raise MissingIntervalError(
                f"value_at: {ts.isoformat()} 不在序列覆盖范围 "
                f"[{self.start.isoformat()}, {self.end.isoformat()}] 内"
            )
        idx = int((ts - self.start).total_seconds() // (self.resolution_minutes * 60))
        idx = min(idx, len(self.values) - 1)
        return self.values[idx]


@dataclass(frozen=True)
class CarbonIntensitySeries(Series):
    """碳强度曲线(gCO2/kWh)。口径标签为必填字段——不可构造无口径的碳强度(R1.5)。"""

    accounting: Accounting = field(kw_only=True)

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.accounting, Accounting):
            raise SeriesSchemaError(
                f"碳强度口径标签非法: {self.accounting!r};合法域 {[a.value for a in Accounting]}"
            )
        if self.unit != "gco2_per_kwh":
            raise SeriesSchemaError(f"碳强度单位必须为 'gco2_per_kwh',收到 {self.unit!r}")
        for v in self.values:
            if v < 0:
                raise SeriesSchemaError(f"碳强度出现负值 {v}(DEP-1.4)")


@dataclass(frozen=True)
class Forecast:
    """预报 = 序列 + 生成时间。实时值与预报是两个概念(R1.2);时龄校验见 DEP-1.2。"""

    series: Series
    issued_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "issued_at", ensure_utc(self.issued_at, "Forecast.issued_at"))

    def age_minutes(self, now: datetime) -> float:
        return (ensure_utc(now, "Forecast.age") - self.issued_at).total_seconds() / 60.0
