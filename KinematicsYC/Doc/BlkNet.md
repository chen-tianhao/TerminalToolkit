# BlkNet 模块文档

> 本文档基于 KinematicsYC/Net 目录下的 C# 源代码生成，所有描述均以代码为准。

---

## 一、概述

BlkNet 是滚装船（PCTC/RCC）集装箱堆场管理的核心数据模型，命名空间为 `Assets.SingaPort`。该模块以分层结构组织数据，从宏观的甲板区域（Block）到中观的贝位（Bay），再到微观的具体槽位（Slot），完整覆盖了集装箱堆场的三维空间表示与存取操作逻辑。

文件结构如下：

| 文件 | 职责 |
|---|---|
| `Slot.cs` | 槽位三维坐标 |
| `Container.cs` | 集装箱实体与分组 |
| `Bay.cs` | 单个贝位及行堆叠管理 |
| `Block.cs` | 甲板区域，管理所有贝位 |
| `Inventory.cs` | 全局库存操作：分配槽位、翻箱、重排目标选择 |

---

## 二、数据类型

### 2.1 枚举

**`ContainerSize`（Container.cs 第 22 行）**

```csharp
public enum ContainerSize { FortyFeet, TwentyFeet }
```

两种标准集装箱尺寸规格，不存在其他枚举值。

---

**`Inventory.JobType`（Inventory.cs 第 13-17 行）**

```csharp
public enum JobType
{
    Stacking,   // 堆箱（放入）
    Unstacking  // 取箱（取出）
}
```

---

### 2.2 Slot —— 槽位坐标

`Slot.cs`，第 3-15 行：

```csharp
public class Slot
{
    public int Bay { get; set; }
    public int Row { get; set; }
    public int Tier { get; set; }

    public Slot(int bay, int row, int tier) { ... }
}
```

**字段含义：**

| 字段 | 含义 | 取值范围 |
|---|---|---|
| `Bay` | 贝位索引 | `1` ~ `NumBays * 2 - 1`（奇数为 20 尺，偶数为 40 尺中心位） |
| `Row` | 排索引 | `1` ~ `NumRows` |
| `Tier` | 层索引（从下往上） | `1` ~ `MaxNumTiers` |

> **注意：** 40 尺集装箱在物理上占 `bay-1` 和 `bay+1` 两个奇数 bay 位（见 Inventory 第 548-551 行），但 `Slot.Bay` 字段记录的是偶数中心位。例如 40 尺箱的 Slot 表示为 Bay=2，实际占用 Bay=1 和 Bay=3。

---

### 2.3 Container —— 集装箱

`Container.cs`，第 23-38 行：

```csharp
public class Container
{
    public static int Count { get; private set; } = 0;
    public const float Height = 2.59f;
    public int Index { get; private set; }
    public ContainerSize Size { get; private set; }
    public Group Group { get; set; }
    public Block Block { get; set; }
    public Slot Slot { get; set; }

    public Container(Group group)
    {
        Index = ++Count;
        Group = group;
        Size = group.TEUs == 2 ? ContainerSize.FortyFeet : ContainerSize.TwentyFeet;
    }
}
```

**属性说明：**

| 属性 | 说明 |
|---|---|
| `Count` | 静态计数器，所有 Container 实例共享，用于为每个集装箱分配唯一序号 |
| `Height` | 常量 `2.59f`（米），仅作为参考数据，未参与任何计算逻辑 |
| `Index` | 实例序号，从 1 开始，每次构造递增 1 |
| `Size` | 由 `Group.TEUs` 决定：TEUs=2 → `FortyFeet`，否则 → `TwentyFeet` |
| `Group` | 该箱所属的分组（PSWC，同票货物） |
| `Block` | 该箱所在甲板区域引用 |
| `Slot` | 该箱在堆场中的槽位坐标，可以为 null（未分配时） |

---

### 2.4 Group —— 集装箱分组

`Container.cs`，第 9-20 行：

```csharp
public class Group
{
    public int Index { get; set; }
    public int TEUs { get; set; }
    public int Size { get; set; }
    public List<Container> Containers { get; set; } = new List<Container>();
    public DateTime Timestamp_Unstack { get; set; }

    public override string ToString() => $"Group#{Index}";
}
```

**属性说明：**

| 属性 | 说明 |
|---|---|
| `Index` | 分组序号 |
| `TEUs` | 该组总 TEUs 数（1 或 2），决定集装箱尺寸 |
| `Size` | 含义不明确，代码中未使用 |
| `Containers` | 该组包含的所有集装箱实例列表 |
| `Timestamp_Unstack` | 该组被取走（出栈）的时间戳 |

---

## 三、Bay 类

`Bay.cs`，第 9-104 行。

### 3.1 核心属性

```csharp
public ContainerSize ContainerSize { get; private set; }
public Dictionary<int, List<Container>> Stacks { get; private set; }
public Block Block { get; private set; }
```

- `Stacks` 是一个以 `Row`（排号）为键、`List<Container>` 为值的字典，List 内元素顺序即堆叠顺序（索引 0 = 底层）。
- `ContainerSize` 在构造时固定，不可更改（`private set`）。
- 同一个 Bay 内所有集装箱尺寸必须一致，由外部 `CreateBayIfNotExist` 保证。

### 3.2 派生属性

| 属性 | 计算公式 |
|---|---|
| `NumContainers` | `Stacks.Values.Sum(v => v.Count)` —— 所有排的集装箱总数 |
| `NumTEUs` | `NumContainers * (ContainerSize == FortyFeet ? 2 : 1)` |
| `IsFull` | 当且仅当**所有排**的堆高均达到 `Block.MaxNumTiers` 时为 true |

### 3.3 构造器

```csharp
public Bay(Block block, ContainerSize size)
{
    Block = block;
    ContainerSize = size;
    Stacks = Enumerable.Range(1, block.NumRows)
                       .ToDictionary(i => i, i => new List<Container>());
}
```

初始化后，所有排均为空 List，不预分配任何 Slot。

### 3.4 `GetRowIndexToStack` —— 选择最优 Row

**第 45-85 行**。在给定 Bay 内选择一个最合适的 Row 放置集装箱，返回值满足以下**全部 6 项约束**：

| 编号 | 约束条件 | 对应代码行 |
|---|---|---|
| 1 | 该排当前层数 < `MaxNumTiers` | 第 54 行 `Stacks[i].Count >= Block.MaxNumTiers` |
| 2 | 该排层数 - 最低排层数 ≤ 4 | 第 58 行 `Stacks[i].Count >= minHeight + 4` |
| 3 | 上侧（row+1）**不能更矮**（无陡坡） | 第 62 行 `Stacks[i].Count > Stacks[i+1].Count` |
| 4 | 下侧（row-1）**不能更矮**（无陡坡） | 第 66 行 `Stacks[i].Count > Stacks[i-1].Count` |
| 5 | 若当前排与上排等高，则 row+2 及更高排中**不能有更高的排**（无上洞） | 第 70-72 行 |
| 6 | 若当前排与下排等高，则 row-2 及更低排中**不能有更高的排**（无下洞） | 第 76-78 行 |

算法流程：
1. 遍历 1~NumRows 所有排，收集满足全部 6 项约束的排号到 `indices` 列表。
2. 若列表为空返回 null。
3. 若列表非空，从满足条件的排中**随机选一个**返回（第 84 行）。

> **关键设计点：** 约束 3 和 4 意味着 Bay 内的行高度变化只能是"上低下高"的**阶梯状**，不允许中间高两边低（凸起）或中间低两边高（凹陷）。约束 5 和 6 确保阶梯顶部两侧没有隐藏的更高层。

### 3.5 `StackContainer` —— 堆箱

两个重载：

```csharp
// 重载1：通过随机 Row 分配（Bay 内自动选 Row）
public bool StackContainer(Container container, Random rs,
    ref int? rowIndex, ref int? tierIndex)
{
    rowIndex = GetRowIndexToStack(rs);
    if (rowIndex == null) return false;
    return StackContainer(container, rowIndex.Value, ref tierIndex);
}

// 重载2：指定 Row
public bool StackContainer(Container container, int rowIndex, ref int? tierIndex)
{
    if (container.Size != ContainerSize || Stacks[rowIndex].Count >= Block.MaxNumTiers)
        return false;
    Stacks[rowIndex].Add(container);
    tierIndex = Stacks[rowIndex].Count;
    return true;
}
```

- 重载1 先调用 `GetRowIndexToStack` 随机选 Row，再调用重载2。
- 重载2 放入前检查两点：① 集装箱尺寸必须与 Bay 一致；② 该排未满。
- 放入成功后 `tierIndex` 被赋值为 `Stacks[rowIndex].Count`（堆入后的层号，即当前最高层+1）。

---

## 四、Block 类

`Block.cs`，第 12-155 行。

### 4.1 静态字段（全局常量）

| 字段 | 值 | 说明 |
|---|---|---|
| `Count` | `0` | 静态计数器，已创建 Block 总数 |
| `SlotLength` | `6.5f` | 单个槽位长度（米） |
| `SlotWidth` | `2.5f` | 单个槽位宽度（米） |
| `SlotHeight` | `2.6f` | 单个槽位高度（米） |

> 注意：`SlotLength`、`SlotWidth`、`SlotHeight` 是物理尺寸，不参与核心逻辑计算。

### 4.2 实例属性

| 属性 | 计算公式 |
|---|---|
| `Index` | `++Count`，构造时赋值，Block 的唯一序号 |
| `NumBays` | 构造参数，最初设计的 bay 总数 |
| `NumRows` | 构造参数，每 bay 的排数 |
| `MaxNumTiers` | 构造参数，最大堆层数 |
| `CapacityTEUs` | `(NumBays + 1) / 2 * NumRows * MaxNumTiers` |
| `NumContainers` | `Bays.Values.Sum(v => v.NumContainers)` |
| `NumTEUs` | `Bays.Values.Sum(v => v.NumTEUs)` |

> **关于 CapacityTEUs：** 公式中 `(NumBays + 1) / 2` 表示将物理 bay 索引（1..NumBays*2-1）映射为连续的逻辑 bay 编号（1..NumBays），奇数位为 20 尺中心，偶数位为 40 尺中心（每个 40 尺占两个逻辑 bay 位置）。

### 4.3 `GetBayIndexToStack` —— Bay 选择算法

**第 46-119 行**。根据集装箱尺寸选择一个最合适的 Bay，返回值或 null。

#### 20 尺箱（`ContainerSize.TwentyFeet`）

仅考虑**奇数** bay（1, 3, 5, ...）。

候选条件（满足其一即可）：
1. 该位置已有 20 尺 Bay 且未满（`!Bays[i].IsFull`）。
2. 位置为空，但满足以下**邻近条件之一**：
   - 还没有任何 20 尺 Bay（`twentyFeetBays.Count == 0`）；或
   - 该位置左侧（`i-2` 或 `i-3`）**或**右侧（`i+2` 或 `i+3` 或 `i == NumBays*2-1`）有 20 尺 Bay；且
   - **两侧不产生孤立气泡**：至少有一侧有邻近 Bay（`i-2/i-3/i+2/i+3` 其一存在），且中间间隔位（`i-1` 和 `i+1`）均为空。

3. 20 尺装载率 ≤ 40 尺装载率时（`lessTwentyBays == true`），放宽邻近条件。

> **气泡规则（第 85-87 行）：** 不允许在完全没有相邻 bay 的情况下创建孤立的单独 bay。例如 bay 5 两侧（bay 4 和 bay 6）都为空，且 bay 3 和 bay 7 也不存在，则不允许在 bay 5 创建新 bay。

#### 40 尺箱（`ContainerSize.FortyFeet`）

仅考虑**偶数** bay（2, 4, 6, ...）。40 尺箱物理上占 bay-1 和 bay+1 两个奇数位。

候选条件（满足其一即可）：
1. 该位置已有 40 尺 Bay 且未满。
2. 位置为空，且 `fortyFeetBays.Count == 0` 或 `!lessTwentyBays`（40 尺装载率较高时）；同时两侧（bay-1, bay+1, bay-2, bay+2）均无已有 Bay。

#### `lessTwentyBays` 的计算逻辑（第 54-56 行）

```csharp
var lessTwentyBays =
    (twentyFeetBays.Count > 0 ? twentyFeetBays.Average(b => 1.0f * b.NumContainers) : 0f)
    >= (fortyFeetBays.Count > 0 ? fortyFeetBays.Average(b => 1.0f * b.NumContainers) : 0f);
```

当 `lessTwentyBays == true` 时，表示 20 尺 Bay 的**平均**装载量 >= 40 尺 Bay 的平均装载量，即 20 尺 Bay "更满"，此时应优先新建 40 尺 Bay；反之亦然。

### 4.4 `StackContainer` 重载

与 Bay 类的重载模式相同：

```csharp
// 重载1：通过随机 Bay 分配
public bool StackContainer(Container container, Random rs,
    ref int? bayIndex, ref int? rowIndex, ref int? tierIndex)

// 重载2：指定 Bay
public bool StackContainer(Container container, Random rs,
    int bayIndex, ref int? rowIndex, ref int? tierIndex)
```

### 4.5 `CreateBayIfNotExist` —— 创建新 Bay

**第 142-154 行**，在指定 bay 索引处创建新 Bay（若不存在）。

**前置校验（不满足则抛出异常）：**

| 条件 | 含义 |
|---|---|
| `bayIndex < 1` 或 `bayIndex > NumBays * 2 - 1` | 索引越界 |
| `Bays.ContainsKey(bayIndex - 1)` 或 `Bays.ContainsKey(bayIndex + 1)` | 该 bay 左右已存在 Bay |
| `bayIndex % 2 == 0` 且（`bayIndex-2` 或 `bayIndex+2` 存在） | 40 尺 bay 的跨度（bay±2）内已有其他 bay |

创建后返回对应 Bay 实例引用。

---

## 五、Inventory 类

`Inventory.cs`，第 11-692 行，是模块中规模最大、逻辑最复杂的类。

### 5.1 内部数据结构

**`GroundSlot`（第 19-23 行）**

```csharp
private sealed class GroundSlot
{
    public List<Container> gsStack { get; } = new();  // 自底向上存储
    public int FlippedLayers { get; set; }           // 已翻动层数累计
}
```

`gsStack` 即该槽位（bay × row）的堆栈，索引 0 = 底层。`FlippedLayers` 记录针对该 GroundSlot 已发生的翻箱（rehandle）次数。

**`_map`（第 25 行）**

```csharp
private readonly Dictionary<(int blockId, int dim1, int dim2), GroundSlot> _map = new();
```

键为三元组 `(blockId, dim1, dim2)`，用于唯一索引一个 GroundSlot。

### 5.2 Bay 索引压缩 —— `ToDim1`（第 28 行）

```csharp
private static int ToDim1(int bay) => bay % 2 == 0 ? bay / 2 : (bay + 1) / 2;
```

将原始 bay 索引（1..NumBays*2-1）压缩为连续的逻辑索引（1..NumBays）：

| 原始 bay | 类型 | dim1 |
|---|---|---|
| 奇数（1,3,5,...） | 20尺中心 | `(bay+1)/2` |
| 偶数（2,4,6,...） | 40尺中心 | `bay/2` |

例如 bay=5 → dim1=3，bay=2 → dim1=1。

### 5.3 `Allocate` —— 槽位分配（核心算法）

**第 31-249 行**。为核心集装箱分配最优槽位，采用**四阶段优先策略**：

```
Stage 1: 同 PSWC（Group）已有的最高可堆放位置
Stage 2: 空槽位（随机选择）
Stage 3: 最高未满槽位（优先取高）
Stage 4: 返回 null（无有效位置）
```

#### 5.3.1 Stage 1：同 PSWC 已有位置

对于 40 尺箱（第 82-98 行）：
- 遍历所有偶数 bay（`2, 4, 6, ...`），随机顺序遍历各 row。
- `CanPlaceForty(bay, row, out tier)` 确认可以放置（见 5.3.4）。
- 顶层箱（`Peek(block, Slot(bay-1, row, 1))`）若与目标箱属于同一 Group，直接返回该位置。

对于 20 尺箱（第 99-120 行）：
- 遍历所有奇数 bay（`1, 3, 5, ...`），随机顺序遍历各 row。
- 确认 `Peek` 到的顶层箱与目标箱同 Group。
- 同时要求该 bay 未被 40 尺箱阻塞（`IsBayBlockedFor20`）。
- 有效层 < `MaxNumTiers` 时方可返回。

#### 5.3.2 Stage 2：空槽位

对于 40 尺箱（第 123-174 行）：
- 收集所有满足以下全部条件的候选 (bay, row, tier)：
  - `bay-1` 和 `bay+1` 在所有 row 上高度一致（`heightsConsistent`）。
  - 若两侧有箱则必须是同一个实例引用（`containersConsistent`），即来自同一个 40 尺箱。
  - 当前 row 的两侧均为空（高度=0）。
  - `CanPlaceForty` 返回 true。
- 从候选列表中随机选一个返回。

对于 20 尺箱（第 175-197 行）：
- 收集所有满足：bay 未被阻塞、该 bay-row 高度=0 的候选。
- 从中随机选一个返回（tier=1）。

#### 5.3.3 Stage 3：最高未满槽位

对于两种尺寸（第 199-244 行）：
- 遍历所有有效 bay 和 row，计算当前堆高 `h`。
- 对于 40 尺：`h = tier - 1`（其中 tier 来自 `CanPlaceForty`）。
- 对于 20 尺：`h = GetHeight`。
- 选取 `h` 最大的候选（`bestHeight`），若有并列不比较行距离，直接取遍历中最后遇到的。
- 若 `bestBay > 0` 返回该位置，否则进入 Stage 4。

#### 5.3.4 `CanPlaceForty` —— 40 尺放置可行性（第 51-76 行）

```csharp
bool CanPlaceForty(int bay, int row, out int tier)
```

返回 true 当且仅当满足以下**所有条件**：

| # | 条件 | 代码 |
|---|---|---|
| 1 | `bay` 必须为偶数 | `bay % 2 != 0` 时返回 false |
| 2 | `bay > 1` 且 `bay < maxBayIndex`（不超过边界） | 第 55 行 |
| 3 | `bay-1` 和 `bay+1` 所有 row 中**不存在**任何 20 尺箱 | 第 62-69 行 |
| 4 | 两排高度相等：`h1 == h2` | 第 72 行 |
| 5 | 顶层一致性：两侧**同时为空**或**同时指向同一 40 尺箱实例** | 第 70-72 行 |
| 6 | 当前高度 < `MaxNumTiers` | 第 73 行 |

满足时 `tier = h1 + 1`（两侧高度 +1 层）。

#### 5.3.5 `IsBayBlockedFor20` —— 20 尺 Bay 阻塞判断（第 40-48 行）

```csharp
bool IsBayBlockedFor20(int bay)
```

当该 bay 任一 row 的底层存在 40 尺箱时（`Peek` 返回的箱尺寸为 FortyFeet），返回 true。意味着该 bay 物理上已被 40 尺箱占满，20 尺箱无法再放入。

### 5.4 `UnstackWithoutReshuffle` —— 无重排取箱判断

**第 251-257 行**：

```csharp
public bool UnstackWithoutReshuffle(Container container)
{
    Container? containerOnTop = Peek(container.Block, container.Slot);
    if (containerOnTop == null) return true;
    bool ret = container.Group == containerOnTop.Group;
    return ret;
}
```

逻辑：查看目标箱上方的箱，若无箱（目标箱在栈顶）→ 可直接取；若有箱 → 仅当两组属于同一 Group 时才可直接取，否则需要翻箱（reshuffle）。

### 5.5 `Update` —— 库存状态更新

**第 259-275 行**：

```csharp
public void Update(Container container, JobType opType)
```

| opType | 行为 |
|---|---|
| `Stacking` | 调用 `Stack(container.Block, container.Slot, container)` |
| `Unstacking` | 调用 `Unstack(container.Block, container.Slot)` |

若 `container.Slot` 任一分量为 0（即未分配过槽位），方法直接返回，不做任何操作。

### 5.6 `Stack` / `Unstack` —— 底层堆叠操作

**`Stack`（第 543-557 行）：**

```csharp
private void Stack(Block block, Slot slot, Container container)
{
    if (container.Size == ContainerSize.FortyFeet)
    {
        int leftBay = slot.Bay - 1;
        int rightBay = slot.Bay + 1;
        GetGroundSlot(block, new Slot(leftBay, slot.Row, slot.Tier)).gsStack.Add(container);
        GetGroundSlot(block, new Slot(rightBay, slot.Row, slot.Tier)).gsStack.Add(container);
    }
    else
    {
        GetGroundSlot(block, slot).gsStack.Add(container);
    }
}
```

- 40 尺箱**同时**放入 `bay-1` 和 `bay+1` 两个 GroundSlot，每次 Add 的是同一个 Container 实例引用。
- 20 尺箱只放入对应 bay 的 GroundSlot。

**`Unstack`（第 559-571 行）：**

```csharp
private Container? Unstack(Block block, Slot slot)
{
    var gs = GetGroundSlot(block, slot);
    if (gs.gsStack.Count == 0) return null;
    var top = gs.gsStack[^1];
    gs.gsStack.RemoveAt(gs.gsStack.Count - 1);
    if (top.Size == ContainerSize.FortyFeet)
    {
        var gsPair = GetGroundSlot(block, new Slot(slot.Bay + 2, slot.Row, slot.Tier));
        if (gsPair.gsStack.Count > 0) gsPair.gsStack.RemoveAt(gsPair.gsStack.Count - 1);
    }
    return top;
}
```

- 总是取栈顶箱（`gsStack[^1]`），并从栈中移除。
- 对于 40 尺箱，额外从 `bay+2` 位置的对应 GroundSlot 中也移除栈顶（因为 `bay-1` 的已经在上面 `gs.gsStack` 中移除了，`bay+2` 是另一半的对应位置）。

> **注意：** Unstack 中 `slot.Bay + 2` 而不是 `slot.Bay + 1`。这是因为 40 尺箱占 bay-1 和 bay+1，当从 bay 的偶数中心位 Unstack 时，已经处理了 bay+1 的那一半；另一半对应的是 bay+2（即 (bay+1)+1）。这里存在一个潜在问题：如果bay+2越界，可能会访问到错误的GroundSlot。

### 5.7 `GetBestJobByPswc` —— 按 Group 最优取箱选择

**第 282-335 行**。在指定 Block 内找到属于给定 Group 的所有集装箱中，"最优"（最容易取出）的一个。

**优先级排序规则（三级比较）：**

| 优先级 | 字段 | 含义 | 越小越优 |
|---|---|---|---|
| 第1 | `depthFromTop` | 栈内深度，0=栈顶 | ✅ |
| 第2 | `height` | 该 GroundSlot 总层数 | 越大越优 |
| 第3a | `bay` | Bay 索引 | 越大越优 |
| 第3b | `row` | Row 索引 | 越大越优 |

算法：从顶向下遍历每个 GroundSlot，第一个匹配的箱即为该 Stack 中的最优候选；跨 Stack 之间按三级比较确定最优。

### 5.8 `DecideReshuffleTarget` —— 重排目标选择

**第 337-530 行**。当取箱需要翻箱时，确定将箱移至哪个替代槽位。

**Case A（第 483-491 行）：当前 bay 未完全堆满**

优先在当前 bay 内部解决，不移动到其他 bay：

```
SamePswcTop(bay) ?? ClosestEmpty(bay) ?? TallestNonFull(bay)
```

**Case B（第 494-529 行）：当前 bay 已完全堆满**

需要跨 bay 移动。使用 `PickAcross` 辅助函数，搜索所有 bay：

```
优先避开同 PSWC → SamePswcTop → ClosestEmpty → TallestNonFull
若均无结果 → 不限 PSWC → SamePswcTop → ClosestEmpty → TallestNonFull
```

`PickAcross` 的选择逻辑：先比较 bay 距离（`Math.Abs(b - currentBay)`），距离近者优先；距离相同时比较 row 距离，距离近者优先。

**三个辅助 picker 函数：**

| 函数 | 策略 |
|---|---|
| `SamePswcTop(b)` | 在指定 bay 中找与参考箱同 Group 的最高可堆位置 |
| `ClosestEmpty(b)` | 在指定 bay 中找高度=0（空）的最近槽位 |
| `TallestNonFull(b)` | 在指定 bay 中选未满且当前高度最高的槽位（并列时取 row 最近） |

### 5.9 `IsRowValidByBayRules` —— Bay 风格堆叠限制验证

**第 579-661 行**。与 `Bay.GetRowIndexToStack` 的 6 项约束完全一致，但在 `Inventory.Allocate` 的 Stage 1/2/3 中作为可选过滤条件使用（`applyRowStackingLimit` 参数）。

对于 40 尺箱，该函数同时检查 bay-1 和 bay+1 两侧，取两侧高度的最大值进行计算（第 597-606 行）。

### 5.10 `Peek` —— 查看栈顶箱

**第 573-577 行**：

```csharp
public Container? Peek(Block block, Slot slot)
{
    var gs = GetGroundSlot(block, slot);
    return gs.gsStack.Count == 0 ? null : gs.gsStack[^1];
}
```

返回指定 Slot 对应 GroundSlot 的栈顶集装箱引用，若栈为空返回 null。

### 5.11 `GetHeight` —— 获取堆高

**第 277-280 行**：

```csharp
public int GetHeight(Block block, Slot slot)
{
    return GetGroundSlot(block, slot).gsStack.Count;
}
```

即该 GroundSlot 中已堆叠的集装箱数量（从 0 开始）。

---

## 六、数据流总览

```
Group / Container
    │
    ▼
Block.GetBayIndexToStack()  ──►  Bay.CreateBayIfNotExist()
    │                                  │
    ▼                                  ▼
 Bay.StackContainer()          Bay.GetRowIndexToStack()
    │                                  │
    ▼                                  ▼
 Inventory.Allocate()          分配 Slot (bay, row, tier)
    │
    ├───[Stacking]────► Inventory.Stack() ──► GroundSlot.gsStack.Add()
    │
    └───[Unstacking]──► Inventory.Unstack() ──► GroundSlot.gsStack.RemoveAt()
```

---

## 七、关键设计约束汇总

| 约束 | 位置 | 说明 |
|---|---|---|
| Bay 内只能堆放同尺寸集装箱 | `Bay` 构造外部保证 | 不同尺寸不能混放入同一 Bay |
| 40 尺箱占 bay-1 和 bay+1 两个奇数位 | `Inventory.Stack()` | 同一实例引用同时放入两侧 GroundSlot |
| 20 尺箱不能放入存在 40 尺箱的 Bay | `IsBayBlockedFor20()` | 任一 row 有 40 尺顶箱则整 bay 阻塞 |
| 40 尺箱放置需两侧 20 尺箱全不存在 | `CanPlaceForty()` | 包括所有 row 的全面检查 |
| 40 尺箱放置需两侧高度一致 | `CanPlaceForty()` | h1 == h2，两侧层数必须相等 |
| Bay 内各排高度差不超过 4 层 | `Bay.GetRowIndexToStack()` | 限制2 |
| Bay 内不允许出现陡坡或凹陷 | `Bay.GetRowIndexToStack()` | 限制3-6 |
| Bay 内最大层数受 `MaxNumTiers` 限制 | 多处 | 所有涉及层数判断处 |
