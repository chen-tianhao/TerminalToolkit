#nullable enable
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading.Tasks;


namespace Assets.SingaPort
{
    public class Block
    {
        public static int Count { get; private set; } = 0;
        public static float SlotLength = 6.5f;
        public static float SlotWidth = 2.5f;
        public static float SlotHeight = 2.6f;
        public int Index { get; private set; }
        public int NumBays { get; private set; }
        public int NumRows { get; private set; }
        public int MaxNumTiers { get; private set; }
        public int CapacityTEUs { get { return (NumBays + 1) / 2 * NumRows * MaxNumTiers; } }
        public int NumContainers { get { return Bays.Values.Sum(v => v.NumContainers); } }
        public int NumTEUs { get { return Bays.Values.Sum(v => v.NumTEUs); } }
        public Dictionary<int, Bay> Bays { get; private set; }

        // numBays must be odd, coz bayIndex: 1,2,3,... odd: 20ft even:40ft
        public Block(int numBays, int numRows, int maxNumTiers)
        {
            Index = ++Count;
            Bays = new Dictionary<int, Bay>();
            NumBays = numBays;
            NumRows = numRows;
            MaxNumTiers = maxNumTiers;
        }
        /// <summary>
        /// 为集装箱选择合适的 Bay 位置
        /// 算法目标：
        /// 1. 优先使用已有且未满的同尺寸 Bay
        /// 2. 新建 Bay 时保持合理的空间布局（避免零散的单独 Bay）
        /// 3. 平衡 20 尺和 40 尺 Bay 的利用率
        /// </summary>
        /// <param name="containerSize">集装箱尺寸</param>
        /// <param name="rs">随机数生成器</param>
        /// <returns>选中的 Bay 索引，若无合适位置则返回 null</returns>
        public int? GetBayIndexToStack(ContainerSize containerSize, Random rs)
        {
            var indices = new List<int>();
            var twentyFeetBays = Bays.Values.Where(b => b.ContainerSize == ContainerSize.TwentyFeet).ToList();
            var fortyFeetBays = Bays.Values.Where(b => b.ContainerSize == ContainerSize.FortyFeet).ToList();

            // lessTwentyBays: 判断当前 20 尺箱的平均装载量是否小于等于 40 尺箱
            // 如果 20 尺箱装载率较低，则倾向于创建新的 20 尺 Bay
            var lessTwentyBays =
                (twentyFeetBays.Count > 0 ? twentyFeetBays.Average(b => 1.0f * b.NumContainers) : 0f)
                >= (fortyFeetBays.Count > 0 ? fortyFeetBays.Average(b => 1.0f * b.NumContainers) : 0f);

            switch (containerSize)
            {
                case ContainerSize.TwentyFeet:
                    // 20尺柜只能放在奇数位置 (1,3,5,...)
                    for (int i = 1; i < NumBays * 2; i += 2)
                    {
                        // 特殊处理：如果是第一个 Bay，直接接受，避免无法起仓
                        if (Bays.Count == 0)
                        {
                            indices.Add(i);
                            break;
                        }

                        // 情况1: 该位置已有 20 尺 Bay 且未满 -> 可用
                        if (Bays.ContainsKey(i))
                        {
                            if (!Bays[i].IsFull) indices.Add(i);
                        }
                        // 情况2: 该位置为空，尝试创建新的 20 尺 Bay
                        // 条件：1) 还没有任何 20 尺 Bay；或 2) 两侧有邻近的 20 尺 Bay（形成连续区域）；或 3) 20 尺装载率较低需要平衡
                        else if (twentyFeetBays.Count == 0 ||
                            ((i == 1 || Bays.ContainsKey(i - 2) || Bays.ContainsKey(i - 3)) &&
                            (Bays.ContainsKey(i + 2) || Bays.ContainsKey(i + 3) || i == NumBays * 2 - 1))
                            || lessTwentyBays)
                        {
                            // 不在两侧创建"气泡"（孤立的单个 Bay）
                            // 至少有一侧有两个相邻的 Bay 才认为是合理的布局
                            if (!Bays.ContainsKey(i - 1) && !Bays.ContainsKey(i + 1))
                                if (Bays.ContainsKey(i - 2) || Bays.ContainsKey(i - 3) || Bays.ContainsKey(i + 2) || Bays.ContainsKey(i + 3))
                                    indices.Add(i);
                        }
                    }
                    break;
                case ContainerSize.FortyFeet:
                    // 40尺柜只能放在偶数位置 (2,4,6,...)，占用 bay-1 和 bay+1 两个奇数位置
                    for (int i = 2; i < NumBays * 2; i += 2)
                    {
                        // 情况1: 该位置已有 40 尺 Bay 且未满 -> 可用
                        if (Bays.ContainsKey(i))
                        {
                            if (!Bays[i].IsFull) indices.Add(i);
                        }
                        // 情况2: 该位置为空，尝试创建新的 40 尺 Bay
                        // 条件：1) 还没有任何 40 尺 Bay；或 2) 40 尺装载率较高需要平衡
                        else if (fortyFeetBays.Count == 0 || !lessTwentyBays)
                        {
                            // 确保两侧 (bay-1, bay+1, bay-2, bay+2) 都有足够空间，避免与现有 Bay 冲突
                            if (!Bays.ContainsKey(i - 1) && !Bays.ContainsKey(i + 1) &&
                                !Bays.ContainsKey(i - 2) && !Bays.ContainsKey(i + 2))
                                indices.Add(i);
                        }
                    }
                    break;
                default:
                    throw new Exception();

            }
            if (indices.Count == 0) return null;
            //if (containerSize == ContainerSize.TwentyFeet) return indices.Min();
            //else return indices.Max();
            return indices[rs.Next(indices.Count)];
        }

        public bool StackContainer(Container container, Random rs, ref int? bayIndex, ref int? rowIndex, ref int? tierIndex)
        {
            // 当前函数的用途是返回bayIndex，全部调用结束后，实际返回index of bay/row/tier
            bayIndex = GetBayIndexToStack(container.Size, rs);
            if (bayIndex == null) return false;
            return StackContainer(container, rs, bayIndex.Value, ref rowIndex, ref tierIndex);
        }

        public bool StackContainer(Container container, Random rs, int bayIndex, ref int? rowIndex, ref int? tierIndex)
        {
            // 当前函数的用途是根据bayIndex找到或创建bay
            var bay = CreateBayIfNotExist(bayIndex, container.Size);
            return bay.StackContainer(container, rs, ref rowIndex, ref tierIndex);
        }

        // public bool StackContainer(Container container, int bayIndex, int rowIndex, ref int? tierIndex)
        // {
        //     var bay = CreateBayIfNotExist(bayIndex, container.Size);
        //     return bay.StackContainer(container, rowIndex, ref tierIndex);
        // }

        internal Bay CreateBayIfNotExist(int bayIndex, ContainerSize size)
        {
            if (!Bays.ContainsKey(bayIndex))
            {
                if (bayIndex < 1 || bayIndex > NumBays * 2 - 1 ||
                    Bays.ContainsKey(bayIndex - 1) || Bays.ContainsKey(bayIndex + 1))
                    throw new Exception("Bay Index Infeasible.");
                if (size == ContainerSize.FortyFeet && bayIndex % 2 != 0)
                    throw new Exception("Bay Index Infeasible.");
                if (bayIndex % 2 == 0 && (Bays.ContainsKey(bayIndex - 2) || Bays.ContainsKey(bayIndex + 2)))
                    throw new Exception("Bay Index Infeasible.");
                Bays.Add(bayIndex, new Bay(this, size));
            }
            return Bays[bayIndex];
        }

        public static void ResetCount() { Count = 0; }
    }
}
