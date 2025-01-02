import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template, request
import folium
import networkx as nx

# Create necessary directories for templates and static files
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

# Create the directed graph from connections
def create_directed_graph(connections):
    graph = {}
    for start, end, capacity in connections:
        if start not in graph:
            graph[start] = {}
        if end not in graph:
            graph[end] = {}
        graph[start][end] = capacity
        graph[end][start] = capacity  # Add reverse capacity
    return graph

# Ford-Fulkerson algorithm for calculating maximum flow
def ford_fulkerson(graph, source, sink):
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

    # Initialize residual graph
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
            residual[v][u] += path_flow  # Add flow to reverse edge
            v = parent[v]

    return max_flow, flow, paths

# Main route to handle form submission and display results
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        source = request.form.get("source_city")
        destination = request.form.get("destination_city")

        # Ensure that the selected source is a valid mine and destination is an industrial city
        if source not in mines:
            return "Invalid source city selected. Please select a mine as the source city."
        if destination not in industrial_cities:
            return "Invalid destination city selected. Please select an industrial city."

        # Create the graph and calculate the Ford-Fulkerson flow
        graph = create_directed_graph(connections)
        max_flow, flow_dict, paths = ford_fulkerson(graph, source, destination)

        message = f"Maximum flow from {source} to {destination}: {max_flow} units\n\nPaths used:\n"
        message += "\n".join([" -> ".join(path) for path in paths])

        # Create map with flow visualization
        map = folium.Map(location=[31.5, -6.5], zoom_start=6)

        for city, coord in city_coordinates.items():
            folium.Marker(coord, popup=city).add_to(map)

        colors = ['red', 'blue', 'green', 'purple', 'orange']
        
        # Draw connections between cities on the map
        for start, end, _ in connections:
            if start in city_coordinates and end in city_coordinates:
                folium.PolyLine([city_coordinates[start], city_coordinates[end]], color="grey", weight=2).add_to(map)

        # Highlight paths used with flow visualization
        for i, path in enumerate(paths):
            color = colors[i % len(colors)]
            for j in range(len(path) - 1):
                start, end = path[j], path[j + 1]
                if start in city_coordinates and end in city_coordinates:
                    flow_value = flow_dict[start][end]
                    folium.PolyLine([city_coordinates[start], city_coordinates[end]], color=color, weight=2 + (flow_value / 50), popup=f"Flow: {flow_value}").add_to(map)

        # Save map
        map.save("templates/map.html")

        # Generate graph image using NetworkX
        G = nx.DiGraph(graph)
        plt.figure(figsize=(14, 10))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=3000, font_size=10, font_weight='bold', edge_color='gray', arrows=True)

        # Add edge labels to graph
        edge_labels = {}
        for start in flow_dict:
            for end in flow_dict[start]:
                if flow_dict[start][end] > 0:
                    edge_labels[(start, end)] = f"{flow_dict[start][end]}/{graph[start][end]}"

        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

        # Highlight paths used with different colors
        for i, path in enumerate(paths):
            color = colors[i % len(colors)]
            path_edges = list(zip(path[:-1], path[1:]))
            nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color=color, width=3, arrows=True)

        # Save graph image
        plt.savefig("static/graph.png", bbox_inches='tight', dpi=300)
        plt.close()

        return render_template("result.html", message=message, graph_image_path="graph.png")

    return render_template("index.html", cities=list(city_coordinates.keys()), connections=connections, mines=mines, industrial_cities=industrial_cities)

if __name__ == "__main__":
    app.run(debug=True)
