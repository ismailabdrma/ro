import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template, request
import folium
import networkx as nx



app = Flask(__name__)

# List of Moroccan cities with their coordinates
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
    "Laayoune": (27.1483, -13.1995),
    "Nador": (35.1682, -2.9335),
    "Errachidia": (31.9314, -4.4239),
    "Ouarzazate": (30.9335, -6.937),
    "Guelmim": (28.987, -10.0572),
    "Essaouira": (31.506327, -9.754354),
    "Jorf Lasfar": (33.1069, -8.6375),
    "Youssoufia": (32.2469, -8.5289),
    "Benguerir": (32.2360, -7.9506),
    "Kenitra": (34.2610, -6.5802),
    "Al Hoceima": (35.2516, -3.9372),
    "Berkane": (34.9200, -2.3200),
    "Taza": (34.2100, -4.0100),
    "Tiznit": (29.6974, -9.7300),
    "Tan Tan": (28.4378, -11.1023),
    "Boujdour": (26.1288, -14.4842),
    "Dakhla": (23.7128, -15.9370),
    "Zagora": (30.3324, -5.8384),
    "Bouarfa": (32.0732, -1.9622),
    "Figuig": (32.1089, -1.2269)

}

# Logical connections with default capacities
connections = [
   # PRIMARY PHOSPHATE NETWORK - Highest Priority Routes
    ("Khouribga", "Jorf Lasfar", 400),    # Main phosphate slurry pipeline
    ("Khouribga", "Casablanca", 350),     # Main industrial corridor
    ("Khouribga", "Safi", 300),           # Secondary export route
    ("Youssoufia", "Safi", 300),          # Direct port access
    ("Benguerir", "Safi", 280),           # Port connection
    ("Benguerir", "Marrakech", 250),      # Southern distribution
    
    # NORTHERN CORRIDOR - Atlantic Coast to Mediterranean
    ("Casablanca", "Rabat", 300),         # Major highway route
    ("Rabat", "Kenitra", 250),            # Coastal connection
    ("Kenitra", "Tangier", 200),          # Northern route
    ("Tangier", "Tetouan", 180),          # Mediterranean access
    ("Tetouan", "Al Hoceima", 150),       # Rif mountains route
    ("Al Hoceima", "Nador", 150),         # Eastern coast
    ("Nador", "Oujda", 180),              # Eastern connection
    
    # CENTRAL NETWORK - Interior Connections
    ("Casablanca", "El Jadida", 250),     # Southern coastal
    ("El Jadida", "Jorf Lasfar", 200),    # Industrial zone
    ("Jorf Lasfar", "Safi", 200),         # Coastal industry
    ("Safi", "Essaouira", 180),           # Coastal route
    ("Essaouira", "Agadir", 200),         # Major coastal
    
    # INTERIOR ROUTES - Cross-Country Connections
    ("Khouribga", "Beni Mellal", 200),   # Interior access
    ("Beni Mellal", "Fes", 180),          # Atlas route
    ("Fes", "Meknes", 200),               # Imperial connection
    ("Meknes", "Rabat", 180),             # Northern interior
    ("Marrakech", "Beni Mellal", 170),    # Atlas crossing
    
    # EASTERN NETWORK
    ("Fes", "Taza", 150),                 # Eastern corridor
    ("Taza", "Oujda", 160),               # Eastern connection
    ("Oujda", "Berkane", 140),            # Agricultural zone
    
    # SOUTHERN ROUTES
    ("Marrakech", "Agadir", 220),         # Major southern
    ("Agadir", "Tiznit", 150),            # Southern coastal
    ("Tiznit", "Guelmim", 130),           # Pre-saharan
    ("Guelmim", "Tan Tan", 100),          # Southern access
    ("Tan Tan", "Laayoune", 120),         # Sahara route
    ("Laayoune", "Boujdour", 90),         # Deep south
    ("Boujdour", "Dakhla", 80),           # Southern terminal
    
    # ATLAS AND DESERT CONNECTIONS
    ("Marrakech", "Ouarzazate", 150),     # Atlas crossing
    ("Ouarzazate", "Errachidia", 130),    # Desert route
    ("Ouarzazate", "Zagora", 120),        # Southern oasis
    ("Errachidia", "Bouarfa", 110),       # Eastern desert
    ("Bouarfa", "Figuig", 100),           # Eastern oasis
    ("Bouarfa", "Oujda", 130),      # Atlas mountains route
]

# Create a graph with the connections
city_graph = nx.Graph()
for start, end, capacity in connections:
    city_graph.add_edge(start, end, capacity=capacity)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        # Get source and destination from form
        source = request.form.get("source_city")
        destination = request.form.get("destination_city")
        use_default = request.form.get("use_default") == "yes"

        # Update capacities if user opts for manual input
        if not use_default:
            for start, end, _ in connections:
                user_capacity = request.form.get(f"capacity_{start}_{end}")
                if user_capacity:
                    city_graph[start][end]["capacity"] = int(user_capacity)

        # Find the optimal path
        try:
            path = nx.shortest_path(city_graph, source=source, target=destination, weight="capacity")
            total_capacity = sum(city_graph[path[i]][path[i + 1]]['capacity'] for i in range(len(path) - 1))
            message = f"Optimal path from {source} to {destination}: {' -> '.join(path)} with total capacity of {total_capacity} units."
        except nx.NetworkXNoPath:
            path = None
            message = f"No path exists between {source} and {destination}."

        # Generate the map with Folium
        pipeline_map = folium.Map(location=[31.5, -6.5], zoom_start=6)

        # Add city markers on the map
        for city, coord in city_coordinates.items():
            folium.Marker(coord, popup=city).add_to(pipeline_map)

        # Add all connections in grey
        for start, end, _ in connections:
            start_coord = city_coordinates[start]
            end_coord = city_coordinates[end]
            folium.PolyLine([start_coord, end_coord], color="grey", weight=2.5).add_to(pipeline_map)

        # Highlight the optimal path in red
        if path:
            for i in range(len(path) - 1):
                start_coord = city_coordinates[path[i]]
                end_coord = city_coordinates[path[i + 1]]
                folium.PolyLine([start_coord, end_coord], color="red", weight=5).add_to(pipeline_map)

        # Save the map as an HTML file (this will be displayed inline)
        map_html = "templates/map.html"
        pipeline_map.save(map_html)

        # Generate the graph image (Matplotlib)
        graph_image_path = "static/graph.png"
        plt.figure(figsize=(14, 10))
        pos = nx.spring_layout(city_graph)
        nx.draw(city_graph, pos, with_labels=True, node_color='skyblue', node_size=3000, font_size=10, font_weight='bold', edge_color='gray')

        # Highlight the optimal path on the graph
        if path:
            path_edges = list(zip(path, path[1:]))
            nx.draw_networkx_edges(city_graph, pos, edgelist=path_edges, edge_color='red', width=3)

        # Annotate the edges with their capacities
        edge_labels = nx.get_edge_attributes(city_graph, 'capacity')
        nx.draw_networkx_edge_labels(city_graph, pos, edge_labels=edge_labels, font_size=8)

        # Save the graph image
        plt.savefig(graph_image_path)
        plt.close()

        return render_template("result.html", message=message, map_html=map_html, graph_image_path=graph_image_path)

    return render_template("index.html", cities=list(city_coordinates.keys()), connections=connections)

@app.route("/map")
def display_map():
    return render_template("map.html")

if __name__ == "__main__":
    app.run(debug=True)
