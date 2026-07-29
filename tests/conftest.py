"""共享测试夹具。

红证纪律(R0.2)说明:本测试套件与框架同一提交诞生,逐用例的"未修复代码上 FAIL"
红证自下一个 PR 起强制附带;本文件中每个断言都落在被判定的量本身
(指标值/错误类型/字节一致性),不做行数或键存在类的代理断言(R7 高危点)。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from greenpulse.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"

UTC = timezone.utc
T0 = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)


@pytest.fixture()
def cfg():
    return load_config(DEFAULT_CONFIG)


def ts_grid(start: datetime, n: int, minutes: int) -> tuple[datetime, ...]:
    return tuple(start + timedelta(minutes=minutes * i) for i in range(n))
