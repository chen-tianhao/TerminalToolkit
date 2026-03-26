import json
from collections import defaultdict

# Read data
with open('data\\control_points_v16.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

points = data['points']

# Classify points by color type
def get_color_type(p):
    region = p['region']
    kind = p.get('meta', {}).get('kind', '')

    if region == 'grey':
        return 'grey'
    elif region == 'purple':
        if kind == 'h':
            return 'purple_horizontal'
        elif kind == 'v':
            return 'vertical_purple'
    elif region == 'orange':
        return 'orange'
    elif region == 'green':
        return 'green'
    elif region == 'blue':
        return 'blue'

    return None

# Separate points by color type
color_points = defaultdict(list)
for p in points:
    ct = get_color_type(p)
    if ct:
        color_points[ct].append(p)

print("Raw counts:")
for ct, pts in color_points.items():
    print(f"  {ct}: {len(pts)}")

endpoints = {
    'purple_horizontal': [],
    'vertical_purple': [],
    'grey': [],
    'orange': [],
    'green': [],
    'blue': [],
    'vertical_grey': []
}

# Grey: keep all
for p in color_points['grey']:
    endpoints['grey'].append({
        'id': p['id'],
        'x': p['x'],
        'y': p['y'],
        'region': p['region'],
        'kind': p.get('meta', {}).get('kind', ''),
        'color_type': 'grey'
    })

# vertical_grey: region=grey, kind=v
for p in color_points['grey']:
    if p.get('meta', {}).get('kind') == 'v':
        endpoints['vertical_grey'].append({
            'id': p['id'],
            'x': p['x'],
            'y': p['y'],
            'region': p['region'],
            'kind': 'v',
            'color_type': 'vertical_grey'
        })

# For horizontal types (purple_horizontal, orange, green):
# Group by y (row), keep leftmost and rightmost
def keep_horizontal_endpoints(points_list, color_type):
    by_y = defaultdict(list)
    for p in points_list:
        by_y[p['y']].append(p)

    row_endpoints = set()
    for y, pts in by_y.items():
        if len(pts) >= 2:
            sorted_pts = sorted(pts, key=lambda p: p['x'])
            row_endpoints.add(sorted_pts[0]['id'])
            row_endpoints.add(sorted_pts[-1]['id'])
        else:
            row_endpoints.add(pts[0]['id'])

    result = []
    for p in points_list:
        if p['id'] in row_endpoints:
            result.append({
                'id': p['id'],
                'x': p['x'],
                'y': p['y'],
                'region': p['region'],
                'kind': p.get('meta', {}).get('kind', ''),
                'color_type': color_type
            })
    return result

# For vertical types (vertical_purple, blue):
# Group by x (column), keep topmost and bottommost
def keep_vertical_endpoints(points_list, color_type):
    by_x = defaultdict(list)
    for p in points_list:
        by_x[p['x']].append(p)

    col_endpoints = set()
    for x, pts in by_x.items():
        if len(pts) >= 2:
            sorted_pts = sorted(pts, key=lambda p: p['y'])
            col_endpoints.add(sorted_pts[0]['id'])
            col_endpoints.add(sorted_pts[-1]['id'])
        else:
            col_endpoints.add(pts[0]['id'])

    result = []
    for p in points_list:
        if p['id'] in col_endpoints:
            result.append({
                'id': p['id'],
                'x': p['x'],
                'y': p['y'],
                'region': p['region'],
                'kind': p.get('meta', {}).get('kind', ''),
                'color_type': color_type
            })
    return result

# Process horizontal types (by rows)
for ct in ['purple_horizontal', 'orange', 'green']:
    endpoints[ct] = keep_horizontal_endpoints(color_points.get(ct, []), ct)

# Process vertical types (by columns)
for ct in ['vertical_purple', 'blue']:
    endpoints[ct] = keep_vertical_endpoints(color_points.get(ct, []), ct)

# Output results
print("\nEndpoint counts:")
for ct, pts in endpoints.items():
    print(f"  {ct}: {len(pts)}")

# Save to layout_parallel.json
with open('data\\path\\layout_parallel.json', 'w', encoding='utf-8') as f:
    json.dump(endpoints, f, indent=2, ensure_ascii=False)

print("\nSaved to layout_parallel.json")
