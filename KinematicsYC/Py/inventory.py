from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from consts import TWENTY_FOOT, FORTY_FOOT
from slot import Slot

if TYPE_CHECKING:
    from container import Container, Group


class JobType:
    Stacking = "Stacking"
    Unstacking = "Unstacking"


@dataclass
class GroundSlot:
    """单个槽位（bay x row）的堆叠容器。"""
    gs_stack: List['Container'] = field(default_factory=list)
    flipped_layers: int = 0  # 已翻动层数累计


class Inventory:
    """
    全局库存操作类。
    负责槽位分配、翻箱逻辑、重排目标选择等核心操作。
    """

    def __init__(self):
        # 键: (blockId, dim1, dim2) -> GroundSlot
        # dim1 = ToDim1(bay) 将 bay 索引压缩为连续编号 1..NumBays
        self._map: Dict[Tuple[int, int, int], GroundSlot] = {}

    # ---------- 内部工具 ----------

    @staticmethod
    def _to_dim1(bay: int) -> int:
        """将原始 bay 索引（1..NumBays*2-1）压缩为逻辑索引（1..NumBays）。"""
        return bay // 2 if bay % 2 == 0 else (bay + 1) // 2

    def _get_ground_slot(self, block: 'Block', slot: Slot) -> GroundSlot:  # type: ignore[name-defined]
        """获取或创建指定 Block + Slot 对应的 GroundSlot。"""
        gs_idx = (block.index, self._to_dim1(slot.bay), slot.row)
        if gs_idx not in self._map:
            self._map[gs_idx] = GroundSlot()
        return self._map[gs_idx]

    @staticmethod
    def _is_forty(c: Optional['Container']) -> bool:
        return c is not None and c.size == FORTY_FOOT

    @staticmethod
    def _is_twenty(c: Optional['Container']) -> bool:
        return c is not None and c.size == TWENTY_FOOT

    def _get_height(self, block: 'Block', slot: Slot) -> int:  # type: ignore[name-defined]
        return len(self._get_ground_slot(block, slot).gs_stack)

    def _peek(self, block: 'Block', slot: Slot) -> Optional['Container']:  # type: ignore[name-defined]
        gs = self._get_ground_slot(block, slot)
        return gs.gs_stack[-1] if gs.gs_stack else None

    # ---------- 40尺放置可行性 ----------

    def _is_bay_blocked_for_20(self, block: 'Block', bay: int) -> bool:  # type: ignore[name-defined]
        """判断指定 bay 是否被 40 尺箱阻塞（20 尺箱不可放入）。"""
        for row in range(1, block.num_rows + 1):
            top = self._peek(block, Slot(bay, row, 1))
            if self._is_forty(top):
                return True
        return False

    def _can_place_forty(self, block: 'Block', bay: int, row: int) -> Tuple[bool, int]:  # type: ignore[name-defined]
        """
        判断在指定 bay（偶数中心位）是否可以放置 40 尺箱。
        返回 (can_place, tier)。
        """
        tier = -1
        if bay % 2 != 0:
            return False, tier
        if bay <= 1 or bay >= block.num_bays * 2 - 1:
            return False, tier
        left_bay = bay - 1
        right_bay = bay + 1
        h1 = self._get_height(block, Slot(left_bay, row, 1))
        h2 = self._get_height(block, Slot(right_bay, row, 1))
        top1 = self._peek(block, Slot(left_bay, row, 1))
        top2 = self._peek(block, Slot(right_bay, row, 1))
        if self._is_twenty(top1) or self._is_twenty(top2):
            return False, tier
        for r in range(1, block.num_rows + 1):
            if self._is_twenty(self._peek(block, Slot(left_bay, r, 1))):
                return False, tier
            if self._is_twenty(self._peek(block, Slot(right_bay, r, 1))):
                return False, tier
        tops_cross_same_forty = self._is_forty(top1) and top1 is top2
        tops_without_forty = not self._is_forty(top1) and not self._is_forty(top2)
        if not (h1 == h2 and (tops_cross_same_forty or tops_without_forty)):
            return False, tier
        if h1 >= block.max_num_tiers:
            return False, tier
        tier = h1 + 1
        return True, tier

    # ---------- Bay 风格堆叠限制验证 ----------

    def _get_heights(self, block: 'Block', b: int) -> List[int]:  # type: ignore[name-defined]
        """获取指定 bay 所有 row 的高度（1-indexed）。"""
        heights = [0] * (block.num_rows + 1)
        for r in range(1, block.num_rows + 1):
            heights[r] = self._get_height(block, Slot(b, r, 1))
        return heights

    def _is_row_valid_by_bay_rules(self, block: 'Block', bay: int, row: int, size: str) -> bool:  # type: ignore[name-defined]
        """验证指定 bay/row 位置是否满足 Bay 风格的堆叠限制（6项）。"""
        max_tier = block.max_num_tiers

        if size == FORTY_FOOT:
            h1 = self._get_heights(block, bay - 1)
            h2 = self._get_heights(block, bay + 1)
            heights = [0] * (block.num_rows + 1)
            for r in range(1, block.num_rows + 1):
                heights[r] = max(h1[r], h2[r])
        else:
            heights = self._get_heights(block, bay)

        current_height = heights[row]
        if current_height >= max_tier:
            return False

        min_height = min(heights[1:]) if block.num_rows > 0 else 0
        if current_height >= min_height + 4:
            return False

        if row < block.num_rows and current_height > heights[row + 1]:
            return False

        if row > 1 and current_height > heights[row - 1]:
            return False

        if row < block.num_rows - 1 and current_height == heights[row + 1]:
            if any(heights[r] > current_height for r in range(row + 2, block.num_rows + 1)):
                return False

        if row > 2 and current_height == heights[row - 1]:
            if any(heights[r] > current_height for r in range(1, row - 1)):
                return False

        return True

    # ---------- 槽位分配（核心算法） ----------

    def allocate(
        self,
        container: 'Container',
        rs,
        apply_row_stacking_limit: bool = False,
    ) -> Optional[Slot]:
        """
        为集装箱分配最优槽位，采用四阶段优先策略：
          Stage 1: 同 Group（PSWC）已有的最高可堆放位置
          Stage 2: 空槽位（随机选择）
          Stage 3: 最高未满槽位（优先取高）
          Stage 4: 返回 None（无有效位置）
        """
        block = container.block
        max_bay_index = block.num_bays * 2 - 1

        # 生成随机顺序的 row 列表
        rows = list(range(1, block.num_rows + 1))
        import random
        random.shuffle(rows)

        # ------- Stage 1: 同 PSWC 已有位置 -------
        if container.size == FORTY_FOOT:
            for bay in range(2, max_bay_index, 2):
                for row in rows:
                    can_place, tier = self._can_place_forty(block, bay, row)
                    if not can_place:
                        continue
                    if apply_row_stacking_limit and not self._is_row_valid_by_bay_rules(block, bay, row, FORTY_FOOT):
                        continue
                    top_job = self._peek(block, Slot(bay - 1, row, 1))
                    if top_job is not None and top_job.group.index == container.group.index:
                        return Slot(bay, row, tier)
        else:
            for bay in range(1, max_bay_index + 1, 2):
                for row in rows:
                    if self._is_bay_blocked_for_20(block, bay):
                        continue
                    base_slot = Slot(bay, row, 1)
                    tier = self._get_height(block, base_slot)
                    if tier <= 0:
                        continue
                    if apply_row_stacking_limit and not self._is_row_valid_by_bay_rules(block, bay, row, TWENTY_FOOT):
                        continue
                    top_job = self._peek(block, base_slot)
                    if top_job is not None and top_job.group.index == container.group.index:
                        if tier < block.max_num_tiers:
                            return Slot(bay, row, tier + 1)

        # ------- Stage 2: 空槽位 -------
        if container.size == FORTY_FOOT:
            candidates: List[Tuple[int, int, int]] = []
            for bay in range(2, max_bay_index, 2):
                left_bay = bay - 1
                right_bay = bay + 1

                heights_consistent = True
                containers_consistent = True
                for r in range(1, block.num_rows + 1):
                    h_left = self._get_height(block, Slot(left_bay, r, 1))
                    h_right = self._get_height(block, Slot(right_bay, r, 1))
                    if h_left != h_right:
                        heights_consistent = False
                        break
                    top_left = self._peek(block, Slot(left_bay, r, 1))
                    top_right = self._peek(block, Slot(right_bay, r, 1))
                    if top_left is not None and top_right is not None and top_left is not top_right:
                        containers_consistent = False
                        break
                if not heights_consistent or not containers_consistent:
                    continue

                for row in rows:
                    if self._get_height(block, Slot(left_bay, row, 1)) != 0:
                        continue
                    if self._get_height(block, Slot(right_bay, row, 1)) != 0:
                        continue
                    can_place, tier = self._can_place_forty(block, bay, row)
                    if not can_place:
                        continue
                    if apply_row_stacking_limit and not self._is_row_valid_by_bay_rules(block, bay, row, FORTY_FOOT):
                        continue
                    candidates.append((bay, row, tier))

            if candidates:
                sel = candidates[rs.randint(0, len(candidates) - 1)]
                return Slot(sel[0], sel[1], sel[2])
        else:
            candidates: List[Tuple[int, int]] = []
            for bay in range(1, max_bay_index + 1, 2):
                for row in rows:
                    if self._is_bay_blocked_for_20(block, bay):
                        continue
                    if self._get_height(block, Slot(bay, row, 1)) == 0:
                        if apply_row_stacking_limit and not self._is_row_valid_by_bay_rules(block, bay, row, TWENTY_FOOT):
                            continue
                        candidates.append((bay, row))
            if candidates:
                sel = candidates[rs.randint(0, len(candidates) - 1)]
                return Slot(sel[0], sel[1], 1)

        # ------- Stage 3: 最高未满槽位 -------
        best_bay = -1
        best_row = -1
        best_height = -1

        if container.size == FORTY_FOOT:
            for bay in range(2, max_bay_index, 2):
                for row in rows:
                    can_place, tier = self._can_place_forty(block, bay, row)
                    if not can_place:
                        continue
                    if apply_row_stacking_limit and not self._is_row_valid_by_bay_rules(block, bay, row, FORTY_FOOT):
                        continue
                    h = tier - 1
                    if h > best_height:
                        best_height = h
                        best_bay = bay
                        best_row = row
        else:
            for bay in range(1, max_bay_index + 1, 2):
                for row in rows:
                    if self._is_bay_blocked_for_20(block, bay):
                        continue
                    if apply_row_stacking_limit and not self._is_row_valid_by_bay_rules(block, bay, row, TWENTY_FOOT):
                        continue
                    tier = self._get_height(block, Slot(bay, row, 1))
                    if tier < block.max_num_tiers and tier > best_height:
                        best_height = tier
                        best_bay = bay
                        best_row = row

        if best_bay > 0:
            return Slot(best_bay, best_row, best_height + 1)

        return None

    # ---------- 出栈判断 ----------

    def unstack_without_reshuffle(self, container: 'Container') -> bool:
        """判断取箱是否无需重排（无翻箱）。"""
        top = self._peek(container.block, container.slot)
        if top is None:
            return True
        return container.group == top.group

    # ---------- 状态更新 ----------

    def update(self, container: 'Container', op_type: str) -> None:
        """根据操作类型更新库存状态。"""
        if container.slot is None or container.slot.bay == 0 or container.slot.row == 0 or container.slot.tier == 0:
            return
        if op_type == JobType.Stacking:
            self._stack(container.block, container.slot, container)
        else:
            self._unstack(container.block, container.slot)

    def _stack(self, block: 'Block', slot: Slot, container: 'Container') -> None:  # type: ignore[name-defined]
        """将集装箱放入指定槽位。"""
        if container.size == FORTY_FOOT:
            left_bay = slot.bay - 1
            right_bay = slot.bay + 1
            self._get_ground_slot(block, Slot(left_bay, slot.row, slot.tier)).gs_stack.append(container)
            self._get_ground_slot(block, Slot(right_bay, slot.row, slot.tier)).gs_stack.append(container)
        else:
            self._get_ground_slot(block, slot).gs_stack.append(container)

    def _unstack(self, block: 'Block', slot: Slot) -> Optional['Container']:  # type: ignore[name-defined]
        """从指定槽位取出顶部集装箱，返回被移除的 Container 引用。"""
        gs = self._get_ground_slot(block, slot)
        if not gs.gs_stack:
            return None
        top = gs.gs_stack.pop()
        if top.size == FORTY_FOOT:
            gs_pair = self._get_ground_slot(block, Slot(slot.bay + 2, slot.row, slot.tier))
            if gs_pair.gs_stack:
                gs_pair.gs_stack.pop()
        return top

    def peek(self, block: 'Block', slot: Slot) -> Optional['Container']:  # type: ignore[name-defined]
        """查看指定槽位顶部的集装箱（不修改状态）。"""
        gs = self._get_ground_slot(block, slot)
        return gs.gs_stack[-1] if gs.gs_stack else None

    def get_height(self, block: 'Block', slot: Slot) -> int:  # type: ignore[name-defined]
        """获取指定槽位的堆叠高度。"""
        return len(self._get_ground_slot(block, slot).gs_stack)

    # ---------- 按 Group 最优取箱选择 ----------

    def get_best_job_by_pswc(self, block: 'Block', group: 'Group') -> Optional['Container']:  # type: ignore[name-defined]
        """在指定 Block 内找到属于给定 Group 的所有集装箱中最优（最容易取出）的一个。"""
        best: Optional['Container'] = None
        best_depth = float('inf')
        best_height = float('-inf')
        best_bay = float('-inf')
        best_row = float('-inf')

        target_size = FORTY_FOOT if group.te_us == 2 else TWENTY_FOOT

        for gs_idx, gs in self._map.items():
            block_id, dim1, dim2 = gs_idx
            if block_id != block.index:
                continue
            if not gs.gs_stack:
                continue

            for idx in range(len(gs.gs_stack) - 1, -1, -1):
                container = gs.gs_stack[idx]
                if container.size != target_size or container.group.index != group.index:
                    continue

                depth_from_top = (len(gs.gs_stack) - 1) - idx
                height = len(gs.gs_stack)
                bay = dim1
                row = dim2

                better = False
                if depth_from_top < best_depth:
                    better = True
                elif depth_from_top == best_depth:
                    if height > best_height:
                        better = True
                    elif height == best_height:
                        if bay > best_bay:
                            better = True
                        elif bay == best_bay and row > best_row:
                            better = True

                if better:
                    best = container
                    best_depth = depth_from_top
                    best_height = height
                    best_bay = bay
                    best_row = row

                break
        return best

    # ---------- 重排目标选择 ----------

    def decide_reshuffle_target(
        self,
        r_container: 'Container',
        ref_container: 'Container',
    ) -> Optional[Slot]:
        """
        当取箱需要翻箱时，确定将箱移至哪个替代槽位。
        Case A: 当前 bay 未完全堆满，优先在 bay 内部解决
        Case B: 当前 bay 已满，需要跨 bay 移动
        """
        block = r_container.block
        bay = r_container.slot.bay

        def is_bay_blocked_for_20(b: int) -> bool:
            for row in range(1, block.num_rows + 1):
                top_self = self._peek(block, Slot(b, row, 1))
                if self._is_forty(top_self):
                    return True
                top_left = self._peek(block, Slot(b - 1, row, 1)) if b > 1 else None
                top_right = self._peek(block, Slot(b + 1, row, 1)) if b < block.num_bays else None
                if top_left is not None and self._is_forty(top_left) and top_self is not None and top_left is top_self:
                    return True
                if top_right is not None and self._is_forty(top_right) and top_self is not None and top_right is top_self:
                    return True
            return False

        def can_place_forty(b: int, row: int) -> Tuple[bool, int]:
            tier = -1
            if b >= block.num_bays:
                return False, tier
            h1 = self._get_height(block, Slot(b, row, 1))
            h2 = self._get_height(block, Slot(b + 1, row, 1))
            top1 = self._peek(block, Slot(b, row, 1))
            top2 = self._peek(block, Slot(b + 1, row, 1))
            if self._is_twenty(top1) or self._is_twenty(top2):
                return False, tier
            for r in range(1, block.num_rows + 1):
                if self._is_twenty(self._peek(block, Slot(b, r, 1))):
                    return False, tier
                if self._is_twenty(self._peek(block, Slot(b + 1, r, 1))):
                    return False, tier
            tops_cross_same_forty = self._is_forty(top1) and top1 is top2
            tops_without_forty = not self._is_forty(top1) and not self._is_forty(top2)
            if not (h1 == h2 and (tops_cross_same_forty or tops_without_forty)):
                return False, tier
            if h1 >= block.max_num_tiers:
                return False, tier
            tier = h1 + 1
            return True, tier

        def bay_fully_stacked(b: int) -> bool:
            for row in range(1, block.num_rows + 1):
                if self._get_height(block, Slot(b, row, 1)) < block.max_num_tiers:
                    return False
            return True

        def has_same_pswc_top(s: Slot) -> bool:
            top = self._peek(block, Slot(s.bay, s.row, 1))
            return top is not None and top.group == ref_container.group

        def is_current_gs(s: Slot) -> bool:
            return s.bay == r_container.slot.bay and s.row == r_container.slot.row

        # Case A: 当前 bay 未完全堆满
        if not bay_fully_stacked(bay):
            # SamePswcTop
            best1: Optional[Slot] = None
            best1_height = -1
            for row in range(1, block.num_rows + 1):
                tier = self._get_height(block, Slot(bay, row, 1))
                if tier == 0 or tier >= block.max_num_tiers:
                    continue
                top = self._peek(block, Slot(bay, row, 1))
                if top is None or top.group != ref_container.group:
                    continue
                if r_container.size == TWENTY_FOOT and is_bay_blocked_for_20(bay):
                    continue
                can_pl, forty_tier = (False, -1) if r_container.size == FORTY_FOOT else (True, -1)
                if r_container.size == FORTY_FOOT:
                    can_pl, forty_tier = can_place_forty(bay, row)
                    if not can_pl:
                        continue
                cur_h = (forty_tier - 1 if r_container.size == FORTY_FOOT else tier)
                next_t = (forty_tier if r_container.size == FORTY_FOOT else tier + 1)
                cand = Slot(bay, row, next_t)
                if is_current_gs(cand):
                    continue
                if cur_h > best1_height:
                    best1_height = cur_h
                    best1 = cand
            if best1 is not None and not is_current_gs(best1):
                return best1

            # ClosestEmpty
            best2: Optional[Slot] = None
            best2_dist = float('inf')
            for row in range(1, block.num_rows + 1):
                if self._get_height(block, Slot(bay, row, 1)) != 0:
                    continue
                if r_container.size == TWENTY_FOOT and is_bay_blocked_for_20(bay):
                    continue
                if r_container.size == FORTY_FOOT:
                    can_pl, forty_tier = can_place_forty(bay, row)
                    if not can_pl:
                        continue
                dist = abs(row - r_container.slot.row)
                if dist < best2_dist:
                    cand = Slot(bay, row, (forty_tier if r_container.size == FORTY_FOOT else 1))
                    if not is_current_gs(cand):
                        best2_dist = dist
                        best2 = cand
            if best2 is not None and not is_current_gs(best2):
                return best2

            # TallestNonFull
            best3: Optional[Slot] = None
            best3_height = -1
            best3_dist = float('inf')
            for row in range(1, block.num_rows + 1):
                tier = self._get_height(block, Slot(bay, row, 1))
                if tier >= block.max_num_tiers:
                    continue
                if r_container.size == TWENTY_FOOT and is_bay_blocked_for_20(bay):
                    continue
                if r_container.size == FORTY_FOOT:
                    can_pl, forty_tier = can_place_forty(bay, row)
                    if not can_pl:
                        continue
                dist = abs(row - r_container.slot.row)
                cur_h = (forty_tier - 1 if r_container.size == FORTY_FOOT else tier)
                next_t = (forty_tier if r_container.size == FORTY_FOOT else tier + 1)
                cand = Slot(bay, row, next_t)
                if is_current_gs(cand):
                    continue
                if cur_h > best3_height or (cur_h == best3_height and dist < best3_dist):
                    best3_height = cur_h
                    best3_dist = dist
                    best3 = cand
            if best3 is not None and not is_current_gs(best3):
                return best3

        # Case B: bay 已满，需要跨 bay 移动
        def pick_across(picker, prefer_different_pswc: bool):
            chosen: Optional[Slot] = None
            chosen_bay_dist = float('inf')
            chosen_row_dist = float('inf')
            for b in range(1, block.num_bays + 1):
                cand = picker(b)
                if cand is None:
                    continue
                if is_current_gs(cand):
                    continue
                if prefer_different_pswc and has_same_pswc_top(cand):
                    continue
                bay_dist = abs(b - bay)
                row_dist = abs(cand.row - r_container.slot.row)
                if bay_dist < chosen_bay_dist or (bay_dist == chosen_bay_dist and row_dist < chosen_row_dist):
                    chosen = cand
                    chosen_bay_dist = bay_dist
                    chosen_row_dist = row_dist
            return chosen

        def same_pswc_top(b: int) -> Optional[Slot]:
            best: Optional[Slot] = None
            best_h = -1
            for row in range(1, block.num_rows + 1):
                tier = self._get_height(block, Slot(b, row, 1))
                if tier == 0 or tier >= block.max_num_tiers:
                    continue
                top = self._peek(block, Slot(b, row, 1))
                if top is None or top.group != ref_container.group:
                    continue
                if r_container.size == TWENTY_FOOT and is_bay_blocked_for_20(b):
                    continue
                if r_container.size == FORTY_FOOT:
                    can_pl, forty_tier = can_place_forty(b, row)
                    if not can_pl:
                        continue
                    cur_h = forty_tier - 1
                    next_t = forty_tier
                else:
                    cur_h = tier
                    next_t = tier + 1
                cand = Slot(b, row, next_t)
                if is_current_gs(cand):
                    continue
                if cur_h > best_h:
                    best_h = cur_h
                    best = cand
            return best

        def closest_empty(b: int) -> Optional[Slot]:
            best: Optional[Slot] = None
            best_dist = float('inf')
            for row in range(1, block.num_rows + 1):
                if self._get_height(block, Slot(b, row, 1)) != 0:
                    continue
                if r_container.size == TWENTY_FOOT and is_bay_blocked_for_20(b):
                    continue
                if r_container.size == FORTY_FOOT:
                    can_pl, forty_tier = can_place_forty(b, row)
                    if not can_pl:
                        continue
                dist = abs(row - r_container.slot.row)
                if dist < best_dist:
                    cand = Slot(b, row, (forty_tier if r_container.size == FORTY_FOOT else 1))
                    if not is_current_gs(cand):
                        best_dist = dist
                        best = cand
            return best

        def tallest_non_full(b: int) -> Optional[Slot]:
            best: Optional[Slot] = None
            best_h = -1
            best_dist = float('inf')
            for row in range(1, block.num_rows + 1):
                tier = self._get_height(block, Slot(b, row, 1))
                if tier >= block.max_num_tiers:
                    continue
                if r_container.size == TWENTY_FOOT and is_bay_blocked_for_20(b):
                    continue
                if r_container.size == FORTY_FOOT:
                    can_pl, forty_tier = can_place_forty(b, row)
                    if not can_pl:
                        continue
                dist = abs(row - r_container.slot.row)
                cur_h = (forty_tier - 1 if r_container.size == FORTY_FOOT else tier)
                next_t = (forty_tier if r_container.size == FORTY_FOOT else tier + 1)
                cand = Slot(b, row, next_t)
                if is_current_gs(cand):
                    continue
                if cur_h > best_h or (cur_h == best_h and dist < best_dist):
                    best_h = cur_h
                    best_dist = dist
                    best = cand
            return best

        best_slot: Optional[Slot] = None
        best_slot = (
            pick_across(same_pswc_top, True)
            or pick_across(closest_empty, True)
            or pick_across(tallest_non_full, True)
            or pick_across(same_pswc_top, False)
            or pick_across(closest_empty, False)
            or pick_across(tallest_non_full, False)
        )
        return best_slot
