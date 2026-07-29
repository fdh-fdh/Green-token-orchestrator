"""配置加载器(R1.1 单一真源;DFR DEP-6)。"""

import pytest
from conftest import DEFAULT_CONFIG

from greenpulse.config import load_config
from greenpulse.errors import ConfigError


def _mutated_yaml(tmp_path, transform):
    text = DEFAULT_CONFIG.read_text()
    p = tmp_path / "config.yaml"
    p.write_text(transform(text))
    return p


def test_default_config_loads_and_hash_stable(cfg):
    assert cfg.run.seed == 42
    assert cfg.objective.gamma_sla > cfg.objective.beta_carbon  # SLA 权重必须远大于节能项
    assert len(cfg.config_hash) == 16
    assert load_config(DEFAULT_CONFIG).config_hash == cfg.config_hash


def test_missing_file_named():
    with pytest.raises(ConfigError, match="不存在"):
        load_config("no/such/config.yaml")


def test_empty_file_rejected(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("")
    with pytest.raises(ConfigError, match="为空"):
        load_config(p)


def test_unknown_key_rejected_with_name(tmp_path):
    """未知叶子键命名拒绝——YAML 中不得存在无人消费的键(R1.1 配置消费测试)。"""
    p = _mutated_yaml(tmp_path, lambda s: s + "\nmystery_knob: 1\n")
    with pytest.raises(ConfigError, match="mystery_knob"):
        load_config(p)


def test_unknown_nested_key_rejected(tmp_path):
    """嵌套层未知键同样拒绝(姊妹项目'顶层键检查放过嵌套死配置'事故的免疫)。"""
    p = _mutated_yaml(tmp_path, lambda s: s.replace("  seed: 42", "  seed: 42\n  dead_leaf: 1"))
    with pytest.raises(ConfigError, match="dead_leaf"):
        load_config(p)


def test_missing_weight_rejected(tmp_path):
    p = _mutated_yaml(tmp_path, lambda s: s.replace("  beta_carbon: 1.0\n", ""))
    with pytest.raises(ConfigError, match="beta_carbon"):
        load_config(p)


def test_negative_weight_rejected_with_domain(tmp_path):
    """权重负值拒绝并报键名与合法域(DEP-6.1);不做隐式归一化。"""
    p = _mutated_yaml(tmp_path, lambda s: s.replace("beta_carbon: 1.0", "beta_carbon: -0.5"))
    with pytest.raises(ConfigError, match=r"beta_carbon.*合法域"):
        load_config(p)


def test_indivisible_resolution_rejected(tmp_path):
    """步数由物理时间推导,除不尽即报错(R1.5)。"""
    p = _mutated_yaml(
        tmp_path, lambda s: s.replace("resolution_minutes: 15", "resolution_minutes: 7")
    )
    with pytest.raises(ConfigError, match="resolution_minutes"):
        load_config(p)


def test_bad_accounting_rejected(tmp_path):
    p = _mutated_yaml(
        tmp_path, lambda s: s.replace('accounting: "average"', 'accounting: "vibes"')
    )
    with pytest.raises(ConfigError, match=r"accounting.*合法域"):
        load_config(p)


def test_config_frozen(cfg):
    with pytest.raises(Exception):  # noqa: B017  FrozenInstanceError
        cfg.run = None
