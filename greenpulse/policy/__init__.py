"""调度策略层:调度器接口 + 注册表 + 五基线全家桶(R3.5)。"""

from . import baselines  # noqa: F401  import 即注册
from .base import Scheduler, create_scheduler, registered_policies  # noqa: F401
