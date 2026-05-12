from typing import Dict, List, Optional, TYPE_CHECKING

from consts import TWENTY_FOOT, FORTY_FOOT

if TYPE_CHECKING:
    from bay import Bay
    from container import Container


class Block:
    """
    甲板区域（Block），管理堆场内所有 Bay 实例。
    负责 Bay 级别的集装箱分配决策。
    """

    count: int = 0  # 静态计数器

    # 物理尺寸常量（米）
    slot_length: float = 6.5
    slot_width: float = 2.5
    slot_height: float = 2.6

    def __init__(self, num_bays: int, num_rows: int, max_num_tiers: int):
        Block.count += 1
        self.index: int = Block.count
        self.bays: Dict[int, 'Bay'] = {}
        self.num_bays: int = num_bays
        self.num_rows: int = num_rows
        self.max_num_tiers: int = max_num_tiers

    @property
    def num_containers(self) -> int:
        return sum(bay.num_containers for bay in self.bays.values())

    @property
    def num_te_us(self) -> int:
        return sum(bay.num_te_us for bay in self.bays.values())

    @property
    def capacity_te_us(self) -> int:
        return (self.num_bays + 1) // 2 * self.num_rows * self.max_num_tiers

    def get_bay_index_to_stack(self, container_size: str, rs) -> Optional[int]:
        """
        为集装箱选择最合适的 Bay 位置。

        算法目标：
          1. 优先使用已有且未满的同尺寸 Bay
          2. 新建 Bay 时保持合理的空间布局（避免零散的单独 Bay）
          3. 平衡 20 尺和 40 尺 Bay 的利用率
        """
        twenty_feet_bays = [
            b for b in self.bays.values() if b.container_size == TWENTY_FOOT
        ]
        forty_feet_bays = [
            b for b in self.bays.values() if b.container_size == FORTY_FOOT
        ]

        avg_20 = (
            sum(b.num_containers for b in twenty_feet_bays) / len(twenty_feet_bays)
            if twenty_feet_bays else 0.0
        )
        avg_40 = (
            sum(b.num_containers for b in forty_feet_bays) / len(forty_feet_bays)
            if forty_feet_bays else 0.0
        )
        less_twenty_bays = avg_20 >= avg_40

        indices: List[int] = []

        if container_size == TWENTY_FOOT:
            # 特殊处理：如果是第一个 Bay，直接接受，避免无法起仓
            if not self.bays:
                return 1
            for i in range(1, self.num_bays * 2, 2):
                if i in self.bays:
                    if not self.bays[i].is_full:
                        indices.append(i)
                else:
                    if (
                        len(twenty_feet_bays) == 0
                        or (
                            (i == 1 or i - 2 in self.bays or i - 3 in self.bays)
                            and (
                                i + 2 in self.bays
                                or i + 3 in self.bays
                                or i == self.num_bays * 2 - 1
                            )
                        )
                        or less_twenty_bays
                    ):
                        if i - 1 not in self.bays and i + 1 not in self.bays:
                            if (
                                i - 2 in self.bays
                                or i - 3 in self.bays
                                or i + 2 in self.bays
                                or i + 3 in self.bays
                            ):
                                indices.append(i)

        elif container_size == FORTY_FOOT:
            for i in range(2, self.num_bays * 2, 2):
                if i in self.bays:
                    if not self.bays[i].is_full:
                        indices.append(i)
                else:
                    if len(forty_feet_bays) == 0 or not less_twenty_bays:
                        if (
                            i - 1 not in self.bays
                            and i + 1 not in self.bays
                            and i - 2 not in self.bays
                            and i + 2 not in self.bays
                        ):
                            indices.append(i)
        else:
            raise ValueError(f"Unknown container size: {container_size}")

        if not indices:
            return None
        return indices[rs.randint(0, len(indices) - 1)]

    def stack_container(
        self,
        container: 'Container',
        rs,
        bay_index: Optional[int] = None,
        bay_index_out: Optional[List[int]] = None,
        row_index: Optional[List[int]] = None,
        tier_index: Optional[List[int]] = None,
    ) -> bool:
        """
        重载1（bay_index=None）：通过随机 Bay 分配。
        重载2（指定 bay_index）：在指定 Bay 堆叠。
        bay_index_out: bay 索引输出参数，通过列表传引用语义返回选中的 bay 号。
        row_index: 行索引输出参数，通过列表传引用语义返回选中的 row 号。
        tier_index: 层号输出参数，通过列表传引用语义返回堆叠后的层号。
        返回是否成功。
        """
        if bay_index is None:
            bi = self.get_bay_index_to_stack(container.size, rs)
            if bi is None:
                return False
            return self.stack_container(container, rs, bay_index=bi,
                                        bay_index_out=bay_index_out,
                                        row_index=row_index, tier_index=tier_index)

        bay = self._create_bay_if_not_exist(bay_index, container.size)
        if bay_index_out is not None:
            bay_index_out[0] = bay_index
        return bay.stack_container(container, rs, row_index=row_index, tier_index=tier_index)

    def _create_bay_if_not_exist(self, bay_index: int, size: str) -> 'Bay':
        from bay import Bay

        if bay_index not in self.bays:
            max_idx = self.num_bays * 2 - 1
            if bay_index < 1 or bay_index > max_idx:
                raise ValueError("Bay Index Infeasible.")
            if (bay_index - 1) in self.bays or (bay_index + 1) in self.bays:
                raise ValueError("Bay Index Infeasible.")
            if bay_index % 2 == 0 and (
                (bay_index - 2) in self.bays or (bay_index + 2) in self.bays
            ):
                raise ValueError("Bay Index Infeasible.")
            self.bays[bay_index] = Bay(self, size)
        return self.bays[bay_index]
