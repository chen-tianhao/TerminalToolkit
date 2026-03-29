"""
10_CreateRoutingTable.py
根据 data/routing/interpolation 下的文件创建路由表，输出到 data/routing_table
"""
import json
import os
from pathlib import Path
from collections import defaultdict

INTERPOLATION_DIR = Path(__file__).parent / "data" / "routing" / "interpolation"
OUTPUT_DIR = Path(__file__).parent / "data" / "routing_table"

# 创建输出目录
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 例外的 Y 值对 (不相连)
EXCLUDE_Y_PAIRS = [(16, 22), (22, 16)]
# 例外的 X 值对 (不相连)
EXCLUDE_X_PAIRS = [(931, 937), (937, 931)]
# 例外的 Y 值对 (不相连)
EXCLUDE_Y_PAIRS_EXTRA = [(229, 235), (235, 229)]

# 特殊 Y 值
SPECIAL_Y_19 = 19
SPECIAL_Y_232 = 232
SPECIAL_Y_16 = 16
SPECIAL_Y_22 = 22
SPECIAL_Y_229 = 229
SPECIAL_Y_235 = 235

# 特殊 X 值
SPECIAL_X_934 = 934
SPECIAL_X_931 = 931
SPECIAL_X_937 = 937

# 误差容限
EPSILON = 0.1


def is_same_row(y1: float, y2: float) -> bool:
    """判断两个点是否在同一行 (y 相同)"""
    return abs(y1 - y2) <= EPSILON


def is_same_col(x1: float, x2: float) -> bool:
    """判断两个点是否在同一列 (x 相同)"""
    return abs(x1 - x2) <= EPSILON


def is_excluded_pair(y1: float, y2: float) -> bool:
    """检查 Y 值对是否在排除列表中"""
    return (y1, y2) in EXCLUDE_Y_PAIRS or (y1, y2) in EXCLUDE_Y_PAIRS_EXTRA


def is_x_excluded(x1: float, x2: float) -> bool:
    """检查 X 值对是否在排除列表中"""
    return (x1, x2) in EXCLUDE_X_PAIRS


def build_spatial_index(points: list) -> tuple:
    """构建空间索引，按 x 分组和按 y 分组"""
    by_x = defaultdict(list)
    by_y = defaultdict(list)

    for pt in points:
        x_key = round(pt['x'], 6)
        y_key = round(pt['y'], 6)
        by_x[x_key].append(pt)
        by_y[y_key].append(pt)

    return by_x, by_y


def find_nearest_in_direction(pt: dict, candidates: list, direction: str, exclude_pair_fn=None) -> str:
    """
    在给定方向上找最近的可连接点
    direction: 'up', 'down', 'left', 'right'
    exclude_pair_fn: 排除特定点对的函数
    """
    if not candidates:
        return None

    best = None
    best_dist = float('inf')

    for cand in candidates:
        if cand['id'] == pt['id']:
            continue

        if direction in ('up', 'down'):
            # 垂直方向，检查 x 是否相同
            if not is_same_col(pt['x'], cand['x']):
                continue
            # 检查是否在正确方向
            if direction == 'up' and cand['y'] <= pt['y']:
                continue
            if direction == 'down' and cand['y'] >= pt['y']:
                continue
            # 检查排除对
            if exclude_pair_fn and exclude_pair_fn(pt['y'], cand['y']):
                continue
            dist = abs(cand['y'] - pt['y'])
        else:
            # 水平方向，检查 y 是否相同
            if not is_same_row(pt['y'], cand['y']):
                continue
            # 检查是否在正确方向
            if direction == 'left' and cand['x'] >= pt['x']:
                continue
            if direction == 'right' and cand['x'] <= pt['x']:
                continue
            # 检查排除对
            if exclude_pair_fn and exclude_pair_fn(pt['x'], cand['x']):
                continue
            dist = abs(cand['x'] - pt['x'])

        if 0 < dist < best_dist:
            best_dist = dist
            best = cand['id']

    return best


def find_nearest_y_points(pt: dict, by_y: dict, target_y_values: list) -> list:
    """找到指定 Y 值列表中最近的点"""
    results = []
    for y_key, group in by_y.items():
        if any(abs(y_key - ty) <= EPSILON for ty in target_y_values):
            # 在这个 y 值上找最近的点
            for cand in group:
                if cand['id'] != pt['id'] and is_same_col(pt['x'], cand['x']):
                    results.append((abs(cand['y'] - pt['y']), cand['id']))
    return results


def find_nearest_x_points(pt: dict, by_x: dict, target_x_values: list) -> list:
    """找到指定 X 值列表中最近的点"""
    results = []
    for x_key, group in by_x.items():
        if any(abs(x_key - tx) <= EPSILON for tx in target_x_values):
            # 在这个 x 值上找最近的点
            for cand in group:
                if cand['id'] != pt['id'] and is_same_row(pt['y'], cand['y']):
                    results.append((abs(cand['x'] - pt['x']), cand['id']))
    return results


def process_file(input_path: Path) -> None:
    """处理单个文件"""
    print(f"Processing: {input_path.name}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 收集所有点
    all_points = []
    for section, items in data.items():
        if isinstance(items, list):
            for pt in items:
                point = {
                    'id': pt['id'],
                    'x': pt['x'],
                    'y': pt['y'],
                    'region': pt.get('region', section),
                    'inout': pt.get('inout', False),
                    'next': []
                }
                all_points.append(point)

    print(f"  Total points: {len(all_points)}")

    # 构建空间索引
    by_x, by_y = build_spatial_index(all_points)

    # 按 region 分组点
    points_by_region = defaultdict(list)
    for pt in all_points:
        points_by_region[pt['region']].append(pt)

    # 为每个非 grey 点添加连接
    connection_count = 0
    for pt in all_points:
        is_grey = pt['region'] == 'grey'

        # 特殊规则应用于所有点（包括 grey 点）
        y = pt['y']
        x = pt['x']

        # 特殊规则: Y=19 连接 Y=16 和 Y=22
        if abs(y - SPECIAL_Y_19) <= EPSILON:
            nearest = find_nearest_y_points(pt, by_y, [SPECIAL_Y_16, SPECIAL_Y_22])
            nearest.sort(key=lambda x: x[0])
            for dist, nid in nearest[:2]:
                if nid not in pt['next']:
                    pt['next'].append(nid)
                    connection_count += 1

        # 特殊规则: Y=232 连接 Y=229 和 Y=235
        if abs(y - SPECIAL_Y_232) <= EPSILON:
            nearest = find_nearest_y_points(pt, by_y, [SPECIAL_Y_229, SPECIAL_Y_235])
            nearest.sort(key=lambda x: x[0])
            for dist, nid in nearest[:2]:
                if nid not in pt['next']:
                    pt['next'].append(nid)
                    connection_count += 1

        # 特殊规则: X=934 连接 X=931 和 X=937
        if abs(x - SPECIAL_X_934) <= EPSILON:
            nearest = find_nearest_x_points(pt, by_x, [SPECIAL_X_931, SPECIAL_X_937])
            nearest.sort(key=lambda x: x[0])
            for dist, nid in nearest[:2]:
                if nid not in pt['next']:
                    pt['next'].append(nid)
                    connection_count += 1

        # 非 grey 点才有普通连接规则
        if is_grey:
            continue

        y = pt['y']
        x = pt['x']

        # 水平连接 (左右)
        left_candidates = by_y.get(round(y, 6), [])
        right_candidates = by_y.get(round(y, 6), [])

        left_id = find_nearest_in_direction(
            pt, by_y.get(round(y, 6), []), 'left',
            exclude_pair_fn=is_x_excluded
        )
        if left_id:
            pt['next'].append(left_id)
            connection_count += 1

        right_id = find_nearest_in_direction(
            pt, by_y.get(round(y, 6), []), 'right',
            exclude_pair_fn=is_x_excluded
        )
        if right_id:
            pt['next'].append(right_id)
            connection_count += 1

        # 垂直连接 (上下)
        up_id = find_nearest_in_direction(
            pt, by_x.get(round(x, 6), []), 'up',
            exclude_pair_fn=is_excluded_pair
        )
        if up_id:
            pt['next'].append(up_id)
            connection_count += 1

        down_id = find_nearest_in_direction(
            pt, by_x.get(round(x, 6), []), 'down',
            exclude_pair_fn=is_excluded_pair
        )
        if down_id:
            pt['next'].append(down_id)
            connection_count += 1

    print(f"  Connections added: {connection_count}")

    # 构建输出数据
    output = {
        "meta": {
            "source": input_path.name,
            "total_points": len(all_points),
            "notes": [
                "Connectivity edges are bidirectional (A->B implies B->A).",
                "Non-grey points connect to nearest same-x (up/down) and same-y (left/right) points.",
                "Y=16/Y=22, Y=229/Y=235, X=931/X=937 are excluded from cross-connections.",
                "Y=19 connects to nearest Y=16 and Y=22.",
                "Y=232 connects to nearest Y=229 and Y=235.",
                "X=934 connects to nearest X=931 and X=937."
            ]
        },
        "points": all_points
    }

    # 输出文件名
    output_name = input_path.stem.replace("_interpolated", "") + "_rt.json"
    output_path = OUTPUT_DIR / output_name

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  Output: {output_path.name}")


def main():
    files = sorted(INTERPOLATION_DIR.glob("*.json"))
    print(f"Found {len(files)} files\n")

    for filepath in files:
        process_file(filepath)
        print()

    print("Done!")


if __name__ == "__main__":
    main()
