"""static-json Provider — 从本地 JSON 文件读取曲线(一等公民,S-X1)。

用途:企业教练/真实源提供的可公开曲线快照、评审复现、契约测试样例。
文件格式(每种信号一个文件,路径按约定 `data/{kind}_{site_id}.json`):

    {
      "unit": "gco2_per_kwh",
      "resolution_minutes": 15,
      "provenance": "real",
      "source": "example-grid-2026",
      "accounting": "average",          # 仅碳强度需要;缺失即拒绝(DEP-1.4)
      "points": [["2026-08-01T00:00:00+00:00", 512.0], ...]
    }

所有校验(步距/重复/缺口/口径/时区)由类型层在构造时执行——本文件不重复实现,也不豁免。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..config import Config
from ..errors import SeriesSchemaError, SignalUnavailableError
from ..types import Accounting, CarbonIntensitySeries, Forecast, Provenance, Series, ensure_utc
from .base import (
    CarbonSignalProvider,
    GreenPowerForecastProvider,
    PriceProvider,
    register_provider,
)

_REQUIRED = ("unit", "resolution_minutes", "provenance", "source", "points")


def _load(path: Path) -> dict:
    if not path.exists():
        raise SignalUnavailableError(
            f"static-json 文件不存在: {path};请提供曲线文件或改用 synthetic Provider(DEP-2.1)"
        )
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise SeriesSchemaError(f"static-json 文件 {path} 解析失败: {e}") from e
    missing = [k for k in _REQUIRED if k not in data]
    if missing:
        raise SeriesSchemaError(f"static-json 文件 {path} 缺失字段 {missing};必填 {_REQUIRED}")
    if not data["points"]:
        raise SeriesSchemaError(f"static-json 文件 {path} 零数据点(DEP-2.3)")
    return data


def _parse_points(data: dict, path: Path) -> tuple[tuple[datetime, ...], tuple[float, ...]]:
    ts, vs = [], []
    for i, point in enumerate(data["points"]):
        if not isinstance(point, list) or len(point) != 2:
            raise SeriesSchemaError(f"{path} points[{i}]: 期望 [iso时间戳, 数值],收到 {point!r}")
        ts.append(ensure_utc(datetime.fromisoformat(point[0]), f"{path} points[{i}]"))
        vs.append(float(point[1]))
    return tuple(ts), tuple(vs)


def _series_from_file(path: Path) -> Series:
    data = _load(path)
    ts, vs = _parse_points(data, path)
    return Series(
        timestamps=ts,
        values=vs,
        unit=data["unit"],
        resolution_minutes=int(data["resolution_minutes"]),
        provenance=Provenance(data["provenance"]),
        source=data["source"],
    )


class StaticJsonCarbonProvider(CarbonSignalProvider):
    def __init__(self, config: Config, data_dir: str = "data"):
        self._dir = Path(data_dir)

    def carbon_series(self, site_id: str, start: datetime, end: datetime) -> CarbonIntensitySeries:
        path = self._dir / f"carbon_{site_id}.json"
        data = _load(path)
        if "accounting" not in data:
            raise SeriesSchemaError(
                f"{path}: 碳强度缺少口径标签 accounting;合法域 "
                f"{[a.value for a in Accounting]}(DEP-1.4:无口径的碳强度不可构造)"
            )
        ts, vs = _parse_points(data, path)
        return CarbonIntensitySeries(
            timestamps=ts,
            values=vs,
            unit=data["unit"],
            resolution_minutes=int(data["resolution_minutes"]),
            provenance=Provenance(data["provenance"]),
            source=data["source"],
            accounting=Accounting(data["accounting"]),
        )


class StaticJsonGreenForecastProvider(GreenPowerForecastProvider):
    def __init__(self, config: Config, data_dir: str = "data"):
        self._dir = Path(data_dir)

    def green_power_forecast(
        self, site_id: str, issued_at: datetime, start: datetime, end: datetime
    ) -> Forecast:
        series = _series_from_file(self._dir / f"green_power_{site_id}.json")
        return Forecast(series=series, issued_at=issued_at)


class StaticJsonPriceProvider(PriceProvider):
    def __init__(self, config: Config, data_dir: str = "data"):
        self._dir = Path(data_dir)

    def price_series(self, site_id: str, start: datetime, end: datetime) -> Series:
        return _series_from_file(self._dir / f"price_{site_id}.json")


register_provider("carbon", "static-json")(StaticJsonCarbonProvider)
register_provider("green_forecast", "static-json")(StaticJsonGreenForecastProvider)
register_provider("price", "static-json")(StaticJsonPriceProvider)
