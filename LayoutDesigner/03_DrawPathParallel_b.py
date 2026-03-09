import json
from collections import defaultdict
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output

# Unit conversion: 1U = 4 meters
U_TO_M = 4

# Read data and convert to meters
with open('layout_parallel.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# Convert coordinates from U to meters
data = {}
for color_type, points in raw_data.items():
    data[color_type] = [
        {
            'id': p['id'],
            'x': p['x'] * U_TO_M,
            'y': p['y'] * U_TO_M,
            'region': p['region'],
            'kind': p['kind'],
            'color_type': p['color_type']
        }
        for p in points
    ]

colors = {
    'purple_horizontal': 'purple',
    'vertical_purple': 'darkviolet',
    'orange': 'orange',
    'green': 'green',
    'blue': 'blue'
}

display_names = {
    'purple_horizontal': 'Purple Horizontal',
    'vertical_purple': 'Vertical Purple',
    'orange': 'Orange',
    'green': 'Green',
    'blue': 'Blue'
}

def get_blue_vertical_data(ct, num_bays):
    """
    Get vertical blue line data with adjustable number of bays.
    - num_bays=43: 12 groups (same as original)
    - num_bays=39: 13 groups
    - num_bays=47: 11 groups
    First and last group stay fixed, middle groups evenly distributed.
    """
    points_list = data.get(ct, [])
    if not points_list:
        return [], {}

    # Group by x (vertical lines)
    by_x = defaultdict(list)
    for p in points_list:
        by_x[p['x']].append(p)

    # Get unique x values sorted
    x_values = sorted(by_x.keys())

    if len(x_values) < 4:
        return [], {}

    # Calculate number of groups based on bays
    # 43 bays -> 12 groups (original)
    # 39 bays -> 13 groups
    # 47 bays -> 11 groups
    n_groups = 51 - num_bays  # 51-43=12, 51-39=13, 51-47=11

    # Get original number of groups (each group has 4 columns)
    n_orig_groups = len(x_values) // 4

    # First group at x_values[0], last group at x_values[(n_orig_groups-1)*4]
    first_group_x = x_values[0]
    last_group_x = x_values[(n_orig_groups - 1) * 4]

    if n_orig_groups < 2:
        return [], {}

    # Total span between first and last group
    total_span = last_group_x - first_group_x

    # Calculate new group start positions
    # First and last group fixed, middle groups evenly distributed
    new_group_starts = []

    if n_groups == 12:
        # 43 bays - keep original positions (12 groups)
        # Original spacing: 44 * U_TO_M / 11 = 176m per group interval
        group_spacing = total_span / 11
        for i in range(12):
            new_group_starts.append(first_group_x + i * group_spacing)
    else:
        # For 11 or 13 groups
        group_spacing = total_span / (n_groups - 1)
        for i in range(n_groups):
            if i == 0:
                new_group_starts.append(first_group_x)
            elif i == n_groups - 1:
                new_group_starts.append(last_group_x)
            else:
                new_pos = first_group_x + i * group_spacing
                new_group_starts.append(new_pos)

    # Create x offset mapping (each group has 4 columns with 4m spacing)
    x_offset_map = {}
    for gi in range(n_orig_groups):
        orig_start = x_values[gi * 4]
        if gi < n_groups:
            new_start = new_group_starts[gi]
        else:
            # Extra original groups go to last position
            new_start = new_group_starts[-1]

        for col in range(4):
            orig_col_x = orig_start + col * U_TO_M
            new_col_x = new_start + col * U_TO_M
            x_offset_map[orig_col_x] = new_col_x

    # Build line data
    lines = []
    for x, pts in by_x.items():
        if len(pts) >= 2:
            new_x = x_offset_map.get(x, x)
            sorted_pts = sorted(pts, key=lambda p: p['y'])
            lines.append({
                'x': [new_x] * len(sorted_pts),
                'y': [p['y'] for p in sorted_pts],
                'name': f"x={new_x}"
            })

    return lines, x_offset_map

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H3("Parallel layout Settings (in meters)"),
    html.Div([
        html.Label("Blue line distance (bays):"),
        dcc.RadioItems(
            id='blue-distance-slider',
            options=[
                {'label': ' 39 bays (13 groups) ', 'value': 39},
                {'label': ' 43 bays (12 groups) ', 'value': 43},
                {'label': ' 47 bays (11 groups) ', 'value': 47},
            ],
            value=43,
            inline=True,
            style={'marginTop': '10px'}
        ),
    ], style={'width': '50%', 'marginBottom': '20px'}),

    html.Div(id='blue-distance-display', style={'marginBottom': '10px'}),

    dcc.Graph(id='paths-graph')
])

@app.callback(
    [Output('paths-graph', 'figure'),
     Output('blue-distance-display', 'children')],
    Input('blue-distance-slider', 'value')
)
def update_graph(num_bays):
    fig = go.Figure()

    # Fixed orange lines at 92m (12 rows layout)
    orange_points = data.get('orange', [])
    by_y = defaultdict(list)
    for p in orange_points:
        by_y[p['y']].append(p)

    y_values = sorted(by_y.keys())
    if len(y_values) >= 8:
        orig_group_starts = [y_values[0], y_values[4], y_values[8], y_values[12],
                            y_values[16], y_values[20], y_values[24], y_values[28]]
        offset = 0  # Fixed at 92m
        new_y_positions = [
            orig_group_starts[0],
            orig_group_starts[1] + offset,
            orig_group_starts[2] + offset * 2,
            orig_group_starts[3] + offset * 3,
            orig_group_starts[4] - offset * 3,
            orig_group_starts[5] - offset * 2,
            orig_group_starts[6] - offset,
            orig_group_starts[7],
        ]
        y_offset_map = {}
        for i, orig_y in enumerate(orig_group_starts):
            for row in range(4):
                y_offset_map[orig_y + row * U_TO_M] = new_y_positions[i] + row * U_TO_M
    else:
        y_offset_map = {y: y for y in y_values}

    # Draw orange lines
    for y, pts in by_y.items():
        if len(pts) >= 2:
            new_y = y_offset_map.get(y, y)
            sorted_pts = sorted(pts, key=lambda p: p['x'])
            fig.add_trace(go.Scatter(
                x=[p['x'] for p in sorted_pts],
                y=[new_y] * len(sorted_pts),
                mode='lines',
                line=dict(color='orange', width=0.5),
                hoverinfo='skip',
                showlegend=False
            ))

    # Add orange markers
    marker_x = []
    marker_y = []
    for p in orange_points:
        new_y = y_offset_map.get(p['y'], p['y'])
        marker_x.append(p['x'])
        marker_y.append(new_y)

    fig.add_trace(go.Scatter(
        x=marker_x,
        y=marker_y,
        mode='markers',
        name=f"Orange ({len(orange_points)})",
        marker=dict(size=1, color='orange'),
        hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
        customdata=[[p['id']] for p in orange_points]
    ))

    # Draw blue lines with adjusted distance
    blue_lines, x_offset_map = get_blue_vertical_data('blue', num_bays)

    for line in blue_lines:
        fig.add_trace(go.Scatter(
            x=line['x'],
            y=line['y'],
            mode='lines',
            line=dict(color='blue', width=0.5),
            hoverinfo='skip',
            showlegend=False
        ))

    # Add blue markers with adjusted positions
    blue_points = data.get('blue', [])
    marker_x = []
    marker_y = []
    for p in blue_points:
        new_x = x_offset_map.get(p['x'], p['x'])
        marker_x.append(new_x)
        marker_y.append(p['y'])

    fig.add_trace(go.Scatter(
        x=marker_x,
        y=marker_y,
        mode='markers',
        name=f"Blue ({len(blue_points)})",
        marker=dict(size=1, color='blue'),
        hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
        customdata=[[p['id']] for p in blue_points]
    ))

    # Draw other lines (static)
    for ct in ['purple_horizontal', 'green', 'blue', 'vertical_purple']:
        points_list = data.get(ct, [])
        if not points_list:
            continue

        by_coord = defaultdict(list)
        for p in points_list:
            if ct in ['purple_horizontal', 'green']:
                by_coord[p['y']].append(p)
            else:  # blue, vertical_purple - vertical lines
                by_coord[p['x']].append(p)

        # Draw lines
        for _, pts in by_coord.items():
            if len(pts) >= 2:
                if ct in ['purple_horizontal', 'green']:
                    sorted_pts = sorted(pts, key=lambda p: p['x'])
                    fig.add_trace(go.Scatter(
                        x=[p['x'] for p in sorted_pts],
                        y=[p['y'] for p in sorted_pts],
                        mode='lines',
                        line=dict(color=colors[ct], width=0.5),
                        hoverinfo='skip',
                        showlegend=False
                    ))
                else:  # blue, vertical_purple - vertical
                    sorted_pts = sorted(pts, key=lambda p: p['y'])
                    fig.add_trace(go.Scatter(
                        x=[p['x'] for p in sorted_pts],
                        y=[p['y'] for p in sorted_pts],
                        mode='lines',
                        line=dict(color=colors[ct], width=0.5),
                        hoverinfo='skip',
                        showlegend=False
                    ))

        # Add markers
        fig.add_trace(go.Scatter(
            x=[p['x'] for p in points_list],
            y=[p['y'] for p in points_list],
            mode='markers',
            name=f"{display_names[ct]} ({len(points_list)})",
            marker=dict(size=1, color=colors[ct]),
            hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
            customdata=[[p['id']] for p in points_list]
        ))

    # Calculate number of groups
    n_groups = 51 - num_bays

    # Layout (ranges in meters)
    fig.update_layout(
        title=f'Traffic Network Paths (blue distance={num_bays}bays, {n_groups} groups)',
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        yaxis=dict(autorange='reversed', range=[0, 1200], scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-200, 4000], scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        width=1575,
        height=600
    )

    display_text = f"Current blue distance: {num_bays} bays ({num_bays * U_TO_M}m), {n_groups} groups (Orange fixed at 92m)"

    return fig, display_text

if __name__ == '__main__':
    print("Starting Dash server...")
    print("Open http://127.0.0.1:8050 in your browser")
    app.run(debug=True, port=8050)
