"""GreenPulse — 面向绿色 Token 智算工厂的能源-算力协同调度框架(Digital Twin MVP)。

分层结构(PLAN.md P0-X1):
    signal/    信号层:碳强度/绿电预报/电价 Provider 抽象 + 注册表 + 边界校验
    sim/       仿真内核:时钟、Pod、任务队列、前视泄漏守护
    policy/    调度策略:五基线全家桶 + 碳感知调度器
    eval/      评测与留痕:实验记录、决策记录、指标
    executors/ 执行层适配器接口(本届只交付接口定义)
"""

__version__ = "0.1.0"
