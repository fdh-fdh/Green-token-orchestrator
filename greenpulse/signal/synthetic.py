"""合成信号 Provider — MVP 主数据源(R1.3:合成是一等 Provider,不是特例分支)。

- 所有产物携带 provenance=SYNTHETIC 溯源标记(DFR DEP-3.2);
- 同 seed 确定性:曲线值仅由 (seed, site_id, 时刻) 决定,双跑 bit 级一致(DEP-3.3);
- 曲线形状:碳强度日内正弦(午间光伏压低)+ 噪声;光伏钟形;电价峰谷两段。
  标定依据待 P0-X4 探源后回填 docs/DATA_LICENSES.md。
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta

import numpy as np

from ..config import Config
from ..errors import ConfigError
from ..types import Accounting, CarbonIntensitySeries, Forecast, Provenance, Series, ensure_utc
from .base import (
    CarbonSignalProvider,
    GreenPowerForecastProvider,
    PriceProvider,
    register_provider,
)


def _grid(start: datetime, end: datetime, resolution_minutes: int) -> tuple[datetime, ...]:
    start = ensure_utc(start, "synthetic._grid.start")
    end = ensure_utc(end, "synthetic._grid.end")
    if end < start:
        raise ConfigError(f"区间反转: start={start.isoformat()} > end={end.isoformat()}(DEP-3.1)")
    step = timedelta(minutes=resolution_minutes)
    n = int((end - start) / step) + 1
    return tuple(start + i * step for i in range(n))


def _rng(seed: int, site_id: str, ts: datetime) -> np.random.Generator:
    """时刻级确定性 RNG:同 (seed, site, 时刻) 永远同值,与请求窗口无关。"""
    key = f"{seed}:{site_id}:{ts.isoformat()}".encode()
    digest = hashlib.sha256(key).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "little"))


def _hour_frac(ts: datetime) -> float:
    return ts.hour + ts.minute / 60.0


class SyntheticCarbonProvider(CarbonSignalProvider):
    def __init__(self, config: Config):
        self._cfg = config

    def carbon_series(self, site_id: str, start: datetime, end: datetime) -> CarbonIntensitySeries:
        s = self._cfg.signals.synthetic
        ts = _grid(start, end, self._cfg.time.resolution_minutes)
        values = []
        for t in ts:
            # 午间光伏出力压低碳强度,夜间抬升;峰值错开到傍晚
            diurnal = math.cos((_hour_frac(t) - 14.0) / 24.0 * 2 * math.pi)
            noise = float(_rng(self._cfg.run.seed, site_id, t).normal(0.0, 1.0))
            v = (
                s.carbon_base_gco2_per_kwh
                + s.carbon_swing_gco2_per_kwh * diurnal * -1.0
                + s.carbon_noise_gco2_per_kwh * noise
            )
            values.append(max(v, 0.0))
        return CarbonIntensitySeries(
            timestamps=ts,
            values=tuple(values),
            unit="gco2_per_kwh",
            resolution_minutes=self._cfg.time.resolution_minutes,
            provenance=Provenance.SYNTHETIC,
            source="synthetic-carbon",
            accounting=Accounting(s.accounting),
        )


class SyntheticGreenForecastProvider(GreenPowerForecastProvider):
    def __init__(self, config: Config):
        self._cfg = config

    def green_power_forecast(
        self, site_id: str, issued_at: datetime, start: datetime, end: datetime
    ) -> Forecast:
        s = self._cfg.signals.synthetic
        ts = _grid(start, end, self._cfg.time.resolution_minutes)
        values = []
        for t in ts:
            h = _hour_frac(t)
            daylight = 6 <= h <= 18
            solar = (
                s.solar_peak_kw * max(0.0, math.sin((h - 6.0) / 12.0 * math.pi))
                if daylight
                else 0.0
            )
            wind_noise = float(_rng(self._cfg.run.seed + 1, site_id, t).normal(1.0, 0.3))
            wind = max(0.0, s.wind_mean_kw * wind_noise)
            values.append(solar + wind)
        series = Series(
            timestamps=ts,
            values=tuple(values),
            unit="kw",
            resolution_minutes=self._cfg.time.resolution_minutes,
            provenance=Provenance.SYNTHETIC,
            source="synthetic-green-power",
        )
        return Forecast(series=series, issued_at=issued_at)


class SyntheticPriceProvider(PriceProvider):
    def __init__(self, config: Config):
        self._cfg = config

    def price_series(self, site_id: str, start: datetime, end: datetime) -> Series:
        s = self._cfg.signals.synthetic
        ts = _grid(start, end, self._cfg.time.resolution_minutes)
        values = []
        for t in ts:
            h = _hour_frac(t)
            peak = (8.0 <= h < 12.0) or (17.0 <= h < 22.0)  # 峰段形状;标定依据 P0-X4 回填
            values.append(s.price_peak_per_kwh if peak else s.price_offpeak_per_kwh)
        return Series(
            timestamps=ts,
            values=tuple(values),
            unit="per_kwh",
            resolution_minutes=self._cfg.time.resolution_minutes,
            provenance=Provenance.SYNTHETIC,
            source="synthetic-price",
        )


register_provider("carbon", "synthetic")(SyntheticCarbonProvider)
register_provider("green_forecast", "synthetic")(SyntheticGreenForecastProvider)
register_provider("price", "synthetic")(SyntheticPriceProvider)
