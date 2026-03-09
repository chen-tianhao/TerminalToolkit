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

# ---------------------------------------------------------------------------
# Blue line classification (in meters after U->m conversion)
#   "蓝色线" = long blue lines with y=88 / y=916  (length 828m)
#   "短蓝线" = short blue lines with y=112 / y=892 (length 780m, 4 lines)
# ---------------------------------------------------------------------------
BLUE_Y_LONG = {88.0, 916.0}
BLUE_Y_SHORT = {112.0, 892.0}

# Distance options -> number of blue-line groups
DISTANCE_TO_GROUPS = {
    298.75: 13,   # 39 bays – one more group than 324m
    324.0:  12,   # 43 bays – original layout
    349.25: 11,   # 47 bays – one fewer group than 324m
}


def _get_orig_blue_long_group_starts():
    """Return the original group-start x positions (meters) for the 12 long
    blue-line groups, extracted from the JSON data."""
    blue_points = data.get('blue', [])
    long_blue_xs = sorted({p['x'] for p in blue_points if p['y'] in BLUE_Y_LONG})

    # Cluster consecutive x values (within-group gap = U_TO_M = 4m)
    group_starts = []
    i = 0
    while i < len(long_blue_xs):
        group_starts.append(long_blue_xs[i])
        # skip remaining members of this group
        while (i + 1 < len(long_blue_xs)
               and long_blue_xs[i + 1] - long_blue_xs[i] <= U_TO_M):
            i += 1
        i += 1
    return group_starts


ORIG_BLUE_GROUP_STARTS = _get_orig_blue_long_group_starts()   # 12 values


def compute_blue_group_starts(distance):
    """Compute blue-line group start x-positions for the chosen distance.

    * 324m  → 12 groups, **original** positions from JSON (matches 04)
    * 298.75m → 13 groups, first & last fixed, middle groups evenly distributed
    * 349.25m → 11 groups, first & last fixed, middle groups evenly distributed
    """
    n_groups = DISTANCE_TO_GROUPS[distance]

    if distance == 324.0:
        # Keep original 12-group positions exactly (hint 1)
        return list(ORIG_BLUE_GROUP_STARTS)

    first = ORIG_BLUE_GROUP_STARTS[0]       # 0 m
    last  = ORIG_BLUE_GROUP_STARTS[-1]      # 3688 m
    total_span = last - first               # 3688 m

    starts = []
    for i in range(n_groups):
        if i == 0:
            starts.append(first)
        elif i == n_groups - 1:
            starts.append(last)
        else:
            starts.append(first + i * total_span / (n_groups - 1))
    return starts


# =====================  Dash App  =====================
app = Dash(__name__)

app.layout = html.Div([
    html.H3("Parallel layout Settings (in meters)"),
    html.Div([
        html.Label("Blue line distance (m):"),
        dcc.RadioItems(
            id='blue-distance-radio',
            options=[
                {'label': ' 298.75m (13 groups) ', 'value': 298.75},
                {'label': ' 324m (12 groups) ',    'value': 324.0},
                {'label': ' 349.25m (11 groups) ', 'value': 349.25},
            ],
            value=324.0,
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
    Input('blue-distance-radio', 'value')
)
def update_graph(distance):
    fig = go.Figure()
    n_groups = DISTANCE_TO_GROUPS[distance]

    # ----- Orange lines (fixed at 92m, no distance adjustment) -----
    orange_points = data.get('orange', [])
    by_y = defaultdict(list)
    for p in orange_points:
        by_y[p['y']].append(p)

    for y, pts in by_y.items():
        if len(pts) >= 2:
            sorted_pts = sorted(pts, key=lambda p: p['x'])
            fig.add_trace(go.Scatter(
                x=[p['x'] for p in sorted_pts],
                y=[y] * len(sorted_pts),
                mode='lines',
                line=dict(color='orange', width=0.5),
                hoverinfo='skip',
                showlegend=False
            ))

    fig.add_trace(go.Scatter(
        x=[p['x'] for p in orange_points],
        y=[p['y'] for p in orange_points],
        mode='markers',
        name=f"Orange ({len(orange_points)})",
        marker=dict(size=1, color='orange'),
        hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
        customdata=[[p['id']] for p in orange_points]
    ))

    # ----- Blue long lines (Y=88↔916, adjusted by distance) -----
    group_starts = compute_blue_group_starts(distance)

    # batch all long-blue lines into one trace (using None separators)
    bl_xs, bl_ys = [], []
    blue_marker_x, blue_marker_y = [], []
    for gs in group_starts:
        for col in range(4):
            x = gs + col * U_TO_M
            bl_xs.extend([x, x, None])
            bl_ys.extend([88.0, 916.0, None])
            blue_marker_x.extend([x, x])
            blue_marker_y.extend([88.0, 916.0])

    fig.add_trace(go.Scatter(
        x=bl_xs, y=bl_ys,
        mode='lines',
        line=dict(color='blue', width=0.5),
        hoverinfo='skip',
        showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=blue_marker_x,
        y=blue_marker_y,
        mode='markers',
        name=f"Blue long ({len(blue_marker_x)})",
        marker=dict(size=1, color='blue'),
        hovertemplate='X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
    ))

    # ----- Blue short lines (Y=112↔892, always fixed) -----
    blue_points = data.get('blue', [])
    short_blue = [p for p in blue_points if p['y'] in BLUE_Y_SHORT]

    if short_blue:
        sb_xs, sb_ys = [], []
        by_x = defaultdict(list)
        for p in short_blue:
            by_x[p['x']].append(p)
        for x_val in sorted(by_x):
            pts = by_x[x_val]
            if len(pts) >= 2:
                sorted_pts = sorted(pts, key=lambda p: p['y'])
                sb_xs.extend([sp['x'] for sp in sorted_pts] + [None])
                sb_ys.extend([sp['y'] for sp in sorted_pts] + [None])

        fig.add_trace(go.Scatter(
            x=sb_xs, y=sb_ys,
            mode='lines',
            line=dict(color='blue', width=0.5),
            hoverinfo='skip',
            showlegend=False
        ))

        fig.add_trace(go.Scatter(
            x=[p['x'] for p in short_blue],
            y=[p['y'] for p in short_blue],
            mode='markers',
            name=f"Blue short ({len(short_blue)})",
            marker=dict(size=1, color='blue'),
            hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
            customdata=[[p['id']] for p in short_blue]
        ))

    # ----- Other static lines (purple, green, vertical purple) -----
    # NOTE: 'blue' is NOT in this list – it is handled above
    for ct in ['purple_horizontal', 'green', 'vertical_purple']:
        points_list = data.get(ct, [])
        if not points_list:
            continue

        by_coord = defaultdict(list)
        for p in points_list:
            if ct in ['purple_horizontal', 'green']:
                by_coord[p['y']].append(p)
            else:   # vertical_purple
                by_coord[p['x']].append(p)

        for _, pts in by_coord.items():
            if len(pts) >= 2:
                if ct in ['purple_horizontal', 'green']:
                    sorted_pts = sorted(pts, key=lambda p: p['x'])
                else:
                    sorted_pts = sorted(pts, key=lambda p: p['y'])
                fig.add_trace(go.Scatter(
                    x=[p['x'] for p in sorted_pts],
                    y=[p['y'] for p in sorted_pts],
                    mode='lines',
                    line=dict(color=colors[ct], width=0.5),
                    hoverinfo='skip',
                    showlegend=False
                ))

        fig.add_trace(go.Scatter(
            x=[p['x'] for p in points_list],
            y=[p['y'] for p in points_list],
            mode='markers',
            name=f"{display_names[ct]} ({len(points_list)})",
            marker=dict(size=1, color=colors[ct]),
            hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
            customdata=[[p['id']] for p in points_list]
        ))

    # ----- Layout -----
    fig.update_layout(
        title=f'Traffic Network Paths (blue distance={distance}m, {n_groups} groups)',
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        yaxis=dict(autorange='reversed', range=[0, 1200],
                   scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-200, 4000],
                   scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        width=1575,
        height=600
    )

    display_text = (f"Current blue distance: {distance}m, "
                    f"{n_groups} groups (Orange fixed at 92m)")

    return fig, display_text


if __name__ == '__main__':
    print("Starting Dash server...")
    print("Open http://127.0.0.1:8050 in your browser")
    app.run(debug=True, port=8050)
