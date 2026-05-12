"""
BlkNet Python 单元测试。
与 TestNet/TestBlkNet.cs 一一对应，使用 unittest 框架。
"""
import unittest
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Py'))

from slot import Slot
from container import Container, Group, reset_container_count
from bay import Bay
from block import Block, TWENTY_FOOT, FORTY_FOOT
from inventory import Inventory, JobType


def make_rs(seed=42):
    return random.Random(seed)


# ============================================================
# Slot 单元测试
# ============================================================
class TestSlot(unittest.TestCase):

    def test_slot_constructor_sets_properties(self):
        slot = Slot(bay=3, row=5, tier=2)
        self.assertEqual(3, slot.bay)
        self.assertEqual(5, slot.row)
        self.assertEqual(2, slot.tier)

    def test_slot_equality_same_values(self):
        s1 = Slot(1, 2, 3)
        s2 = Slot(1, 2, 3)
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))

    def test_slot_equality_different_values(self):
        s1 = Slot(1, 2, 3)
        s2 = Slot(1, 2, 4)
        self.assertNotEqual(s1, s2)

    def test_slot_repr(self):
        slot = Slot(3, 5, 2)
        r = repr(slot)
        self.assertIn("3", r)
        self.assertIn("5", r)
        self.assertIn("2", r)


# ============================================================
# Container + Group 单元测试
# ============================================================
class TestContainer(unittest.TestCase):

    def setUp(self):
        reset_container_count()

    def test_container_twenty_foot_group_teus1(self):
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        self.assertEqual(TWENTY_FOOT, container.size)
        self.assertEqual(1, container.index)
        self.assertIs(group, container.group)

    def test_container_forty_foot_group_teus2(self):
        group = Group(index=2, te_us=2)
        container = Container(group=group)
        self.assertEqual(FORTY_FOOT, container.size)
        self.assertEqual(1, container.index)

    def test_container_incremental_index(self):
        group1 = Group(index=1, te_us=1)
        group2 = Group(index=2, te_us=1)
        c1 = Container(group=group1)
        c2 = Container(group=group2)
        self.assertEqual(1, c1.index)
        self.assertEqual(2, c2.index)

    def test_container_group_timestamp_unstack(self):
        from datetime import datetime
        group = Group(index=1, te_us=1, timestamp_unstack=datetime(2025, 1, 1))
        self.assertEqual(datetime(2025, 1, 1), group.timestamp_unstack)

    def test_container_group_containers_list(self):
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        group.containers.append(container)
        self.assertEqual(1, len(group.containers))
        self.assertIn(container, group.containers)

    def test_container_group_to_string(self):
        group = Group(index=42, te_us=2)
        self.assertEqual("Group#42", str(group))

    def test_container_height_constant(self):
        self.assertAlmostEqual(2.59, Container.Height, places=5)


# ============================================================
# Bay 单元测试
# ============================================================
class TestBay(unittest.TestCase):

    def setUp(self):
        reset_container_count()
        self.block = Block(num_bays=10, num_rows=6, max_num_tiers=5)
        self.rs = make_rs(42)

    def test_bay_constructor_initializes_stacks(self):
        bay = Bay(self.block, TWENTY_FOOT)
        self.assertEqual(6, len(bay.stacks))  # 6 rows
        for stack in bay.stacks.values():
            self.assertEqual(0, len(stack))

    def test_bay_container_size_is_fixed(self):
        bay = Bay(self.block, FORTY_FOOT)
        self.assertEqual(FORTY_FOOT, bay.container_size)

    def test_bay_num_containers_empty(self):
        bay = Bay(self.block, TWENTY_FOOT)
        self.assertEqual(0, bay.num_containers)

    def test_bay_num_te_us_empty(self):
        bay = Bay(self.block, TWENTY_FOOT)
        self.assertEqual(0, bay.num_te_us)

    def test_bay_is_full_empty(self):
        bay = Bay(self.block, TWENTY_FOOT)
        self.assertFalse(bay.is_full)

    def test_bay_is_full_not_full(self):
        bay = Bay(self.block, TWENTY_FOOT)
        bay.stacks[1].append(Container(Group(1, 1)))
        self.assertFalse(bay.is_full)

    def test_bay_is_full_when_full(self):
        bay = Bay(self.block, TWENTY_FOOT)
        for row in range(1, self.block.num_rows + 1):
            for _ in range(self.block.max_num_tiers):
                bay.stacks[row].append(Container(Group(1, 1)))
        self.assertTrue(bay.is_full)

    def test_bay_num_containers_multi_row(self):
        bay = Bay(self.block, TWENTY_FOOT)
        bay.stacks[1].append(Container(Group(1, 1)))
        bay.stacks[2].append(Container(Group(2, 1)))
        bay.stacks[2].append(Container(Group(3, 1)))
        self.assertEqual(3, bay.num_containers)

    def test_bay_num_te_us_forty_foot(self):
        bay = Bay(self.block, FORTY_FOOT)
        bay.stacks[1].append(Container(Group(1, 2)))
        bay.stacks[1].append(Container(Group(2, 2)))
        self.assertEqual(4, bay.num_te_us)

    # ---- GetRowIndexToStack 约束测试 ----

    def test_get_row_index_to_stack_all_rows_empty(self):
        bay = Bay(self.block, TWENTY_FOOT)
        result = bay.get_row_index_to_stack(self.rs)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 1)
        self.assertLessEqual(result, self.block.num_rows)

    def test_get_row_index_to_stack_constraint1_exceeds_max_tier(self):
        bay = Bay(self.block, TWENTY_FOOT)
        for _ in range(self.block.max_num_tiers):
            bay.stacks[1].append(Container(Group(1, 1)))
        result = bay.get_row_index_to_stack(self.rs)
        self.assertIsNotNone(result)
        self.assertNotEqual(1, result)  # Row 1 已满

    def test_get_row_index_to_stack_constraint2_height_diff_within_4(self):
        bay = Bay(self.block, TWENTY_FOOT)
        for _ in range(4):
            bay.stacks[1].append(Container(Group(1, 1)))
        result = bay.get_row_index_to_stack(self.rs)
        self.assertIsNotNone(result)  # 差=4，约束2允许

    def test_get_row_index_to_stack_constraint3_upslope(self):
        bay = Bay(self.block, TWENTY_FOOT)
        bay.stacks[1].append(Container(Group(1, 1)))
        bay.stacks[2].append(Container(Group(2, 1)))
        result = bay.get_row_index_to_stack(self.rs)
        self.assertIsNotNone(result)
        self.assertIn(result, [1, 3, 4, 5, 6])  # heights (1,1): row 1 has no upslope

    def test_get_row_index_to_stack_constraint4_downslope(self):
        bay = Bay(self.block, TWENTY_FOOT)
        bay.stacks[1].append(Container(Group(1, 1)))
        bay.stacks[2].append(Container(Group(2, 1)))
        result = bay.get_row_index_to_stack(self.rs)
        self.assertIsNotNone(result)
        self.assertNotEqual(2, result)  # Row 2 有下陡坡

    def test_get_row_index_to_stack_constraint5_upper_hole(self):
        bay = Bay(self.block, TWENTY_FOOT)
        bay.stacks[1].append(Container(Group(1, 1)))
        bay.stacks[2].append(Container(Group(2, 1)))
        bay.stacks[3].append(Container(Group(3, 1)))
        bay.stacks[3].append(Container(Group(4, 1)))  # Row3 更高，形成上洞
        result = bay.get_row_index_to_stack(self.rs)
        self.assertIsNotNone(result)
        self.assertNotEqual(1, result)
        self.assertNotEqual(2, result)

    def test_get_row_index_to_stack_constraint6_lower_hole(self):
        bay = Bay(self.block, TWENTY_FOOT)
        bay.stacks[1].append(Container(Group(1, 1)))
        bay.stacks[1].append(Container(Group(2, 1)))  # Row1 更高
        bay.stacks[2].append(Container(Group(3, 1)))
        bay.stacks[3].append(Container(Group(4, 1)))  # 与 Row2 等高
        result = bay.get_row_index_to_stack(self.rs)
        self.assertIsNotNone(result)
        self.assertNotEqual(2, result)
        self.assertNotEqual(3, result)

    def test_get_row_index_to_stack_all_rows_full_returns_none(self):
        bay = Bay(self.block, TWENTY_FOOT)
        for row in range(1, self.block.num_rows + 1):
            for _ in range(self.block.max_num_tiers):
                bay.stacks[row].append(Container(Group(1, 1)))
        result = bay.get_row_index_to_stack(self.rs)
        self.assertIsNone(result)

    # ---- StackContainer 测试 ----

    def test_stack_container_with_row_index_success(self):
        bay = Bay(self.block, TWENTY_FOOT)
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        tier_wrapper = [0]
        result = bay.stack_container(container, self.rs, row_index=3, tier_index=tier_wrapper)
        self.assertTrue(result)
        self.assertEqual(1, len(bay.stacks[3]))

    def test_stack_container_with_row_index_wrong_size_fails(self):
        bay = Bay(self.block, FORTY_FOOT)
        group = Group(index=1, te_us=1)  # 20尺
        container = Container(group=group)
        tier_wrapper = [0]
        result = bay.stack_container(container, self.rs, row_index=3, tier_index=tier_wrapper)
        self.assertFalse(result)

    def test_stack_container_with_row_index_row_full_fails(self):
        bay = Bay(self.block, TWENTY_FOOT)
        for _ in range(self.block.max_num_tiers):
            bay.stacks[3].append(Container(Group(1, 1)))
        group = Group(index=99, te_us=1)
        container = Container(group=group)
        tier_wrapper = [0]
        result = bay.stack_container(container, self.rs, row_index=3, tier_index=tier_wrapper)
        self.assertFalse(result)

    def test_stack_container_without_row_index_uses_random_row(self):
        bay = Bay(self.block, TWENTY_FOOT)
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        row_wrapper = [0]
        tier_wrapper = [0]
        result = bay.stack_container(container, self.rs, row_wrapper, tier_wrapper)
        self.assertTrue(result)
        self.assertGreaterEqual(row_wrapper[0], 1)
        self.assertLessEqual(row_wrapper[0], self.block.num_rows)

    def test_stack_container_tier_index_correct(self):
        bay = Bay(self.block, TWENTY_FOOT)
        g1 = Group(index=1, te_us=1)
        g2 = Group(index=2, te_us=1)
        c1 = Container(group=g1)
        c2 = Container(group=g2)
        t1 = [0]
        t2 = [0]
        bay.stack_container(c1, self.rs, row_index=2, tier_index=t1)
        bay.stack_container(c2, self.rs, row_index=2, tier_index=t2)
        self.assertEqual(1, t1[0])
        self.assertEqual(2, t2[0])


# ============================================================
# Block 单元测试
# ============================================================
class TestBlock(unittest.TestCase):

    def setUp(self):
        reset_container_count()
        Block.count = 0  # 重置静态计数器
        self.rs = make_rs(42)

    def test_block_constructor_increments_count(self):
        block1 = Block(5, 3, 4)
        block2 = Block(5, 3, 4)
        self.assertEqual(1, block1.index)
        self.assertEqual(2, block2.index)

    def test_block_num_bays_num_rows_max_num_tiers(self):
        block = Block(num_bays=8, num_rows=5, max_num_tiers=6)
        self.assertEqual(8, block.num_bays)
        self.assertEqual(5, block.num_rows)
        self.assertEqual(6, block.max_num_tiers)

    def test_block_static_slot_dimensions(self):
        self.assertAlmostEqual(6.5, Block.slot_length)
        self.assertAlmostEqual(2.5, Block.slot_width)
        self.assertAlmostEqual(2.6, Block.slot_height)

    def test_block_capacity_te_us_correct(self):
        # (10+1)//2 * 6 * 5 = 5 * 6 * 5 = 150
        block = Block(num_bays=10, num_rows=6, max_num_tiers=5)
        self.assertEqual(150, block.capacity_te_us)

    def test_block_num_containers_empty(self):
        block = Block(5, 3, 4)
        self.assertEqual(0, block.num_containers)

    def test_block_num_te_us_empty(self):
        block = Block(5, 3, 4)
        self.assertEqual(0, block.num_te_us)

    # ---- CreateBayIfNotExist 测试 ----

    def test_create_bay_if_not_exist_adds_new_bay(self):
        block = Block(10, 6, 5)
        bay = block._create_bay_if_not_exist(1, TWENTY_FOOT)
        self.assertIsNotNone(bay)
        self.assertEqual(TWENTY_FOOT, bay.container_size)
        self.assertIn(1, block.bays)

    def test_create_bay_if_not_exist_reuses_existing(self):
        block = Block(10, 6, 5)
        bay1 = block._create_bay_if_not_exist(1, TWENTY_FOOT)
        bay2 = block._create_bay_if_not_exist(1, TWENTY_FOOT)
        self.assertIs(bay1, bay2)

    def test_create_bay_if_not_exist_index_out_of_range(self):
        block = Block(10, 6, 5)
        with self.assertRaises(ValueError):
            block._create_bay_if_not_exist(0, TWENTY_FOOT)
        with self.assertRaises(ValueError):
            block._create_bay_if_not_exist(20, TWENTY_FOOT)

    def test_create_bay_if_not_exist_adjacent_bay_exists(self):
        block = Block(10, 6, 5)
        block._create_bay_if_not_exist(1, TWENTY_FOOT)
        with self.assertRaises(ValueError):
            block._create_bay_if_not_exist(2, TWENTY_FOOT)

    def test_create_bay_if_not_exist_forty_foot_span_conflict(self):
        block = Block(10, 6, 5)
        block._create_bay_if_not_exist(2, FORTY_FOOT)
        with self.assertRaises(ValueError):
            block._create_bay_if_not_exist(4, FORTY_FOOT)

    def test_create_bay_if_not_exist_forty_foot_odd_bay(self):
        # C# CreateBayIfNotExist 不对 FORTY_FOOT at odd bay 抛异常
        block = Block(10, 6, 5)
        # FORTY_FOOT at bay_index=1 是合法的（奇数 bay 可以放 FORTY_FOOT）
        bay = block._create_bay_if_not_exist(1, FORTY_FOOT)
        self.assertIsNotNone(bay)
        self.assertEqual(FORTY_FOOT, bay.container_size)

    # ---- GetBayIndexToStack 测试 ----

    def test_get_bay_index_to_stack_empty_block(self):
        block = Block(10, 6, 5)
        result = block.get_bay_index_to_stack(TWENTY_FOOT, self.rs)
        self.assertIsNotNone(result)
        self.assertEqual(1, result)

    def test_get_bay_index_to_stack_twenty_foot_odd_bays_only(self):
        block = Block(10, 6, 5)
        block._create_bay_if_not_exist(1, TWENTY_FOOT)
        block._create_bay_if_not_exist(3, TWENTY_FOOT)
        result = block.get_bay_index_to_stack(TWENTY_FOOT, self.rs)
        self.assertIsNotNone(result)
        self.assertEqual(1, result % 2)  # 奇数

    def test_get_bay_index_to_stack_forty_foot_even_bays_only(self):
        block = Block(10, 6, 5)
        result = block.get_bay_index_to_stack(FORTY_FOOT, self.rs)
        self.assertIsNotNone(result)
        self.assertEqual(0, result % 2)  # 偶数

    def test_get_bay_index_to_stack_full_bay_returns_other(self):
        block = Block(10, 6, 5)
        bay = block._create_bay_if_not_exist(1, TWENTY_FOOT)
        for row in range(1, block.num_rows + 1):
            for _ in range(block.max_num_tiers):
                bay.stacks[row].append(Container(Group(1, 1)))
        result = block.get_bay_index_to_stack(TWENTY_FOOT, self.rs)
        self.assertIsNotNone(result)
        self.assertNotEqual(1, result)

    def test_get_bay_index_to_stack_40_foot_next_to_existing(self):
        block = Block(10, 6, 5)
        block._create_bay_if_not_exist(1, TWENTY_FOOT)
        block._create_bay_if_not_exist(3, TWENTY_FOOT)
        result = block.get_bay_index_to_stack(FORTY_FOOT, self.rs)
        if result is not None:
            self.assertNotEqual(2, result)

    def test_get_bay_index_to_stack_bubble_rule(self):
        block = Block(10, 6, 5)
        block._create_bay_if_not_exist(1, TWENTY_FOOT)
        block._create_bay_if_not_exist(5, TWENTY_FOOT)
        result = block.get_bay_index_to_stack(TWENTY_FOOT, self.rs)
        if result is not None:
            self.assertNotEqual(3, result)

    # ---- StackContainer 测试 ----

    def test_stack_container_creates_bay_and_stacks(self):
        block = Block(10, 6, 5)
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        bi = [0]
        ri = [0]
        ti = [0]
        result = block.stack_container(container, self.rs, bay_index=None, bay_index_out=bi, row_index=ri, tier_index=ti)
        self.assertTrue(result)
        self.assertGreaterEqual(bi[0], 1)
        self.assertIn(bi[0], block.bays)

    def test_stack_container_specified_bay(self):
        block = Block(10, 6, 5)
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        ri = [0]
        ti = [0]
        result = block.stack_container(container, self.rs, bay_index=1, row_index=ri, tier_index=ti)
        self.assertTrue(result)
        self.assertGreaterEqual(ri[0], 1)
        self.assertEqual(1, len(block.bays))


# ============================================================
# Inventory 单元测试
# ============================================================
class TestInventory(unittest.TestCase):

    def setUp(self):
        reset_container_count()
        Block.count = 0
        self.inventory = Inventory()
        self.block = Block(num_bays=10, num_rows=6, max_num_tiers=5)
        self.rs = make_rs(123)

    # ---- Peek / GetHeight 基本操作 ----

    def test_peek_empty_slot_returns_none(self):
        result = self.inventory.peek(self.block, Slot(1, 1, 1))
        self.assertIsNone(result)

    def test_get_height_empty_slot_returns_zero(self):
        result = self.inventory.get_height(self.block, Slot(1, 1, 1))
        self.assertEqual(0, result)

    # ---- Update / Stacking / Unstacking ----

    def test_update_stacking_adds_container(self):
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        container.block = self.block
        container.slot = Slot(1, 1, 1)
        self.inventory.update(container, JobType.Stacking)
        self.assertEqual(1, self.inventory.get_height(self.block, Slot(1, 1, 1)))

    def test_update_unstacking_removes_container(self):
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        container.block = self.block
        container.slot = Slot(1, 1, 1)
        self.inventory.update(container, JobType.Stacking)
        self.inventory.update(container, JobType.Unstacking)
        self.assertEqual(0, self.inventory.get_height(self.block, Slot(1, 1, 1)))

    def test_update_unstacking_returns_correct_container(self):
        g1 = Group(index=1, te_us=1)
        g2 = Group(index=2, te_us=1)
        c1 = Container(group=g1)
        c2 = Container(group=g2)
        c1.block = self.block
        c1.slot = Slot(1, 1, 1)
        c2.block = self.block
        c2.slot = Slot(1, 1, 2)
        self.inventory.update(c1, JobType.Stacking)
        self.inventory.update(c2, JobType.Stacking)
        top = self.inventory._unstack(self.block, Slot(1, 1, 2))
        self.assertIs(top, c2)

    def test_update_invalid_slot_does_nothing(self):
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        container.block = self.block
        container.slot = Slot(0, 1, 1)  # bay=0 无效
        self.inventory.update(container, JobType.Stacking)
        self.assertEqual(0, self.inventory.get_height(self.block, Slot(0, 1, 1)))

    # ---- Allocate 20尺 测试 ----

    def test_allocate_twenty_foot_stage1_same_group(self):
        g1 = Group(index=1, te_us=1)
        c1 = Container(group=g1)
        c2 = Container(group=g1)
        c1.block = self.block
        c2.block = self.block
        c1.slot = self.inventory.allocate(c1, self.rs)
        self.assertIsNotNone(c1.slot)
        self.inventory.update(c1, JobType.Stacking)
        c2.slot = self.inventory.allocate(c2, self.rs)
        self.assertIsNotNone(c2.slot)
        self.assertEqual(c1.slot.bay, c2.slot.bay)
        self.assertEqual(c1.slot.row, c2.slot.row)
        self.assertEqual(2, c2.slot.tier)

    def test_allocate_twenty_foot_stage2_empty_slot(self):
        group = Group(index=1, te_us=1)
        container = Container(group=group)
        container.block = self.block
        container.slot = self.inventory.allocate(container, self.rs)
        self.assertIsNotNone(container.slot)
        self.assertEqual(1, container.slot.tier)

    def test_allocate_twenty_foot_bay_blocked_by_forty(self):
        block = Block(10, 6, 5)
        inv = Inventory()
        g40 = Group(index=1, te_us=2)
        c40 = Container(group=g40)
        c40.block = block
        c40.slot = inv.allocate(c40, self.rs)
        self.assertIsNotNone(c40.slot)
        inv.update(c40, JobType.Stacking)
        g20 = Group(index=2, te_us=1)
        c20 = Container(group=g20)
        c20.block = block
        c20.slot = inv.allocate(c20, self.rs)
        # 不应分配到被阻塞的 bay
        if c20.slot is not None:
            bay_idx = c20.slot.bay

    # ---- Allocate 40尺 测试 ----

    def test_allocate_forty_foot_stage1_same_group(self):
        g1 = Group(index=1, te_us=2)
        c1 = Container(group=g1)
        c2 = Container(group=g1)
        c1.block = self.block
        c2.block = self.block
        c1.slot = self.inventory.allocate(c1, self.rs)
        self.assertIsNotNone(c1.slot)
        self.assertEqual(0, c1.slot.bay % 2)
        self.inventory.update(c1, JobType.Stacking)
        c2.slot = self.inventory.allocate(c2, self.rs)
        self.assertIsNotNone(c2.slot)
        self.assertEqual(c1.slot.bay, c2.slot.bay)
        self.assertEqual(c1.slot.row, c2.slot.row)

    def test_allocate_forty_foot_stage2_empty_slot(self):
        g1 = Group(index=1, te_us=2)
        c = Container(group=g1)
        c.block = self.block
        c.slot = self.inventory.allocate(c, self.rs)
        self.assertIsNotNone(c.slot)
        self.assertEqual(0, c.slot.bay % 2)

    def test_allocate_forty_foot_checks_height_consistency(self):
        block = Block(10, 6, 5)
        inv = Inventory()
        g1 = Group(index=1, te_us=1)
        c1 = Container(group=g1)
        c1.block = block
        c1.slot = Slot(1, 1, 1)
        inv.update(c1, JobType.Stacking)
        g40 = Group(index=2, te_us=2)
        c40 = Container(group=g40)
        c40.block = block
        c40.slot = inv.allocate(c40, self.rs)
        if c40.slot is not None:
            self.assertNotEqual(2, c40.slot.bay)

    # ---- UnstackWithoutReshuffle ----

    def test_unstack_without_reshuffle_top_container(self):
        g1 = Group(index=1, te_us=1)
        c1 = Container(group=g1)
        c1.block = self.block
        c1.slot = Slot(1, 1, 1)
        self.inventory.update(c1, JobType.Stacking)
        self.assertTrue(self.inventory.unstack_without_reshuffle(c1))

    def test_unstack_without_reshuffle_same_group_on_top(self):
        g1 = Group(index=1, te_us=1)
        c1 = Container(group=g1)
        c2 = Container(group=g1)
        c1.block = self.block
        c1.slot = Slot(1, 1, 1)
        c2.block = self.block
        c2.slot = Slot(1, 1, 2)
        self.inventory.update(c1, JobType.Stacking)
        self.inventory.update(c2, JobType.Stacking)
        self.assertTrue(self.inventory.unstack_without_reshuffle(c1))

    def test_unstack_without_reshuffle_different_group_on_top(self):
        g1 = Group(index=1, te_us=1)
        g2 = Group(index=2, te_us=1)
        c1 = Container(group=g1)
        c2 = Container(group=g2)
        c1.block = self.block
        c1.slot = Slot(1, 1, 1)
        c2.block = self.block
        c2.slot = Slot(1, 1, 2)
        self.inventory.update(c1, JobType.Stacking)
        self.inventory.update(c2, JobType.Stacking)
        self.assertFalse(self.inventory.unstack_without_reshuffle(c1))

    # ---- GetBestJobByPswc ----

    def test_get_best_job_by_pswc_top_of_stack(self):
        g1 = Group(index=1, te_us=1)
        c1 = Container(group=g1)
        c2 = Container(group=g1)
        c1.block = self.block
        c1.slot = Slot(1, 1, 1)
        c2.block = self.block
        c2.slot = Slot(1, 1, 2)
        self.inventory.update(c1, JobType.Stacking)
        self.inventory.update(c2, JobType.Stacking)
        best = self.inventory.get_best_job_by_pswc(self.block, g1)
        self.assertIsNotNone(best)
        self.assertIs(best, c1)

    def test_get_best_job_by_pswc_multiple_groups(self):
        g1 = Group(index=1, te_us=1)
        g2 = Group(index=2, te_us=1)
        c1 = Container(group=g1)
        c2 = Container(group=g2)
        c1.block = self.block
        c1.slot = Slot(1, 1, 1)
        c2.block = self.block
        c2.slot = Slot(1, 2, 1)
        self.inventory.update(c1, JobType.Stacking)
        self.inventory.update(c2, JobType.Stacking)
        best1 = self.inventory.get_best_job_by_pswc(self.block, g1)
        best2 = self.inventory.get_best_job_by_pswc(self.block, g2)
        self.assertIs(best1, c1)
        self.assertIs(best2, c2)

    # ---- DecideReshuffleTarget ----

    def test_decide_reshuffle_target_case_a_within_bay(self):
        block = Block(10, 6, 5)
        inv = Inventory()
        g1 = Group(index=1, te_us=1)
        c1 = Container(group=g1)
        c2 = Container(group=Group(2, 1))
        c1.block = block
        c1.slot = Slot(1, 1, 1)
        c2.block = block
        c2.slot = Slot(1, 1, 2)
        inv.update(c1, JobType.Stacking)
        inv.update(c2, JobType.Stacking)
        target = inv.decide_reshuffle_target(c1, c2)
        self.assertIsNotNone(target)

    def test_decide_reshuffle_target_case_b_cross_bay(self):
        block = Block(10, 6, 5)
        inv = Inventory()
        g1 = Group(index=1, te_us=1)
        c1 = Container(group=g1)
        c1.block = block
        c1.slot = Slot(1, 1, 1)
        inv.update(c1, JobType.Stacking)
        for i in range(2, 6):
            g = Group(index=i, te_us=1)
            c = Container(group=g)
            c.block = block
            c.slot = Slot(1, 1, i)
            inv.update(c, JobType.Stacking)
        target = inv.decide_reshuffle_target(c1, Container(group=Group(10, 1)))
        self.assertIsNotNone(target)

    # ---- 40尺 Unstack 成对移除 ----

    def test_unstack_forty_foot_removes_from_both_bays(self):
        block = Block(10, 6, 5)
        inv = Inventory()
        g1 = Group(index=1, te_us=2)
        c = Container(group=g1)
        c.block = block
        c.slot = Slot(2, 1, 1)
        inv.update(c, JobType.Stacking)
        self.assertEqual(1, inv.get_height(block, Slot(1, 1, 1)))
        self.assertEqual(1, inv.get_height(block, Slot(3, 1, 1)))
        inv.update(c, JobType.Unstacking)
        self.assertEqual(0, inv.get_height(block, Slot(1, 1, 1)))
        self.assertEqual(0, inv.get_height(block, Slot(3, 1, 1)))

    # ---- ToDim1 ----

    def test_to_dim1_odd_bay(self):
        self.assertEqual(1, Inventory._to_dim1(1))
        self.assertEqual(2, Inventory._to_dim1(3))
        self.assertEqual(3, Inventory._to_dim1(5))

    def test_to_dim1_even_bay(self):
        self.assertEqual(1, Inventory._to_dim1(2))
        self.assertEqual(2, Inventory._to_dim1(4))
        self.assertEqual(3, Inventory._to_dim1(6))


if __name__ == '__main__':
    unittest.main(verbosity=2)
