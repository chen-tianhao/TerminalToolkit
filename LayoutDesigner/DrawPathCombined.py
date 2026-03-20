import json
import os
from collections import defaultdict
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, callback, State
import io

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Unit conversion: 1U = 4 meters
U_TO_M = 4

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

# ============== Bay Layout Constants ==============
# Blue line classification (in meters after U->m conversion)
BLUE_Y_LONG = {88.0, 916.0}
BLUE_Y_SHORT = {112.0, 892.0}

# Distance options -> number of blue-line groups
DISTANCE_TO_GROUPS = {
    298.75: 13,   # 39 bays – one more group than 324m
    324.0:  12,   # 43 bays – original layout
    349.25: 11,   # 47 bays – one fewer group than 324m
}

def load_data(layout_type):
    """Load and convert data based on layout type"""
    filename = os.path.join(BASE_DIR, f'layout_{layout_type}.json')
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


# ============== Bay Layout Functions ==============
def _get_orig_blue_long_group_starts(data):
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


ORIG_BLUE_GROUP_STARTS = None  # Will be initialized after data loading


def compute_blue_group_starts(distance):
    """Compute blue-line group start x-positions for the chosen distance.

    * 324m  → 12 groups, **original** positions from JSON (matches 04)
    * 298.75m → 13 groups, first & last fixed, middle groups evenly distributed
    * 349.25m → 11 groups, first & last fixed, middle groups evenly distributed
    """
    global ORIG_BLUE_GROUP_STARTS
    if ORIG_BLUE_GROUP_STARTS is None:
        ORIG_BLUE_GROUP_STARTS = _get_orig_blue_long_group_starts(data_parallel)

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


# ============== Parallel Layout Functions ==============
def get_horizontal_data(data, ct, distance=92):
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

    return lines, y_offset_map


# ============== Perpendicular Layout Functions ==============
def get_vertical_data(data, ct, distance=92):
    """Get vertical line data with adjustable distance (in meters)"""
    points_list = data.get(ct, [])

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

        # Each group has 4 columns, spacing 1U = 4m between columns
        # Group width = 3 * 4m = 12m (from column 0 to column 3)
        group_width = 12

        # Get y values from the first column (same pattern for all columns)
        first_x = x_values[0]
        first_col_ys = sorted([p['y'] for p in by_x[first_x]])

        # Generate new groups
        # Group 37: starts at last_point_x + distance
        # Group 38: starts at (last_point_x + distance + group_width) + distance = last_point_x + 2*distance + group_width
        for g in range(extra_groups):
            # New group x position: last group last point + group_width + distance for each previous extra group
            new_group_x = last_point_x + distance + g * (distance + group_width)

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


# ============== Load Data ==============
data_parallel = load_data('parallel')
data_perpendicular = load_data('perpendicular')


# ============== Create Dash app ==============
# Support URL path prefix for reverse proxy
requests_pathname_prefix = os.environ.get('DASH_PATH_PREFIX', '/')
app = Dash(__name__, suppress_callback_exceptions=True, requests_pathname_prefix=requests_pathname_prefix)
server = app.server  # For gunicorn

# Layout selector dropdown
layout_dropdown = html.Div([
    html.Label("Select Layout: ", style={
        'fontSize': '16px',
        'fontWeight': 'bold',
        'marginRight': '10px'
    }),
    dcc.Dropdown(
        id='layout-selector',
        options=[
            {'label': 'Parallel Layout (Row Adjustable)', 'value': 'parallel'},
            {'label': 'Parallel Layout (Bay Adjustable)', 'value': 'bay'},
            {'label': 'Perpendicular Layout', 'value': 'perpendicular'},
        ],
        value='parallel',
        clearable=False,
        style={'width': '400px'}
    ),
], style={'marginBottom': '20px', 'display': 'flex', 'alignItems': 'center'})

app.layout = html.Div([
    html.H3("Layout Settings (in meters)"),

    layout_dropdown,

    # Sliders for all layouts (visible based on current page)
    html.Div([
        html.Div([
            html.Label("Distance between orange path groups (total blocks / number of rows):"),
            dcc.RadioItems(
                id='parallel-distance-slider',
                options=[
                    {'label': ' 80m (176 blks/ 10 rows) ', 'value': 80},
                    {'label': ' 86m (154 blks/ 11 rows) ', 'value': 86},
                    {'label': ' 92m (154 blks / 12 rows) ', 'value': 92},
                ],
                value=92,
                inline=True,
                style={'marginTop': '10px'}
            ),
        ], id='parallel-slider-container', style={'width': '50%', 'marginBottom': '20px', 'display': 'block'}),

        html.Div([
            html.Label("Distance between blue path groups (total blocks / 12 rows):"),
            dcc.RadioItems(
                id='bay-distance-slider',
                options=[
                    {'label': ' 298.75m (168 blks) ', 'value': 298.75},
                    {'label': ' 324m (154 blks) ',    'value': 324.0},
                    {'label': ' 349.25m (140 blks) ', 'value': 349.25},
                ],
                value=324.0,
                inline=True,
                style={'marginTop': '10px'}
            ),
        ], id='bay-slider-container', style={'width': '33%', 'marginBottom': '20px', 'display': 'block'}),

        html.Div([
            html.Label("Distance between blue path groups (total blocks / number of rows):"),
            dcc.RadioItems(
                id='perpendicular-distance-slider',
                options=[
                    {'label': ' 80m ( / 10 rows) ', 'value': 80},
                    {'label': ' 86m ( / 11 rows) ', 'value': 86},
                    {'label': ' 92m ( / 12 rows) ', 'value': 92},
                ],
                value=92,
                inline=True,
                style={'marginTop': '10px'}
            ),
        ], id='perpendicular-slider-container', style={'width': '33%', 'marginBottom': '20px', 'display': 'block'}),
    ], style={'display': 'flex'}),

    # Download controls
    html.Div([
        html.H4("Download Settings"),
        html.Div([
            html.Label("Resolution (width x height, aspect ratio locked):"),
            dcc.Dropdown(
                id='resolution-dropdown',
                options=[
                    {'label': '800 x 306', 'value': '800'},
                    {'label': '1200 x 459', 'value': '1200'},
                    {'label': '1600 x 612', 'value': '1600'},
                    {'label': '2000 x 765', 'value': '2000'},
                    {'label': '2400 x 918', 'value': '2400'},
                    {'label': '3200 x 1224', 'value': '3200'},
                    {'label': '4000 x 1531', 'value': '4000'},
                    {'label': '4800 x 1834', 'value': '4800'},
                    {'label': '5600 x 2139', 'value': '5600'},
                    {'label': '6400 x 2446', 'value': '6400'},
                    {'label': '7200 x 2750', 'value': '7200'},
                    {'label': '8000 x 3057', 'value': '8000'},
                    {'label': '8800 x 3363', 'value': '8800'},
                    {'label': '9600 x 3669', 'value': '9600'},
                    {'label': '10752 x 4096', 'value': '10752'},
                ],
                value='1600',
                clearable=False,
                style={'width': '150px', 'display': 'inline-block', 'verticalAlign': 'middle'}
            ),
            html.Button('Download PNG', id='download-btn', n_clicks=0,
                       style={'marginLeft': '15px', 'padding': '8px 16px', 'fontSize': '14px'}),
        ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
        dcc.Download(id='download-image'),
    ]),

    html.Div(id='page-content'),

    # Store for current figure data
    dcc.Store(id='current-figure-store', data=None),
])


@app.callback(
    Output('page-content', 'children'),
    Input('layout-selector', 'value')
)
def display_page(layout):
    if layout == 'perpendicular':
        return render_perpendicular()
    elif layout == 'bay':
        return render_bay()
    else:
        return render_parallel()


# Callback to store current figure data
@app.callback(
    Output('current-figure-store', 'data'),
    Input('layout-selector', 'value'),
    Input('parallel-distance-slider', 'value'),
    Input('bay-distance-slider', 'value'),
    Input('perpendicular-distance-slider', 'value'),
)
def store_current_figure(layout, parallel_dist, bay_dist, perp_dist):
    """Generate and store the current figure for download"""
    if layout == 'perpendicular':
        fig = update_perpendicular_graph(perp_dist)
    elif layout == 'bay':
        fig = update_bay_graph(bay_dist)
    else:
        fig = update_parallel_graph(parallel_dist)

    # Return figure as dict (Dash can serialize it)
    return fig.to_dict()


# Callback to show/hide sliders based on selected layout
@app.callback(
    Output('parallel-slider-container', 'style'),
    Output('bay-slider-container', 'style'),
    Output('perpendicular-slider-container', 'style'),
    Input('layout-selector', 'value')
)
def update_slider_visibility(layout):
    if layout == 'perpendicular':
        return (
            {'display': 'none'},
            {'display': 'none'},
            {'width': '33%', 'marginBottom': '20px', 'display': 'block'}
        )
    elif layout == 'bay':
        return (
            {'display': 'none'},
            {'width': '33%', 'marginBottom': '20px', 'display': 'block'},
            {'display': 'none'}
        )
    else:
        return (
            {'width': '33%', 'marginBottom': '20px', 'display': 'block'},
            {'display': 'none'},
            {'display': 'none'}
        )


def render_parallel():
    return html.Div([
        dcc.Graph(id='parallel-paths-graph')
    ])


def render_bay():
    return html.Div([
        dcc.Graph(id='bay-paths-graph')
    ])


def render_perpendicular():
    return html.Div([
        dcc.Graph(id='perpendicular-paths-graph')
    ])


# Parallel layout callbacks
@app.callback(
    Output('parallel-paths-graph', 'figure'),
    Input('parallel-distance-slider', 'value')
)
def update_parallel_graph(distance):
    fig = go.Figure()

    # Draw orange lines with adjusted distance
    orange_lines, y_offset_map = get_horizontal_data(data_parallel, 'orange', distance)

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
    orange_points = data_parallel.get('orange', [])

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
        points_list = data_parallel.get(ct, [])
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

    # Layout (ranges in meters)
    fig.update_layout(
        title=f'Parallel Layout (distance={distance}m)',
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        yaxis=dict(autorange='reversed', range=[0, 1200], scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-200, 4000], scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        width=1575,
        height=600
    )

    return fig


# ============== Bay layout callbacks ==============
@app.callback(
    Output('bay-paths-graph', 'figure'),
    Input('bay-distance-slider', 'value')
)
def update_bay_graph(distance):
    fig = go.Figure()
    n_groups = DISTANCE_TO_GROUPS[distance]

    # ----- Orange lines (fixed at 92m, no distance adjustment) -----
    orange_points = data_parallel.get('orange', [])
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
    blue_points = data_parallel.get('blue', [])
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
        points_list = data_parallel.get(ct, [])
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
        title=f'Parallel Layout - Bay Adjustable ({(n_groups - 1) * 14} groups)',
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

    return fig


# Perpendicular layout callbacks
@app.callback(
    Output('perpendicular-paths-graph', 'figure'),
    Input('perpendicular-distance-slider', 'value')
)
def update_perpendicular_graph(distance):
    fig = go.Figure()

    # Draw purple_horizontal (static)
    for ct in ['purple_horizontal', 'green']:
        points_list = data_perpendicular.get(ct, [])
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
    blue_lines, blue_markers = get_vertical_data(data_perpendicular, 'blue', distance)

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
        title=f'Perpendicular Layout (distance={distance}m)',
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        yaxis=dict(autorange='reversed', range=[0, 1200], scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-200, 4000], scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        width=1575,
        height=600
    )

    return fig


# Download callback
@callback(
    Output('download-image', 'data'),
    Input('download-btn', 'n_clicks'),
    Input('layout-selector', 'value'),
    Input('parallel-distance-slider', 'value'),
    Input('bay-distance-slider', 'value'),
    Input('perpendicular-distance-slider', 'value'),
    State('resolution-dropdown', 'value'),
    State('current-figure-store', 'data'),
    prevent_initial_call=True,
)
def download_image(n_clicks, layout, parallel_dist, bay_dist, perp_dist, resolution, figure_data):
    """Download the current figure as PNG with selected resolution"""
    if n_clicks is None or n_clicks == 0 or figure_data is None:
        return None

    # Get current figure
    fig = go.Figure(figure_data)

    # Calculate dimensions (aspect ratio: 1575:600 = 2.625:1 ≈ 800:306)
    width = int(resolution)
    height = int(width * 600 / 1575)

    # Generate PNG
    try:
        img_bytes = fig.to_image(format='png', width=width, height=height, scale=2)
    except Exception as e:
        # Fallback: try without scale
        img_bytes = fig.to_image(format='png', width=width, height=height)

    return dcc.send_bytes(img_bytes, f'layout_{layout}_{width}x{height}.png')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    print("Starting Dash server...")
    print(f"Open http://127.0.0.1:{port}/ to view layouts")
    app.run(debug=False, host='0.0.0.0', port=port)
