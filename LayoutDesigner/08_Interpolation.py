"""
08_Interpolation.py
对位于同一水平线或垂直线上的相邻点进行等间距差值，使相邻点间距不大于30。
- 水平线 (y 相同): x 间距 > 30 时插入 ADDXI 点
- 垂直线 (x 相同): y 间距 > 30 时插入 ADDYI 点 (排除已有 ADDXI 点)
"""
import json
import os
import glob
import sys
import math
from collections import defaultdict

# Fix Windows stdout encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = "data"
INPUT_DIR = os.path.join(BASE_DIR, "routing", "merged")
OUTPUT_DIR = os.path.join(BASE_DIR, "routing", "interpolation")
THRESHOLD = 30


def traditional_round(value):
    """传统四舍五入 (不用银行家取整法)"""
    import decimal
    return int(decimal.Decimal(str(value)).quantize(
        decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP))


def format_y(y):
    """格式化 y 坐标为 3 位字符串 (R013)"""
    return f"R{traditional_round(y):03d}"


def format_x(x):
    """格式化 x 坐标为 4 位字符串 (C0004)"""
    return f"C{traditional_round(x):04d}"


def make_addxi_id(y, x):
    """生成 ADDXI 点 ID"""
    return f"ADDXI_{format_y(y)}_{format_x(x)}"


def make_addyi_id(y, x):
    """生成 ADDYI 点 ID"""
    return f"ADDYI_{format_y(y)}_{format_x(x)}"


def is_addxi_point(point):
    """检查是否为 ADDXI 点"""
    return point.get('id', '').startswith('ADDXI')


def is_grey_point(point):
    """检查是否为灰色点 (grey)"""
    return point.get('color_type', '') == 'grey' or point.get('region', '') == 'grey'


def interpolate_horizontal(points):
    """
    处理水平线差值: 同一 y 值的相邻点，按 x 排序后对间距 >30 的进行差值。
    灰色点不参与差值计算，直接保留。
    返回新的点列表 (原始点 + 插入的点)
    """
    if not points:
        return points

    # 按 y 分组
    by_y = defaultdict(list)
    for p in points:
        by_y[p['y']].append(p)

    result = []

    for y, pts in by_y.items():
        # 每组内按 x 排序
        sorted_pts = sorted(pts, key=lambda p: p['x'])

        for i in range(len(sorted_pts)):
            p = sorted_pts[i]
            result.append(p)

            # 灰色点不参与差值计算
            if is_grey_point(p):
                continue

            # 检查与下一个点的 x 间距
            if i < len(sorted_pts) - 1:
                next_p = sorted_pts[i + 1]
                distance = next_p['x'] - p['x']

                if distance > THRESHOLD:
                    # 需要插入的点数量
                    n = math.ceil(distance / THRESHOLD) - 1
                    step = distance / (n + 1)

                    for j in range(1, n + 1):
                        new_x = p['x'] + step * j
                        new_id = make_addxi_id(y, new_x)
                        new_point = {
                            'id': new_id,
                            'x': new_x,
                            'y': y,
                            'region': p.get('region', ''),
                            'kind': p.get('kind', 'h'),
                            'color_type': p.get('color_type', '')
                        }
                        result.append(new_point)

    return result


def interpolate_vertical(points):
    """
    处理垂直线差值: 同一 x 值的相邻非 ADDXI 非灰色点，按 y 排序后对间距 >30 的进行差值。
    ADDXI 点和灰色点会被保留但不参与垂直差值计算。
    返回新的点列表 (原始点 + 插入的点)
    """
    if not points:
        return points

    # 按 x 分组
    by_x = defaultdict(list)
    for p in points:
        by_x[p['x']].append(p)

    result = []

    for x, pts in by_x.items():
        # 分离 ADDXI 点、灰色点和其他点
        addxi_pts = [p for p in pts if is_addxi_point(p)]
        grey_pts = [p for p in pts if is_grey_point(p) and not is_addxi_point(p)]
        other_pts = [p for p in pts if not is_addxi_point(p) and not is_grey_point(p)]

        # 每组内按 y 排序 (只对非 ADDXI 非灰色的点)
        sorted_pts = sorted(other_pts, key=lambda p: p['y'])

        for i in range(len(sorted_pts)):
            p = sorted_pts[i]
            result.append(p)

            # 检查与下一个点的 y 间距
            if i < len(sorted_pts) - 1:
                next_p = sorted_pts[i + 1]
                distance = next_p['y'] - p['y']

                if distance > THRESHOLD:
                    # 需要插入的点数量
                    n = math.ceil(distance / THRESHOLD) - 1
                    step = distance / (n + 1)

                    for j in range(1, n + 1):
                        new_y = p['y'] + step * j
                        new_id = make_addyi_id(new_y, x)
                        new_point = {
                            'id': new_id,
                            'x': x,
                            'y': new_y,
                            'region': p.get('region', ''),
                            'kind': p.get('kind', 'v'),
                            'color_type': p.get('color_type', '')
                        }
                        result.append(new_point)

        # 将 ADDXI 点和灰色点添加到结果中
        for p in addxi_pts:
            result.append(p)
        for p in grey_pts:
            result.append(p)

    return result


def process_file(input_file):
    """处理单个 JSON 文件"""
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}

    # 处理所有 color_type 的点列表
    for color_type, points in data.items():
        if color_type == 'junction':
            # junction 列表单独处理
            continue

        # 先水平差值
        processed = interpolate_horizontal(points)
        # 再垂直差值
        processed = interpolate_vertical(processed)
        result[color_type] = processed

    # 处理 junction 列表
    if 'junction' in data:
        junction_points = data['junction']
        # 先水平差值
        processed = interpolate_horizontal(junction_points)
        # 再垂直差值
        processed = interpolate_vertical(processed)
        result['junction'] = processed

    return result


def main():
    print("=" * 60)
    print("Interpolation: Add points for gaps > 30")
    print("=" * 60)

    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 查找所有输入文件
    input_pattern = os.path.join(INPUT_DIR, "*.json")
    input_files = glob.glob(input_pattern)

    if not input_files:
        print(f"No input files found in: {INPUT_DIR}")
        return

    print(f"\nFound {len(input_files)} input file(s)\n")

    for input_file in sorted(input_files):
        filename = os.path.basename(input_file).replace("_merged.json", "_interpolated.json")
        output_file = os.path.join(OUTPUT_DIR, filename)

        print(f"Processing: {filename}")

        try:
            result = process_file(input_file)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # 统计点数
            total_points = sum(len(v) for v in result.values())
            print(f"  -> OK: {total_points} total points")

            # 统计插值点数量
            addxi_count = sum(1 for pts in result.values() for p in pts if p['id'].startswith('ADDXI'))
            addyi_count = sum(1 for pts in result.values() for p in pts if p['id'].startswith('ADDYI'))
            if addxi_count > 0 or addyi_count > 0:
                print(f"    ADDXI points: {addxi_count}, ADDYI points: {addyi_count}")

        except Exception as e:
            print(f"  -> ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"Output written to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
