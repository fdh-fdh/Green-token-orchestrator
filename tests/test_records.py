"""实验留痕(R3.4;DFR DEP-8.1/8.2)。"""

import pytest

from greenpulse.errors import MissingArtifactError, RecordSchemaError
from greenpulse.eval.records import (
    EXPERIMENT_COLUMNS,
    append_experiment_record,
    assert_artifacts_exist,
    assert_baselines_complete,
)


def _row(**overrides):
    row = {c: "x" for c in EXPERIMENT_COLUMNS}
    row.update(overrides)
    return row


def test_append_and_reread(tmp_path):
    p = tmp_path / "experiments.csv"
    append_experiment_record(p, _row(policy="carbon_agnostic"))
    append_experiment_record(p, _row(policy="oracle"))
    lines = p.read_text().strip().splitlines()
    assert lines[0].split(",") == EXPERIMENT_COLUMNS
    assert len(lines) == 3


def test_corrupt_header_rejected_naming_path(tmp_path):
    """既有文件表头不匹配 → 拒绝并命名路径,绝不合并混入(DEP-8.1 鬼表头事故免疫)。"""
    p = tmp_path / "experiments.csv"
    p.write_text("ghost,columns\n1,2\n")
    with pytest.raises(RecordSchemaError, match=str(p.name)):
        append_experiment_record(p, _row())
    assert "ghost,columns" in p.read_text()  # 原文件未被污染


def test_missing_column_rejected():
    row = _row()
    del row["config_hash"]
    with pytest.raises(RecordSchemaError, match="config_hash"):
        append_experiment_record("unused.csv", row)


def test_unknown_column_rejected():
    with pytest.raises(RecordSchemaError, match="smuggled"):
        append_experiment_record("unused.csv", _row(smuggled="1"))


def test_missing_artifact_fails_run(tmp_path):
    """声明产物缺失 → 报错,流程不得报成功(DEP-8.2 假成功免疫)。"""
    existing = tmp_path / "a.jsonl"
    existing.write_text("{}\n")
    with pytest.raises(MissingArtifactError, match="missing.jsonl"):
        assert_artifacts_exist([existing, tmp_path / "missing.jsonl"])


def test_incomplete_baselines_refused():
    """五基线缺一 → 拒绝生成对照表(R3.5)。"""
    with pytest.raises(RecordSchemaError, match="oracle"):
        assert_baselines_complete(["carbon_agnostic", "best_static", "price_only", "carbon_only"])
    # 全家桶齐全 → 放行
    assert_baselines_complete(
        ["carbon_agnostic", "best_static", "price_only", "carbon_only", "oracle", "carbon_aware"]
    )
