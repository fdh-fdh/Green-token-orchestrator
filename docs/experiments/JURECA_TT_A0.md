# JURECA Blackhole A0 运行记录

## 修复后实测

| 项目 | 记录 |
|---|---|
| 协议 | `tt-a0-matmul-1` |
| 负载 | 固定输入 BF16 矩阵乘法，`1024 × 1024`，预热 2 次，测量 10 次 |
| Slurm 分区 | `eval-ttbh` |
| 申请资源 | 1 节点、1 个 Blackhole、1 CPU task、4 GiB 内存、3 分钟时限 |
| 作业时段 | 2026-11-09 17:28:50–17:29:03 UTC |
| 作业状态 | `COMPLETED`，退出码 `0:0`，Slurm 耗时 13 秒 |
| 数值校验 | `exact_match`，所有输出元素均为 1024 |
| 单次计时 | 中位数 100.471 µs，范围 89.665–137.547 µs |

计时覆盖每次 TTNN 矩阵乘法调用和设备同步，预热、首次内核编译及结果回读在测量窗口之外。这里的输入是合成矩阵，计时来自真实 Blackhole。作业未取得可用能耗样本。原始计时数组、软件版本和已核对的代码及配置哈希见[测量 JSON](JURECA_TT_A0.profile.json)，其中省略作业编号和设备编号。

原始日志摘录：

```text
JSC Lmod unavailable; using GreenPulse private GCC runtime libraries
riscv-tt-elf-g++ (tenstorrent/sfpi:7.89.0[1050]) 15.1.0
Allocated Tenstorrent PCIe device: 0
2026-11-09 18:28:51.566 | info     |             UMD | Opening local chip ids/PCIe ids: {0}/[0] and remote chip ids {} (cluster.cpp:173)
2026-11-09 18:29:03.663 | info     |    BuildKernels | JIT cache stats: 0/17 hits (0.0%) [0 cached, 0 build-once dedup, 0 merged artifacts, 0 merged genfiles] (build_cache_telemetry.cpp:362)
```

## 首跑失败与修复

首跑于 2026-11-09 09:27:24 UTC 启动，59 秒后以 `FAILED (1:0)` 结束。计算节点找不到继承的 Lmod 程序，随后 `srun` 在读取 Slurm 配置时退出。

```text
srun: error: s_p_parse_file: cannot stat file /run/slurm/conf/slurm.conf: No such file or directory
srun: error: ClusterName needs to be specified
srun: fatal: Unable to process configuration file
```

- 用独立的 Python 3.12.12 和 TTNN 0.81.1 直接在 Slurm 批作业内启动。恢复账户 `HOME`，解决在干净环境中可复现的 TTNN 导入段错误。
- 在打开设备前去掉调度器字段的尾随空格，并核对 Slurm 和站点分配的设备编号一致。
- 显式尝试加载 JSC `Stages/2026`、GCCcore、GMP、MPFR 和 MPC。成功作业所在节点的 Lmod 路径仍不可用，因此使用 GreenPulse 私有的 `libatomic`、GMP、MPFR 和 MPC 运行库。
- 安装 TTNN 版本文件指定的 SFPI 7.89.0，核对发布包 SHA256。作业先运行最小 Blackhole C++ 编译，验证 `cc1plus` 的依赖，再打开设备。

[实验计划与复现命令](../JURECA_EXPERIMENT_PLAN.md)
