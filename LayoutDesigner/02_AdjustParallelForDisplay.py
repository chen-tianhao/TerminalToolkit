import json
from collections import defaultdict

# Read data
with open('layout_parallel_0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Horizontal line types: purple_horizontal, orange, green
horizontal_types = ['purple_horizontal', 'orange', 'green']
# Vertical line types: vertical_purple, blue
vertical_types = ['vertical_purple', 'blue']

# Deep copy to avoid modifying original
result = {}

# ========== Horizontal Lines Processing ==========
for color_type in horizontal_types:
    if color_type not in data:
        result[color_type] = []
        continue

    points = data[color_type]

    # Step 1: Move all endpoints up by 0.5U (y = y - 0.5)
    for p in points:
        p['y'] = p['y'] - 0.5

    # Step 2: Group points by same x value
    by_x = defaultdict(list)
    for p in points:
        by_x[p['x']].append(p)

    # Step 3: For each x group, sort by y and process groups of 4
    new_points = []
    for x, pts in by_x.items():
        # Sort by y (top to bottom)
        sorted_pts = sorted(pts, key=lambda p: p['y'])

        # Process in groups of 4 consecutive points
        for i in range(0, len(sorted_pts), 4):
            group = sorted_pts[i:i+4]

            # Add original points
            for p in group:
                new_points.append(p)

            # If we have a full group of 4, add a new point below
            if len(group) == 4:
                last_point = group[-1]
                new_point = {
                    'id': last_point['id'] + '_NEW',
                    'x': last_point['x'],
                    'y': last_point['y'] + 1.0,  # Below: y + 1U = 4m (since Y increases downward)
                    'region': last_point['region'],
                    'kind': last_point['kind'],
                    'color_type': last_point['color_type']
                }
                new_points.append(new_point)

    result[color_type] = new_points

# ========== Vertical Lines Processing ==========
for color_type in vertical_types:
    if color_type not in data:
        result[color_type] = []
        continue

    points = data[color_type]

    # Step 1: Move all endpoints up by 0.5U (y = y - 0.5)
    for p in points:
        p['y'] = p['y'] - 0.5

    # Step 2: Group points by same y value
    by_y = defaultdict(list)
    for p in points:
        by_y[p['y']].append(p)

    # Step 3: For each y group, sort by x and process groups of 4
    new_points = []
    for y, pts in by_y.items():
        # Sort by x (left to right)
        sorted_pts = sorted(pts, key=lambda p: p['x'])

        # Process in groups of 4 consecutive points
        for i in range(0, len(sorted_pts), 4):
            group = sorted_pts[i:i+4]

            # Add original points
            for p in group:
                new_points.append(p)

            # If we have a full group of 4, add a new point to the right
            if len(group) == 4:
                last_point = group[-1]
                new_point = {
                    'id': last_point['id'] + '_NEW',
                    'x': last_point['x'] + 1.0,  # Right: x + 1U = 4m (since X increases rightward)
                    'y': last_point['y'],
                    'region': last_point['region'],
                    'kind': last_point['kind'],
                    'color_type': last_point['color_type']
                }
                new_points.append(new_point)

    result[color_type] = new_points

# Copy other color types unchanged (grey, vertical_grey)
for color_type in data:
    if color_type not in horizontal_types and color_type not in vertical_types:
        result[color_type] = data[color_type]

# Save to layout_parallel.json
with open('layout_parallel.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("Processing complete!")
print("\nPoint counts:")
for ct in result:
    print(f"  {ct}: {len(result[ct])}")

print("\nSaved to layout_parallel.json")
