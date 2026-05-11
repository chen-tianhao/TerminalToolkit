#nullable enable
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace Assets.SingaPort
{
    public class Inventory
    {
        public enum JobType
        {
            Stacking,
            Unstacking
        }

        private sealed class GroundSlot
        {
            public List<Container> gsStack { get; } = new();   // 自底向上存储
            public int FlippedLayers { get; set; }     // 已翻动层数累计
        }

        private readonly Dictionary<(int blockId, int dim1, int dim2), GroundSlot> _map = new();

        // 将奇偶 bay 编码映射到连续的 dim1（1..NumBays）
        private static int ToDim1(int bay) => bay % 2 == 0 ? bay / 2 : (bay + 1) / 2;


        public Slot? Allocate(Container container, Random rs, bool applyRowStackingLimit = false)
        {
            // if (Config.traceAllocate) Debug.Log($"[{container.ToString()}] [Allocate] Finding slot...");
            Block block = container.Block;
            int maxBayIndex = block.NumBays * 2 - 1;
            bool IsForty(Container? j) => j != null && j.Size == ContainerSize.FortyFeet;
            bool IsTwenty(Container? j) => j != null && j.Size == ContainerSize.TwentyFeet;

            // 20 尺可继续在已放 20 的 bay 堆放；仅当该 bay 参与了一只 40 尺（跨 bay）时阻塞 20 尺
            bool IsBayBlockedFor20(int bay)
            {
                for (int row = 1; row <= block.NumRows; row++)
                {
                    var self = Peek(block, new Slot(bay, row, 1));
                    if (IsForty(self)) return true;
                }
                return false;
            }

            // bay 及 bay+1 不得存在 20 尺箱，且两侧高度对齐（若顶层为 40，要求跨到同一只箱）
            bool CanPlaceForty(int bay, int row, out int tier)
            {
                tier = -1;
                if (bay % 2 != 0) return false; // 40ft 以偶数为中心
                if (bay <= 1 || bay >= maxBayIndex) return false;
                int leftBay = bay - 1;
                int rightBay = bay + 1;
                int h1 = GetHeight(block, new Slot(leftBay, row, 1));
                int h2 = GetHeight(block, new Slot(rightBay, row, 1));
                var top1 = Peek(block, new Slot(leftBay, row, 1));
                var top2 = Peek(block, new Slot(rightBay, row, 1));
                // 不允许任一侧已有 20 尺
                if (IsTwenty(top1) || IsTwenty(top2)) return false;
                // 若任一侧存在 20 尺于其他行，需要整体阻塞
                for (int r = 1; r <= block.NumRows; r++)
                {
                    if (IsTwenty(Peek(block, new Slot(leftBay, r, 1)))) return false;
                    if (IsTwenty(Peek(block, new Slot(rightBay, r, 1)))) return false;
                }
                bool topsCrossSameForty = IsForty(top1) && ReferenceEquals(top1, top2);
                bool topsWithoutForty = !IsForty(top1) && !IsForty(top2);
                if (!(h1 == h2 && (topsCrossSameForty || topsWithoutForty))) return false;
                if (h1 >= block.MaxNumTiers) return false;
                tier = h1 + 1;
                return true;
            }

            
            // 生成随机顺序的 row 列表
            var rows = Enumerable.Range(1, block.NumRows).OrderBy(_ => rs.Next()).ToList();
            // 1) Look for a GS with the same PSWC that is not full
            if (container.Size == ContainerSize.FortyFeet)
            {
                for (int bay = 2; bay < maxBayIndex; bay += 2)
                {
                    foreach (int row in rows)
                    {
                        if (!CanPlaceForty(bay, row, out var tier)) continue;
                        if (applyRowStackingLimit && !IsRowValidByBayRules(block, bay, row, ContainerSize.FortyFeet)) continue;
                        var topJob = Peek(block, new Slot(bay - 1, row, 1));
                        if (topJob != null && topJob.Group.Index == container.Group.Index)
                        {
                            // if (Config.traceAllocate) Debug.Log($"[{container.ToString()}] [Allocate-1] 40ft same PSWC at Yc {yc.id}, Bay {bay}-{bay + 1}, Row {row}, Tier {tier}");
                            return new Slot(bay, row, tier);
                        }
                    }
                }
            }
            else
            {
                for (int bay = 1; bay <= maxBayIndex; bay += 2)
                {
                    foreach (int row in rows)
                    {
                        var baseSlot = new Slot(bay, row, 1);
                        int tier = GetHeight(block, baseSlot);
                        if (tier <= 0) continue;
                        if (applyRowStackingLimit && !IsRowValidByBayRules(block, bay, row, ContainerSize.TwentyFeet)) continue;
                        var topJob = Peek(block, baseSlot);
                        if (topJob != null && topJob.Group.Index == container.Group.Index && !IsBayBlockedFor20(bay))
                        {
                            if (tier < block.MaxNumTiers)
                            {
                                // if (Config.traceAllocate) Debug.Log($"[{container.ToString()}] [Allocate-1] 20ft same PSWC at Yc {yc.id}, Bay {bay}, Row {row}, Tier {tier + 1}");
                                return new Slot(bay, row, tier + 1);
                            }
                        }
                    }
                }
            }

            // 2) search empties - random selection
            if (container.Size == ContainerSize.FortyFeet)
            {
                // 收集所有符合条件的候选 (bay, row)
                var candidates = new List<(int bay, int row, int tier)>();
                for (int bay = 2; bay < maxBayIndex; bay += 2)
                {
                    int leftBay = bay - 1;
                    int rightBay = bay + 1;

                    // 检查 bay 级别的一致性：leftBay 和 rightBay 在所有 row 上高度必须一致
                    bool heightsConsistent = true;
                    bool containersConsistent = true;
                    for (int r = 1; r <= block.NumRows; r++)
                    {
                        int hLeft = GetHeight(block, new Slot(leftBay, r, 1));
                        int hRight = GetHeight(block, new Slot(rightBay, r, 1));
                        if (hLeft != hRight)
                        {
                            heightsConsistent = false;
                            break;
                        }

                        var topLeft = Peek(block, new Slot(leftBay, r, 1));
                        var topRight = Peek(block, new Slot(rightBay, r, 1));
                        // 如果两边都有容器但不是同一个实例，则不一致
                        if (topLeft != null && topRight != null && !ReferenceEquals(topLeft, topRight))
                        {
                            containersConsistent = false;
                            break;
                        }
                    }
                    if (!heightsConsistent || !containersConsistent) continue;

                    foreach (int row in rows)
                    {
                        // 检查当前 row 的 leftBay 和 rightBay 是否为空
                        if (GetHeight(block, new Slot(leftBay, row, 1)) != 0) continue;
                        if (GetHeight(block, new Slot(rightBay, row, 1)) != 0) continue;
                        if (CanPlaceForty(bay, row, out var tier))
                        {
                            if (applyRowStackingLimit && !IsRowValidByBayRules(block, bay, row, ContainerSize.FortyFeet)) continue;
                            candidates.Add((bay, row, tier));
                        }
                    }
                }
                if (candidates.Count > 0)
                {
                    var selected = candidates[rs.Next(candidates.Count)];
                    // var selected = candidates[0];
                    return new Slot(selected.bay, selected.row, selected.tier);
                }
            }
            else
            {
                // 收集所有符合条件的候选 (bay, row)
                var candidates = new List<(int bay, int row)>();
                for (int bay = 1; bay <= maxBayIndex; bay += 2)
                {
                    foreach (int row in rows)
                    {
                        if (IsBayBlockedFor20(bay)) continue;
                        if (GetHeight(block, new Slot(bay, row, 1)) == 0)
                        {
                            if (applyRowStackingLimit && !IsRowValidByBayRules(block, bay, row, ContainerSize.TwentyFeet)) continue;
                            candidates.Add((bay, row));
                        }
                    }
                }
                if (candidates.Count > 0)
                {
                    var selected = candidates[rs.Next(candidates.Count)];
                    // var selected = candidates[0];
                    return new Slot(selected.bay, selected.row, 1);
                }
            }

            // 3) pick highest non-full respecting size rules
            int bestBay = -1;
            int bestRow = -1;
            int bestHeight = -1;
            if (container.Size == ContainerSize.FortyFeet)
            {
                for (int bay = 2; bay < maxBayIndex; bay += 2)
                {
                    foreach (int row in rows)
                    {
                        if (!CanPlaceForty(bay, row, out var tier)) continue;
                        if (applyRowStackingLimit && !IsRowValidByBayRules(block, bay, row, ContainerSize.FortyFeet)) continue;
                        int h = tier - 1;
                        if (h > bestHeight)
                        {
                            bestHeight = h;
                            bestBay = bay;
                            bestRow = row;
                        }
                    }
                }
            }
            else
            {
                for (int bay = 1; bay <= maxBayIndex; bay += 2)
                {
                    foreach (int row in rows)
                    {
                        if (IsBayBlockedFor20(bay)) continue;
                        if (applyRowStackingLimit && !IsRowValidByBayRules(block, bay, row, ContainerSize.TwentyFeet)) continue;
                        int tier = GetHeight(block, new Slot(bay, row, 1));
                        if (tier < block.MaxNumTiers && tier > bestHeight)
                        {
                            bestHeight = tier;
                            bestBay = bay;
                            bestRow = row;
                        }
                    }
                }
            }
            if (bestBay > 0)
            {
                int tier = bestHeight + 1;
                // if (Config.traceAllocate) Debug.Log($"[{container.ToString()}] [Allocate-3] Selected at Yc {yc.id}, Bay {bestBay}{(container.Size==ContainerSize.FortyFeet?$"-{bestBay+1}":string.Empty)}, Row {bestRow}, Tier {tier}");
                return new Slot(bestBay, bestRow, tier);
            }

            // 4) If no GS is found that is not full, return null
            // if (Config.traceAllocate) Debug.Log($"[{container.ToString()}] [Allocate-4] No empty slot found");
            return null;
        }

        public bool UnstackWithoutReshuffle(Container container)
        {
            Container? containerOnTop = Peek(container.Block, container.Slot);
            if (containerOnTop == null) return true;
            bool ret = container.Group == containerOnTop.Group;
            return ret;
        }

        public void Update(Container container, JobType opType)
        {
            if (container.Slot == null || container.Slot.Bay == 0 || container.Slot.Row == 0 || container.Slot.Tier == 0) 
            {
                // Debug.Log($"[{job.ToString()}] [ERROR] Invalid slot: {job.slot.ToString()}");
                return;
            }
            if (opType == JobType.Stacking)
            {
                // Make sure job.slot is set already
                Stack(container.Block, container.Slot, container);
            }
            else
            {
                Unstack(container.Block, container.Slot);
            }
        }

        public int GetHeight(Block block, Slot slot)  // Height of stack
        {
            return GetGroundSlot(block, slot).gsStack.Count;
        }

        public Container? GetBestJobByPswc(Block bu, Group group)
        {
            Container? best = null;
            int bestDepth = int.MaxValue; // 0 means top of stack
            int bestHeight = int.MinValue;
            int bestBay = int.MinValue;
            int bestRow = int.MinValue;

            foreach (var kv in _map)
            {
                int blockId = kv.Key.blockId;
                int bay = kv.Key.dim1;
                int row = kv.Key.dim2;
                if (blockId != bu.Index) continue;
                var stack = kv.Value.gsStack;
                if (stack.Count == 0) continue;

                // 从顶向下找第一个匹配的 job
                for (int idx = stack.Count - 1; idx >= 0; idx--)
                {
                    var container = stack[idx];
                    if (container.Size != (group.TEUs == 2 ? ContainerSize.FortyFeet : ContainerSize.TwentyFeet) 
                    || container.Group.Index != group.Index)
                    {
                        continue;
                    }

                    int depthFromTop = (stack.Count - 1) - idx; // 0 = 顶
                    int height = stack.Count; // ground slot height
                    bool better = false;
                    if (depthFromTop < bestDepth) better = true;
                    else if (depthFromTop == bestDepth)
                    {
                        if (height > bestHeight) better = true;
                        else if (height == bestHeight)
                        {
                            if (bay > bestBay) better = true;
                            else if (bay == bestBay && row > bestRow) better = true;
                        }
                    }
                    if (better)
                    {
                        best = container;
                        bestDepth = depthFromTop;
                        bestHeight = height;
                        bestBay = bay;
                        bestRow = row;
                    }
                    // 找到匹配后即可跳出当前 stack 的搜索（更深层不会更优）
                    break;
                }
            }
            return best;
        }

        public Slot? DecideReshuffleTarget(Container rContainer, Container refContainer)
        {
            var block = rContainer.Block;
            int bay = rContainer.Slot.Bay;
            bool IsForty(Container? ctn) => ctn != null && ctn.Size == ContainerSize.FortyFeet;
            bool IsTwenty(Container? ctn) => ctn != null && ctn.Size == ContainerSize.TwentyFeet;
            bool IsCurrentGS(Slot s) => s.Bay == rContainer.Slot.Bay && s.Row == rContainer.Slot.Row;
            bool HasSamePswcTop(Slot s)
            {
                var top = Peek(block, new Slot(s.Bay, s.Row, 1));
                return top != null && top.Group == refContainer.Group;
            }

            // 与 Allocate 保持一致：20 尺仅在 bay 或 bay-1 有 40 尺时阻塞
            bool IsBayBlockedFor20(int b)
            {
                if (block == null) return false;
                for (int row = 1; row <= block.NumRows; row++)
                {
                    var self = Peek(block, new Slot(b, row, 1));
                    var left = b > 1 ? Peek(block, new Slot(b - 1, row, 1)) : null;
                    var right = b < block.NumBays ? Peek(block, new Slot(b + 1, row, 1)) : null;

                    if (IsForty(self)) return true;
                    if (IsForty(left) && self != null && ReferenceEquals(left, self)) return true;
                    if (IsForty(right) && self != null && ReferenceEquals(right, self)) return true;
                }
                return false;
            }

            // 40 尺需两侧无 20 且高度对齐（若顶层为 40，要求跨到同一只箱）
            bool CanPlaceForty(int b, int row, out int tier)
            {
                tier = -1;
                if (b >= block.NumBays) return false;
                int h1 = GetHeight(block, new Slot(b, row, 1));
                int h2 = GetHeight(block, new Slot(b + 1, row, 1));
                var top1 = Peek(block, new Slot(b, row, 1));
                var top2 = Peek(block, new Slot(b + 1, row, 1));
                if (IsTwenty(top1) || IsTwenty(top2)) return false;
                for (int r = 1; r <= block.NumRows; r++)
                {
                    if (IsTwenty(Peek(block, new Slot(b, r, 1)))) return false;
                    if (IsTwenty(Peek(block, new Slot(b + 1, r, 1)))) return false;
                }
                bool topsCrossSameForty = IsForty(top1) && ReferenceEquals(top1, top2);
                bool topsWithoutForty = !IsForty(top1) && !IsForty(top2);
                if (!(h1 == h2 && (topsCrossSameForty || topsWithoutForty))) return false;
                if (h1 >= block.MaxNumTiers) return false;
                tier = h1 + 1;
                return true;
            }

            // 当前 bay 是否所有行都已堆满（高度达上限）
            bool BayFullyStacked(int b)
            {
                for (int row = 1; row <= block.NumRows; row++)
                {
                    if (GetHeight(block, new Slot(b, row, 1)) < block.MaxNumTiers) return false;
                }
                return true;
            }

            // 找到指定 bay 中同 PSWC 且未满的最高堆顶（返回下一可放置层），带尺寸约束
            Slot? SamePswcTop(int b)
            {
                Slot? best = null;
                int bestHeight = -1;
                for (int row = 1; row <= block.NumRows; row++)
                {
                    var baseSlot = new Slot(b, row, 1);
                    int tier = GetHeight(block, baseSlot);
                    if (tier == 0 || tier >= block.MaxNumTiers) continue;
                    var top = Peek(block, baseSlot);
                    if (top == null || top.Group != refContainer.Group) continue;
                    if (rContainer.Size == ContainerSize.TwentyFeet && IsBayBlockedFor20(b)) continue;
                    int fortyTier = -1;
                    if (rContainer.Size == ContainerSize.FortyFeet && !CanPlaceForty(b, row, out fortyTier)) continue;

                    int curHeight = rContainer.Size == ContainerSize.FortyFeet ? fortyTier - 1 : tier;
                    int nextTier = rContainer.Size == ContainerSize.FortyFeet ? fortyTier : tier + 1;
                    var candidate = new Slot(b, row, nextTier);
                    if (IsCurrentGS(candidate)) continue;
                    if (curHeight > bestHeight)
                    {
                        bestHeight = curHeight;
                        best = candidate;
                    }
                }
                return best;
            }

            // 在指定 bay 中寻找离当前行最近的空槽（高度为 0），带尺寸约束
            Slot? ClosestEmpty(int b)
            {
                Slot? best = null;
                int bestDist = int.MaxValue;
                for (int row = 1; row <= block.NumRows; row++)
                {
                    if (GetHeight(block, new Slot(b, row, 1)) != 0) continue;
                    if (rContainer.Size == ContainerSize.TwentyFeet && IsBayBlockedFor20(b)) continue;
                    int fortyTier = -1;
                    if (rContainer.Size == ContainerSize.FortyFeet && !CanPlaceForty(b, row, out fortyTier)) continue;

                    int dist = Math.Abs(row - rContainer.Slot.Row);
                    if (dist < bestDist)
                    {
                        var candidate = new Slot(b, row, rContainer.Size == ContainerSize.FortyFeet ? fortyTier : 1);
                        if (IsCurrentGS(candidate)) continue;
                        bestDist = dist;
                        best = candidate;
                    }
                }
                return best;
            }

            // 在指定 bay 中选择未满且最高的槽位，若并列取行距离最近，带尺寸约束
            Slot? TallestNonFull(int b)
            {
                Slot? best = null;
                int bestHeight = -1;
                int bestDist = int.MaxValue;
                for (int row = 1; row <= block.NumRows; row++)
                {
                    int tier = GetHeight(block, new Slot(b, row, 1));
                    if (tier >= block.MaxNumTiers) continue;
                    if (rContainer.Size == ContainerSize.TwentyFeet && IsBayBlockedFor20(b)) continue;
                    int fortyTier = -1;
                    if (rContainer.Size == ContainerSize.FortyFeet && !CanPlaceForty(b, row, out fortyTier)) continue;

                    int dist = Math.Abs(row - rContainer.Slot.Row);
                    int curHeight = rContainer.Size == ContainerSize.FortyFeet ? fortyTier - 1 : tier;
                    int nextTier = rContainer.Size == ContainerSize.FortyFeet ? fortyTier : tier + 1;
                    var candidate = new Slot(b, row, nextTier);
                    if (IsCurrentGS(candidate)) continue;
                    if (curHeight > bestHeight || (curHeight == bestHeight && dist < bestDist))
                    {
                        bestHeight = curHeight;
                        bestDist = dist;
                        best = candidate;
                    }
                }
                return best;
            }

            // Case A: current bay not fully stacked -> avoid gantry
            if (!BayFullyStacked(bay))
            {
                var target = SamePswcTop(bay) ?? ClosestEmpty(bay) ?? TallestNonFull(bay);
                if (target != null && !IsCurrentGS(target)) 
                {
                    // if (Config.traceReshuffleTarget) Info($"[{rContainer.ToString()}] [TargetSlot-CaseA] Target Slot: {target}");
                    return target;
                }
            }

            // Case B: bay is full -> gantry allowed, search across bays (closest by bay distance then row distance)
            Slot? bestSlot = null;

            // 跨 bay 选择候选槽：先比 bay 距离，再比行距离
            Slot? PickAcross(Func<int, Slot?> picker, bool preferDifferentPswc)
            {
                Slot? chosen = null;
                int chosenBayDist = int.MaxValue;
                int chosenRowDist = int.MaxValue;
                for (int b = 1; b <= block.NumBays; b++)
                {
                    var cand = picker(b);
                    if (cand == null) continue;
                    if (IsCurrentGS(cand)) continue;
                    if (preferDifferentPswc && HasSamePswcTop(cand)) continue;
                    int bayDist = Math.Abs(b - bay);
                    int rowDist = Math.Abs(cand.Row - rContainer.Slot.Row);
                    if (bayDist < chosenBayDist || (bayDist == chosenBayDist && rowDist < chosenRowDist))
                    {
                        chosen = cand;
                        chosenBayDist = bayDist;
                        chosenRowDist = rowDist;
                    }
                }
                return chosen;
            }

            // 首先尝试避开与 refJob 同 PSWC 的顶箱；若不可行，再放宽约束
            bestSlot = PickAcross(SamePswcTop, true)
                        ?? PickAcross(ClosestEmpty, true)
                        ?? PickAcross(TallestNonFull, true)
                        ?? PickAcross(SamePswcTop, false)
                        ?? PickAcross(ClosestEmpty, false)
                        ?? PickAcross(TallestNonFull, false);
            
            // if (Config.traceReshuffleTarget) Info($"[{rContainer.ToString()}] [TargetSlot-CaseB] Target Slot: {bestSlot}");
            return bestSlot;
        }

        private GroundSlot GetGroundSlot(Block block, Slot slot)
        {
            var gsIdx = (block.Index, ToDim1(slot.Bay), slot.Row);
            if (!_map.TryGetValue(gsIdx, out var gs))
            {
                gs = new GroundSlot();
                _map[gsIdx] = gs;
            }
            return gs;
        }

        private void Stack(Block block, Slot slot, Container container)  // Stacking
        {
            // 40尺箱占用两个相邻 bay、同 row、同 tier
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

        private Container? Unstack(Block block, Slot slot)  // Unstacking
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

        public Container? Peek(Block block, Slot slot)
        {
            var gs = GetGroundSlot(block, slot);
            return gs.gsStack.Count == 0 ? null : gs.gsStack[^1];
        }

        // 检查指定 bay/row 是否满足 Bay 风格的堆叠限制（6项限制）
        // 对40尺柜，同时检查 bay-1 和 bay+1 两侧
        private bool IsRowValidByBayRules(Block block, int bay, int row, ContainerSize size)
        {
            int maxTier = block.MaxNumTiers;

            // 获取需要检查的所有 bay 和 row 的高度
            int[] GetHeights(int b)
            {
                var heights = new int[block.NumRows + 1]; // 1-indexed
                for (int r = 1; r <= block.NumRows; r++)
                {
                    heights[r] = GetHeight(block, new Slot(b, r, 1));
                }
                return heights;
            }

            int[] heights;
            if (size == ContainerSize.FortyFeet)
            {
                // 40尺需要两侧高度一致，取两侧的最大值
                int[] h1 = GetHeights(bay - 1);
                int[] h2 = GetHeights(bay + 1);
                heights = new int[block.NumRows + 1];
                for (int r = 1; r <= block.NumRows; r++)
                {
                    heights[r] = Math.Max(h1[r], h2[r]);
                }
            }
            else
            {
                heights = GetHeights(bay);
            }

            int currentHeight = heights[row];
            if (currentHeight >= maxTier) return false; // 限制1: 避免超最大层数

            // 获取最小高度
            int minHeight = heights[1];
            for (int r = 2; r <= block.NumRows; r++)
            {
                if (heights[r] < minHeight) minHeight = heights[r];
            }
            if (currentHeight >= minHeight + 4) return false; // 限制2: 避免高度差>4

            // 限制3: 上侧无陡坡
            if (row < block.NumRows && currentHeight > heights[row + 1]) return false;

            // 限制4: 下侧无陡坡
            if (row > 1 && currentHeight > heights[row - 1]) return false;

            // 限制5: 上侧无洞
            if (row < block.NumRows - 1 && currentHeight == heights[row + 1])
            {
                bool hasHigherAbove = false;
                for (int r = row + 2; r <= block.NumRows; r++)
                {
                    if (heights[r] > currentHeight)
                    {
                        hasHigherAbove = true;
                        break;
                    }
                }
                if (hasHigherAbove) return false;
            }

            // 限制6: 下侧无洞
            if (row > 2 && currentHeight == heights[row - 1])
            {
                bool hasHigherBelow = false;
                for (int r = 1; r <= row - 2; r++)
                {
                    if (heights[r] > currentHeight)
                    {
                        hasHigherBelow = true;
                        break;
                    }
                }
                if (hasHigherBelow) return false;
            }

            return true;
        }

        // Not use in Unity demo project
        private string Insight(string tag)
        {
            // return "";
            StringBuilder sbInsight = new StringBuilder();
            var entries = _map.Where(kv => kv.Value.gsStack.Count > 0)
                               .OrderBy(kv => kv.Key.blockId)
                               .ThenBy(kv => kv.Key.dim1)
                               .ThenBy(kv => kv.Key.dim2)
                               .ToList();

            sbInsight.AppendLine($"Inventory snapshot: {tag}");
            if (entries.Count == 0)
            {
                sbInsight.AppendLine("  (empty)");
                return sbInsight.ToString();
            }

            foreach (var kv in entries)
            {
                int blockId = kv.Key.blockId;
                int bay = kv.Key.dim1;
                int row = kv.Key.dim2;
                var stack = kv.Value.gsStack;
                var items = string.Join(" | ", stack.Select(container => $"{container.Index:D6}({(container.Size == ContainerSize.FortyFeet ? "40" : "20")}/{container.Group.Index})"));
                sbInsight.AppendLine($"  YC {blockId:D2} GS({bay},{row}) h={stack.Count}: {items}");
            }
            return sbInsight.ToString();
        }
    }
}
