import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template, request
import folium
import networkx as nx

# Create necessary directories
Path("templates").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)

app = Flask(__name__)

# Coordinates for cities
city_coordinates = {
    "Casablanca": (33.5731, -7.5898),
    "Rabat": (34.0209, -6.8416),
    "Tangier": (35.7595, -5.8339),
    "Marrakech": (31.6295, -7.9811),
    "Fes": (34.0331, -5.0003),
    "Meknes": (33.8947, -5.5473),
    "Agadir": (30.4278, -9.5981),
    "Oujda": (34.6814, -1.9086),
    "Tetouan": (35.577, -5.3684),
    "Safi": (32.2994, -9.2372),
    "El Jadida": (33.2561, -8.5089),
    "Beni Mellal": (32.3394, -6.3498),
    "Khouribga": (32.8809, -6.9063),
    "Kenitra": (34.2610, -6.5802),
    "Jorf Lasfar": (33.1069, -8.6375),
    "Benguerir": (32.2359364, -7.953837799999974)
}

# Mines and industrial cities
mines = ["Khouribga", "El Jadida", "Benguerir"]
industrial_cities = [
    "Casablanca", "Rabat", "Tangier", "Marrakech", "Fes", "Meknes", 
    "Agadir", "Oujda", "Tetouan", "Safi", "El Jadida", "Beni Mellal", 
    "Kenitra", "Jorf Lasfar", "Benguerir"
]

# Initial connections with their capacities
connections = [
    ("Khouribga", "Casablanca", 250),
    ("Khouribga", "Rabat", 230),
    ("Khouribga", "Tangier", 300),
    ("Khouribga", "Marrakech", 400),
    ("Khouribga", "Fes", 350),
    ("Khouribga", "Agadir", 450),
    ("Benguerir", "Casablanca", 180),
    ("Benguerir", "Marrakech", 120),
    ("Benguerir", "Kenitra", 230),
    ("Jorf Lasfar", "Casablanca", 150),
    ("Jorf Lasfar", "Safi", 100),
    ("Casablanca", "Rabat", 60),
    ("Casablanca", "Tangier", 90),
    ("Casablanca", "Marrakech", 270),
    ("Casablanca", "Fes", 150),
    ("Casablanca", "Agadir", 320),
    ("Casablanca", "Oujda", 600),
    ("Casablanca", "Tetouan", 70),
    ("Casablanca", "Safi", 250),
    ("Casablanca", "El Jadida", 200),
    ("Marrakech", "Fes", 130),
    ("Marrakech", "Tetouan", 210),
    ("Agadir", "Safi", 150),
    ("Beni Mellal", "El Jadida", 180),
]

def create_directed_graph(connections):
    """Create a directed graph from connections."""
    graph = {}
    for start, end, capacity in connections:
        if start not in graph:
            graph[start] = {}
        if end not in graph:
            graph[end] = {}
        graph[start][end] = capacity
        graph[end][start] = capacity  # Add reverse capacity
    return graph

def ford_fulkerson(graph, source, sink):
    """Implement Ford-Fulkerson algorithm for maximum flow."""
    def bfs(residual_graph, s, t, parent):
        visited = {s}
        queue = [s]
        parent[s] = None
        
        while queue:
            u = queue.pop(0)
            for v in residual_graph[u]:
                if v not in visited and residual_graph[u][v] > 0:
                    queue.append(v)
                    visited.add(v)
                    parent[v] = u
                    if v == t:
                        return True
        return False

    residual = {u: {v: graph[u][v] for v in graph[u]} for u in graph}
    flow = {u: {v: 0 for v in graph[u]} for u in graph}
    max_flow = 0
    paths = []

    while bfs(residual, source, sink, parent := {}):
        path_flow = float('inf')
        s = sink
        path = [s]
        
        while s != source:
            path_flow = min(path_flow, residual[parent[s]][s])
            s = parent[s]
            path.append(s)
        
        max_flow += path_flow
        paths.append(list(reversed(path)))
        
        v = sink
        while v != source:
            u = parent[v]
            flow[u][v] += path_flow
            residual[u][v] -= path_flow
            residual[v][u] += path_flow
            v = parent[v]

    return max_flow, flow, paths

def create_land_route(start_coord, end_coord, cities_on_path):
    """Create a route that follows land by adding waypoints through cities."""
    route_points = [start_coord]
    
    # Add all intermediate city coordinates as waypoints
    for city in cities_on_path[1:-1]:  # Exclude start and end cities
        if city in city_coordinates:
            route_points.append(city_coordinates[city])
    
    route_points.append(end_coord)
    
    # For each segment, add intermediate points to curve inland
    final_route = []
    for i in range(len(route_points) - 1):
        start = route_points[i]
        end = route_points[i + 1]
        start_lat, start_lng = start
        end_lat, end_lng = end
        
        # Calculate inland curve point
        mid_lat = (start_lat + end_lat) / 2
        mid_lng = (start_lng + end_lng) / 2
        
        # Push the curve inland (east) for western routes
        if start_lng < -6 and end_lng < -6:
            mid_lng += 0.5  # Push east to avoid sea
        
        # Add extra points for smoother curves
        final_route.extend([
            start,
            (mid_lat, mid_lng),
            end
        ])
    
    return final_route

def create_flow_map(paths, flow_dict, graph, source, destination):
    """Create an improved map visualization with clear path colors and land routes."""
    map = folium.Map(location=[31.5, -6.5], zoom_start=6, tiles='CartoDB positron')
    
    # Define consistent colors for paths
    colors = ['#FF0000', '#00FF00', '#0000FF', '#FFA500', '#800080']
    
    # Create a legend for paths
    legend_html = f"""
    <div style="position: fixed; 
                bottom: 50px; 
                left: 50px; 
                z-index: 1000; 
                background-color: white;
                padding: 10px; 
                border: 2px solid grey; 
                border-radius: 5px;">
        <h4>Maximum flow from {source} to {destination}</h4>
    """
    
    # Draw paths first (so they appear under the markers)
    for i, path in enumerate(paths):
        color = colors[i % len(colors)]
        
        # Add path to legend
        legend_html += f"""
        <div style="margin-bottom: 5px;">
            <span style="color: {color};">━━━</span>
            Path {i + 1}: {' → '.join(path)}
        </div>
        """
        
        # Create the route through all cities in the path
        route = create_land_route(
            city_coordinates[path[0]],
            city_coordinates[path[-1]],
            path
        )
        
        # Calculate flow for this path
        path_flows = []
        for j in range(len(path)-1):
            if path[j] in flow_dict and path[j+1] in flow_dict[path[j]]:
                path_flows.append(flow_dict[path[j]][path[j+1]])
        flow_value = min(path_flows) if path_flows else 0
        
        # Create detailed popup
        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px;">
            <b>Path {i + 1}:</b><br>
            Route: {' → '.join(path)}<br>
            Flow: {flow_value} units
        </div>
        """
        
        # Add the path to the map
        folium.PolyLine(
            route,
            color=color,
            weight=3,
            opacity=0.8,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(map)
    
    # Add markers for cities
    for city, coord in city_coordinates.items():
        if city == source:
            icon = folium.Icon(color='red', icon='info-sign')
            popup_text = f'<b>{city}</b> (Source)'
        elif city == destination:
            icon = folium.Icon(color='green', icon='info-sign')
            popup_text = f'<b>{city}</b> (Destination)'
        elif city in mines:
            icon = folium.Icon(color='red', icon='industry', prefix='fa')
            popup_text = f'<b>{city}</b> (Mine)'
        elif city in industrial_cities:
            icon = folium.Icon(color='blue', icon='building', prefix='fa')
            popup_text = f'<b>{city}</b> (Industrial)'
        else:
            icon = folium.Icon(color='gray', icon='info-sign')
            popup_text = f'<b>{city}</b>'
        
        folium.Marker(
            coord,
            popup=popup_text,
            icon=icon,
            tooltip=city
        ).add_to(map)
    
    # Complete and add the legend
    legend_html += """
        <div style="margin-top: 10px;">
            <p>🔴 Source/Mine</p>
            <p>🟢 Destination</p>
            <p>🔵 Industrial City</p>
        </div>
    </div>
    """
    map.get_root().html.add_child(folium.Element(legend_html))
    
    return map

def create_network_graph(graph, flow_dict, paths):
    """Create an improved network visualization."""
    G = nx.DiGraph(graph)
    plt.figure(figsize=(15, 10))
    
    # Use a more visually appealing layout
    pos = nx.spring_layout(G, k=1, iterations=50)
    
    # Draw base graph
    nx.draw_networkx_nodes(G, pos,
                          node_color='lightblue',
                          node_size=3000,
                          node_shape='o',
                          edgecolors='black')
    
    nx.draw_networkx_labels(G, pos,
                           font_size=10,
                           font_weight='bold')
    
    # Draw edges with capacity information
    edge_labels = {}
    for start in flow_dict:
        for end in flow_dict[start]:
            if flow_dict[start][end] > 0:
                edge_labels[(start, end)] = f"{flow_dict[start][end]}/{graph[start][end]}"
    
    # Draw paths with different colors
    colors = ['red', 'green', 'blue', 'orange', 'purple']
    for i, path in enumerate(paths):
        path_edges = list(zip(path[:-1], path[1:]))
        nx.draw_networkx_edges(G, pos,
                             edgelist=path_edges,
                             edge_color=colors[i % len(colors)],
                             width=2,
                             alpha=0.7)
    
    nx.draw_networkx_edge_labels(G, pos,
                                edge_labels=edge_labels,
                                font_size=8)
    
    plt.title("Network Flow Graph", pad=20)
    plt.axis('off')
    return plt

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        source = request.form.get("source_city")
        destination = request.form.get("destination_city")

        if source not in mines:
            return "Invalid source city selected. Please select a mine as the source city."
        if destination not in industrial_cities:
            return "Invalid destination city selected. Please select an industrial city."

        # Create graph and calculate flow
        graph = create_directed_graph(connections)
        max_flow, flow_dict, paths = ford_fulkerson(graph, source, destination)

        # Create visualizations
        map = create_flow_map(paths, flow_dict, graph, source, destination)
        map.save("templates/map.html")

        plt = create_network_graph(graph, flow_dict, paths)
        plt.savefig("static/graph.png", bbox_inches='tight', dpi=300)
        plt.close()

        return render_template(
            "result.html",
            source=source,
            destination=destination,
            map=map._repr_html_(),
            graph_image_path="graph.png",
            max_flow=max_flow,
            paths=paths
        )

    return render_template(
        "index.html",
        cities=list(city_coordinates.keys()),
        connections=connections,
        mines=mines,
        industrial_cities=industrial_cities
    )

if __name__ == "__main__":
    app.run(debug=True)