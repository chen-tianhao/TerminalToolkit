"""
Find all line segment intersections from layout files.
Input:  data/path/*.json
Output: data/routing/*_point.json
"""

import json
import os
import glob
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

horizontal_types = ['purple_horizontal', 'orange', 'green']
vertical_types = ['vertical_purple', 'blue']


def load_layout(file_path):
    """Load layout data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_line_coords(data):
    """
    Extract horizontal and vertical line coordinates.
    Returns: (horizontal_lines, vertical_lines)
    - horizontal_lines: dict {y: [x1, x2, ...]} for each horizontal line at y
    - vertical_lines: dict {x: [y1, y2, ...]} for each vertical line at x
    """
    horizontal_lines = defaultdict(list)
    vertical_lines = defaultdict(list)

    # Process horizontal lines (group by y)
    for h_type in horizontal_types:
        if h_type not in data:
            continue
        points = data[h_type]
        by_y = defaultdict(list)
        for p in points:
            by_y[p['y']].append(p['x'])
        for y, x_list in by_y.items():
            if len(x_list) >= 2:
                horizontal_lines[y].extend(x_list)

    # Process vertical lines (group by x)
    for v_type in vertical_types:
        if v_type not in data:
            continue
        points = data[v_type]
        by_x = defaultdict(list)
        for p in points:
            by_x[p['x']].append(p['y'])
        for x, y_list in by_x.items():
            if len(y_list) >= 2:
                vertical_lines[x].extend(y_list)

    return horizontal_lines, vertical_lines


def find_intersections(horizontal_lines, vertical_lines):
    """
    Find all intersection points between horizontal and vertical lines.
    Returns list of intersection points with their coordinates.
    """
    intersections = []

    # Each horizontal line at y can intersect with each vertical line at x
    for y, x_list in horizontal_lines.items():
        h_min_x = min(x_list)
        h_max_x = max(x_list)

        for x, y_list in vertical_lines.items():
            v_min_y = min(y_list)
            v_max_y = max(y_list)

            # Check if the lines actually cross within their segments
            if h_min_x <= x <= h_max_x and v_min_y <= y <= v_max_y:
                # This is a valid intersection
                intersections.append({'x': x, 'y': y})

    return intersections


def generate_point_id(x, y):
    """
    Generate intersection point ID.
    ID format: INTER_Rxxx_Cyyyy
    xxx = row (from y coordinate)
    yyyy = col (from x coordinate)
    """
    # Extract row and col numbers from coordinates
    # y -> row number, x -> column number
    row = int(round(y))
    col = int(round(x))
    return f"INTER_R{row:03d}_C{col:04d}"


def create_output(points, input_filename):
    """Create output structure matching the requested JSON format."""
    output_points = []

    for pt in points:
        point_id = generate_point_id(pt['x'], pt['y'])
        # Extract row and col from the point id for meta
        # Format: INTER_Rxxx_Cyyyy
        parts = point_id.split('_')
        row_part = parts[1]  # Rxxx
        col_part = parts[2]  # Cyyyy
        row_num = int(row_part[1:])
        col_num = int(col_part[1:])

        output_points.append({
            "id": point_id,
            "x": round(pt['x'], 2),
            "y": round(pt['y'], 2),
            "region": "inter",
            "meta": {
                "kind": "cell",
                "row": row_num,
                "col": col_num
            },
            "inout": False,
            "next": []
        })

    return {"points": output_points}


def process_file(input_file):
    """Process a single layout file and find all intersections."""
    print(f"Processing: {input_file}")

    data = load_layout(input_file)
    horizontal_lines, vertical_lines = extract_line_coords(data)
    intersections = find_intersections(horizontal_lines, vertical_lines)

    print(f"  Found {len(intersections)} intersection points")

    return create_output(intersections, input_file)


def main():
    # Create output directory if it doesn't exist
    output_dir = os.path.join(BASE_DIR, 'data', 'routing')
    os.makedirs(output_dir, exist_ok=True)

    # Find all layout files in data/path
    input_files = glob.glob(os.path.join(BASE_DIR, 'data', 'path', '*.json'))

    if not input_files:
        print("No layout files found in data/path/")
        return

    # Filter out _disp.json and _point.json files
    input_files = [f for f in input_files if not f.endswith('_disp.json') and not f.endswith('_point.json')]
    input_files.sort()

    print(f"Found {len(input_files)} files to process")

    for input_file in input_files:
        # Get base filename
        basename = os.path.basename(input_file)
        output_file = os.path.join(output_dir, basename.replace('.json', '_point.json'))

        result = process_file(input_file)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"  -> {output_file}")

    print("\nAll processing complete!")


if __name__ == '__main__':
    main()