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

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H3("Perpendicular layout Settings (in meters)"),
    dcc.Graph(id='paths-graph')
])

@app.callback(
    Output('paths-graph', 'figure'),
    Input('paths-graph', 'id')
)
def update_graph(_):
    fig = go.Figure()

    # Draw all lines (static, no adjustment)
    for ct in ['orange', 'purple_horizontal', 'green', 'blue']:
        points_list = data.get(ct, [])
        if not points_list:
            continue

        if ct in ['orange', 'purple_horizontal', 'green']:
            # Horizontal lines - group by y
            by_coord = defaultdict(list)
            for p in points_list:
                by_coord[p['y']].append(p)

            # Draw lines
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
            # Blue - vertical lines, group by x
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
            hovertemplate='<b>%{customdata[0]}</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>',
            customdata=[[p['id']] for p in points_list]
        ))

    # Layout
    fig.update_layout(
        title='Perpendicular layout Settings (layout_perpendicular.json)',
        xaxis_title='X (m)',
        yaxis_title='Y (m)',
        yaxis=dict(autorange='reversed', range=[0, 1200], scaleanchor='x', scaleratio=1),
        xaxis=dict(range=[-200, 4000], scaleanchor='y', scaleratio=1),
        hovermode='closest',
        showlegend=True,
        width=1575,
        height=600
    )

    return fig

if __name__ == '__main__':
    print("Starting Dash server...")
    print("Open http://127.0.0.1:8050 in your browser")
    app.run(debug=True, port=8050)
