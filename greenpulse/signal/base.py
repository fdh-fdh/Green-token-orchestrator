"""Provider 接口与注册表。

验收标准(R1.2):接一个新 Provider = 新增 1 个文件 + 1 行配置,改动 0 个下游文件。
实时值与预报为两个接口——不假设 Provider 两者都有(GSF Carbon Aware SDK 的教训性设计)。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from ..errors import ConfigError
from ..types import CarbonIntensitySeries, Forecast, Series

if TYPE_CHECKING:
    from ..config import Config


class CarbonSignalProvider(ABC):
    """实时(已实现)碳强度。返回值必须携带口径标签与来源(类型层强制)。"""

    @abstractmethod
    def carbon_series(self, site_id: str, start: datetime, end: datetime) -> CarbonIntensitySeries:
        """[start, end] 区间的已实现碳强度曲线。缺失/断供必须抛 SignalError,禁止编造。"""


class GreenPowerForecastProvider(ABC):
    """绿电出力预报。预报携带生成时间;消费端负责时龄校验(DEP-1.2)。"""

    @abstractmethod
    def green_power_forecast(
        self, site_id: str, issued_at: datetime, start: datetime, end: datetime
    ) -> Forecast:
        """在 issued_at 时刻生成的 [start, end] 绿电出力(kW)预报。"""


class PriceProvider(ABC):
    """分时电价。"""

    @abstractmethod
    def price_series(self, site_id: str, start: datetime, end: datetime) -> Series:
        """[start, end] 区间的分时电价曲线(每 kWh)。"""


_REGISTRY: dict[str, dict[str, Callable[[Config], object]]] = {
    "carbon": {},
    "green_forecast": {},
    "price": {},
}


def register_provider(kind: str, name: str):
    """注册 Provider 工厂。kind ∈ {carbon, green_forecast, price}。"""
    if kind not in _REGISTRY:
        raise ConfigError(f"未知 Provider 类别 {kind!r};合法域 {sorted(_REGISTRY)}")

    def deco(factory: Callable[[Config], object]):
        _REGISTRY[kind][name] = factory
        return factory

    return deco


def registered_names(kind: str) -> list[str]:
    return sorted(_REGISTRY[kind])


def create_provider(kind: str, name: str, config: Config):
    """按名构造 Provider。未知名在构造任何对象之前拒绝并列出全部注册名(DEP-6.2)。"""
    if kind not in _REGISTRY:
        raise ConfigError(f"未知 Provider 类别 {kind!r};合法域 {sorted(_REGISTRY)}")
    if name not in _REGISTRY[kind]:
        raise ConfigError(
            f"未知 {kind} Provider {name!r};已注册: {registered_names(kind)}"
        )
    return _REGISTRY[kind][name](config)
