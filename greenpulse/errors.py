"""错误类型。命名对应 DFR 矩阵中的失效模式,错误信息必须命名字段、值与合法域(fail-closed)。"""


class GreenPulseError(Exception):
    """所有 GreenPulse 错误的基类。"""


class ConfigError(GreenPulseError):
    """配置缺失、未知键、出域值(DFR DEP-6)。"""


class SignalError(GreenPulseError):
    """信号层错误基类(DFR DEP-1)。"""


class SignalUnavailableError(SignalError):
    """Provider 不可达(DEP-1.1)。消费端必须显式降级,绝不静默沿用旧曲线。"""


class StaleForecastError(SignalError):
    """预报过期(DEP-1.2):生成时间早于配置的最大时龄。"""


class MissingIntervalError(SignalError):
    """请求区间中段缺失(DEP-1.3)。禁止零填/插值补齐后继续。"""


class SeriesSchemaError(SignalError):
    """口径标签缺失、单位异常、负值、量级离谱(DEP-1.4)。"""


class ResolutionMismatchError(SignalError):
    """时间步距与声明分辨率不符(DEP-1.5)。"""


class DuplicateTimestampError(SignalError):
    """重复时间戳(DEP-1.6)。"""


class NaiveTimestampError(SignalError):
    """无时区信息的时间戳(DEP-1.7)。边界处统一为 UTC。"""


class LookaheadError(GreenPulseError):
    """前视泄漏(DEP-4.4):调度器试图读取决策时刻之后的实时信号。"""


class RecordSchemaError(GreenPulseError):
    """实验/决策记录文件损坏或列不匹配(DEP-8.1)。拒绝合并混入。"""


class MissingArtifactError(GreenPulseError):
    """运行声明的产物缺失但流程报成功(DEP-8.2)。"""
