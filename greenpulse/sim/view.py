"""SignalView — 调度器读取信号的唯一通道,前视泄漏守护(DFR DEP-4.4)。

铁律:调度器可见的实时信号窗口严格 ≤ 决策时刻;预报必须经时龄校验(DEP-1.2);
Provider 断供时显式降级(degraded=True)而非编造(DEP-1.1)。
oracle 基线是唯一例外:显式构造 oracle=True 的视图,其产出永远带 oracle 标志。
"""

from __future__ import annotations

from datetime import datetime

from ..config import Config
from ..errors import LookaheadError, SignalError, StaleForecastError
from ..signal.base import CarbonSignalProvider, GreenPowerForecastProvider, PriceProvider
from ..types import CarbonIntensitySeries, Forecast, Series, ensure_utc


class SignalView:
    def __init__(
        self,
        config: Config,
        carbon: CarbonSignalProvider,
        green_forecast: GreenPowerForecastProvider,
        price: PriceProvider,
        *,
        oracle: bool = False,
    ):
        self._cfg = config
        self._carbon = carbon
        self._green = green_forecast
        self._price = price
        self._now: datetime | None = None
        self.oracle = oracle
        self.degraded = False   # 任一信号断供即置位;决策记录必须携带(铁律推论 2)

    def set_now(self, now: datetime) -> None:
        self._now = ensure_utc(now, "SignalView.set_now")
        self.degraded = False

    @property
    def now(self) -> datetime:
        if self._now is None:
            raise LookaheadError("SignalView 未设置当前时刻;引擎必须先 set_now")
        return self._now

    def _guard(self, end: datetime, what: str) -> None:
        end = ensure_utc(end, f"SignalView.{what}")
        if not self.oracle and end > self.now:
            raise LookaheadError(
                f"前视泄漏(DEP-4.4):{what} 请求窗口终点 {end.isoformat()} "
                f"> 决策时刻 {self.now.isoformat()}"
            )

    def carbon_series(
        self, site_id: str, start: datetime, end: datetime
    ) -> CarbonIntensitySeries | None:
        """已实现碳强度(≤ now)。断供返回 None 并置 degraded——绝不返回旧曲线冒充。"""
        self._guard(end, "carbon_series")
        try:
            return self._carbon.carbon_series(site_id, start, end)
        except SignalError:
            self.degraded = True
            return None

    def price_series(self, site_id: str, start: datetime, end: datetime) -> Series | None:
        self._guard(end, "price_series")
        try:
            return self._price.price_series(site_id, start, end)
        except SignalError:
            self.degraded = True
            return None

    def green_power_forecast(self, site_id: str, start: datetime, end: datetime) -> Forecast | None:
        """预报可以覆盖未来(这是预报的意义),但生成时间必须 ≤ now 且未超时龄。"""
        try:
            fc = self._green.green_power_forecast(site_id, self.now, start, end)
        except SignalError:
            self.degraded = True
            return None
        if fc.issued_at > self.now:
            self.degraded = True
            raise LookaheadError(
                f"前视泄漏(DEP-4.4):预报生成时间 {fc.issued_at.isoformat()} "
                f"> 决策时刻 {self.now.isoformat()}"
            )
        max_age = self._cfg.time.forecast_max_age_minutes
        if fc.age_minutes(self.now) > max_age:
            self.degraded = True
            raise StaleForecastError(
                f"预报过期(DEP-1.2):生成于 {fc.issued_at.isoformat()},"
                f"时龄 {fc.age_minutes(self.now):.0f} 分钟 > 阈值 {max_age} 分钟"
            )
        return fc

    def carbon_future(self, site_id: str, start: datetime, end: datetime) -> CarbonIntensitySeries:
        """未来已实现碳强度——仅 oracle 视图可用;产出的一切数字必须带 'oracle 上界' 前缀(R3.2)。"""
        if not self.oracle:
            raise LookaheadError("carbon_future 仅 oracle 视图可用(DEP-4.4)")
        return self._carbon.carbon_series(site_id, start, end)

    def price_future(self, site_id: str, start: datetime, end: datetime) -> Series:
        """未来电价——仅 oracle 视图可用(引擎核算/上限分析用)。"""
        if not self.oracle:
            raise LookaheadError("price_future 仅 oracle 视图可用(DEP-4.4)")
        return self._price.price_series(site_id, start, end)

    def green_future(self, site_id: str, start: datetime, end: datetime) -> Series:
        """未来绿电出力(视作完美预报)——仅 oracle 视图可用。"""
        if not self.oracle:
            raise LookaheadError("green_future 仅 oracle 视图可用(DEP-4.4)")
        return self._green.green_power_forecast(site_id, start, start, end).series
