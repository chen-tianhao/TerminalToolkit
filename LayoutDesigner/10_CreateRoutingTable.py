"""
10_CreateRoutingTable.py
根据 data/routing/interpolation 下的文件创建路由表，输出到 data/routing_table
"""
import json
from pathlib import Path
from collections import defaultdict

INTERPOLATION_DIR = Path(__file__).parent / "data" / "routing" / "interpolation"
OUTPUT_DIR = Path(__file__).parent / "data" / "routing_table"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EPSILON = 0.1

# 排除的 Y 值对 (不相连)
EXCLUDE_Y_PAIRS = {(16, 22), (22, 16), (229, 235), (235, 229)}
# 排除的 X 值对 (不相连)
EXCLUDE_X_PAIRS = {(931, 937), (937, 931)}


def is_same_row(y1: float, y2: float) -> bool:
    return abs(y1 - y2) <= EPSILON


def is_same_col(x1: float, x2: float) -> bool:
    return abs(x1 - x2) <= EPSILON


def is_excluded_pair(y1: float, y2: float) -> bool:
    return (round(y1), round(y2)) in EXCLUDE_Y_PAIRS


def is_x_excluded(x1: float, x2: float) -> bool:
    return (round(x1), round(x2)) in EXCLUDE_X_PAIRS


def is_addxi(pt: dict) -> bool:
    """判断是否为 ADDXI 点（只能水平连接）"""
    return pt['id'].startswith('ADDXI')


def is_addyi(pt: dict) -> bool:
    """判断是否为 ADDYI 点（只能垂直连接）"""
    return pt['id'].startswith('ADDYI')


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


def find_nearest_in_direction(pt: dict, candidates: list, direction: str) -> str:
    """在给定方向上找最近的可连接点"""
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
            if is_excluded_pair(pt['y'], cand['y']):
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
            if is_x_excluded(pt['x'], cand['x']):
                continue
            dist = abs(cand['x'] - pt['x'])

        if 0 < dist < best_dist:
            best_dist = dist
            best = cand['id']

    return best


def find_nearest_y_points(pt: dict, by_y: dict, target_y_values: list, exclude_addxi_addyi: bool = True) -> list:
    """找到指定 Y 值列表中最近的点"""
    results = []
    for y_key, group in by_y.items():
        if any(abs(y_key - ty) <= EPSILON for ty in target_y_values):
            for cand in group:
                if cand['id'] != pt['id'] and is_same_col(pt['x'], cand['x']):
                    # 排除 ADDXI/ADDYI 点（除非是起点本身）
                    if exclude_addxi_addyi and (is_addxi(cand) or is_addyi(cand)):
                        continue
                    results.append((abs(cand['y'] - pt['y']), cand['id']))
    return results


def find_nearest_x_points(pt: dict, by_x: dict, target_x_values: list, exclude_addxi_addyi: bool = True) -> list:
    """找到指定 X 值列表中最近的点"""
    results = []
    for x_key, group in by_x.items():
        if any(abs(x_key - tx) <= EPSILON for tx in target_x_values):
            for cand in group:
                if cand['id'] != pt['id'] and is_same_row(pt['y'], cand['y']):
                    # 排除 ADDXI/ADDYI 点（除非是起点本身）
                    if exclude_addxi_addyi and (is_addxi(cand) or is_addyi(cand)):
                        continue
                    results.append((abs(cand['x'] - pt['x']), cand['id']))
    return results


def add_bidirectional_connection(points_dict: dict, id1: str, id2: str):
    """添加双向连接"""
    if id1 in points_dict and id2 in points_dict:
        if id2 not in points_dict[id1]['next']:
            points_dict[id1]['next'].append(id2)
        if id1 not in points_dict[id2]['next']:
            points_dict[id2]['next'].append(id1)


def process_file(input_path: Path) -> None:
    """处理单个文件"""
    print(f"Processing: {input_path.name}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 收集所有点，建立 id -> point 映射
    all_points = []
    points_by_id = {}
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
                points_by_id[point['id']] = point

    print(f"  Total points: {len(all_points)}")

    # 构建空间索引
    by_x, by_y = build_spatial_index(all_points)

    connection_count = 0

    # 第一步：非 grey 点的普通连接
    for pt in all_points:
        if pt['region'] == 'grey':
            continue

        # 检查是否是 ADDXI 或 ADDYI，决定连接方向限制
        is_addxi_pt = is_addxi(pt)
        is_addyi_pt = is_addyi(pt)

        y = pt['y']
        x = pt['x']

        # 水平连接 (左右) - ADDXI 只能水平连接
        if not is_addyi_pt:  # ADDYI 不能水平连接
            left_id = find_nearest_in_direction(pt, by_y.get(round(y, 6), []), 'left')
            if left_id:
                pt['next'].append(left_id)
                connection_count += 1
                # 双向连接
                points_by_id[left_id]['next'].append(pt['id'])
                connection_count += 1

            right_id = find_nearest_in_direction(pt, by_y.get(round(y, 6), []), 'right')
            if right_id:
                pt['next'].append(right_id)
                connection_count += 1
                points_by_id[right_id]['next'].append(pt['id'])
                connection_count += 1

        # 垂直连接 (上下) - ADDYI 只能垂直连接
        if not is_addxi_pt:  # ADDXI 不能垂直连接
            up_id = find_nearest_in_direction(pt, by_x.get(round(x, 6), []), 'up')
            if up_id:
                pt['next'].append(up_id)
                connection_count += 1
                points_by_id[up_id]['next'].append(pt['id'])
                connection_count += 1

            down_id = find_nearest_in_direction(pt, by_x.get(round(x, 6), []), 'down')
            if down_id:
                pt['next'].append(down_id)
                connection_count += 1
                points_by_id[down_id]['next'].append(pt['id'])
                connection_count += 1

    # 第二步：特殊规则（仅适用于 grey 和 junction 点，不适用于 ADDXI/ADDYI）
    for pt in all_points:
        # 跳过 ADDXI 和 ADDYI
        if is_addxi(pt) or is_addyi(pt):
            continue

        y = pt['y']
        x = pt['x']

        # Y=19 连接 Y=16 和 Y=22
        if abs(y - 19) <= EPSILON:
            nearest = find_nearest_y_points(pt, by_y, [16, 22])
            nearest.sort(key=lambda x: x[0])
            for dist, nid in nearest[:2]:
                if nid not in pt['next']:
                    add_bidirectional_connection(points_by_id, pt['id'], nid)
                    connection_count += 1

        # Y=232 连接 Y=229 和 Y=235
        if abs(y - 232) <= EPSILON:
            nearest = find_nearest_y_points(pt, by_y, [229, 235])
            nearest.sort(key=lambda x: x[0])
            for dist, nid in nearest[:2]:
                if nid not in pt['next']:
                    add_bidirectional_connection(points_by_id, pt['id'], nid)
                    connection_count += 1

        # X=934 连接 X=931 和 X=937
        if abs(x - 934) <= EPSILON:
            nearest = find_nearest_x_points(pt, by_x, [931, 937])
            nearest.sort(key=lambda x: x[0])
            for dist, nid in nearest[:2]:
                if nid not in pt['next']:
                    add_bidirectional_connection(points_by_id, pt['id'], nid)
                    connection_count += 1

    print(f"  Connections added: {connection_count}")

    # 去重每个点的 next 列表
    for pt in all_points:
        pt['next'] = list(dict.fromkeys(pt['next']))

    # 构建输出数据
    output = {
        "meta": {
            "source": input_path.name,
            "total_points": len(all_points),
            "notes": [
                "Connectivity edges are bidirectional (A->B implies B->A).",
                "Non-grey points connect to nearest same-x (up/down) and same-y (left/right) points.",
                "Y=16/Y=22, Y=229/Y=235, X=931/X=937 are excluded from cross-connections.",
                "ADDXI can only connect horizontally (same Y).",
                "ADDYI can only connect vertically (same X).",
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
