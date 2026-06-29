import networkx as nx


def preprocess_graph(G, seed_nodes, root_node):
    # Step 1: Remove self-loops
    G.remove_edges_from(nx.selfloop_edges(G))

    # Step 2: Remove edges leading to the root and nodes not descendants of the root
    descendants = nx.descendants(G, root_node)
    descendants.add(root_node)
    nodes_to_remove = [node for node in G.nodes if node not in descendants and node not in seed_nodes]
    G.remove_nodes_from(nodes_to_remove)

    # Step 3: Remove nodes with zero in-degree or out-degree iteratively
    nodes_to_check = set(G.nodes) - set(seed_nodes)
    while nodes_to_check:
        zero_degree_nodes = {node for node in nodes_to_check if (G.in_degree(node) == 0 or G.out_degree(node) == 0)}
        if not zero_degree_nodes:
            break
        G.remove_nodes_from(zero_degree_nodes)
        nodes_to_check = set(G.nodes) - set(seed_nodes)

    return G


# Compute Agony Score
def compute_agony(G):
    try:
        hierarchy = {node: i for i, node in enumerate(nx.topological_sort(G))}
    except nx.NetworkXUnfeasible:
        # Return empty dict if G is not a DAG
        hierarchy = {}
    agony_dict = {}
    for u, v in G.edges():
        agony = max(0, hierarchy.get(u, 0) - hierarchy.get(v, 0) + 1)
        agony_dict[(u, v)] = agony
    return agony_dict


# Cycle removal
def remove_cycles(G):
    while True:
        try:
            hierarchy = list(nx.topological_sort(G))
            break
        except nx.NetworkXUnfeasible:
            # Find and remove one edge from each cycle
            cycles = list(nx.simple_cycles(G))
            if not cycles:
                break
            for cycle in cycles:
                u, v = cycle[0], cycle[1]
                G.remove_edge(u, v)
                break  # Remove only one edge per iteration

    # Now, with no cycles, compute the backward edges and remove them
    agony_dict = compute_agony(G)
    hierarchy = {node: i for i, node in enumerate(nx.topological_sort(G))}
    backward_edges = [(u, v) for u, v in G.edges if hierarchy[u] >= hierarchy[v]]
    for edge in backward_edges:
        G.remove_edge(*edge)

    return G


def remove_redundant_relations(G):
    edges_to_remove = []
    for u, v in G.edges():
        if G.out_degree(u) > 1 and G.in_degree(v) > 1:
            # Find other paths using BFS or DFS
            try:
                paths = list(nx.all_simple_paths(G, source=u, target=v, cutoff=5))
                if len(paths) > 1:
                    edges_to_remove.append((u, v))
            except nx.NetworkXNoPath:
                continue

    G.remove_edges_from(edges_to_remove)
    return G
