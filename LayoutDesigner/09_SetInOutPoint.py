"""
09_SetInOutPoint.py
为 data/routing/interpolation 目录下的文件添加 "inout" 属性
"""
import json
import os
from pathlib import Path

# 文件目录
INTERPOLATION_DIR = Path(__file__).parent / "data" / "routing" / "interpolation"

# 通用的 purple 点条件
PURPLE_Y_VALUES = {13, 14, 15, 16, 235, 236, 237, 238}
PURPLE_X_VALUES = {937, 938, 939, 940}

# Parallel 专用条件
PARALLEL_Y_VALUES = {28, 31, 54, 57, 80, 83, 106, 109, 142, 145, 168, 171, 194, 197, 220, 223}

# Perpendicular 专用条件 (浮点数，使用 tolerance 比较)
PERPENDICULAR_Y_VALUES = {82, 51.57, 81.14, 110.71, 140.29, 169.86, 199.43, 229}
Y_TOLERANCE = 0.1


def is_y_equal(y: float, target_values: set, tolerance: float = Y_TOLERANCE) -> bool:
    """判断 y 值是否在 target_values 中的某个值附近（容差 tolerance）"""
    return any(abs(y - v) <= tolerance for v in target_values)


def is_purple_inout(point: dict) -> bool:
    """判断 purple 点是否应设为 inout=true"""
    y = point.get("y", 0)
    x = point.get("x", 0)
    return y in PURPLE_Y_VALUES or x in PURPLE_X_VALUES


def is_grey_inout(point: dict) -> bool:
    """所有 grey 点都设为 inout=true"""
    return point.get("region") == "grey" or point.get("color_type") == "grey"


def is_parallel_special_y(point: dict) -> bool:
    """Parallel 专用：判断点是否满足 Y 条件且不是 INTER_ 开头"""
    point_id = point.get("id", "")
    if point_id.startswith("INTER_"):
        return False
    y = point.get("y", 0)
    return y in PARALLEL_Y_VALUES


def is_perpendicular_special_y(point: dict) -> bool:
    """Perpendicular 专用：判断点是否满足特殊的 Y 值条件"""
    y = point.get("y", 0)
    return is_y_equal(y, PERPENDICULAR_Y_VALUES)


def process_file(filepath: Path) -> bool:
    """处理单个文件，返回是否有更改"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 判断文件类型
    is_parallel = "parallel" in filepath.name
    is_perpendicular = "perpendicular" in filepath.name

    modified = False

    # 遍历所有 sections
    for section_key, section_data in data.items():
        if not isinstance(section_data, list):
            continue

        for point in section_data:
            # 初始设为 false
            if "inout" not in point:
                point["inout"] = False

            # 1. 通用规则：purple 点
            if point.get("region") == "purple" and is_purple_inout(point):
                if not point["inout"]:
                    point["inout"] = True
                    modified = True

            # 2. 通用规则：grey 点
            if is_grey_inout(point):
                if not point["inout"]:
                    point["inout"] = True
                    modified = True

            # 3. Parallel 专用规则
            if is_parallel and is_parallel_special_y(point):
                if not point["inout"]:
                    point["inout"] = True
                    modified = True

            # 4. Perpendicular 专用规则
            if is_perpendicular and is_perpendicular_special_y(point):
                if not point["inout"]:
                    point["inout"] = True
                    modified = True

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated: {filepath.name}")
    else:
        print(f"No changes: {filepath.name}")

    return modified


def main():
    # 获取所有 interpolated 文件
    files = sorted(INTERPOLATION_DIR.glob("*.json"))
    print(f"Found {len(files)} files in {INTERPOLATION_DIR}")
    print()

    for filepath in files:
        process_file(filepath)

    print("\nDone!")


if __name__ == "__main__":
    main()
