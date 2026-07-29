"""配置加载器 — 单一 YAML 真源(ENGINEERING_RULES R1.1;DFR DEP-6)。

纪律:
- 所有超参数、阈值、路径、权重、Pod 定义、信号源选择只能来自这里;
- 未知键拒绝(命名键)、缺失键拒绝(命名键)、出域值拒绝(命名键+值+合法域);
- 加载产物为冻结 dataclass;权重不做隐式归一化;
- 每个叶子键必须被 schema 消费——加载器本身就是配置消费测试的执行点。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError


@dataclass(frozen=True)
class RunConfig:
    seed: int
    protocol_version: str
    results_dir: str


@dataclass(frozen=True)
class TimeConfig:
    resolution_minutes: int
    horizon_hours: int
    forecast_max_age_minutes: int


@dataclass(frozen=True)
class SyntheticSignalConfig:
    carbon_base_gco2_per_kwh: float
    carbon_swing_gco2_per_kwh: float
    carbon_noise_gco2_per_kwh: float
    solar_peak_kw: float
    wind_mean_kw: float
    price_offpeak_per_kwh: float
    price_peak_per_kwh: float
    accounting: str


@dataclass(frozen=True)
class SignalsConfig:
    carbon_provider: str
    green_forecast_provider: str
    price_provider: str
    synthetic: SyntheticSignalConfig


@dataclass(frozen=True)
class PodConfig:
    name: str
    gpu_count: int
    power_budget_kw: float


@dataclass(frozen=True)
class DatacenterConfig:
    site_id: str
    pue_base: float
    pue_swing: float
    pods: tuple[PodConfig, ...]


@dataclass(frozen=True)
class SyntheticWorkloadConfig:
    online_inference_jobs: int
    finetune_jobs: int
    batch_inference_jobs: int


@dataclass(frozen=True)
class WorkloadConfig:
    synthetic: SyntheticWorkloadConfig
    gpu_power_draw_kw: float
    tokens_per_gpu_hour: float


@dataclass(frozen=True)
class ObjectiveConfig:
    """目标函数权重(README 五项)。缺失或负值在此拒绝(DEP-6.1);不做隐式归一化。"""

    alpha_cost: float
    beta_carbon: float
    gamma_sla: float
    delta_peak: float
    epsilon_migration: float


@dataclass(frozen=True)
class SchedulerConfig:
    policy: str
    eco_mode_off: bool
    defer_quantile: float          # price-only/carbon-only:低于历史分位数才启动弹性任务
    static_window_start_hour: int  # best-static 基线:固定运行窗起点(UTC 小时)
    static_window_hours: int       # best-static 基线:固定运行窗长度
    green_improvement_margin: float  # carbon_aware:预报绿电超出当前比例阈值才等待


@dataclass(frozen=True)
class Config:
    run: RunConfig
    time: TimeConfig
    signals: SignalsConfig
    datacenter: DatacenterConfig
    workload: WorkloadConfig
    objective: ObjectiveConfig
    scheduler: SchedulerConfig
    config_hash: str = ""  # 原始 YAML 字节的 sha256,由加载器计算,进实验记录(R3.4)


def _build(cls: type, data: Any, path: str) -> Any:
    """把 YAML 映射构造成冻结 dataclass;未知键/缺失键/类型错误逐一命名(DEP-6)。"""
    if not is_dataclass(cls):
        raise ConfigError(f"{path}: 内部错误 — {cls} 不是 dataclass")
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: 期望映射,收到 {type(data).__name__}")
    field_map = {f.name: f for f in fields(cls) if f.name != "config_hash"}
    unknown = set(data) - set(field_map)
    if unknown:
        raise ConfigError(f"{path}: 未知键 {sorted(unknown)};合法键 {sorted(field_map)}")
    missing = set(field_map) - set(data)
    if missing:
        raise ConfigError(f"{path}: 缺失键 {sorted(missing)}")
    kwargs: dict[str, Any] = {}
    for name, f in field_map.items():
        raw = data[name]
        ftype = f.type if isinstance(f.type, str) else f.type.__name__
        sub_path = f"{path}.{name}"
        if ftype in ("RunConfig", "TimeConfig", "SignalsConfig", "SyntheticSignalConfig",
                     "DatacenterConfig", "WorkloadConfig", "SyntheticWorkloadConfig",
                     "ObjectiveConfig", "SchedulerConfig"):
            kwargs[name] = _build(globals()[ftype], raw, sub_path)
        elif ftype == "tuple[PodConfig, ...]":
            if not isinstance(raw, list) or not raw:
                raise ConfigError(f"{sub_path}: 期望非空列表")
            kwargs[name] = tuple(_build(PodConfig, item, f"{sub_path}[{i}]")
                                 for i, item in enumerate(raw))
        elif ftype == "int":
            if not isinstance(raw, int) or isinstance(raw, bool):
                raise ConfigError(f"{sub_path}: 期望整数,收到 {raw!r}")
            kwargs[name] = raw
        elif ftype == "float":
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ConfigError(f"{sub_path}: 期望数值,收到 {raw!r}")
            kwargs[name] = float(raw)
        elif ftype == "bool":
            if not isinstance(raw, bool):
                raise ConfigError(f"{sub_path}: 期望布尔值,收到 {raw!r}")
            kwargs[name] = raw
        elif ftype == "str":
            if not isinstance(raw, str):
                raise ConfigError(f"{sub_path}: 期望字符串,收到 {raw!r}")
            kwargs[name] = raw
        else:
            raise ConfigError(f"{sub_path}: 内部错误 — 未处理的字段类型 {ftype!r}")
    return cls(**kwargs)


def _validate(cfg: Config) -> None:
    """出域值校验:命名键、值与合法域。"""
    for name in ("alpha_cost", "beta_carbon", "gamma_sla", "delta_peak", "epsilon_migration"):
        v = getattr(cfg.objective, name)
        if v < 0:
            raise ConfigError(f"objective.{name}: 权重 {v} 为负;合法域 [0, +inf)(DEP-6.1)")
    if cfg.time.resolution_minutes <= 0 or 60 % cfg.time.resolution_minutes != 0:
        raise ConfigError(
            f"time.resolution_minutes: {cfg.time.resolution_minutes} 非法;"
            f"必须为正且整除 60(R1.5:步数由物理时间推导,除不尽即报错)"
        )
    if cfg.time.horizon_hours <= 0:
        raise ConfigError(f"time.horizon_hours: {cfg.time.horizon_hours} 必须为正")
    if cfg.time.forecast_max_age_minutes <= 0:
        raise ConfigError(
            f"time.forecast_max_age_minutes: {cfg.time.forecast_max_age_minutes} 必须为正"
        )
    if cfg.signals.synthetic.accounting not in ("average", "marginal"):
        raise ConfigError(
            f"signals.synthetic.accounting: {cfg.signals.synthetic.accounting!r} 非法;"
            f"合法域 ['average', 'marginal']"
        )
    names = [p.name for p in cfg.datacenter.pods]
    if len(set(names)) != len(names):
        raise ConfigError(f"datacenter.pods: Pod 名重复 {names}")


def load_config(path: str | Path) -> Config:
    """从单一 YAML 加载并冻结配置。任何形状问题在此 fail-closed,绝不带病进入仿真。"""
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"配置文件不存在: {p}")
    raw_bytes = p.read_bytes()
    if not raw_bytes.strip():
        raise ConfigError(f"配置文件为空: {p}")
    try:
        data = yaml.safe_load(raw_bytes)
    except yaml.YAMLError as e:
        raise ConfigError(f"配置文件 {p} 解析失败: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件 {p} 顶层必须是映射,收到 {type(data).__name__}")
    cfg = _build(Config, data, "config")
    object.__setattr__(cfg, "config_hash", hashlib.sha256(raw_bytes).hexdigest()[:16])
    _validate(cfg)
    return cfg
