"""合成任务流生成器(R1.3:合成负载与真实 trace 派生负载走同一 Task 模型)。

- 同 seed 确定性(DEP-3.3);
- 三类任务画像对应 README:在线推理(刚性)/ 批量推理(半弹性)/ 微调训练(弹性);
- 统计特征标定依据待 P0-X4 探源后回填(当前为示意形状,产物带 synthetic 标注)。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from ..config import Config
from ..types import ensure_utc
from .model import Task, TaskKind


def synthetic_workload(config: Config, sim_start: datetime) -> list[Task]:
    sim_start = ensure_utc(sim_start, "synthetic_workload.sim_start")
    rng = np.random.default_rng(config.run.seed)
    horizon = timedelta(hours=config.time.horizon_hours)
    sim_end = sim_start + horizon
    step_min = config.time.resolution_minutes
    w = config.workload.synthetic
    tokens_per_gpu_min = config.workload.tokens_per_gpu_hour / 60.0
    tasks: list[Task] = []

    def snap(minutes: float) -> int:
        """时长对齐到步距(R1.5:步数由物理时间推导)。"""
        return max(step_min, int(round(minutes / step_min)) * step_min)

    for i in range(w.online_inference_jobs):
        arrival = sim_start + timedelta(
            minutes=float(rng.uniform(0, horizon.total_seconds() / 60 * 0.9))
        )
        duration = snap(float(rng.uniform(30, 90)))
        tasks.append(
            Task(
                name=f"online-{i:03d}",
                kind=TaskKind.RIGID,
                gpus=int(rng.integers(2, 9)),
                duration_minutes=duration,
                arrival=arrival,
                deadline=arrival + timedelta(minutes=duration),  # 刚性:到达即须服务
                interruptible=False,
                tokens_expected=0.0,  # 占位:刚性任务 token 计量随协议冻结定口径(S-X4)
            )
        )

    for i in range(w.batch_inference_jobs):
        arrival = sim_start + timedelta(
            minutes=float(rng.uniform(0, horizon.total_seconds() / 60 * 0.5))
        )
        duration = snap(float(rng.uniform(60, 180)))
        gpus = int(rng.integers(8, 33))
        tasks.append(
            Task(
                name=f"batch-{i:03d}",
                kind=TaskKind.SEMI_ELASTIC,
                gpus=gpus,
                duration_minutes=duration,
                arrival=arrival,
                deadline=min(arrival + timedelta(hours=12), sim_end),
                interruptible=True,
                tokens_expected=gpus * duration * tokens_per_gpu_min,
            )
        )

    for i in range(w.finetune_jobs):
        arrival = sim_start + timedelta(
            minutes=float(rng.uniform(0, horizon.total_seconds() / 60 * 0.25))
        )
        duration = snap(float(rng.uniform(240, 480)))
        gpus = int(rng.integers(32, 65))
        tasks.append(
            Task(
                name=f"finetune-{i:03d}",
                kind=TaskKind.ELASTIC,
                gpus=gpus,
                duration_minutes=duration,
                arrival=arrival,
                deadline=sim_end,
                interruptible=False,
                tokens_expected=gpus * duration * tokens_per_gpu_min,
            )
        )

    tasks.sort(key=lambda t: (t.arrival, t.name))
    return tasks
