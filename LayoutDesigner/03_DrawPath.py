import json
from collections import defaultdict
import plotly.graph_objects as go

# Read data
with open('temp_1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Group points for horizontal lines (orange, green, purple_horizontal)
horizontal_types = ['orange', 'green', 'purple_horizontal']
# Group points for vertical lines (vertical_purple, blue)
vertical_types = ['vertical_purple', 'blue']

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

# Create figure
fig = go.Figure()

# Process horizontal lines (connect points with same y)
for ct in horizontal_types:
    points_list = data.get(ct, [])
    if not points_list:
        continue

    # Group by y
    by_y = defaultdict(list)
    for p in points_list:
        by_y[p['y']].append(p)

    # Draw lines for each y
    for y, pts in by_y.items():
        if len(pts) >= 2:
            # Sort by x
            sorted_pts = sorted(pts, key=lambda p: p['x'])
            fig.add_trace(go.Scatter(
                x=[p['x'] for p in sorted_pts],
                y=[p['y'] for p in sorted_pts],
                mode='lines',
                name=f"{display_names[ct]} (y={y})",
                line=dict(color=colors[ct], width=0.5),
                hoverinfo='skip',
                showlegend=False
            ))

    # Also add markers at endpoints
    fig.add_trace(go.Scatter(
        x=[p['x'] for p in points_list],
        y=[p['y'] for p in points_list],
        mode='markers',
        name=f"{display_names[ct]} ({len(points_list)})",
        marker=dict(size=1, color=colors[ct]),
        hovertemplate=
        '<b>ID</b>: %{customdata[0]}<br>' +
        '<b>X</b>: %{x}<br>' +
        '<b>Y</b>: %{y}<br>' +
        '<b>Color Type</b>: ' + ct + '<extra></extra>',
        customdata=[[p['id']] for p in points_list]
    ))

# Process vertical lines (connect points with same x)
for ct in vertical_types:
    points_list = data.get(ct, [])
    if not points_list:
        continue

    # Group by x
    by_x = defaultdict(list)
    for p in points_list:
        by_x[p['x']].append(p)

    # Draw lines for each x
    for x, pts in by_x.items():
        if len(pts) >= 2:
            # Sort by y
            sorted_pts = sorted(pts, key=lambda p: p['y'])
            fig.add_trace(go.Scatter(
                x=[p['x'] for p in sorted_pts],
                y=[p['y'] for p in sorted_pts],
                mode='lines',
                name=f"{display_names[ct]} (x={x})",
                line=dict(color=colors[ct], width=0.5),
                hoverinfo='skip',
                showlegend=False
            ))

    # Also add markers at endpoints
    fig.add_trace(go.Scatter(
        x=[p['x'] for p in points_list],
        y=[p['y'] for p in points_list],
        mode='markers',
        name=f"{display_names[ct]} ({len(points_list)})",
        marker=dict(size=1, color=colors[ct]),
        hovertemplate=
        '<b>ID</b>: %{customdata[0]}<br>' +
        '<b>X</b>: %{x}<br>' +
        '<b>Y</b>: %{y}<br>' +
        '<b>Color Type</b>: ' + ct + '<extra></extra>',
        customdata=[[p['id']] for p in points_list]
    ))

# Layout
fig.update_layout(
    title='Traffic Network Paths (temp_1.json)',
    xaxis_title='X',
    yaxis_title='Y',
    yaxis=dict(autorange='reversed', range=[0, 300], scaleanchor='x', scaleratio=1),
    xaxis=dict(range=[-50, 1000], scaleanchor='y', scaleratio=1),
    hovermode='closest',
    showlegend=True,
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='right',
        x=0.5
    ),
    width=1575,
    height=600
)

# Save to HTML
fig.write_html('paths.html')
print("Saved to paths.html")
