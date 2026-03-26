import json
import sys

# NoC (Number of Columns) 选项，表示中间非固定组的数量
# 总组数 = 1 (左侧固定组) + NoC (中间组) + 2 (右侧固定组)
NOC_OPTIONS = [34, 35, 36]

# 固定组配置
LEFT_FIXED_GROUPS = 1   # 左侧：1个组 (4条线)
RIGHT_FIXED_GROUPS = 2  # 右侧：2个组 (8条线)

def get_blue_group_starts(points):
    """
    通过x值聚类识别蓝色线的组起始位置。
    间距在1U以内的点属于同一组 (1U = 4m)。
    每组有4条线 (4个连续的x值)。
    返回组起始x位置的列表。
    """
    if not points:
        return []

    # 获取所有唯一的x值并排序
    x_values = sorted({p['x'] for p in points})

    if len(x_values) < 4:
        return x_values

    # 将x值聚类成组（组内间距 <= 1U）
    group_starts = []
    i = 0
    while i < len(x_values):
        group_starts.append(x_values[i])
        # 跳过同一组内的所有x值（与前一个x比较）
        i += 1
        while i < len(x_values) and x_values[i] - x_values[i-1] <= 1:
            i += 1

    return group_starts


def convert_blue_vertical_spacing(points, noc, left_fixed=1, right_fixed=2):
    """
    转换蓝色垂直线间距，两端固定，中间均匀分布。

    算法说明：
    1. 从输入数据获取固定组位置（左侧固定在x=0，右侧固定在x=922, x=928）
    2. 计算间距：中间组应填充在左侧固定组和第一个右侧固定组之间
    3. 重新生成所有点：左侧固定组 + noc个中间组 + 右侧固定组

    参数说明：
        points: 蓝色线点列表
        noc: 中间非固定组数量
        left_fixed: 左侧固定组数量（默认1）
        right_fixed: 右侧固定组数量（默认2）

    返回：
        转换后的点列表
    """
    if not points:
        return points

    # 从输入数据获取y值（只取最大和最小）
    all_y = {p['y'] for p in points}
    if not all_y:
        return points
    y_values = sorted([min(all_y), max(all_y)])
    if not y_values:
        return points

    # 使用修正后的聚类算法从输入数据获取固定组x位置
    orig_group_starts = get_blue_group_starts(points)

    if len(orig_group_starts) < left_fixed + right_fixed:
        print(f"Error: Need at least {left_fixed + right_fixed} groups for fixed positions")
        return points

    # 从输入数据获取固定组位置
    first_fixed_x = orig_group_starts[0]  # 应该是0
    # 右侧固定组：排序后的最后两个
    right_fixed_x = [orig_group_starts[-2], orig_group_starts[-1]]  # 应该是 [922, 928]

    # 计算中间组的间距
    # 中间组应该结束在 right_fixed_x[0] (922) 之前
    # 公式: right_fixed_x[0] = first_fixed_x + 4 + noc * (4 + new_gap)
    # 因此: new_gap = (right_fixed_x[0] - first_fixed_x - 4) / noc - 4
    new_gap = (right_fixed_x[0] - first_fixed_x - 4 - noc * 4) / (noc + 1)

    # 按正确的x顺序构建所有组的x位置
    # 顺序：左侧固定组、中间组、右侧固定组（按x排序）
    group_x_starts = []

    # 左侧固定组
    group_x_starts.append(first_fixed_x)  # x=0

    # 中间组（noc个组，每组4U宽，带间距）
    for i in range(noc):
        group_x_starts.append(first_fixed_x + 4 + new_gap + i * (4 + new_gap))

    # 右侧固定组（位于原始x位置）
    group_x_starts.extend(right_fixed_x)

    # 按x排序确保正确顺序
    group_x_starts.sort()

    # 重新生成所有点
    converted = []
    group_idx = 0

    for y in y_values:
        for group_x in group_x_starts:
            for col in range(4):
                converted.append({
                    'id': f'BLU_R{group_idx:03d}_{int(y):04d}',
                    'x': group_x + col,
                    'y': y,
                    'region': 'blue',
                    'kind': 'v',
                    'color_type': 'blue'
                })
            group_idx += 1

    return converted


def main():
    # 从命令行参数获取NoC，若无则使用默认值
    if len(sys.argv) > 1:
        try:
            noc = int(sys.argv[1])
            if noc not in NOC_OPTIONS:
                print(f"Invalid NoC value: {noc}. Valid options: {NOC_OPTIONS}")
                sys.exit(1)
        except ValueError:
            print(f"Invalid NoC argument: {sys.argv[1]}. Must be an integer.")
            sys.exit(1)
    else:
        noc = NOC_OPTIONS[1]  # 默认为中间值
        print(f"No NoC specified, using default: {noc}")

    # 读取数据
    with open('data\\path\\layout_parallel.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理每种颜色类型
    result = {}

    # 保留 purple_horizontal, vertical_purple, green 不变
    for ct in ['purple_horizontal', 'vertical_purple', 'green']:
        if ct in data:
            result[ct] = data[ct]

    # 灰色类型保持不变
    for ct in ['grey', 'vertical_grey']:
        if ct in data:
            result[ct] = data[ct]

    # 蓝色线 - 使用NoC的新算法
    if 'blue' in data:
        result['blue'] = convert_blue_vertical_spacing(
            data['blue'],
            noc=noc,
            left_fixed=LEFT_FIXED_GROUPS,
            right_fixed=RIGHT_FIXED_GROUPS
        )

    # 橙色线被移除（不在垂直布局中渲染）

    # 保存到文件，U值保留2位小数
    output_file = f'data\\path\\layout_perpendicular_{noc}.json'

    def format_point(p):
        return {
            'id': p['id'],
            'x': round(p['x'], 2),
            'y': round(p['y'], 2),
            'region': p['region'],
            'kind': p['kind'],
            'color_type': p['color_type']
        }

    formatted_result = {ct: [format_point(p) for p in points] for ct, points in result.items()}
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(formatted_result, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_file}")
    print(f"NoC: {noc}")
    print(f"Left fixed groups: {LEFT_FIXED_GROUPS}")
    print(f"Right fixed groups: {RIGHT_FIXED_GROUPS}")
    print(f"Total blue groups: {LEFT_FIXED_GROUPS + noc + RIGHT_FIXED_GROUPS}")

if __name__ == '__main__':
    main()
