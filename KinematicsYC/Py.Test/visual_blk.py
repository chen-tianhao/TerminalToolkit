"""
visual_blk.py - Block 2D top-down view visualization

Usage:
    python visual_blk.py                              # default params
    python visual_blk.py --num-bays 10 --num-rows 6 --max-tiers 5
    python visual_blk.py --save output.png
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Py'))

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from block import Block

# 颜色配置
COLOR_20FT = "#AED6F1"   # 浅蓝 - 20尺集装箱
COLOR_40FT = "#F9E79F"   # 浅橙 - 40尺集装箱（跨bay）
COLOR_GRID = "gray"
COLOR_TEXT = "black"
COLOR_BAY_LABEL = "#2C3E50"  # 深色用于bay编号

# Bay 物理尺寸（米），用于计算格子比例
SLOT_ROW_SPACING = 0.25  # row方向（Y）- 集装箱之间的间隔
SLOT_BAY_SPACING = 0.25  # bay方向（X）- 集装箱之间的间隔
SLOT_WIDTH = Block.slot_width + SLOT_ROW_SPACING  # bay方向（X）- 集装箱宽度
SLOT_LENGTH = Block.slot_length + SLOT_BAY_SPACING  # row方向（Y）- 集装箱长度
CELL_ASPECT = SLOT_LENGTH / SLOT_WIDTH


def draw_block_top_view(block: Block, save_path: str = None):
    """
    绘制 Block 的 2D 俯视图（top-down view）

    参数:
        block: Block 实例
        save_path: 可选，保存图片路径
    """
    num_bays = block.num_bays
    num_rows = block.num_rows

    # 计算物理 bay 索引范围: 1 ~ num_bays*2-1
    max_bay_index = num_bays * 2 - 1

    # 创建 figure（保持长宽比）
    cell_lenth = 0.8  # 每个 bay slot 的宽度（英寸）
    cell_height = cell_lenth * CELL_ASPECT
    fig_width = max(10, num_bays * cell_lenth + 1.5)
    fig_height = max(6, num_rows * cell_height + 1.5)
    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))

    # 设置背景色
    ax.set_facecolor('white')

    # ---- 绘制格子 ----
    # 物理 bay 布局:
    # - 奇数 bay (1,3,5...): 20' 箱的独立槽位
    # - 偶数 bay (2,4,6...): 40' 箱跨 bay-1 和 bay+1 两个奇数位
    #
    # bay索引与x坐标对应关系:
    # bay:  01  02  03  04  05  06  07  08  09 ...
    # x:     0   1   2   3   4   5   6   7   8 ...
    #
    # 40' 箱 bay 02 占用 bay 01(x=0~1) 和 bay 03(x=2~3)，跨度=3

    # 只绘制奇数 bay 的槽位（20ft 独立槽位）
    for bay in range(1, num_bays + 1, 1):  # 1, 3, 5, 7, ...
        for row in range(1, num_rows + 1):
            x = bay - 1
            rect = patches.Rectangle(
                (x, row - 1), 1, 1,
                linewidth=0.5,
                edgecolor=COLOR_GRID,
                facecolor=COLOR_20FT,
                alpha=0.6
            )
            ax.add_patch(rect)
            # 标注"20'"表示20ft
            ax.text(x + 0.5, row - 0.5, "20'",
                   ha='center', va='center',
                   fontsize=6, color="#1A5276", alpha=0.7)

    # # 绘制 40ft bay（偶数bay）的覆盖矩形
    # # 偶数 bay i 跨越 bay-1 和 bay+1 两个奇数位
    # # 例如 bay 02 -> 占用 bay 01 和 bay 03，跨度从 x=0 到 x=3
    # for bay in range(2, max_bay_index, 2):  # 偶数 bay: 2, 4, 6, ...
    #     left_odd = bay - 1   # 左侧被占用的奇数bay (e.g., bay 02 -> left_odd=1)
    #     right_odd = bay + 1  # 右侧被占用的奇数bay (e.g., bay 02 -> right_odd=3)
    #     left_x = left_odd - 1  # x坐标起点 (bay 01 -> x=0)
    #     right_x = right_odd     # x坐标终点 (bay 03 -> x=3)
    #     span = right_x - left_x  # 跨度=3 (bay 01~03)

    #     for row in range(1, num_rows + 1):
    #         rect = patches.Rectangle(
    #             (left_x, row - 1), span, 1,
    #             linewidth=1.5,
    #             edgecolor="#D68910",
    #             facecolor=COLOR_40FT,
    #             alpha=0.5
    #         )
    #         ax.add_patch(rect)
    #         # 标注"40'"表示40ft
    #         ax.text((left_x + right_x) / 2, row - 0.5, "40'",
    #                ha='center', va='center',
    #                fontsize=6, color="#9C640C", alpha=0.8)

    # ---- 标注 Bay 编号 ----
    # 奇数 bay: 标注在格子中心
    for bay in range(1, max_bay_index + 1, 2):
        ax.text(bay / 2, num_rows + 0.3, f"{bay}",
               ha='center', va='center',
               fontsize=9, color=COLOR_BAY_LABEL, fontweight='bold')

    # 偶数 bay: 标注在跨 bay 矩形的中心（40' 箱占据的位置）
    for bay in range(2, max_bay_index, 2):
        # left_odd = bay - 1
        # right_odd = bay + 1
        # left_x = left_odd - 1
        # right_x = right_odd
        # center_x = (left_x + right_x) / 2
        ax.text(bay / 2, num_rows + 0.3, f"{bay}",
               ha='center', va='center',
               fontsize=9, color="#9C640C", fontweight='bold')

    # ---- 标注 Row 编号 ----
    for row in range(1, num_rows + 1):
        ax.text(-0.1, row - 0.5, f"{row}",
               ha='right', va='center',
               fontsize=9, color=COLOR_TEXT, fontweight='bold')

    # ---- 设置坐标轴 ----
    ax.set_xlim(-0.5, num_bays + 0.5)
    ax.set_ylim(-0.5, num_rows + 0.8)
    ax.set_xticks(range(1, num_bays + 1))
    ax.set_yticks(range(1, num_rows + 1))
    ax.set_xlabel("Bay Index (Odd=20' Bay, Even=40' Bay occupying Odd-1 & Odd+1)", fontsize=10)
    ax.set_ylabel("Row Index", fontsize=10)
    ax.set_title(f"Block Top-Down View (Bays={num_bays}, Rows={num_rows}, MaxTiers={block.max_num_tiers})\n"
                 f"Physical: {SLOT_WIDTH}m (bay) x {SLOT_LENGTH}m (row), Aspect={CELL_ASPECT}:1",
                 fontsize=11, fontweight='bold')

    # 保持长宽比（用 data 坐标单位，这样 1 unit in Y = 1 unit in X）
    ax.set_aspect(1.0 / CELL_ASPECT)  # 使 1 unit X = CELL_ASPECT unit Y

    # 反转 Y 轴，使 Row 1 在底部
    ax.invert_yaxis()

    # 添加网格
    ax.grid(True, which='major', linestyle='--', alpha=0.3)

    # ---- 添加图例 ----
    legend_elements = [
        patches.Patch(facecolor=COLOR_20FT, edgecolor=COLOR_GRID,
                      alpha=0.6, label='20ft Bay (Odd)'),
        patches.Patch(facecolor=COLOR_40FT, edgecolor="#D68910",
                      alpha=0.5, label='40ft Bay (Even, Cross-Bay)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

    plt.tight_layout()

    # 保存或显示
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Image saved to: {save_path}")
    else:
        plt.show()

    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Block 2D 俯视图可视化")
    parser.add_argument("--num-bays", type=int, default=20,
                        help="Bay 数量 (默认: 20)")
    parser.add_argument("--num-rows", type=int, default=6,
                        help="Row 数量 (默认: 6)")
    parser.add_argument("--max-tiers", type=int, default=5,
                        help="最大堆叠层数 (默认: 5)")
    parser.add_argument("--save", type=str, default=None,
                        help="保存图片路径 (可选)")
    args = parser.parse_args()

    # 创建 Block 实例
    block = Block(
        num_bays=args.num_bays,
        num_rows=args.num_rows,
        max_num_tiers=args.max_tiers
    )

    print(f"Block params: bays={block.num_bays}, rows={block.num_rows}, max_tiers={block.max_num_tiers}")
    print(f"Bay index range: 1 ~ {args.num_bays * 2 - 1}")
    print(f"Row index range: 1 ~ {args.num_rows}")

    # 绘制俯视图
    draw_block_top_view(block, save_path=args.save)


if __name__ == "__main__":
    main()