import json
import os
from collections import defaultdict
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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


def load_data(layout_type, source='disp'):
    """Load layout data from JSON file.

    Args:
        layout_type: 'parallel', 'parallel_8', 'parallel_9', 'parallel_10',
                     'perpendicular_34', 'perpendicular_35', 'perpendicular_36'
        source: 'path' for data\path\*.json, 'disp' for data\path_disp\*_disp.json
    """
    if source == 'path':
        filename = os.path.join(BASE_DIR, f'data\\path\\layout_{layout_type}.json')
    else:
        filename = os.path.join(BASE_DIR, f'data\\path_disp\\layout_{layout_type}_disp.json')

    with open(filename, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    data = {}
    for color_type, points in raw_data.items():
        data[color_type] = [
            {
                'id': p['id'],
                'x': round(p['x'], 2),
                'y': round(p['y'], 2),
                'region': p['region'],
                'kind': p['kind'],
                'color_type': p['color_type']
            }
            for p in points
        ]
    return data


# ============== Load Data ==============
# Display layout data (from path_disp)
data_parallel_disp = load_data('parallel', 'disp')
data_parallel_8_disp = load_data('parallel_8', 'disp')
data_parallel_9_disp = load_data('parallel_9', 'disp')
data_parallel_10_disp = load_data('parallel_10', 'disp')
data_perpendicular_34_disp = load_data('perpendicular_34', 'disp')
data_perpendicular_35_disp = load_data('perpendicular_35', 'disp')
data_perpendicular_36_disp = load_data('perpendicular_36', 'disp')

# Path layout data (from path)
data_parallel_path = load_data('parallel', 'path')
data_parallel_8_path = load_data('parallel_8', 'path')
data_parallel_9_path = load_data('parallel_9', 'path')
data_parallel_10_path = load_data('parallel_10', 'path')
data_perpendicular_34_path = load_data('perpendicular_34', 'path')
data_perpendicular_35_path = load_data('perpendicular_35', 'path')
data_perpendicular_36_path = load_data('perpendicular_36', 'path')

# Map block count to data (disp - current default)
perp_data_map = {
    '140': data_perpendicular_34_disp,
    '144': data_perpendicular_35_disp,
    '148': data_perpendicular_36_disp
}

parallel_data_map = {
    '126': data_parallel_8_disp,
    '140': data_parallel_9_disp,
    '154': data_parallel_disp
}

# Path version maps
perp_data_map_path = {
    '140': data_perpendicular_34_path,
    '144': data_perpendicular_35_path,
    '148': data_perpendicular_36_path
}

parallel_data_map_path = {
    '126': data_parallel_8_path,
    '140': data_parallel_9_path,
    '154': data_parallel_path
}


# ============== Create Dash app ==============
requests_pathname_prefix = os.environ.get('DASH_PATH_PREFIX', '/')
app = Dash(__name__, suppress_callback_exceptions=True, requests_pathname_prefix=requests_pathname_prefix)
server = app.server


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
            {'label': '1. Parallel Layout (Path)', 'value': 'parallel_path'},
            {'label': '2. Perpendicular Layout (Path)', 'value': 'perpendicular_path'},
            {'label': '3. Parallel Layout (Display)', 'value': 'parallel_disp'},
            {'label': '4. Perpendicular Layout (Display)', 'value': 'perpendicular_disp'},
            {'label': '5. Parallel Layout (CP)', 'value': 'parallel_cp'},
            {'label': '6. Perpendicular Layout (CP)', 'value': 'perpendicular_cp'},
            {'label': '7. Parallel Layout (Routing)', 'value': 'parallel_routing'},
            {'label': '8. Perpendicular Layout (Routing)', 'value': 'perpendicular_routing'},
        ],
        value='parallel_disp',
        clearable=False,
        style={'width': '400px'}
    ),
], style={'marginBottom': '20px', 'display': 'flex', 'alignItems': 'center'})


app.layout = html.Div([
    html.H3("Layout Settings (in U, 1U = 4m)"),

    layout_dropdown,

    # Block selectors (always in DOM, visibility toggled by callback)
    html.Div([
        html.Label("Number of Blocks:", style={'fontSize': '14px', 'marginRight': '10px'}),
        html.Div([
            dcc.RadioItems(
                id='parallel-blocks-selector',
                options=[
                    {'label': '126', 'value': '126'},
                    {'label': '140', 'value': '140'},
                    {'label': '154', 'value': '154'},
                ],
                value='154',
                inline=True,
            ),
        ], id='parallel-blocks-container', style={'display': 'inline-block'}),
        html.Div([
            dcc.RadioItems(
                id='blocks-selector',
                options=[
                    {'label': '140', 'value': '140'},
                    {'label': '144', 'value': '144'},
                    {'label': '148', 'value': '148'},
                ],
                value='132',
                inline=True,
            ),
        ], id='perp-blocks-container', style={'display': 'none'}),
    ], style={'marginBottom': '15px', 'display': 'flex', 'alignItems': 'center'}),

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
])


@app.callback(
    Output('page-content', 'children'),
    Output('parallel-blocks-container', 'style'),
    Output('perp-blocks-container', 'style'),
    Input('layout-selector', 'value')
)
def display_page(layout):
    # Show/hide block selectors based on layout type
    show_parallel_blocks = 'parallel' in layout
    show_perp_blocks = 'perpendicular' in layout

    # Determine which graph to show
    if 'perpendicular' in layout:
        return (
            html.Div([dcc.Graph(id='perpendicular-paths-graph')]),
            {'display': 'none'} if not show_parallel_blocks else {'display': 'inline-block'},
            {'display': 'inline-block'} if show_perp_blocks else {'display': 'none'},
        )
    else:
        return (
            html.Div([dcc.Graph(id='parallel-paths-graph')]),
            {'display': 'inline-block'} if show_parallel_blocks else {'display': 'none'},
            {'display': 'none'} if not show_perp_blocks else {'display': 'inline-block'},
        )


def create_parallel_figure(blocks, data_map=None):
    """Create a parallel layout figure for the given block count."""
    fig = go.Figure()

    if data_map is None:
        data_map = parallel_data_map
    parallel_data = data_map.get(blocks, data_map.get('154'))

    # Draw all color types from parallel layout as-is
    for ct in ['orange', 'purple_horizontal', 'green', 'blue', 'vertical_purple']:
        points_list = parallel_data.get(ct, [])
        if not points_list:
            continue

        if ct in ['orange', 'purple_horizontal', 'green']:
            # Horizontal lines - group by y
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
        else:
            # Vertical lines - group by x
            by_coord = defaultdict(list)
            for p in points_list:
                by_coord[p['x']].append(p)

            for _, pts in by_coord.items():
                if len(pts) >= 2:
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
            hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.2f}U<br>Y: %{y:.2f}U<extra></extra>',
            customdata=[[p['id']] for p in points_list]
        ))

    fig.update_layout(
        title=f'Parallel Layout ({blocks} Blocks)',
        xaxis_title='X (U)',
        yaxis_title='Y (U)',
        yaxis=dict(autorange='reversed', range=[0, 250], scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-50, 1000], scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        width=1575,
        height=600
    )

    return fig


@app.callback(
    Output('parallel-paths-graph', 'figure'),
    Input('layout-selector', 'value'),
    Input('parallel-blocks-selector', 'value')
)
def update_parallel_graph(layout, blocks):
    # Select data map based on layout variant
    if layout == 'parallel_path':
        data_map = parallel_data_map_path
    elif layout == 'parallel_cp':
        # CP not implemented yet, use path as placeholder
        data_map = parallel_data_map_path
    elif layout == 'parallel_routing':
        # Routing not implemented yet, use path as placeholder
        data_map = parallel_data_map_path
    else:  # parallel_disp
        data_map = parallel_data_map

    return create_parallel_figure(blocks, data_map)


def create_perpendicular_figure(blocks, data_map=None):
    """Create a perpendicular layout figure for the given block count."""
    fig = go.Figure()

    if data_map is None:
        data_map = perp_data_map
    perp_data = data_map.get(blocks, data_map.get('140'))

    # Draw all color types from perpendicular layout as-is
    for ct in ['purple_horizontal', 'green', 'blue', 'vertical_purple']:
        points_list = perp_data.get(ct, [])
        if not points_list:
            continue

        if ct in ['purple_horizontal', 'green']:
            # Horizontal lines - group by y
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
        else:
            # Vertical lines - group by x
            by_coord = defaultdict(list)
            for p in points_list:
                by_coord[p['x']].append(p)

            for _, pts in by_coord.items():
                if len(pts) >= 2:
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
            hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.2f}U<br>Y: %{y:.2f}U<extra></extra>',
            customdata=[[p['id']] for p in points_list]
        ))

    fig.update_layout(
        title=f'Perpendicular Layout ({blocks} Blocks)',
        xaxis_title='X (U)',
        yaxis_title='Y (U)',
        yaxis=dict(autorange='reversed', range=[0, 250], scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-50, 1000], scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
        width=1575,
        height=600
    )

    return fig


@app.callback(
    Output('perpendicular-paths-graph', 'figure'),
    Input('layout-selector', 'value'),
    Input('blocks-selector', 'value')
)
def update_perpendicular_graph(layout, blocks):
    # Select data map based on layout variant
    if layout == 'perpendicular_path':
        data_map = perp_data_map_path
    elif layout == 'perpendicular_cp':
        # CP not implemented yet, use path as placeholder
        data_map = perp_data_map_path
    elif layout == 'perpendicular_routing':
        # Routing not implemented yet, use path as placeholder
        data_map = perp_data_map_path
    else:  # perpendicular_disp
        data_map = perp_data_map

    return create_perpendicular_figure(blocks, data_map)


# Download callback
@app.callback(
    Output('download-image', 'data'),
    Input('download-btn', 'n_clicks'),
    State('layout-selector', 'value'),
    State('blocks-selector', 'value'),
    State('parallel-blocks-selector', 'value'),
    State('resolution-dropdown', 'value'),
    prevent_initial_call=True,
)
def download_image(n_clicks, layout, blocks, parallel_blocks, resolution):
    """Download the current figure as PNG with selected resolution"""
    if not n_clicks:
        return None

    # Regenerate the figure based on current layout and blocks
    if 'perpendicular' in layout:
        # Select data map
        if layout == 'perpendicular_path':
            data_map = perp_data_map_path
        elif layout == 'perpendicular_cp':
            data_map = perp_data_map_path
        elif layout == 'perpendicular_routing':
            data_map = perp_data_map_path
        else:  # perpendicular_disp
            data_map = perp_data_map
        fig = create_perpendicular_figure(blocks or '140', data_map)
    else:
        # Select data map
        if layout == 'parallel_path':
            data_map = parallel_data_map_path
        elif layout == 'parallel_cp':
            data_map = parallel_data_map_path
        elif layout == 'parallel_routing':
            data_map = parallel_data_map_path
        else:  # parallel_disp
            data_map = parallel_data_map
        fig = create_parallel_figure(parallel_blocks or '154', data_map)

    # Calculate dimensions (aspect ratio: 1575:600 = 2.625:1)
    width = int(resolution)
    height = int(width * 600 / 1575)

    # Generate PNG
    import traceback
    try:
        img_bytes = fig.to_image(format='png', width=width, height=height, scale=2)
    except Exception as e:
        print(f"to_image error: {e}")
        traceback.print_exc()
        # Fallback: try without scale
        try:
            img_bytes = fig.to_image(format='png', width=width, height=height)
        except Exception as e2:
            print(f"to_image fallback error: {e2}")
            traceback.print_exc()
            raise Exception(f"Image export failed: {e2}")

    current_blocks = blocks if layout == 'perpendicular' else parallel_blocks
    filename = f'layout_{layout}_{current_blocks}blocks_{width}x{height}.png'
    return dcc.send_bytes(img_bytes, filename)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    print("Starting Dash server...")
    print(f"Open http://127.0.0.1:{port}/ to view layouts")
    app.run(debug=False, host='0.0.0.0', port=port)
