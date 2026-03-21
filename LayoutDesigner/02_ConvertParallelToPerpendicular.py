import json
import sys

# NoC (Number of Columns) options for blue lines
# NoC = number of non-fixed groups in the middle
# Total groups = 1 (left fixed) + NoC + 2 (right fixed)
NOC_OPTIONS = [32, 34, 36]

# Fixed groups configuration
LEFT_FIXED_GROUPS = 1   # Left side: 1 group (4 lines)
RIGHT_FIXED_GROUPS = 2  # Right side: 2 groups (8 lines)

# Group internal spacing (1U = 4m)
U_TO_M = 4  # meters per U


def get_blue_group_starts(points):
    """
    Identify blue line group starts by clustering x values.
    Points within 1U distance belong to the same group (1U = 4m).
    Each group has 4 lines (4 consecutive x values).
    Returns list of group start x positions.
    """
    if not points:
        return []

    # Get all unique x values and sort them
    x_values = sorted({p['x'] for p in points})

    if len(x_values) < 4:
        return x_values

    # Cluster x values into groups (within-group gap <= 1U)
    group_starts = []
    i = 0
    while i < len(x_values):
        group_starts.append(x_values[i])
        # Skip all x values within this group
        while i < len(x_values) and x_values[i] - group_starts[-1] <= 1:
            i += 1

    return group_starts


def convert_blue_vertical_spacing(points, noc, left_fixed=1, right_fixed=2):
    """
    Convert blue vertical lines spacing with fixed ends and average-distributed middle.

    Algorithm:
    1. Group points by x coordinate (clustering within 1U)
    2. Identify left_fixed groups (fixed), right_fixed groups (fixed), and noc groups (to redistribute)
    3. Calculate new spacing: total_span / (noc + 1) for the gaps between noc groups
    4. Recompute all group x positions

    Args:
        points: Blue line points list
        noc: Number of Columns (middle groups to redistribute)
        left_fixed: Number of fixed groups on left (default 1)
        right_fixed: Number of fixed groups on right (default 2)

    Returns:
        Converted points list
    """
    if not points:
        return points

    # Find group starts using clustering
    orig_group_starts = get_blue_group_starts(points)

    if len(orig_group_starts) < left_fixed + right_fixed + noc:
        print(f"Warning: Not enough groups. Found {len(orig_group_starts)}, need at least {left_fixed + right_fixed + noc}")
        return points

    # Get first and last fixed group positions
    first_fixed_x = orig_group_starts[0]
    last_fixed_x = orig_group_starts[left_fixed + noc - 1]  # Last of the right-fixed groups

    # Calculate original span between first fixed and last fixed group
    orig_span = last_fixed_x - first_fixed_x

    # Calculate fixed groups width (each group is 3U = 12m wide: 4 lines with 3 gaps)
    fixed_groups_width = (left_fixed + right_fixed) * 3

    # Calculate available span for noc groups
    # The span should distribute: left_fixed gap, (noc-1) middle gaps, right_fixed gap
    # But we simplify: total span / (noc + 1) gives the average gap
    available_span = orig_span - fixed_groups_width

    # New gap between each group
    if noc > 0:
        new_gap = available_span / (noc + 1)
    else:
        new_gap = available_span

    # Build x offset mapping
    x_offset_map = {}

    # Position for left-fixed groups (at original positions)
    current_x = first_fixed_x
    for i in range(left_fixed):
        for col in range(4):
            orig_x = orig_group_starts[i] + col
            new_x = current_x + col
            x_offset_map[orig_x] = new_x
        current_x += 4  # Move past this group's 4 lines (4U)

    # Position for noc groups with new average gap
    for i in range(noc):
        for col in range(4):
            orig_x = orig_group_starts[left_fixed + i] + col
            new_x = current_x + col
            x_offset_map[orig_x] = new_x
        current_x += 4 + new_gap  # Group width (4U) + gap

    # Position for right-fixed groups (at original positions)
    # Right fixed groups stay at their original positions
    for i in range(right_fixed):
        group_idx = left_fixed + noc + i
        for col in range(4):
            orig_x = orig_group_starts[group_idx] + col
            # Right fixed groups stay at their original positions
            x_offset_map[orig_x] = orig_x

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


def main():
    # Get NoC from command line argument or use default
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
        noc = NOC_OPTIONS[1]  # Default to 34
        print(f"No NoC specified, using default: {noc}")

    # Read data
    with open('layout_parallel.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Process each color type
    result = {}

    # Keep purple_horizontal, vertical_purple, green unchanged
    for ct in ['purple_horizontal', 'vertical_purple', 'green']:
        if ct in data:
            result[ct] = data[ct]

    # Grey types - keep as is
    for ct in ['grey', 'vertical_grey']:
        if ct in data:
            result[ct] = data[ct]

    # Blue lines - new algorithm with NoC
    if 'blue' in data:
        result['blue'] = convert_blue_vertical_spacing(
            data['blue'],
            noc=noc,
            left_fixed=LEFT_FIXED_GROUPS,
            right_fixed=RIGHT_FIXED_GROUPS
        )

    # Orange is removed (not rendered in perpendicular layout)

    # Save to file with U values rounded to 2 decimal places
    output_file = 'layout_perpendicular.json'

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
