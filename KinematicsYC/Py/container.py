from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from consts import TWENTY_FOOT, FORTY_FOOT

if TYPE_CHECKING:
    from slot import Slot


# 外部调用：重置计数器（用于测试）
_container_count = 0


def reset_container_count() -> None:
    global _container_count
    _container_count = 0


def get_container_count() -> int:
    return _container_count


@dataclass
class Group:
    """集装箱分组，同一票货物（PSWC）的集装箱归为同一 Group。"""
    index: int
    te_us: int          # 1 = 20尺, 2 = 40尺
    size: int = 0       # 含义不明确，代码中未使用
    containers: List['Container'] = field(default_factory=list)
    timestamp_unstack: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"Group#{self.index}"


@dataclass
class Container:
    """集装箱实体。"""
    group: Group
    index: Optional[int] = None
    size: Optional[str] = None
    block: Optional['Block'] = None       # type: ignore[name-defined]
    slot: Optional['Slot'] = None          # type: ignore[name-defined]

    def __post_init__(self):
        global _container_count
        _container_count += 1
        self.index = _container_count
        if self.size is None:
            self.size = FORTY_FOOT if self.group.te_us == 2 else TWENTY_FOOT

    def __repr__(self) -> str:
        sz = "40" if self.size == FORTY_FOOT else "20"
        return f"Container(Index={self.index}, Size={sz}, Group={self.group})"


# 类属性（dataclass 定义之后定义，不受 field 顺序约束）
Container.Height = 2.59  # 集装箱高度（米）
