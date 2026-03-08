import json
from collections import defaultdict
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output

# Unit conversion: 1U = 4 meters
U_TO_M = 4

def load_data(layout_type):
    """Load and convert data based on layout type"""
    filename = f'layout_{layout_type}.json'
    with open(filename, 'r', encoding='utf-8') as f:
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
    return data

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

def get_vertical_data(ct, distance=92):
    """Get vertical line data with adjustable distance (in meters)"""
    # Check if data is loaded (for perpendicular layout)
    try:
        points_list = data.get(ct, [])
    except NameError:
        return [], []

    if not points_list:
        return [], []

    # Determine number of groups based on distance
    # 92m: 36 groups (original)
    # 86m: 38 groups (36 + 2 new)
    # 80m: 41 groups (36 + 5 new)
    if distance == 80:
        num_groups = 41
    elif distance == 86:
        num_groups = 38
    else:  # 92
        num_groups = 36

    # Group by x
    by_x = defaultdict(list)
    for p in points_list:
        by_x[p['x']].append(p)

    # Get unique x values sorted
    x_values = sorted(by_x.keys())

    # Calculate new x positions
    # First group stays fixed, all other groups adjust relative to it
    # Original distance between adjacent group edges: 23U = 92m
    # Adjustable distance in meters
    if len(x_values) >= 8:
        # Calculate offsets (distance - 92 meters, original group edge spacing)
        original_spacing = 23 * U_TO_M  # 23U = 92m
        offset = distance - original_spacing

        # Create x offset mapping
        # Group 0: fixed (offset=0)
        # Group i: offset = i * (distance - original_spacing)
        x_offset_map = {}
        for i in range(len(x_values) // 4):
            orig_group_start = x_values[i * 4]
            new_group_start = orig_group_start + i * offset
            for col in range(4):
                orig = orig_group_start + col * 4
                new = new_group_start + col * 4
                x_offset_map[orig] = new
    else:
        x_offset_map = {x: x for x in x_values}

    # Build line data from original groups
    lines = []
    markers = []
    for x, pts in by_x.items():
        if len(pts) >= 2:
            new_x = x_offset_map.get(x, x)
            sorted_pts = sorted(pts, key=lambda p: p['y'])
            lines.append({
                'x': [new_x] * len(sorted_pts),
                'y': [p['y'] for p in sorted_pts],
            })
            # Add markers with adjusted x
            for p in pts:
                markers.append({
                    'x': x_offset_map.get(p['x'], p['x']),
                    'y': p['y'],
                    'id': p['id']
                })

    # Add extra groups if needed (beyond original 36)
    if num_groups > 36:
        extra_groups = num_groups - 36

        # Get the last original group's last point x position (col 3)
        # x_values[-1] is the last x value (rightmost column of last group)
        last_point_x = x_offset_map.get(x_values[-1], x_values[-1])

        # Get y values from the first column (same pattern for all columns)
        first_x = x_values[0]
        first_col_ys = sorted([p['y'] for p in by_x[first_x]])

        # Generate new groups
        # Group 37 (first extra): starts at last_point_x + distance
        # Group 38 (second extra): starts at last_point_x + 2*distance
        for g in range(extra_groups):
            # New group x position: last group last point + distance
            # The first point (col 0) of new group is at: last_point_x + distance + g * distance
            new_group_x = last_point_x + distance + g * distance

            # Create 4 columns for this group at same y positions
            for col in range(4):
                new_x = new_group_x + col * 4

                # Add markers at each y position
                for y in first_col_ys:
                    # Create unique id for new points
                    new_id = f"extra_{g}_{col}_{y}"
                    markers.append({
                        'x': new_x,
                        'y': y,
                        'id': new_id
                    })

                # Add line for this column
                lines.append({
                    'x': [new_x] * len(first_col_ys),
                    'y': first_col_ys,
                })

    return lines, markers

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H3("Perpendicular layout Settings (in meters)"),
    html.Div([
        html.Label("Blue distance between groups (m):"),
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

# Load initial data
data = load_data('perpendicular')

@app.callback(
    [Output('paths-graph', 'figure'),
     Output('distance-display', 'children')],
    Input('distance-slider', 'value')
)
def update_graph(distance):
    fig = go.Figure()

    # Draw purple_horizontal (static)
    for ct in ['purple_horizontal', 'green']:
        points_list = data.get(ct, [])
        if not points_list:
            continue

        by_coord = defaultdict(list)
        for p in points_list:
            by_coord[p['y']].append(p)

        for _, pts in by_coord.items():
            if len(pts) >= 2:
                sorted_pts = sorted(pts, key=lambda p: p['x'])
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

    # Draw blue with adjustable distance
    blue_lines, blue_markers = get_vertical_data('blue', distance)

    for line in blue_lines:
        fig.add_trace(go.Scatter(
            x=line['x'],
            y=line['y'],
            mode='lines',
            line=dict(color='blue', width=0.5),
            hoverinfo='skip',
            showlegend=False
        ))

    # Add blue markers
    if blue_markers:
        fig.add_trace(go.Scatter(
            x=[m['x'] for m in blue_markers],
            y=[m['y'] for m in blue_markers],
            mode='markers',
            name=f"Blue ({len(blue_markers)})",
            marker=dict(size=1, color='blue'),
            hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
            customdata=[[m['id']] for m in blue_markers]
        ))

    # Layout
    fig.update_layout(
        title=f'Perpendicular layout Settings (distance={distance}m)',
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        yaxis=dict(autorange='reversed', range=[0, 1200], scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-200, 4000], scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        width=1575,
        height=600
    )

    display_text = f"Current blue distance: {distance}m (Leftmost group fixed, all other groups adjust)"

    return fig, display_text

if __name__ == '__main__':
    print("Starting Dash server...")
    print("Open http://127.0.0.1:8050 in your browser")
    app.run(debug=True, port=8050)
