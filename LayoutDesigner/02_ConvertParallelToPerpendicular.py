import json
from collections import defaultdict

# Read data
with open('layout_parallel.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Current spacing values in U
ORANGE_CURRENT_GAP = 26  # U (between orange groups)
BLUE_CURRENT_GAP = 82   # U (between blue groups)

# Target spacing - swap them
ORANGE_NEW_GAP = BLUE_CURRENT_GAP    # 82U
BLUE_NEW_GAP = ORANGE_CURRENT_GAP   # 26U

def convert_horizontal_spacing(points, current_gap, new_gap):
    """
    Convert horizontal lines spacing.
    Groups 1 and 8 stay at their original positions.
    Groups 2-7 are shifted to achieve new_gap between all groups.
    """
    # Group by y
    by_y = defaultdict(list)
    for p in points:
        by_y[p['y']].append(p)

    y_values = sorted(by_y.keys())

    if len(y_values) < 8:
        return points

    # Get original group start positions (every 4 rows)
    n_groups = len(y_values) // 4
    orig_group_starts = [y_values[i * 4] for i in range(n_groups)]

    # Calculate the shift needed for each group
    # Group 1 (index 0) stays at original position
    # Group 8 (index 7) stays at original position
    # Groups 2-7 are distributed evenly between them

    # First, calculate the total span with new gap
    # new_span = (n_groups - 1) * new_gap
    new_span = (n_groups - 1) * new_gap
    orig_span = orig_group_starts[-1] - orig_group_starts[0]

    # Calculate new positions proportionally
    new_group_starts = []
    for i in range(n_groups):
        if i == 0:
            # Group 1: fixed at original position
            new_group_starts.append(orig_group_starts[0])
        elif i == n_groups - 1:
            # Group 8: fixed at original position
            new_group_starts.append(orig_group_starts[-1])
        else:
            # Groups 2-7: proportional distribution
            ratio = i / (n_groups - 1)
            new_pos = orig_group_starts[0] + ratio * new_span
            new_group_starts.append(new_pos)

    # Create y offset mapping
    y_offset_map = {}
    for gi, orig_start in enumerate(orig_group_starts):
        new_start = new_group_starts[gi]
        for row in range(4):
            orig_y = orig_start + row
            new_y = new_start + row
            y_offset_map[orig_y] = new_y

    # Apply offset to points
    converted = []
    for p in points:
        new_y = y_offset_map.get(p['y'], p['y'])
        converted.append({
            'id': p['id'],
            'x': p['x'],
            'y': new_y,
            'region': p['region'],
            'kind': p['kind'],
            'color_type': p['color_type']
        })

    return converted

def convert_vertical_spacing(points, current_gap, new_gap):
    """
    Convert vertical lines spacing.
    First and last groups stay at their original positions.
    Middle groups are shifted to achieve new_gap between all groups.
    """
    # Group by x
    by_x = defaultdict(list)
    for p in points:
        by_x[p['x']].append(p)

    x_values = sorted(by_x.keys())

    if len(x_values) < 8:
        return points

    # Get original group start positions (every 4 columns)
    n_groups = len(x_values) // 4
    orig_group_starts = [x_values[i * 4] for i in range(n_groups)]

    # Calculate new positions
    new_span = (n_groups - 1) * new_gap

    new_group_starts = []
    for i in range(n_groups):
        if i == 0:
            new_group_starts.append(orig_group_starts[0])
        elif i == n_groups - 1:
            new_group_starts.append(orig_group_starts[-1])
        else:
            ratio = i / (n_groups - 1)
            new_pos = orig_group_starts[0] + ratio * new_span
            new_group_starts.append(new_pos)

    # Create x offset mapping
    x_offset_map = {}
    for gi, orig_start in enumerate(orig_group_starts):
        new_start = new_group_starts[gi]
        for col in range(4):
            orig_x = orig_start + col
            new_x = new_start + col
            x_offset_map[orig_x] = new_x

    # Apply offset to points
    converted = []
    for p in points:
        new_x = x_offset_map.get(p['x'], p['x'])
        converted.append({
            'id': p['id'],
            'x': new_x,
            'y': p['y'],
            'region': p['region'],
            'kind': p['kind'],
            'color_type': p['color_type']
        })

    return converted

# Process each color type
result = {}

# Horizontal types - swap to blue spacing
for ct in ['orange', 'green', 'purple_horizontal']:
    points = data.get(ct, [])
    if ct == 'orange':
        result[ct] = convert_horizontal_spacing(points, ORANGE_CURRENT_GAP, ORANGE_NEW_GAP)
    else:
        result[ct] = points

# Vertical types - swap to orange spacing
for ct in ['blue', 'vertical_purple']:
    points = data.get(ct, [])
    if ct == 'blue':
        result[ct] = convert_vertical_spacing(points, BLUE_CURRENT_GAP, BLUE_NEW_GAP)
    else:
        result[ct] = points

# Grey types (keep as is)
for ct in ['grey', 'vertical_grey']:
    if ct in data:
        result[ct] = data[ct]

# Save to file
with open('layout_perpendicular.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("Saved to layout_perpendicular.json")
print(f"Orange spacing: {ORANGE_CURRENT_GAP}U -> {ORANGE_NEW_GAP}U")
print(f"Blue spacing: {BLUE_CURRENT_GAP}U -> {BLUE_NEW_GAP}U")
