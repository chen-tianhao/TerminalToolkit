import json
import plotly.graph_objects as go

# Read data
with open('layout_parallel.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Color type mapping with display colors
color_types = [
    'purple_horizontal',
    'vertical_purple',
    'grey',
    'vertical_grey',
    'orange',
    'green',
    'blue'
]

display_names = {
    'purple_horizontal': 'Purple Horizontal',
    'vertical_purple': 'Vertical Purple',
    'grey': 'Grey',
    'vertical_grey': 'Vertical Grey',
    'orange': 'Orange',
    'green': 'Green',
    'blue': 'Blue'
}

colors = {
    'purple_horizontal': 'purple',
    'vertical_purple': 'darkviolet',
    'grey': 'gray',
    'vertical_grey': 'dimgray',
    'orange': 'orange',
    'green': 'green',
    'blue': 'blue'
}

# Create figure
fig = go.Figure()

for ct in color_types:
    points_list = data.get(ct, [])
    if not points_list:
        continue

    fig.add_trace(go.Scatter(
        x=[p['x'] for p in points_list],
        y=[p['y'] for p in points_list],
        mode='markers',
        name=f"{display_names[ct]} ({len(points_list)})",
        marker=dict(size=3, color=colors[ct], opacity=0.8),
        hovertemplate=
        '<b>ID</b>: %{customdata[0]}<br>' +
        '<b>X</b>: %{x}<br>' +
        '<b>Y</b>: %{y}<br>' +
        '<b>Kind</b>: %{customdata[1]}<br>' +
        '<b>Color Type</b>: ' + ct + '<extra></extra>',
        customdata=[[p['id'], p['kind']] for p in points_list]
    ))

# Layout (Y axis reversed: down is positive, equal aspect ratio)
fig.update_layout(
    title='Traffic Network Endpoints (layout_parallel.json)',
    xaxis_title='X',
    yaxis_title='Y',
    yaxis=dict(autorange='reversed', scaleanchor='x', scaleratio=1),  # Down is positive Y
    xaxis=dict(scaleanchor='y', scaleratio=1),
    hovermode='closest',
    showlegend=True,
    width=1400,
    height=900
)

# Save to HTML (interactive)
fig.write_html('endpoints.html')
print("Saved to endpoints.html (interactive)")

# Also save as static SVG
fig.write_image('endpoints.svg', width=1400, height=900)
print("Saved to endpoints.svg (static)")
