"""实验留痕(ENGINEERING_RULES R3.4;DFR DEP-8)。

- 每次仿真运行落一行:时间戳、git SHA、dirty 标志、config hash、协议版本、指标;
- 追加前校验既有列,列不匹配即拒绝并命名路径,绝不合并混入(DEP-8.1);
- 对照表由记录透视,不得手工誊抄;dirty 树产出的行不得进入对外材料;
- 五基线齐全性断言(R3.5):缺任一基线即拒绝生成对照表。
"""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..errors import MissingArtifactError, RecordSchemaError

EXPERIMENT_COLUMNS = [
    "recorded_at",
    "git_sha",
    "git_dirty",
    "config_hash",
    "protocol_version",
    "seed",
    "policy",
    "metrics_json",
]

REQUIRED_BASELINES = ["carbon_agnostic", "best_static", "price_only", "carbon_only", "oracle"]


def git_state(repo_dir: str | Path = ".") -> tuple[str, bool]:
    """(sha, dirty)。无 git 环境返回 ('nogit', True)——按最保守情形标记。"""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=repo_dir, check=True, timeout=10,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=repo_dir, check=True, timeout=10,
        ).stdout.strip()
        return sha, bool(status)
    except (subprocess.SubprocessError, FileNotFoundError):
        return "nogit", True


def append_experiment_record(path: str | Path, row: dict) -> None:
    """追加一行实验记录。既有文件表头不匹配即拒绝(DEP-8.1)。"""
    p = Path(path)
    missing = [c for c in EXPERIMENT_COLUMNS if c not in row]
    if missing:
        raise RecordSchemaError(f"实验记录缺失列 {missing};要求 {EXPERIMENT_COLUMNS}")
    extra = [c for c in row if c not in EXPERIMENT_COLUMNS]
    if extra:
        raise RecordSchemaError(f"实验记录存在未知列 {extra};要求 {EXPERIMENT_COLUMNS}")
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        with p.open(newline="") as f:
            header = next(csv.reader(f), None)
        if header != EXPERIMENT_COLUMNS:
            raise RecordSchemaError(
                f"实验记录文件 {p} 表头 {header} != 预期 {EXPERIMENT_COLUMNS};"
                f"拒绝追加,绝不合并混入(DEP-8.1)"
            )
        with p.open("a", newline="") as f:
            csv.DictWriter(f, fieldnames=EXPERIMENT_COLUMNS).writerow(row)
    else:
        with p.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=EXPERIMENT_COLUMNS)
            w.writeheader()
            w.writerow(row)


def make_record(config, policy: str, metrics: dict, repo_dir: str | Path = ".") -> dict:
    sha, dirty = git_state(repo_dir)
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": sha,
        "git_dirty": str(dirty).lower(),
        "config_hash": config.config_hash,
        "protocol_version": config.run.protocol_version,
        "seed": str(config.run.seed),
        "policy": policy,
        "metrics_json": json.dumps(metrics, ensure_ascii=False, sort_keys=True),
    }


def write_decision_log(path: str | Path, records: list) -> Path:
    """决策记录落 JSONL;运行结束由调用方校验产物存在(DEP-8.2)。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        for r in records:
            f.write(json.dumps(r.__dict__, ensure_ascii=False, sort_keys=True) + "\n")
    return p


def assert_artifacts_exist(paths: list[str | Path]) -> None:
    """运行声明的产物必须齐全,缺即报错(DEP-8.2:禁止假成功)。"""
    missing = [str(p) for p in paths if not Path(p).exists()]
    if missing:
        raise MissingArtifactError(f"声明的运行产物缺失: {missing}(DEP-8.2:流程不得报成功)")


def assert_baselines_complete(policies_run: list[str]) -> None:
    """五基线全家桶齐全性(R3.5):缺任一即拒绝生成对照表。"""
    missing = [b for b in REQUIRED_BASELINES if b not in policies_run]
    if missing:
        raise RecordSchemaError(
            f"基线不齐,拒绝生成对照表(R3.5):缺 {missing};要求 {REQUIRED_BASELINES}"
        )
