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

def get_horizontal_data(ct, distance=92):
    """Get horizontal line data with adjustable distance (in meters)"""
    points_list = data.get(ct, [])
    if not points_list:
        return []

    # Group by y
    by_y = defaultdict(list)
    for p in points_list:
        by_y[p['y']].append(p)

    # Get unique y values sorted
    y_values = sorted(by_y.keys())

    # Calculate new y positions
    # Group 1 stays at original position, Group 8 stays at original position
    # Groups 2,3,4 move down, groups 5,6,7 move up
    # Original distance between groups: 23U = 92m
    # Adjustable distance in meters
    if len(y_values) >= 8:
        # Original y positions for groups (4 rows each) in meters
        orig_group_starts = [
            y_values[0],   # Group 1 start
            y_values[4],   # Group 2 start
            y_values[8],   # Group 3 start
            y_values[12],  # Group 4 start
            y_values[16],  # Group 5 start
            y_values[20],  # Group 6 start
            y_values[24],  # Group 7 start
            y_values[28],  # Group 8 start
        ]

        # Calculate offsets (distance - 92 meters)
        offset = distance - 92

        new_y_positions = [
            orig_group_starts[0],                           # Group 1: fixed
            orig_group_starts[1] + offset,                  # Group 2: down
            orig_group_starts[2] + offset * 2,             # Group 3: down more
            orig_group_starts[3] + offset * 3,             # Group 4: down most
            orig_group_starts[4] - offset * 3,             # Group 5: up most
            orig_group_starts[5] - offset * 2,             # Group 6: up more
            orig_group_starts[6] - offset,                 # Group 7: up
            orig_group_starts[7],                           # Group 8: fixed
        ]

        # Create y offset mapping
        y_offset_map = {}
        for i, orig_y in enumerate(orig_group_starts):
            for row in range(4):
                orig = orig_y + row * U_TO_M
                new = new_y_positions[i] + row * U_TO_M
                y_offset_map[orig] = new
    else:
        y_offset_map = {y: y for y in y_values}

    # Build line data
    lines = []
    for y, pts in by_y.items():
        if len(pts) >= 2:
            new_y = y_offset_map.get(y, y)
            sorted_pts = sorted(pts, key=lambda p: p['x'])
            lines.append({
                'x': [p['x'] for p in sorted_pts],
                'y': [new_y] * len(sorted_pts),
                'name': f"y={new_y}"
            })

    return lines

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H3("Parallel layout Settings (in meters)"),
    html.Div([
        html.Label("Distance between groups (m):"),
        dcc.RadioItems(
            id='distance-slider',
            options=[
                {'label': ' 80m ', 'value': 80},
                {'label': ' 86m ', 'value': 86},
                {'label': ' 92m ', 'value': 92},
            ],
            value=92,
            inline=True,
            style={'marginTop': '10px'}
        ),
    ], style={'width': '50%', 'marginBottom': '20px'}),

    html.Div(id='distance-display', style={'marginBottom': '10px'}),

    dcc.Graph(id='paths-graph')
])

@app.callback(
    [Output('paths-graph', 'figure'),
     Output('distance-display', 'children')],
    Input('distance-slider', 'value')
)
def update_graph(distance):
    fig = go.Figure()

    # Draw orange lines with adjusted distance
    orange_lines = get_horizontal_data('orange', distance)

    for line in orange_lines:
        fig.add_trace(go.Scatter(
            x=line['x'],
            y=line['y'],
            mode='lines',
            line=dict(color='orange', width=0.5),
            hoverinfo='skip',
            showlegend=False
        ))

    # Add orange markers
    orange_points = data.get('orange', [])
    by_y = defaultdict(list)
    for p in orange_points:
        by_y[p['y']].append(p)

    y_values = sorted(by_y.keys())
    if len(y_values) >= 8:
        orig_group_starts = [y_values[0], y_values[4], y_values[8], y_values[12],
                            y_values[16], y_values[20], y_values[24], y_values[28]]
        offset = distance - 92
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
        for coord, pts in by_coord.items():
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
                else:  # blue - vertical
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

    # Layout (ranges in meters)
    fig.update_layout(
        title=f'Traffic Network Paths (distance={distance}m)',
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        yaxis=dict(autorange='reversed', range=[0, 1200], scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-200, 4000], scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        width=1575,
        height=600
    )

    display_text = f"Current distance: {distance}m (Group 1 and 8 fixed, Groups 2-4 move down, Groups 5-7 move up)"

    return fig, display_text

if __name__ == '__main__':
    print("Starting Dash server...")
    print("Open http://127.0.0.1:8050 in your browser")
    app.run(debug=True, port=8050)
