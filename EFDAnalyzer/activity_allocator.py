"""
Activity Allocator - 从 drawio 文件中提取矩形标签

从 SingaPort_20260226.drawio 文件中识别所有矩形元素的 label，
并保存到 conf/activity_efd.txt 文件中。
"""

import re
from pathlib import Path


def extract_rectangle_labels(drawio_file: str, output_file: str) -> list[str]:
    """
    从 drawio 文件中提取所有矩形的 label

    Args:
        drawio_file: drawio 文件路径
        output_file: 输出文件路径

    Returns:
        提取到的标签列表
    """
    # 读取 drawio 文件
    with open(drawio_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正则表达式匹配 rounded=1 的 mxCell 元素，并提取 value 属性
    # 匹配模式: <mxCell ... value="文本" ... rounded=1 ...
    pattern = r'<mxCell[^>]*value="([^"]*)"[^>]*rounded=1[^>]*>'

    # 查找所有匹配
    matches = re.findall(pattern, content)

    # 过滤掉空值和仅包含样式的值
    labels = []
    for match in matches:
        # 清理 HTML 实体
        label = match.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        label = label.strip()
        # 只保留非空且不是纯样式的标签
        if label:
            labels.append(label)

    # 去重并保持顺序
    unique_labels = []
    seen = set()
    for label in labels:
        if label not in seen:
            seen.add(label)
            unique_labels.append(label)

    # 写入输出文件
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Activity Mapping - 从 SingaPort_20260226.drawio 提取\n")
        f.write("# 格式: 序号 | 活动标签\n")
        f.write("=" * 50 + "\n\n")
        for i, label in enumerate(unique_labels, 1):
            f.write(f"{i:3d} | {label}\n")

    print(f"[OK] Extracted {len(unique_labels)} rectangle labels")
    print(f"[OK] Saved to: {output_file}")

    return unique_labels


def main():
    # 定义文件路径
    base_dir = Path(__file__).parent
    drawio_file = base_dir / "SingaPort_20260226.drawio"
    output_file = base_dir / "conf" / "activity_efd.txt"

    # 检查 drawio 文件是否存在
    if not drawio_file.exists():
        print(f"[ERROR] Drawio file not found: {drawio_file}")
        return

    # 提取标签
    labels = extract_rectangle_labels(str(drawio_file), str(output_file))

    # 打印结果
    print("\nExtracted activity labels:")
    print("-" * 40)
    for i, label in enumerate(labels, 1):
        print(f"  {i:3d}. {label}")


if __name__ == "__main__":
    main()
