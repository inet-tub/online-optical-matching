import numpy as np
import pandas as pd
import json
import random
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.colors as colors
import time
import pickle
import sys


traces=["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib"]

tracefiles={}
tracefiles["HPC-Mocfe"]="hpc_cesar_mocfe.csv"
tracefiles["HPC-Nekbone"]="hpc_cesar_nekbone.csv"
tracefiles["HPC-Boxlib"]="hpc_exact_boxlib_multigrid_c_large.csv"

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

trace = str(sys.argv[1])
alpha = int(sys.argv[2])
maxRequests = int(sys.argv[3])
numNodes = int(sys.argv[4])

alpha = alpha*numNodes

df = pd.read_csv("data/"+tracefiles[trace])
data = df[(df['srcip'] < numNodes) & (df['dstip'] < numNodes)]
src_set = set(data["srcip"])
dst_set = set(data["dstip"])
nodes_set = np.arange(max(len(src_set),len(dst_set)))
numNodes = len(nodes_set)


offlineAlgTrackingGraph = initializeTrackingGraph(len(nodes_set))
offlineAlgMatching = list()
prevTime = 0
t = 0
cost = 0

# Construct the offline algorithm
for t, request in data.iterrows():
    src = request["srcip"]
    dst = request["dstip"]
    offlineAlgTrackingGraph = incrementEdgeWeight(offlineAlgTrackingGraph, src,dst)
    # Find the maximum weight maximal matching
    foundMax, matchingWeight, matchingOFF = matching_with_weight_sum(offlineAlgTrackingGraph, alpha/3, True)
    # Remove the maximal matching
    tempGraph = offlineAlgTrackingGraph.copy()
    for (u,v) in matchingOFF:
        tempGraph[u][v]['weight']=0
    
    edge_weights = nx.get_edge_attributes(tempGraph, "weight")
    if np.sum(list(edge_weights.values())) >= alpha/3:
        offlineAlgMatching.append((matchingOFF, prevTime))
        prevTime = t
        offlineAlgTrackingGraph = initializeTrackingGraph(len(nodes_set))

    # Early exit based on maxRequests
    if t >= maxRequests:
    	if (len(offlineAlgMatching) == 0):
    		offlineAlgMatching.append((matchingOFF, prevTime))
    	break
    # print("Constructing OFF timeslot =",t, " for alpha = ", alpha)

with open('offline/offline-matching-'+str(trace)+'-'+str(alpha)+'.pkl','wb') as f:
    pickle.dump(offlineAlgMatching, f)
    print("dump", alpha, trace)