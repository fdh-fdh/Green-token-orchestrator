# JURECA Blackhole A0 运行记录

| 项目 | 记录 |
|---|---|
| 协议 | `tt-a0-matmul-1` |
| 负载 | 固定输入 BF16 矩阵乘法，`1024 × 1024`，预热 2 次，测量 10 次 |
| Slurm 分区 | `eval-ttbh` |
| 申请资源 | 1 节点、1 个 Blackhole、1 CPU task、4 GiB 内存、3 分钟时限 |
| 提交时间 | 2026-11-08 15:51:42 UTC |
| 启动时间 | 2026-11-09 09:27:24 UTC |
| 结束时间 | 2026-11-09 09:28:23 UTC |
| 排队时间 | 17 小时 35 分 42 秒 |
| 作业状态 | `FAILED`，退出码 `1:0` |
| Slurm 作业耗时 | 59 秒 |
| 设备测量 | 无 `profile.json`，矩阵乘法计时和数值校验未执行 |

提交前在登录节点验证了 TTNN 0.81.1 和 CPU 参考计算环境。计算节点上，`module` 指向的 Lmod 程序无法找到。随后 `srun` 在读取 Slurm 配置时退出：

```text
srun: error: s_p_parse_file: cannot stat file /run/slurm/conf/slurm.conf: No such file or directory
srun: error: ClusterName needs to be specified
srun: fatal: Unable to process configuration file
```

`sacct` 只有作业和 `.batch` 两行，日志停在 `srun` 启动阶段。59 秒是 Slurm 记录的作业耗时，期间未产生 Blackhole 性能、数值校验或可用的能耗样本。再次运行前需确认 `eval-ttbh` 计算节点支持的软件模块入口和单设备启动方式。

[实验计划与复现命令](../JURECA_EXPERIMENT_PLAN.md)
