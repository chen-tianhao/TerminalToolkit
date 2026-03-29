"""
091_RemoveDuplicatedId.py
删除 ADDYI_R111_C0928/929/930/931 重复 ID 中坐标不是整数的点
"""
import json
from pathlib import Path

INTERPOLATION_DIR = Path(__file__).parent / "data" / "routing" / "interpolation"

DUPLICATE_IDS = ['ADDYI_R111_C0928', 'ADDYI_R111_C0929', 'ADDYI_R111_C0930', 'ADDYI_R111_C0931']


def is_integer_coord(point: dict) -> bool:
    """检查点的 x 和 y 是否都是整数"""
    x = point.get('x', 0)
    y = point.get('y', 0)
    return float(x).is_integer() and float(y).is_integer()


def process_file(filepath: Path) -> bool:
    """处理单个文件，删除坐标非整数的重复 ID 点"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = False

    for section_key, section_data in list(data.items()):
        if not isinstance(section_data, list):
            continue

        # 找出需要删除的点（坐标非整数且 ID 在重复列表中）
        points_to_remove = []
        for i, point in enumerate(section_data):
            if point.get('id') in DUPLICATE_IDS and not is_integer_coord(point):
                points_to_remove.append(i)

        # 从后往前删除，避免索引变化
        for i in reversed(points_to_remove):
            removed = section_data.pop(i)
            print(f"  Removed: {section_key} -> id={removed['id']}, x={removed['x']}, y={removed['y']}")
            modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated: {filepath.name}")
    else:
        print(f"No changes: {filepath.name}")

    return modified


def main():
    files = sorted(INTERPOLATION_DIR.glob('*.json'))
    print(f"Found {len(files)} files\n")

    for filepath in files:
        print(f"=== {filepath.name} ===")
        process_file(filepath)
        print()

    print("Done!")


if __name__ == "__main__":
    main()
