from typing import Dict, List, Optional, TYPE_CHECKING

from consts import TWENTY_FOOT, FORTY_FOOT

if TYPE_CHECKING:
    from container import Container


class Bay:
    """单个贝位，管理同一尺寸的所有集装箱在多个 Row 上的堆叠。"""

    def __init__(self, block: 'Block', size: str):
        self._container_size: str = size
        self.stacks: Dict[int, List['Container']] = {
            i: [] for i in range(1, block.num_rows + 1)
        }
        self.block = block

    @property
    def container_size(self) -> str:
        return self._container_size

    @property
    def num_containers(self) -> int:
        """所有排的集装箱总数。"""
        return sum(len(stack) for stack in self.stacks.values())

    @property
    def num_te_us(self) -> int:
        """总 TEUs 数。"""
        return self.num_containers * (2 if self.container_size == FORTY_FOOT else 1)

    @property
    def is_full(self) -> bool:
        """当且仅当所有排均达到最大层数时为 True。"""
        for stack in self.stacks.values():
            if len(stack) < self.block.max_num_tiers:
                return False
        return True

    def get_row_index_to_stack(self, rs) -> Optional[int]:
        """
        为集装箱选择最合适的 Row 位置。

        约束条件：
          1. 不超过最大层数限制
          2. 与最低排的高度差不超过4层
          3. 上侧（排号+1）不能更矮（避免陡坡）
          4. 下侧（排号-1）不能更矮（避免陡坡）
          5. 上侧无"洞"：若当前排与上排等高，则上方不能有更高的排
          6. 下侧无"洞"：若当前排与下排等高，则下方不能有更高的排
        """
        indices: List[int] = []
        min_height = min(len(stack) for stack in self.stacks.values())
        num_rows = len(self.stacks)

        for i in range(1, num_rows + 1):
            stack_i = self.stacks[i]

            # 限制1: 避免超过最大层数
            if len(stack_i) >= self.block.max_num_tiers:
                continue
            # 限制2: 与最低排高度差不大于4层
            if len(stack_i) >= min_height + 4:
                continue
            # 限制3: 上侧无陡坡
            if i < num_rows and len(stack_i) > len(self.stacks[i + 1]):
                continue
            # 限制4: 下侧无陡坡
            if i > 1 and len(stack_i) > len(self.stacks[i - 1]):
                continue
            # 限制5: 上侧无"洞"
            if i < num_rows - 1 and len(stack_i) == len(self.stacks[i + 1]):
                if any(len(self.stacks[r]) > len(stack_i) for r in range(i + 2, num_rows + 1)):
                    continue
            # 限制6: 下侧无"洞"
            if i > 2 and len(stack_i) == len(self.stacks[i - 1]):
                if any(len(self.stacks[r]) > len(stack_i) for r in range(1, i - 1)):
                    continue

            indices.append(i)

        if not indices:
            return None
        return indices[rs.randint(0, len(indices) - 1)]

    def stack_container(
        self,
        container: 'Container',
        rs,
        row_index: Optional[int] = None,
        row_index_out: Optional[List[int]] = None,
        tier_index: Optional[List[int]] = None,
    ) -> bool:
        """
        重载1（row_index=None）：通过随机 Row 分配。
        重载2（指定 row_index）：在指定 Row 堆叠。
        tier_index: 输出参数，通过列表传引用语义返回堆叠后的层号。
        row_index: 传入 int 则在指定行堆叠；传入 list（如 [0]）则将结果写入 list[0]（模拟 C# ref）。
        返回是否成功。
        """
        # 处理 list wrapper（模拟 C# ref 语义）
        # row_index_out: 提取 list wrapper，后续递归调用时原样传递
        _row_index_out: Optional[List[int]] = row_index_out  # 初始值来自参数
        _row_index = row_index
        if isinstance(row_index, list):
            _row_index_out = row_index  # 覆盖：list wrapper 优先
            _row_index = None

        if _row_index is None:
            ri = self.get_row_index_to_stack(rs)
            if ri is None:
                return False
            # row_index_out 原样传递到递归调用
            return self.stack_container(container, rs, row_index=ri,
                                        row_index_out=_row_index_out, tier_index=tier_index)

        if container.size != self.container_size:
            return False
        if len(self.stacks[_row_index]) >= self.block.max_num_tiers:
            return False
        self.stacks[_row_index].append(container)
        new_tier = len(self.stacks[_row_index])
        if _row_index_out is not None:
            _row_index_out[0] = _row_index
        if tier_index is not None:
            tier_index[0] = new_tier
        return True
