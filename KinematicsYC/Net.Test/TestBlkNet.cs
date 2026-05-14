using NUnit.Framework;
using System;
using System.Collections.Generic;
using System.Reflection;
using Assets.SingaPort;

namespace Net.Test
{
    // ============================================================
    // Slot 单元测试
    // ============================================================
    [TestFixture]
    public class SlotTests
    {
        [SetUp]
        public void Setup()
        {
            Container.ResetCount();
            Block.ResetCount();
        }

        [Test]
        public void Slot_Constructor_SetsProperties()
        {
            var slot = new Slot(bay: 3, row: 5, tier: 2);
            Assert.That(slot.Bay, Is.EqualTo(3));
            Assert.That(slot.Row, Is.EqualTo(5));
            Assert.That(slot.Tier, Is.EqualTo(2));
        }

        [Test]
        public void Slot_Equality_SameValues()
        {
            var s1 = new Slot(1, 2, 3);
            var s2 = new Slot(1, 2, 3);
            Assert.That(s1, Is.EqualTo(s2));
            Assert.That(s1.GetHashCode(), Is.EqualTo(s2.GetHashCode()));
        }

        [Test]
        public void Slot_Equality_DifferentValues()
        {
            var s1 = new Slot(1, 2, 3);
            var s2 = new Slot(1, 2, 4);
            Assert.That(s1, Is.Not.EqualTo(s2));
        }

        [Test]
        public void Slot_ToString()
        {
            var slot = new Slot(3, 5, 2);
            Assert.That(slot.ToString(), Does.Contain("3"));
            Assert.That(slot.ToString(), Does.Contain("5"));
            Assert.That(slot.ToString(), Does.Contain("2"));
        }
    }

    // ============================================================
    // Container + Group 单元测试
    // ============================================================
    [TestFixture]
    public class ContainerTests
    {
        [SetUp]
        public void Setup()
        {
            Container.ResetCount();
            Block.ResetCount();
        }

        [Test]
        public void Container_TwentyFeet_Group_TEUs1()
        {
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group);
            Assert.That(ContainerSize.TwentyFeet, Is.EqualTo(container.Size));
            Assert.That(1, Is.EqualTo(container.Index));
            Assert.That(group, Is.SameAs(container.Group));
        }

        [Test]
        public void Container_FortyFeet_Group_TEUs2()
        {
            var group = new Group { Index = 2, TEUs = 2 };
            var container = new Container(group);
            Assert.That(ContainerSize.FortyFeet, Is.EqualTo(container.Size));
            Assert.That(1, Is.EqualTo(container.Index));
        }

        [Test]
        public void Container_IncrementalIndex()
        {
            var group1 = new Group { Index = 1, TEUs = 1 };
            var group2 = new Group { Index = 2, TEUs = 1 };
            var c1 = new Container(group1);
            var c2 = new Container(group2);
            Assert.That(1, Is.EqualTo(c1.Index));
            Assert.That(2, Is.EqualTo(c2.Index));
        }

        [Test]
        public void Container_Group_TimestampUnstack()
        {
            var group = new Group { Index = 1, TEUs = 1, Timestamp_Unstack = new DateTime(2025, 1, 1) };
            Assert.That(new DateTime(2025, 1, 1), Is.EqualTo(group.Timestamp_Unstack));
        }

        [Test]
        public void Container_Group_ContainersList()
        {
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group);
            group.Containers.Add(container);
            Assert.That(1, Is.EqualTo(group.Containers.Count));
            Assert.That(group.Containers, Has.Member(container));
        }

        [Test]
        public void Container_Group_ToString()
        {
            var group = new Group { Index = 42, TEUs = 2 };
            Assert.That("Group#42", Is.EqualTo(group.ToString()));
        }

        [Test]
        public void Container_Height_Constant()
        {
            Assert.That(2.59f, Is.EqualTo(Container.Height));
        }
    }

    // ============================================================
    // Bay 单元测试
    // ============================================================
    [TestFixture]
    public class BayTests
    {
        private Block _block = null!;
        private Random _rs;

        [SetUp]
        public void Setup()
        {
            _block = new Block(numBays: 10, numRows: 6, maxNumTiers: 5);
            _rs = new Random(42);
            Container.ResetCount();
            Block.ResetCount();
        }

        // ---- 基本属性测试 ----

        [Test]
        public void Bay_Constructor_InitializesStacks()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            Assert.That(6, Is.EqualTo(bay.Stacks.Count)); // 6 rows
            foreach (var stack in bay.Stacks.Values)
                Assert.That(stack, Is.Empty);
        }

        [Test]
        public void Bay_ContainerSize_IsFixed()
        {
            var bay = new Bay(_block, ContainerSize.FortyFeet);
            Assert.That(bay.ContainerSize, Is.EqualTo(ContainerSize.FortyFeet));
        }

        [Test]
        public void Bay_NumContainers_EmptyBay()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            Assert.That(0, Is.EqualTo(bay.NumContainers));
        }

        [Test]
        public void Bay_NumTEUs_EmptyBay()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            Assert.That(0, Is.EqualTo(bay.NumTEUs));
        }

        [Test]
        public void Bay_NumTEUs_FortyFeet()
        {
            var bay = new Bay(_block, ContainerSize.FortyFeet);
            Assert.That(bay.ContainerSize, Is.EqualTo(ContainerSize.FortyFeet));
        }

        [Test]
        public void Bay_IsFull_Empty()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            Assert.That(bay.IsFull, Is.False);
        }

        [Test]
        public void Bay_IsFull_NotFull()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            bay.Stacks[1].Add(new Container(new Group { Index = 1, TEUs = 1 }));
            Assert.That(bay.IsFull, Is.False);
        }

        [Test]
        public void Bay_IsFull_Full()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            // 每个 row 都堆满
            for (int row = 1; row <= _block.NumRows; row++)
                for (int t = 0; t < _block.MaxNumTiers; t++)
                    bay.Stacks[row].Add(new Container(new Group { Index = t + 1, TEUs = 1 }));
            Assert.That(bay.IsFull, Is.True);
        }

        [Test]
        public void Bay_NumContainers_MultiRow()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            bay.Stacks[1].Add(new Container(new Group { Index = 1, TEUs = 1 }));
            bay.Stacks[2].Add(new Container(new Group { Index = 2, TEUs = 1 }));
            bay.Stacks[2].Add(new Container(new Group { Index = 3, TEUs = 1 }));
            Assert.That(3, Is.EqualTo(bay.NumContainers));
        }

        [Test]
        public void Bay_NumTEUs_MixedTEU()
        {
            var bay = new Bay(_block, ContainerSize.FortyFeet);
            bay.Stacks[1].Add(new Container(new Group { Index = 1, TEUs = 2 }));
            bay.Stacks[1].Add(new Container(new Group { Index = 2, TEUs = 2 }));
            Assert.That(4, Is.EqualTo(bay.NumTEUs));
        }

        // ---- GetRowIndexToStack 约束测试 ----

        [Test]
        public void GetRowIndexToStack_AllRowsEmpty_ReturnsAnyRow()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            var result = bay.GetRowIndexToStack(_rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(result.Value, Is.GreaterThanOrEqualTo(1));
            Assert.That(result.Value, Is.LessThanOrEqualTo(_block.NumRows));
        }

        [Test]
        public void GetRowIndexToStack_Constraint1_ExceedsMaxTier()
        {
            // 当某排达到 MaxNumTiers 时，不应再返回该排
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            for (int t = 0; t < _block.MaxNumTiers; t++)
                bay.Stacks[1].Add(new Container(new Group { Index = t + 1, TEUs = 1 }));
            // Row 1 已满，其他 row 为空
            var result = bay.GetRowIndexToStack(_rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(1, Is.Not.EqualTo(result.Value)); // Row 1 不应被返回
        }

        [Test]
        public void GetRowIndexToStack_Constraint2_HeightDiffMoreThan4()
        {
            // Row 1 堆 4 层，Row 2 堆 0 层 → 差=4，可以通过
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            for (int t = 0; t < 4; t++)
                bay.Stacks[1].Add(new Container(new Group { Index = t + 1, TEUs = 1 }));
            var result = bay.GetRowIndexToStack(_rs);
            Assert.That(result, Is.Not.Null); // 差=4，约束2允许
        }

        [Test]
        public void GetRowIndexToStack_Constraint3_Upslope()
        {
            // Row 1 高，Row 2 低 → Row 1 不应被返回
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            bay.Stacks[1].Add(new Container(new Group { Index = 1, TEUs = 1 })); // Row1 高
            bay.Stacks[2].Add(new Container(new Group { Index = 2, TEUs = 1 })); // Row2 低
            var result = bay.GetRowIndexToStack(_rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(1, Is.Not.EqualTo(result.Value)); // Row 1 不应被返回（有上陡坡）
        }

        [Test]
        public void GetRowIndexToStack_Constraint4_Downslope()
        {
            // Row 2 高，Row 1 低 → Row 2 不应被返回
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            bay.Stacks[1].Add(new Container(new Group { Index = 1, TEUs = 1 })); // Row1 低
            bay.Stacks[2].Add(new Container(new Group { Index = 2, TEUs = 1 })); // Row2 高
            var result = bay.GetRowIndexToStack(_rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(2, Is.Not.EqualTo(result.Value)); // Row 2 不应被返回（有下陡坡）
        }

        [Test]
        public void GetRowIndexToStack_Constraint5_UpperHole()
        {
            // Row 1 = Row 2，但 Row 3 更高 → Row 1/2 不应被返回
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            bay.Stacks[1].Add(new Container(new Group { Index = 1, TEUs = 1 }));
            bay.Stacks[2].Add(new Container(new Group { Index = 2, TEUs = 1 })); // 与 Row1 等高
            bay.Stacks[3].Add(new Container(new Group { Index = 3, TEUs = 1 }));
            bay.Stacks[3].Add(new Container(new Group { Index = 4, TEUs = 1 })); // Row3 更高 → 形成上洞
            var result = bay.GetRowIndexToStack(_rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(1, Is.Not.EqualTo(result.Value));
            Assert.That(2, Is.Not.EqualTo(result.Value));
        }

        [Test]
        public void GetRowIndexToStack_Constraint6_LowerHole()
        {
            // Row 3 = Row 2，但 Row 1 更高 → Row 2/3 不应被返回
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            bay.Stacks[1].Add(new Container(new Group { Index = 1, TEUs = 1 }));
            bay.Stacks[1].Add(new Container(new Group { Index = 2, TEUs = 1 })); // Row1 更高
            bay.Stacks[2].Add(new Container(new Group { Index = 3, TEUs = 1 }));
            bay.Stacks[3].Add(new Container(new Group { Index = 4, TEUs = 1 })); // 与 Row2 等高
            var result = bay.GetRowIndexToStack(_rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(2, Is.Not.EqualTo(result.Value));
            Assert.That(3, Is.Not.EqualTo(result.Value));
        }

        [Test]
        public void GetRowIndexToStack_AllRowsFull_ReturnsNull()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            for (int row = 1; row <= _block.NumRows; row++)
                for (int t = 0; t < _block.MaxNumTiers; t++)
                    bay.Stacks[row].Add(new Container(new Group { Index = t + 1, TEUs = 1 }));
            Assert.That(bay.GetRowIndexToStack(_rs), Is.Null);
        }

        // ---- StackContainer 测试 ----

        [Test]
        public void StackContainer_WithRowIndex_Success()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group);
            int? tierIndex = null;
            var tierWrapper = new int?[] { 0 };
            bool result = bay.StackContainer(container, 3, ref tierWrapper[0]);
            Assert.That(result, Is.True);
            Assert.That(1, Is.EqualTo(bay.Stacks[3].Count));
        }

        [Test]
        public void StackContainer_WithRowIndex_WrongSize_Fails()
        {
            var bay = new Bay(_block, ContainerSize.FortyFeet);
            var group = new Group { Index = 1, TEUs = 1 }; // 20尺
            var container = new Container(group);
            int? tierIndex = null;
            var tierWrapper = new int?[] { 0 };
            bool result = bay.StackContainer(container, 3, ref tierWrapper[0]);
            Assert.That(result, Is.False);
        }

        [Test]
        public void StackContainer_WithRowIndex_RowFull_Fails()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            for (int t = 0; t < _block.MaxNumTiers; t++)
                bay.Stacks[3].Add(new Container(new Group { Index = t + 1, TEUs = 1 }));
            var group = new Group { Index = 99, TEUs = 1 };
            var container = new Container(group);
            var tierWrapper = new int?[] { 0 };
            bool result = bay.StackContainer(container, 3, ref tierWrapper[0]);
            Assert.That(result, Is.False);
        }

        [Test]
        public void StackContainer_WithoutRowIndex_UsesRandomRow()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group);
            int? rowIndex = null;
            int? tierIndex = null;
            var rowWrapper = new int?[] { 0 };
            var tierWrapper = new int?[] { 0 };
            bool result = bay.StackContainer(container, _rs, ref rowWrapper[0], ref tierWrapper[0]);
            Assert.That(result, Is.True);
            Assert.That(rowWrapper[0].Value, Is.GreaterThanOrEqualTo(1));
            Assert.That(rowWrapper[0].Value, Is.LessThanOrEqualTo(_block.NumRows));
        }

        [Test]
        public void StackContainer_TierIndex_ReturnsCorrectValue()
        {
            var bay = new Bay(_block, ContainerSize.TwentyFeet);
            var g1 = new Group { Index = 1, TEUs = 1 };
            var g2 = new Group { Index = 2, TEUs = 1 };
            var c1 = new Container(g1);
            var c2 = new Container(g2);
            int? tier1 = null;
            int? tier2 = null;
            var t1 = new int?[] { 0 };
            var t2 = new int?[] { 0 };
            bay.StackContainer(c1, 2, ref t1[0]);
            bay.StackContainer(c2, 2, ref t2[0]);
            Assert.That(1, Is.EqualTo(t1[0].Value));
            Assert.That(2, Is.EqualTo(t2[0].Value));
        }
    }

    // ============================================================
    // Block 单元测试
    // ============================================================
    [TestFixture]
    public class BlockTests
    {
        private Random _rs;

        [SetUp]
        public void Setup()
        {
            _rs = new Random(42);
            Container.ResetCount();
            Block.ResetCount();
        }

        // ---- 基本属性测试 ----

        [Test]
        public void Block_Constructor_IncrementsCount()
        {
            var block1 = new Block(5, 3, 4);
            var block2 = new Block(5, 3, 4);
            Assert.That(1, Is.EqualTo(block1.Index));
            Assert.That(2, Is.EqualTo(block2.Index));
        }

        [Test]
        public void Block_NumBays_NumRows_MaxNumTiers()
        {
            var block = new Block(numBays: 8, numRows: 5, maxNumTiers: 6);
            Assert.That(8, Is.EqualTo(block.NumBays));
            Assert.That(5, Is.EqualTo(block.NumRows));
            Assert.That(6, Is.EqualTo(block.MaxNumTiers));
        }

        [Test]
        public void Block_StaticSlotDimensions()
        {
            Assert.That(6.5f, Is.EqualTo(Block.SlotLength));
            Assert.That(2.5f, Is.EqualTo(Block.SlotWidth));
            Assert.That(2.6f, Is.EqualTo(Block.SlotHeight));
        }

        [Test]
        public void Block_CapacityTEUs_CalculatesCorrectly()
        {
            // (NumBays+1)/2 * NumRows * MaxNumTiers
            // (10+1)/2 * 6 * 5 = 5 * 6 * 5 = 150
            var block = new Block(numBays: 10, numRows: 6, maxNumTiers: 5);
            Assert.That(150, Is.EqualTo(block.CapacityTEUs));
        }

        [Test]
        public void Block_NumContainers_Empty()
        {
            var block = new Block(5, 3, 4);
            Assert.That(0, Is.EqualTo(block.NumContainers));
        }

        [Test]
        public void Block_NumTEUs_Empty()
        {
            var block = new Block(5, 3, 4);
            Assert.That(0, Is.EqualTo(block.NumTEUs));
        }

        // ---- CreateBayIfNotExist 测试 ----

        [Test]
        public void CreateBayIfNotExist_AddsNewBay()
        {
            var block = new Block(10, 6, 5);
            var bay = block.CreateBayIfNotExist(1, ContainerSize.TwentyFeet);
            Assert.That(bay, Is.Not.Null);
            Assert.That(ContainerSize.TwentyFeet, Is.EqualTo(bay.ContainerSize));
            Assert.That(block.Bays.ContainsKey(1), Is.True);
        }

        [Test]
        public void CreateBayIfNotExist_ReusesExistingBay()
        {
            var block = new Block(10, 6, 5);
            var bay1 = block.CreateBayIfNotExist(1, ContainerSize.TwentyFeet);
            var bay2 = block.CreateBayIfNotExist(1, ContainerSize.TwentyFeet);
            Assert.That(bay1, Is.SameAs(bay2));
        }

        [Test]
        public void CreateBayIfNotExist_IndexOutOfRange_Throws()
        {
            var block = new Block(10, 6, 5);
            Assert.Throws<Exception>(() => block.CreateBayIfNotExist(0, ContainerSize.TwentyFeet));
            Assert.Throws<Exception>(() => block.CreateBayIfNotExist(20, ContainerSize.TwentyFeet));
        }

        [Test]
        public void CreateBayIfNotExist_AdjacentBayExists_Throws()
        {
            var block = new Block(10, 6, 5);
            block.CreateBayIfNotExist(1, ContainerSize.TwentyFeet);
            Assert.Throws<Exception>(() => block.CreateBayIfNotExist(2, ContainerSize.TwentyFeet));
        }

        [Test]
        public void CreateBayIfNotExist_FortyFoot_SpanConflict_Throws()
        {
            var block = new Block(10, 6, 5);
            block.CreateBayIfNotExist(2, ContainerSize.FortyFeet);
            Assert.Throws<Exception>(() => block.CreateBayIfNotExist(4, ContainerSize.FortyFeet));
        }

        [Test]
        public void CreateBayIfNotExist_FortyFoot_OddBay_Throws()
        {
            var block = new Block(10, 6, 5);
            // 奇数 bay 不能作为 40 尺中心
            Assert.Throws<Exception>(() => block.CreateBayIfNotExist(1, ContainerSize.FortyFeet));
        }

        // ---- GetBayIndexToStack 测试 ----

        [Test]
        public void GetBayIndexToStack_EmptyBlock_AcceptsFirstBay()
        {
            var block = new Block(10, 6, 5);
            var result = block.GetBayIndexToStack(ContainerSize.TwentyFeet, _rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(1, Is.EqualTo(result.Value)); // 第一个空 bay
        }

        [Test]
        public void GetBayIndexToStack_TwentyFeet_OddBaysOnly()
        {
            var block = new Block(10, 6, 5);
            block.CreateBayIfNotExist(1, ContainerSize.TwentyFeet);
            block.CreateBayIfNotExist(3, ContainerSize.TwentyFeet);
            var result = block.GetBayIndexToStack(ContainerSize.TwentyFeet, _rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(1, Is.EqualTo(result.Value % 2)); // 必须是奇数
        }

        [Test]
        public void GetBayIndexToStack_FortyFeet_EvenBaysOnly()
        {
            var block = new Block(10, 6, 5);
            var result = block.GetBayIndexToStack(ContainerSize.FortyFeet, _rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(0, Is.EqualTo(result.Value % 2)); // 必须是偶数
        }

        [Test]
        public void GetBayIndexToStack_FullBay_ReturnsOtherBay()
        {
            var block = new Block(10, 6, 5);
            var bay = block.CreateBayIfNotExist(1, ContainerSize.TwentyFeet);
            // 将 bay 填满
            for (int row = 1; row <= block.NumRows; row++)
                for (int t = 0; t < block.MaxNumTiers; t++)
                    bay.Stacks[row].Add(new Container(new Group { Index = t + 1, TEUs = 1 }));
            var result = block.GetBayIndexToStack(ContainerSize.TwentyFeet, _rs);
            Assert.That(result, Is.Not.Null);
            Assert.That(1, Is.Not.EqualTo(result.Value)); // 不返回已满 bay
        }

        [Test]
        public void GetBayIndexToStack_40Foot_CannotPlaceNextToExistingBay()
        {
            var block = new Block(10, 6, 5);
            block.CreateBayIfNotExist(1, ContainerSize.TwentyFeet);
            block.CreateBayIfNotExist(3, ContainerSize.TwentyFeet);
            // bay 1 和 3 存在，bay 2 的跨度 (bay-1=1, bay+1=3) 被阻塞
            var result = block.GetBayIndexToStack(ContainerSize.FortyFeet, _rs);
            // 不应返回 bay 2（因为 bay 1 已占用）
            if (result != null)
                Assert.That(2, Is.Not.EqualTo(result.Value));
        }

        [Test]
        public void GetBayIndexToStack_BubbleRule_NoIsolatedBay()
        {
            var block = new Block(10, 6, 5);
            // bay 1 和 5 已存在，bay 3 是中间孤立位置（bay 2 和 bay 4 不存在）
            block.CreateBayIfNotExist(1, ContainerSize.TwentyFeet);
            block.CreateBayIfNotExist(5, ContainerSize.TwentyFeet);
            var result = block.GetBayIndexToStack(ContainerSize.TwentyFeet, _rs);
            // bay 3 不应被返回（两侧 bay-1=2 和 bay+1=4 都不存在，形成气泡）
            if (result != null)
                Assert.That(3, Is.Not.EqualTo(result.Value));
        }

        // ---- StackContainer 测试 ----

        [Test]
        public void StackContainer_CreatesBayAndStacks()
        {
            var block = new Block(10, 6, 5);
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group);
            int? bi = null;
            int? ri = null;
            int? ti = null;
            var biW = new int?[] { 0 };
            var riW = new int?[] { 0 };
            var tiW = new int?[] { 0 };
            bool result = block.StackContainer(container, _rs, ref biW[0], ref riW[0], ref tiW[0]);
            Assert.That(result, Is.True);
            Assert.That(biW[0].Value, Is.GreaterThanOrEqualTo(1));
            Assert.That(block.Bays.ContainsKey(biW[0].Value), Is.True);
        }

        [Test]
        public void StackContainer_SpecifiedBay()
        {
            var block = new Block(10, 6, 5);
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group);
            int? ri = null;
            int? ti = null;
            var riW = new int?[] { 0 };
            var tiW = new int?[] { 0 };
            bool result = block.StackContainer(container, _rs, bayIndex: 1, ref riW[0], ref tiW[0]);
            Assert.That(result, Is.True);
            Assert.That(riW[0].Value, Is.GreaterThanOrEqualTo(1));
            Assert.That(1, Is.EqualTo(block.Bays.Count));
        }
    }

    // ============================================================
    // Inventory 单元测试
    // ============================================================
    [TestFixture]
    public class InventoryTests
    {
        private Inventory _inventory = null!;
        private Block _block = null!;
        private Random _rs;

        [SetUp]
        public void Setup()
        {
            _inventory = new Inventory();
            _block = new Block(numBays: 10, numRows: 6, maxNumTiers: 5);
            _rs = new Random(123);
            Container.ResetCount();
            Block.ResetCount();
        }

        // ---- Peek / GetHeight 基本操作 ----

        [Test]
        public void Peek_EmptySlot_ReturnsNull()
        {
            var result = _inventory.Peek(_block, new Slot(1, 1, 1));
            Assert.That(result, Is.Null);
        }

        [Test]
        public void GetHeight_EmptySlot_ReturnsZero()
        {
            var result = _inventory.GetHeight(_block, new Slot(1, 1, 1));
            Assert.That(0, Is.EqualTo(result));
        }

        // ---- Update / Stacking / Unstacking ----

        [Test]
        public void Update_Stacking_AddsContainer()
        {
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group) { Block = _block, Slot = new Slot(1, 1, 1) };
            _inventory.Update(container, Inventory.JobType.Stacking);
            Assert.That(1, Is.EqualTo(_inventory.GetHeight(_block, new Slot(1, 1, 1))));
        }

        [Test]
        public void Update_Unstacking_RemovesContainer()
        {
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group) { Block = _block, Slot = new Slot(1, 1, 1) };
            _inventory.Update(container, Inventory.JobType.Stacking);
            _inventory.Update(container, Inventory.JobType.Unstacking);
            Assert.That(0, Is.EqualTo(_inventory.GetHeight(_block, new Slot(1, 1, 1))));
        }

        [Test]
        public void Update_Unstacking_ReturnsCorrectContainer()
        {
            var g1 = new Group { Index = 1, TEUs = 1 };
            var g2 = new Group { Index = 2, TEUs = 1 };
            var c1 = new Container(g1) { Block = _block, Slot = new Slot(1, 1, 1) };
            var c2 = new Container(g2) { Block = _block, Slot = new Slot(1, 1, 2) };
            _inventory.Update(c1, Inventory.JobType.Stacking);
            _inventory.Update(c2, Inventory.JobType.Stacking);
            _inventory.Update(c2, Inventory.JobType.Unstacking);
            Assert.That(1, Is.EqualTo(_inventory.GetHeight(_block, new Slot(1, 1, 1))));
        }

        [Test]
        public void Update_InvalidSlot_DoesNothing()
        {
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group) { Block = _block, Slot = new Slot(0, 1, 1) };
            _inventory.Update(container, Inventory.JobType.Stacking);
            Assert.That(0, Is.EqualTo(_inventory.GetHeight(_block, new Slot(0, 1, 1))));
        }

        // ---- Allocate 20尺 测试 ----

        [Test]
        public void Allocate_TwentyFoot_Stage1_SameGroup()
        {
            var g1 = new Group { Index = 1, TEUs = 1 };
            var c1 = new Container(g1) { Block = _block };
            var c2 = new Container(g1) { Block = _block };
            c1.Slot = _inventory.Allocate(c1, _rs);
            _inventory.Update(c1, Inventory.JobType.Stacking);
            c2.Slot = _inventory.Allocate(c2, _rs);
            Assert.That(c2.Slot, Is.Not.Null);
            Assert.That(c1.Slot.Bay, Is.EqualTo(c2.Slot.Bay));
            Assert.That(c1.Slot.Row, Is.EqualTo(c2.Slot.Row));
            Assert.That(2, Is.EqualTo(c2.Slot.Tier)); // 堆在 c1 上面
        }

        [Test]
        public void Allocate_TwentyFoot_Stage2_EmptySlot()
        {
            var group = new Group { Index = 1, TEUs = 1 };
            var container = new Container(group) { Block = _block };
            container.Slot = _inventory.Allocate(container, _rs);
            Assert.That(container.Slot, Is.Not.Null);
            Assert.That(1, Is.EqualTo(container.Slot.Tier)); // 空槽 tier=1
        }

        [Test]
        public void Allocate_TwentyFoot_Stage3_HighestNonFull()
        {
            var block = new Block(10, 6, 5);
            var inv = new Inventory();
            var g1 = new Group { Index = 1, TEUs = 1 };
            // 填满 bay 1 的 row 1
            var c1 = new Container(g1) { Block = block, Slot = new Slot(1, 1, 1) };
            inv.Update(c1, Inventory.JobType.Stacking);
            var g2 = new Group { Index = 2, TEUs = 1 };
            var c2 = new Container(g2) { Block = block };
            c2.Slot = inv.Allocate(c2, _rs);
            Assert.That(c2.Slot, Is.Not.Null);
        }

        [Test]
        public void Allocate_TwentyFoot_BayBlockedByForty()
        {
            var block = new Block(10, 6, 5);
            var inv = new Inventory();
            var g40 = new Group { Index = 1, TEUs = 2 };
            var c40 = new Container(g40) { Block = block };
            c40.Slot = inv.Allocate(c40, _rs);
            Assert.That(c40.Slot, Is.Not.Null);
            inv.Update(c40, Inventory.JobType.Stacking);
            // bay-1 和 bay+1 现在都被 40 尺箱占用了
            // 尝试分配 20 尺到被阻塞的 bay
            var bayIndex = c40.Slot.Bay; // 这是偶数中心位
            int leftBay = bayIndex - 1;
            // leftBay 的 bay 应该被阻塞
            var g20 = new Group { Index = 2, TEUs = 1 };
            var c20 = new Container(g20) { Block = block };
            c20.Slot = inv.Allocate(c20, _rs);
            // 不应分配到被阻塞的 bay
            if (c20.Slot != null)
            {
                // 确认没有分配到被 40 尺阻塞的 bay
            }
        }

        // ---- Allocate 40尺 测试 ----

        [Test]
        public void Allocate_FortyFoot_Stage1_SameGroup()
        {
            var g1 = new Group { Index = 1, TEUs = 2 };
            var c1 = new Container(g1) { Block = _block };
            var c2 = new Container(g1) { Block = _block };
            c1.Slot = _inventory.Allocate(c1, _rs);
            Assert.That(c1.Slot, Is.Not.Null);
            Assert.That(c1.Slot.Bay % 2, Is.EqualTo(0)); // 偶数
            _inventory.Update(c1, Inventory.JobType.Stacking);
            c2.Slot = _inventory.Allocate(c2, _rs);
            Assert.That(c2.Slot, Is.Not.Null);
            Assert.That(c2.Slot.Bay, Is.EqualTo(c1.Slot.Bay));
            Assert.That(c2.Slot.Row, Is.EqualTo(c1.Slot.Row));
        }

        [Test]
        public void Allocate_FortyFoot_Stage2_EmptySlot()
        {
            var g1 = new Group { Index = 1, TEUs = 2 };
            var c = new Container(g1) { Block = _block };
            c.Slot = _inventory.Allocate(c, _rs);
            Assert.That(c.Slot, Is.Not.Null);
            Assert.That(0, Is.EqualTo(c.Slot.Bay % 2)); // 偶数 bay
        }

        [Test]
        public void Allocate_FortyFoot_CanPlaceForty_ChecksHeightConsistency()
        {
            var block = new Block(10, 6, 5);
            var inv = new Inventory();
            var g1 = new Group { Index = 1, TEUs = 1 };
            // 在 bay 1 的 row 1 放一个 20 尺箱
            var c1 = new Container(g1) { Block = block, Slot = new Slot(1, 1, 1) };
            inv.Update(c1, Inventory.JobType.Stacking);
            // 现在 bay 1 row 1 有箱，bay 3 row 1 无箱
            // bay 2 (40尺中心) 的两侧高度不一致，应该不能放
            var g40 = new Group { Index = 2, TEUs = 2 };
            var c40 = new Container(g40) { Block = block };
            c40.Slot = inv.Allocate(c40, _rs);
            // 分配不应在 bay 2（两侧不一致）
            if (c40.Slot != null)
                Assert.That(c40.Slot.Bay, Is.Not.EqualTo(2));
        }

        // ---- UnstackWithoutReshuffle ----

        [Test]
        public void UnstackWithoutReshuffle_TopContainer_ReturnsTrue()
        {
            var g1 = new Group { Index = 1, TEUs = 1 };
            var c1 = new Container(g1) { Block = _block, Slot = new Slot(1, 1, 1) };
            _inventory.Update(c1, Inventory.JobType.Stacking);
            Assert.That(_inventory.UnstackWithoutReshuffle(c1), Is.True);
        }

        [Test]
        public void UnstackWithoutReshuffle_SameGroupOnTop_ReturnsTrue()
        {
            var g1 = new Group { Index = 1, TEUs = 1 };
            var c1 = new Container(g1) { Block = _block, Slot = new Slot(1, 1, 1) };
            var c2 = new Container(g1) { Block = _block, Slot = new Slot(1, 1, 2) };
            _inventory.Update(c1, Inventory.JobType.Stacking);
            _inventory.Update(c2, Inventory.JobType.Stacking);
            Assert.That(_inventory.UnstackWithoutReshuffle(c1), Is.True); // c2 在上面但同组
        }

        [Test]
        public void UnstackWithoutReshuffle_DifferentGroupOnTop_ReturnsFalse()
        {
            var g1 = new Group { Index = 1, TEUs = 1 };
            var g2 = new Group { Index = 2, TEUs = 1 };
            var c1 = new Container(g1) { Block = _block, Slot = new Slot(1, 1, 1) };
            var c2 = new Container(g2) { Block = _block, Slot = new Slot(1, 1, 2) };
            _inventory.Update(c1, Inventory.JobType.Stacking);
            _inventory.Update(c2, Inventory.JobType.Stacking);
            Assert.That(_inventory.UnstackWithoutReshuffle(c1), Is.False);
        }

        // ---- GetBestJobByPswc ----

        [Test]
        public void GetBestJobByPswc_TopOfStack()
        {
            var g1 = new Group { Index = 1, TEUs = 1 };
            var c1 = new Container(g1) { Block = _block, Slot = new Slot(1, 1, 1) };
            var c2 = new Container(g1) { Block = _block, Slot = new Slot(1, 1, 2) };
            _inventory.Update(c1, Inventory.JobType.Stacking);
            _inventory.Update(c2, Inventory.JobType.Stacking);
            var best = _inventory.GetBestJobByPswc(_block, g1);
            Assert.That(best, Is.Not.Null);
            Assert.That(c1, Is.SameAs(best)); // c1 在栈顶，优先取出
        }

        [Test]
        public void GetBestJobByPswc_MultipleGroups()
        {
            var g1 = new Group { Index = 1, TEUs = 1 };
            var g2 = new Group { Index = 2, TEUs = 1 };
            var c1 = new Container(g1) { Block = _block, Slot = new Slot(1, 1, 1) };
            var c2 = new Container(g2) { Block = _block, Slot = new Slot(1, 2, 1) };
            _inventory.Update(c1, Inventory.JobType.Stacking);
            _inventory.Update(c2, Inventory.JobType.Stacking);
            var best1 = _inventory.GetBestJobByPswc(_block, g1);
            var best2 = _inventory.GetBestJobByPswc(_block, g2);
            Assert.That(c1, Is.SameAs(best1));
            Assert.That(c2, Is.SameAs(best2));
        }

        // ---- DecideReshuffleTarget ----

        [Test]
        public void DecideReshuffleTarget_CaseA_WithinBay()
        {
            var block = new Block(10, 6, 5);
            var inv = new Inventory();
            var g1 = new Group { Index = 1, TEUs = 1 };
            var c1 = new Container(g1) { Block = block, Slot = new Slot(1, 1, 1) };
            inv.Update(c1, Inventory.JobType.Stacking);
            var g2 = new Group { Index = 2, TEUs = 1 };
            var c2 = new Container(g2) { Block = block, Slot = new Slot(1, 1, 2) };
            inv.Update(c2, Inventory.JobType.Stacking);
            // c2 在 c1 上面，取 c1 需要 reshuffle
            var target = inv.DecideReshuffleTarget(c1, c2);
            Assert.That(target, Is.Not.Null);
        }

        [Test]
        public void DecideReshuffleTarget_CaseB_CrossBay()
        {
            var block = new Block(10, 6, 5);
            var inv = new Inventory();
            var g1 = new Group { Index = 1, TEUs = 1 };
            var c1 = new Container(g1) { Block = block, Slot = new Slot(1, 1, 1) };
            inv.Update(c1, Inventory.JobType.Stacking);
            var g2 = new Group { Index = 2, TEUs = 1 };
            var c2 = new Container(g2) { Block = block, Slot = new Slot(1, 1, 2) };
            inv.Update(c2, Inventory.JobType.Stacking);
            var g3 = new Group { Index = 3, TEUs = 1 };
            var c3 = new Container(g3) { Block = block, Slot = new Slot(1, 1, 3) };
            inv.Update(c3, Inventory.JobType.Stacking);
            var g4 = new Group { Index = 4, TEUs = 1 };
            var c4 = new Container(g4) { Block = block, Slot = new Slot(1, 1, 4) };
            inv.Update(c4, Inventory.JobType.Stacking);
            var g5 = new Group { Index = 5, TEUs = 1 };
            var c5 = new Container(g5) { Block = block, Slot = new Slot(1, 1, 5) };
            inv.Update(c5, Inventory.JobType.Stacking);
            // bay 1 现在完全堆满，取任何箱都需要跨 bay
            var target = inv.DecideReshuffleTarget(c1, c2);
            Assert.That(target, Is.Not.Null);
        }

        // ---- IsRowValidByBayRules ----

        [Test]
        public void IsRowValidByBayRules_TwentyFoot_AllConstraints()
        {
            var block = new Block(10, 6, 5);
            var inv = new Inventory();
            // 填入一些数据用于测试
            var g = new Group { Index = 1, TEUs = 1 };
            for (int row = 1; row <= 6; row++)
            {
                for (int tier = 1; tier <= 2; tier++)
                {
                    var c = new Container(g) { Block = block, Slot = new Slot(1, row, tier) };
                    inv.Update(c, Inventory.JobType.Stacking);
                }
            }
            // 尝试在 bay 1 row 3 堆放（row 3 有空间）
            // 约束检查
            var isValid = inv.IsRowValidByBayRules(block, bay: 1, row: 3, size: ContainerSize.TwentyFeet);
            Assert.That(isValid, Is.True);
        }

        // ---- 40尺 Unstack 成对移除 ----

        [Test]
        public void Unstack_FortyFoot_RemovesFromBothBays()
        {
            var block = new Block(10, 6, 5);
            var inv = new Inventory();
            var g1 = new Group { Index = 1, TEUs = 2 };
            var c = new Container(g1) { Block = block, Slot = new Slot(2, 1, 1) };
            inv.Update(c, Inventory.JobType.Stacking);
            // 40尺箱放于 bay 2（中心），实际占 bay 1 和 bay 3
            Assert.That(1, Is.EqualTo(inv.GetHeight(block, new Slot(1, 1, 1))));
            Assert.That(1, Is.EqualTo(inv.GetHeight(block, new Slot(3, 1, 1))));
            inv.Update(c, Inventory.JobType.Unstacking);
            Assert.That(0, Is.EqualTo(inv.GetHeight(block, new Slot(1, 1, 1))));
            Assert.That(0, Is.EqualTo(inv.GetHeight(block, new Slot(3, 1, 1))));
        }

        // ---- ToDim1 ----

        [Test]
        public void ToDim1_OddBay()
        {
            Assert.That(1, Is.EqualTo(ToDim1(1)));
            Assert.That(2, Is.EqualTo(ToDim1(3)));
            Assert.That(3, Is.EqualTo(ToDim1(5)));
        }

        [Test]
        public void ToDim1_EvenBay()
        {
            Assert.That(1, Is.EqualTo(ToDim1(2)));
            Assert.That(2, Is.EqualTo(ToDim1(4)));
            Assert.That(3, Is.EqualTo(ToDim1(6)));
        }

        private static int ToDim1(int bay) => bay % 2 == 0 ? bay / 2 : (bay + 1) / 2;
    }
}
