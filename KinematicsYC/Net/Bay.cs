using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Assets.SingaPort
{
    public class Bay
    {
        public ContainerSize ContainerSize { get;private set; }
        public Dictionary<int,List<Container>> Stacks { get; private set; }
        public Block Block { get; private set; }
        public int NumContainers { get { return Stacks.Values.Sum(v => v.Count); } }
        public int NumTEUs { get { return NumContainers * (ContainerSize == ContainerSize.FortyFeet ? 2 : 1); } }
        public bool IsFull
        {
            get
            {
                foreach (var stack in Stacks.Values) 
                    if (stack.Count < Block.MaxNumTiers) return false;
                return true;
            }
        }
        public Bay(Block block, ContainerSize size)
        {
            Block = block;
            ContainerSize = size;
            Stacks = Enumerable.Range(1, block.NumRows).ToDictionary(i => i, i => new List<Container>());
        }

        /// <summary>
        /// 为集装箱选择合适的 Row（排）位置
        /// 算法目标：保持贝位内各排的平整性，避免出现陡坡或凹陷
        /// 限制条件（共6项，全部满足才返回 true）：
        ///   1. 不超过最大层数限制
        ///   2. 与最低排的高度差不超过4层
        ///   3. 上侧（排号+1）不能更矮（避免陡坡）
        ///   4. 下侧（排号-1）不能更矮（避免陡坡）
        ///   5. 上侧无"洞"：如果当前排与上排等高，则上方不能有更高的排
        ///   6. 下侧无"洞"：如果当前排与下排等高，则下方不能有更高的排
        /// </summary>
        /// <param name="rs">随机数生成器</param>
        /// <returns>选中的 Row 索引，若无合适位置则返回 null</returns>
        public int? GetRowIndexToStack(Random rs)
        {
            var indices = new List<int>();
            // 获取当前各排的最小高度（用于计算高度差）
            var minHeight = Stacks.Values.Min(v => v.Count);

            for (var i = 1; i <= Stacks.Count; i++)
            {
                // 限制1: 避免超过最大层数
                if (Stacks[i].Count >= Block.MaxNumTiers) continue;

                // 限制2: 避免与最低排高度差大于4层
                // 保持各排相对平衡，避免某一排过高
                if (Stacks[i].Count >= minHeight + 4) continue;

                // 限制3: 上侧无陡坡
                // 当前排不能比上一排（排号更大）更高
                if (i < Stacks.Count && Stacks[i].Count > Stacks[i + 1].Count) continue;

                // 限制4: 下侧无陡坡
                // 当前排不能比下一排（排号更小）更高
                if (i > 1 && Stacks[i].Count > Stacks[i - 1].Count) continue;

                // 限制5: 上侧无"洞"
                // 如果当前排与上排等高，则上方不能存在更高的排（否则会形成凹陷）
                if (i < Stacks.Count - 1 && Stacks[i].Count == Stacks[i + 1].Count &&
                    Enumerable.Range(i + 2, Block.NumRows - i - 1).Count(i1 => Stacks[i1].Count > Stacks[i].Count) > 0)
                    continue;

                // 限制6: 下侧无"洞"
                // 如果当前排与下排等高，则下方不能存在更高的排（否则会形成凹陷）
                if (i > 2 && Stacks[i].Count == Stacks[i - 1].Count &&
                    Enumerable.Range(1, i - 2).Count(i1 => Stacks[i1].Count > Stacks[i].Count) > 0)
                    continue;

                indices.Add(i);
            }
            // 从所有满足条件的 Row 中随机选择一个
            if (indices.Count == 0) return null;
            return indices[rs.Next(indices.Count)];
        } 

        public bool StackContainer(Container container, Random rs, ref int? rowIndex, ref int? tierIndex)
        {
            // 当前函数的用途是返回rowIndex
            rowIndex = GetRowIndexToStack(rs);
            if (rowIndex == null) return false;
            return StackContainer(container, rowIndex.Value, ref tierIndex);
        }

        public bool StackContainer(Container container, int rowIndex, ref int? tierIndex)
        {
            // 当前函数的用途是返回tierIndex
            if (container.Size != ContainerSize || Stacks[rowIndex].Count >= Block.MaxNumTiers)
                return false;
            Stacks[rowIndex].Add(container);
            tierIndex = Stacks[rowIndex].Count;
            return true;
        }
    }
}
