import networkx as nx
import matplotlib.pyplot as plt

# Create an undirected graph
G = nx.Graph()

# Add nodes (hosts and switches)
G.add_nodes_from(['h1', 'h2', 'h3', 'h4'], type='host')
G.add_nodes_from(['s1', 's2'], type='switch')

# Add edges with bandwidth attributes
G.add_edge('h1', 's1', bw=10)
G.add_edge('h2', 's1', bw=10)
G.add_edge('h3', 's2', bw=10)
G.add_edge('h4', 's2', bw=10)
G.add_edge('s1', 's2', bw=20)

# Define positions for visualization (manual layout to mimic Mininet topology)
pos = {
    's1': (0, 1),
    's2': (2, 1),
    'h1': (-1, 2),
    'h2': (-1, 0),
    'h3': (3, 2),
    'h4': (3, 0)
}

# Differentiate nodes by type for visualization
node_colors = ['lightblue' if G.nodes[n]['type'] == 'host' else 'lightgreen' for n in G.nodes]

# Draw the graph
plt.figure(figsize=(8, 6))
nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=1000, font_size=12, font_weight='bold')

# Draw edge labels for bandwidth
edge_labels = nx.get_edge_attributes(G, 'bw')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

# Add title and display
plt.title("NetworkX Representation of Mininet Topology")
plt.show()
