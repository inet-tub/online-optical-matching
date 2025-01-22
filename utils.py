def matching_with_weight_sum(graph, alpha, maxCardinality):
    matchings = nx.algorithms.matching.max_weight_matching(graph, maxcardinality=maxCardinality, weight='weight')
    total_weight = sum(graph[u][v]['weight'] for u, v in matchings)
    return total_weight >= alpha, total_weight, matchings

def initializeTrackingGraph(numNodes):
    G = nx.complete_graph(numNodes)
    nx.set_edge_attributes(G, 0, "weight")
    return G

def initializeMatching(numNodes, offset):
    if numNodes % 2 != 0:
        exit("Error: Number of nodes must be even")

    G = nx.Graph()
    G.add_nodes_from(range(0,numNodes))
    for i in range(numNodes):
        if i%2 == 0:
            G.add_edge(i,(i+1+offset)%numNodes)
    return G

def incrementEdgeWeight(G, u, v):
    if G.has_edge(u, v):
        G[u][v]['weight'] = G[u][v]['weight'] + 1
    else:
        G.add_edge(u, v, weight=1)
    return G

def decrementEdgeWeight(G, u, v):
    if G.has_edge(u, v):
        G[u][v]['weight'] = min([G[u][v]['weight'] - 1, 0])
    else:
        G.add_edge(u, v, weight=1)
    return G

def divideEdgeWeights (G, divisor):
    for u, v in G.edges:
        if G.has_edge(u, v):
            G[u][v]['weight'] = G[u][v]['weight'] / divisor
        else:
            G.add_edge(u, v, weight=1)
    return G
