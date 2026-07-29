"""`make demo` 入口:本地仿真回放,一条命令从零到出表(DFD;A-X1 压缩版)。

- 无外网、无 GPU、无 K8s、无密钥:全部信号来自合成 Provider(DFT);
- 跑五基线全家桶 + carbon_aware,打印对照表(R3.5:缺任一基线拒绝生成);
- 每次运行落实验记录(git SHA + config hash + 协议版本 — R3.4)与决策记录 JSONL;
- 运行结束校验声明产物齐全(DEP-8.2)。

输出纪律:本 demo 打印的所有数字均为【合成场景,非实测】(R3.2);
oracle 行是上限分析的 oracle 上界,不是产品收益(R8)。
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config
from .eval.records import (
    append_experiment_record,
    assert_artifacts_exist,
    assert_baselines_complete,
    make_record,
    write_decision_log,
)
from .policy.base import create_scheduler
from .signal.base import create_provider
from .sim.engine import SimulationEngine
from .sim.view import SignalView
from .sim.workload import synthetic_workload

DEMO_POLICIES = [
    "carbon_agnostic",
    "best_static",
    "price_only",
    "carbon_only",
    "oracle",
    "carbon_aware",
]

# 仿真起点固定为常量:决定性回放的一部分,真实时钟不进入仿真(可复现性)
SIM_START = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)


def run_all(config_path: str) -> dict[str, dict]:
    cfg = load_config(config_path)
    carbon = create_provider("carbon", cfg.signals.carbon_provider, cfg)
    green = create_provider("green_forecast", cfg.signals.green_forecast_provider, cfg)
    price = create_provider("price", cfg.signals.price_provider, cfg)

    results: dict[str, dict] = {}
    out_dir = Path(cfg.run.results_dir)
    record_csv = out_dir / "experiments.csv"
    artifacts: list[Path] = []

    for policy in DEMO_POLICIES:
        oracle = policy == "oracle"
        view = SignalView(cfg, carbon, green, price, oracle=oracle)
        world = SignalView(cfg, carbon, green, price, oracle=True)
        engine = SimulationEngine(cfg, view, world)
        scheduler = create_scheduler(policy, cfg)
        tasks = synthetic_workload(cfg, SIM_START)
        result = engine.run(scheduler, tasks, SIM_START)
        results[policy] = result.metrics
        append_experiment_record(record_csv, make_record(cfg, policy, result.metrics))
        log_path = write_decision_log(out_dir / f"decisions_{policy}.jsonl", result.decisions)
        artifacts.append(log_path)

    assert_baselines_complete(list(results))
    assert_artifacts_exist([record_csv, *artifacts])
    return results


def print_table(results: dict[str, dict]) -> None:
    acc = {r["carbon_accounting"] for r in results.values()}
    prov = {r["data_provenance"] for r in results.values()}
    print()
    print("=" * 100)
    print("GreenPulse 仿真对照表 —【合成场景,非实测】(R3.2)")
    print(f"碳强度口径: {sorted(acc)} | 数据性质: {sorted(prov)} | 协议: 未冻结(draft)")
    print("每个数字四件套见 docs/ENGINEERING_RULES.md R3.1;oracle 行 = oracle 上界,非产品收益")
    print("=" * 100)
    cols = [
        ("policy", 16), ("carbon_gco2", 14), ("cost", 10), ("green_rate", 11),
        ("peak_kw", 9), ("rigid_slo", 10), ("wait_min", 9), ("gco2/token", 12),
    ]
    print("".join(name.ljust(w) for name, w in cols))
    print("-" * 100)
    for policy, m in results.items():
        label = f"{policy}*" if policy == "oracle" else policy
        row = [
            label.ljust(16),
            f"{m['carbon_gco2']:.0f}".ljust(14),
            f"{m['cost']:.0f}".ljust(10),
            f"{m['green_consumption_rate']:.3f}".ljust(11),
            f"{m['peak_power_kw']:.0f}".ljust(9),
            f"{m['rigid_slo_rate']:.3f}".ljust(10),
            f"{m['mean_wait_minutes']:.0f}".ljust(9),
            (f"{m['gco2_per_token']:.4f}" if m["gco2_per_token"] is not None else "n/a").ljust(12),
        ]
        print("".join(row))
    print("-" * 100)
    print("* oracle 上界(事后完美预测);详见 docs/PLAN.md S-X3 上限分析")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="GreenPulse 仿真回放 demo")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument(
        "--all-baselines", action="store_true",
        help="与 demo 相同(demo 本就跑五基线全家桶);保留旗标以对齐 make eval",
    )
    args = parser.parse_args()
    results = run_all(args.config)
    print_table(results)


if __name__ == "__main__":
    main()
