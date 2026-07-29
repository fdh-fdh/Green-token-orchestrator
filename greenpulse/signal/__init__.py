"""信号层:碳强度 / 绿电预报 / 电价的 Provider 抽象、注册表与边界校验。

规则(ENGINEERING_RULES R1.2/R1.3):
- 业务逻辑不 import 具体实现、不按源名分支;按注册表名选择;
- 实时值与预报是两个接口;
- 合成数据是一个 Provider,不是特例分支——与真实 Provider 过同一套契约测试。
"""

from . import static_json, synthetic  # noqa: F401  注册 Provider(import 即注册)
from .base import (  # noqa: F401
    CarbonSignalProvider,
    GreenPowerForecastProvider,
    PriceProvider,
    create_provider,
    register_provider,
    registered_names,
)
