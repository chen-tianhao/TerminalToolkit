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


def load_data(layout_type):
    """Load layout data from JSON file"""
    filename = os.path.join(BASE_DIR, f'layout_{layout_type}_disp.json')
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
data_parallel = load_data('parallel')
data_parallel_8 = load_data('parallel_8')
data_parallel_9 = load_data('parallel_9')
data_perpendicular_34 = load_data('perpendicular_34')
data_perpendicular_35 = load_data('perpendicular_35')
data_perpendicular_36 = load_data('perpendicular_36')

# Map block count to data
perp_data_map = {
    '140': data_perpendicular_34,
    '144': data_perpendicular_35,
    '148': data_perpendicular_36
}

parallel_data_map = {
    '126': data_parallel_8,
    '140': data_parallel_9,
    '154': data_parallel
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
            {'label': 'Parallel Layout', 'value': 'parallel'},
            {'label': 'Perpendicular Layout', 'value': 'perpendicular'},
        ],
        value='parallel',
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
    if layout == 'perpendicular':
        return (
            html.Div([dcc.Graph(id='perpendicular-paths-graph')]),
            {'display': 'none'},
            {'display': 'inline-block'},
        )
    else:
        return (
            html.Div([dcc.Graph(id='parallel-paths-graph')]),
            {'display': 'inline-block'},
            {'display': 'none'},
        )


def create_parallel_figure(blocks):
    """Create a parallel layout figure for the given block count."""
    fig = go.Figure()

    parallel_data = parallel_data_map.get(blocks, data_parallel)

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
def update_parallel_graph(_layout, blocks):
    return create_parallel_figure(blocks)


def create_perpendicular_figure(blocks):
    """Create a perpendicular layout figure for the given block count."""
    fig = go.Figure()

    perp_data = perp_data_map.get(blocks, data_perpendicular_34)

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
def update_perpendicular_graph(_layout, blocks):
    return create_perpendicular_figure(blocks)


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
    if layout == 'perpendicular':
        fig = create_perpendicular_figure(blocks or '132')
    else:
        fig = create_parallel_figure(parallel_blocks or '154')

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
