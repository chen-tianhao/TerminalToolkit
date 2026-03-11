"""
Activity Collector - 从 CSV 文件中提取活动 Header

从 activity_increase_rates.csv 文件中提取所有列名（排除 SimulationTime），
并保存到 conf/activity_collected.txt 文件中。
"""

import csv
from pathlib import Path


def extract_activity_headers(csv_file: str, output_file: str) -> list[str]:
    """
    从 CSV 文件中提取所有活动 header

    Args:
        csv_file: CSV 文件路径
        output_file: 输出文件路径

    Returns:
        提取到的活动 header 列表
    """
    # 读取 CSV 文件的 header
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)

    # 排除第一个 SimulationTime
    activities = [h for h in headers if h != 'SimulationTime']

    # 写入输出文件
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Activity Headers - 从 activity_increase_rates.csv 提取\n")
        f.write("# 格式: 序号 | 活动名称\n")
        f.write("=" * 50 + "\n\n")
        for i, activity in enumerate(activities, 1):
            f.write(f"{i:3d} | {activity}\n")

    print(f"[OK] Extracted {len(activities)} activity headers")
    print(f"[OK] Saved to: {output_file}")

    return activities


def main():
    # 定义文件路径
    base_dir = Path(__file__).parent
    csv_file = base_dir / "21m_agv700_10d" / "activity_increase_rates.csv"
    output_file = base_dir / "conf" / "activity_collected.txt"

    # 检查 CSV 文件是否存在
    if not csv_file.exists():
        print(f"[ERROR] CSV file not found: {csv_file}")
        return

    # 提取 headers
    activities = extract_activity_headers(str(csv_file), str(output_file))

    # 打印结果
    print("\nExtracted activity headers:")
    print("-" * 60)
    for i, activity in enumerate(activities, 1):
        print(f"  {i:3d}. {activity}")


if __name__ == "__main__":
    main()
