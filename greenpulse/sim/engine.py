"""仿真引擎:确定性回放 + 能耗/碳/成本核算 + 结构化决策记录。

- 调度器只能经 SignalView 读信号(前视泄漏守护 DEP-4.4);
- 引擎自身是"世界",直接向 Provider 取已实现曲线做核算——这不是泄漏,调度器看不到;
- 每个决策落一条 DecisionRecord(A-X3 必含字段);
- 同 seed 双跑 bit 级一致(DEP-3.3 / CI 确定性门禁)。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import Config
from ..policy.base import Scheduler
from ..types import ensure_utc
from .model import Action, DecisionRecord, Pod, SimState, Task, TaskKind
from .view import SignalView


@dataclass
class SimulationResult:
    policy: str
    metrics: dict
    decisions: list[DecisionRecord]
    timeline: list[dict] = field(default_factory=list)  # 大屏/可视化消费,不生产证据


def _pue_at(cfg: Config, ts: datetime) -> float:
    """分时 PUE 曲线(S-X2):午后散热压力抬升。形状为示意,标定待 P0-X4。"""
    h = ts.hour + ts.minute / 60.0
    bump = max(0.0, math.sin((h - 6.0) / 12.0 * math.pi)) if 6.0 <= h <= 18.0 else 0.0
    return cfg.datacenter.pue_base + cfg.datacenter.pue_swing * bump


class SimulationEngine:
    def __init__(self, config: Config, view: SignalView, world_view: SignalView):
        """view: 调度器视图(受前视守护);world_view: oracle 视图,引擎核算专用。"""
        self._cfg = config
        self._view = view
        self._world = world_view

    def run(self, scheduler: Scheduler, tasks: list[Task], sim_start: datetime) -> SimulationResult:
        cfg = self._cfg
        sim_start = ensure_utc(sim_start, "SimulationEngine.run")
        step = timedelta(minutes=cfg.time.resolution_minutes)
        n_steps = cfg.time.horizon_hours * 60 // cfg.time.resolution_minutes
        sim_end = sim_start + n_steps * step
        site = cfg.datacenter.site_id

        # 引擎核算用的已实现曲线(世界视角;调度器不可见)
        self._world.set_now(sim_end)
        carbon = self._world.carbon_future(site, sim_start, sim_end)
        price = self._world.price_future(site, sim_start, sim_end)
        green = self._world.green_future(site, sim_start, sim_end)

        if hasattr(scheduler, "sim_start"):
            scheduler.sim_start = sim_start

        state = SimState(
            now=sim_start,
            pods={
                p.name: Pod(name=p.name, gpu_count=p.gpu_count, power_budget_kw=p.power_budget_kw)
                for p in cfg.datacenter.pods
            },
        )
        pending = list(tasks)
        records: list[DecisionRecord] = []
        timeline: list[dict] = []
        completed: list[Task] = []
        start_times: dict[str, datetime] = {}
        dt_hours = cfg.time.resolution_minutes / 60.0
        gpu_kw = cfg.workload.gpu_power_draw_kw

        totals = {
            "energy_kwh": 0.0,
            "carbon_gco2": 0.0,
            "cost": 0.0,
            "green_energy_used_kwh": 0.0,
            "green_energy_available_kwh": 0.0,
            "peak_power_kw": 0.0,
        }

        for _ in range(n_steps):
            now = state.now
            # 1) 完成到期任务,释放资源
            for name in [n for n, (_, _, end) in state.running.items() if end <= now]:
                task, pod_name, _ = state.running.pop(name)
                state.pods[pod_name].gpus_free += task.gpus
                completed.append(task)
            # 2) 新任务入队
            arrived = [t for t in pending if t.arrival <= now]
            pending = [t for t in pending if t.arrival > now]
            state.queue.extend(arrived)
            # 3) 调度决策(经受守护的视图)
            self._view.set_now(now)
            decisions = scheduler.decide(state, self._view)
            snapshot = self._snapshot(carbon, price, green, now)
            for d in decisions:
                task = next(t for t in state.queue if t.name == d.task_name)
                records.append(
                    self._record(d, task, now, step, snapshot, carbon, price, scheduler)
                )
                if d.action == Action.START:
                    pod = state.pods[d.pod_name]
                    if pod.gpus_free < task.gpus:
                        raise RuntimeError(
                            f"调度器超分配:{task.name} 需 {task.gpus} GPU,"
                            f"{pod.name} 仅剩 {pod.gpus_free}(引擎 fail-closed,不静默截断)"
                        )
                    pod.gpus_free -= task.gpus
                    end = now + timedelta(minutes=task.duration_minutes)
                    state.running[task.name] = (task, d.pod_name, end)
                    start_times[task.name] = now
                    state.queue.remove(task)
            # 4) 能耗/碳/成本核算(世界视角)
            it_power_kw = sum(t.gpus * gpu_kw for t, _, _ in state.running.values())
            facility_kw = it_power_kw * _pue_at(cfg, now)
            energy_kwh = facility_kw * dt_hours
            green_kw = green.value_at(now)
            totals["energy_kwh"] += energy_kwh
            totals["carbon_gco2"] += energy_kwh * carbon.value_at(now)
            totals["cost"] += energy_kwh * price.value_at(now)
            totals["green_energy_used_kwh"] += min(facility_kw, green_kw) * dt_hours
            totals["green_energy_available_kwh"] += green_kw * dt_hours
            totals["peak_power_kw"] = max(totals["peak_power_kw"], facility_kw)
            timeline.append(
                {
                    "ts": now.isoformat(),
                    "facility_power_kw": round(facility_kw, 3),
                    "green_power_kw": round(green_kw, 3),
                    "carbon_gco2_per_kwh": round(carbon.value_at(now), 3),
                    "price_per_kwh": round(price.value_at(now), 4),
                    "running": len(state.running),
                    "queued": len(state.queue),
                }
            )
            state.now = now + step

        return SimulationResult(
            policy=scheduler.name,
            metrics=self._metrics(cfg, carbon, totals, tasks, completed, start_times, sim_end),
            decisions=records,
            timeline=timeline,
        )

    # ------------------------------------------------------------------
    def _snapshot(self, carbon, price, green, now) -> dict:
        return {
            "ts": now.isoformat(),
            "carbon_gco2_per_kwh": round(carbon.value_at(now), 3),
            "carbon_accounting": carbon.accounting.value,
            "carbon_provenance": carbon.provenance.value,
            "price_per_kwh": round(price.value_at(now), 4),
            "green_power_kw": round(green.value_at(now), 3),
            "degraded": self._view.degraded,
        }

    def _objective(self, task: Task, now: datetime, carbon, price, start: bool) -> dict:
        """目标函数各项贡献(启发式近似;Stage O 的 MILP 将给出精确版)。"""
        cfg = self._cfg
        energy_kwh = task.gpus * cfg.workload.gpu_power_draw_kw * task.duration_minutes / 60.0
        if not start:
            return {"alpha_cost": 0.0, "beta_carbon": 0.0, "gamma_sla": 0.0,
                    "delta_peak": 0.0, "epsilon_migration": 0.0, "total": 0.0}
        contrib = {
            "alpha_cost": cfg.objective.alpha_cost * energy_kwh * price.value_at(now),
            "beta_carbon": cfg.objective.beta_carbon * energy_kwh * carbon.value_at(now) / 1000.0,
            "gamma_sla": 0.0,
            "delta_peak": cfg.objective.delta_peak * task.gpus * cfg.workload.gpu_power_draw_kw,
            "epsilon_migration": 0.0,
        }
        contrib["total"] = sum(contrib.values())
        return contrib

    def _record(
        self, d, task: Task, now, step, snapshot, carbon, price, scheduler
    ) -> DecisionRecord:
        start = d.action == Action.START
        chosen = self._objective(task, now, carbon, price, start)
        alt = self._objective(task, now, carbon, price, not start)
        alt_action = Action.DELAY.value if start else Action.START.value
        window_end = (
            now + timedelta(minutes=task.duration_minutes) if start else now + step
        )
        return DecisionRecord(
            task=task.name,
            action=d.action.value,
            window_start=now.isoformat(),
            window_end=window_end.isoformat(),
            signal_snapshot=snapshot,
            objective_contributions=chosen,
            rejected_alternatives=[
                {"action": alt_action, "pod": d.pod_name, "objective_total": alt["total"]}
            ],
            degraded=self._view.degraded,
            oracle=self._view.oracle or scheduler.name == "oracle",
        )

    def _metrics(self, cfg, carbon, totals, tasks, completed, start_times, sim_end) -> dict:
        step_min = cfg.time.resolution_minutes
        rigid = [t for t in tasks if t.kind == TaskKind.RIGID and t.arrival < sim_end]
        # SLO 判定:到达后一个调度步之内启动(到达落在步中,最早可启动点是下一步)
        rigid_ok = sum(
            1
            for t in rigid
            if t.name in start_times
            and (start_times[t.name] - t.arrival) <= timedelta(minutes=step_min)
        )
        waits = [
            (start_times[t.name] - t.arrival).total_seconds() / 60.0
            for t in tasks
            if t.name in start_times
        ]
        tokens = sum(t.tokens_expected for t in completed)
        return {
            # 口径纪律(R3.1):carbon_accounting 与 provenance 是指标的一部分,不是注释
            "carbon_accounting": carbon.accounting.value,
            "data_provenance": carbon.provenance.value,
            "energy_kwh": round(totals["energy_kwh"], 2),
            "carbon_gco2": round(totals["carbon_gco2"], 1),
            "cost": round(totals["cost"], 2),
            "peak_power_kw": round(totals["peak_power_kw"], 1),
            "green_consumption_rate": round(
                totals["green_energy_used_kwh"] / totals["green_energy_available_kwh"], 4
            )
            if totals["green_energy_available_kwh"] > 0
            else 0.0,
            "rigid_slo_rate": round(rigid_ok / len(rigid), 4) if rigid else 1.0,
            "mean_wait_minutes": round(sum(waits) / len(waits), 1) if waits else 0.0,
            "tokens_produced": round(tokens, 0),
            "gco2_per_token": round(totals["carbon_gco2"] / tokens, 6) if tokens > 0 else None,
            "tasks_completed": len(completed),
            "tasks_total": len(tasks),
        }
