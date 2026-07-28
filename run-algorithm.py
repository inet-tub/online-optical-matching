import numpy as np
import pandas as pd
import json
import random
import networkx as nx
import time
from filelock import FileLock
import sys
import pickle
from scipy.optimize import linear_sum_assignment
#%%

traces=["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib", "HPC-Combined", "pFabric"]

tracefiles = {
    "HPC-Mocfe": "hpc_cesar_mocfe-orig.csv",
    "HPC-Nekbone": "hpc_cesar_nekbone-orig.csv",
    "HPC-Boxlib": "hpc_exact_boxlib_multigrid_c_large-orig.csv",
    "HPC-Combined": "hpc_combined.csv",
    "pFabric": "pfabric01.csv",
}

trace = str(sys.argv[1])
alpha = int(sys.argv[2])
maxRequests = int(sys.argv[3])
numNodes = int(sys.argv[4])
error = int(sys.argv[5])
outfile = str(sys.argv[6])
alg = str(sys.argv[7])
lock = FileLock(outfile+".lock")
compress = int(sys.argv[8])
freq = int(sys.argv[9])

alpha = alpha

#%%
def process_part(part):
    grouped = part.groupby(['srcip', 'dstip']).size().reset_index(name='count')
    return grouped

df = pd.read_csv("data/"+tracefiles[trace])
data = df[(df["srcip"] < numNodes) & (df["dstip"] < numNodes)].reset_index(drop=True)
if len(data) == 0:
    raise RuntimeError(f"{trace}: no rows left after filtering with numNodes={numNodes}")
# data = df[(df['srcip'] < numNodes) & (df['dstip'] < numNodes)]
# src_set = set(data["srcip"])
# dst_set = set(data["dstip"])
# nodes_set = np.arange(max(len(src_set),len(dst_set)))
max_id = int(max(int(data["srcip"].max()), int(data["dstip"].max())))
num_nodes_filter = numNodes
numNodes = max_id + 1

#%%
def matching_from_weight_matrix(weight_matrix, alpha):
    n = weight_matrix.shape[0]
    C = -weight_matrix.astype(float, copy=True)
    np.fill_diagonal(C, np.inf)
    row, col = linear_sum_assignment(C)
    M = [(i, j) for i, j in zip(row, col) if i < j]
    w = sum(weight_matrix[u][v] for u, v in M)
    return w >= alpha, w, M

def matching_with_weight_sum(graph, alpha, maxCardinality):
    # matchings = nx.algorithms.matching.max_weight_matching(graph, maxcardinality=maxCardinality, weight='weight')
    # total_weight = sum(graph[u][v]['weight'] for u, v in matchings)
    G = graph
    n = G.number_of_nodes()
    C = np.full((n, n), np.inf)
    for i, j, data in G.edges(data=True):
        w = data["weight"]
        C[i, j] = -w
        C[j, i] = -w
    np.fill_diagonal(C, np.inf)
    row, col = linear_sum_assignment(C)
    M = [(i, j) for i, j in zip(row, col) if i < j]
    w = sum(G[u][v]["weight"] for u, v in M)
    return w >= alpha, w, M

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

def initializeMatchingPred(numNodes, offMatching, error):
    if numNodes % 2 != 0:
        exit("Error: Number of nodes must be even")
    G = nx.Graph()
    G.add_nodes_from(range(0,numNodes))
    G.add_edges_from(offMatching)
    for i in range(error):
        e1 = offMatching[(i)%(len(offMatching))]
        e2 = offMatching[(len(offMatching)-1-i)%(len(offMatching))]
        if G.has_edge(*e1): G.remove_edge(*e1)
        if G.has_edge(*e2): G.remove_edge(*e2)
        G.add_edge(e1[0],e2[0])
        G.add_edge(e1[1],e2[1])
        
    return G

def weight_outside_matching(graph, matching):
    tempGraph = graph.copy()
    for (u,v) in matching:
        tempGraph[u][v]['weight']=0

    edge_weights = nx.get_edge_attributes(tempGraph, "weight")
    return np.sum(list(edge_weights.values()))

def weight_outside_matrix_matching(weight_matrix, matching):
    total_weight = np.sum(np.triu(weight_matrix, 1))
    matching_weight = sum(weight_matrix[u][v] for u, v in matching)
    return total_weight - matching_weight

def incrementWeightMatrix(weight_matrix, u, v):
    weight_matrix[u][v] = weight_matrix[u][v] + 1
    weight_matrix[v][u] = weight_matrix[v][u] + 1
    return weight_matrix

# Online Deterministic Algorithm
if alg == "det":
    onlineAlgTrackingGraph = initializeTrackingGraph(numNodes)
    onlineAlgMatching = initializeMatching(numNodes,10)
    t = 0
    cost = 0
    for t, request in data.iterrows():
        src = request["srcip"]
        dst = request["dstip"]
        if onlineAlgMatching.has_edge(src,dst):
            cost = cost + 0 # Nothing to do. Just for readablity
        else:
            cost = cost + 1
            incrementEdgeWeight(onlineAlgTrackingGraph, src,dst)
            if onlineAlgTrackingGraph[src][dst]['weight'] >= alpha/numNodes:
                cost = cost + alpha
                # print("check")
                (srcU, srcV) = list(onlineAlgMatching.edges(src))[0]
                (dstU, dstV) = list(onlineAlgMatching.edges(dst))[0]
                # Swap
                onlineAlgMatching.remove_edge(srcU, srcV)
                onlineAlgMatching.remove_edge(dstU, dstV)
                onlineAlgMatching.add_edge(srcU,dstU)
                onlineAlgMatching.add_edge(srcV, dstV)
                onlineAlgTrackingGraph[srcU][dstU]['weight'] = 0
                onlineAlgTrackingGraph[srcV][dstV]['weight'] = 0

        # Early exit based on maxRequests
        if t >= maxRequests:
            break
    
    with lock:
        with open(outfile, 'a') as file:
            print(trace, "deterministic", alpha, 0, cost, num_nodes_filter, file=file)

# Oblivious Algorithm
# Reconfigure blindly after every timeslot
if alg == "oblivious":
    onlineAlgMatching = initializeMatching(numNodes,10)
    t = 0
    cost = 0
    counter = 0
    for t, request in data.iterrows():
        # print(request["srcip"], request["dstip"])
        src = request["srcip"]
        dst = request["dstip"]
        if onlineAlgMatching.has_edge(src,dst):
            cost = cost + 0 # Nothing to do. Just for readablity
        else:
            cost = cost + 1
        if counter >= freq:
            onlineAlgMatching = initializeMatching(numNodes,t)
            cost = cost + alpha
            counter = 0
        counter = counter + 1
        # Early exit based on maxRequests
        if t >= maxRequests:
            break
    with lock:
        with open(outfile, 'a') as file:
            print(trace, "oblivious-"+str(freq), alpha, 0, cost,num_nodes_filter,file=file)

#%%

# Static Optimal Offline Algorithm
if alg == "staticoff":
    staticAlgTrackingGraph = initializeTrackingGraph(numNodes)
    t = 0
    cost = 0
    for t, request in data.iterrows():
        src = request["srcip"]
        dst = request["dstip"]
        staticAlgTrackingGraph = incrementEdgeWeight(staticAlgTrackingGraph, src,dst)
        
        # Early exit based on maxRequests
        if t >= maxRequests:
            break
    # Find the best matching for the static offline
    found, matchingWeight, matching = matching_with_weight_sum(staticAlgTrackingGraph, alpha, True)
    
    # Now run the algorithm
    cost = 0
    for t, request in data.iterrows():
        src = request["srcip"]
        dst = request["dstip"]
        if (src,dst) in matching or (dst,src) in matching:
            cost = cost + 0
        else:
            cost = cost + 1
        # Early exit based on maxRequests
        if t >= maxRequests:
            break
    with lock:
        with open(outfile, 'a') as file:
            print(trace, "static", alpha, 0, cost,num_nodes_filter,file=file)

#%%

# Offline Algorithm
if alg == "offline":
    cost = 0
    offlineAlgMatching = list()
    with open('offline/offline-matching-'+str(trace)+'-'+str(alpha)+'-'+str(num_nodes_filter)+'.pkl', 'rb') as f:
        offlineAlgMatching = pickle.load(f)
    # Run the offline algorithm
    (matching , timeslot) = offlineAlgMatching.pop(0)
    for t, request in data.iterrows():
        src = request["srcip"]
        dst = request["dstip"]
        if (src,dst) in matching or (dst,src) in matching:
            cost = cost + 0
        else:
            cost = cost + 1
        
        # Check if we need to reconfigure
        if len(offlineAlgMatching) > 0:
            if offlineAlgMatching[0][1]==t:
                cost = cost + alpha
                (matching, timeslot) = offlineAlgMatching.pop(0)
        # Early exit based on maxRequests
        if t >= maxRequests:
            break

    with lock:
        with open(outfile, 'a') as file:
            print(trace, "offline", alpha, 0, cost,num_nodes_filter,file=file)
#%%

# Prediction augmented algorithm
if alg == "pred":
    predAlgTrackingGraph = initializeTrackingGraph(numNodes)
    predAlgMatching = initializeMatching(numNodes,10)
    
    offlineAlgMatching = list()
    with open('offline/offline-matching-'+str(trace)+'-'+str(alpha)+'-'+str(num_nodes_filter)+'.pkl', 'rb') as f:
        offlineAlgMatching = pickle.load(f)
    
    t = 0
    cost = 0
    
    # Run
    (offMatching, prevTime) = offlineAlgMatching.pop(0)
    predAlgMatching = initializeMatchingPred(numNodes,list(offMatching), error)
    for t, request in data.iterrows():
        src = request["srcip"]
        dst = request["dstip"]
        
        predAlgTrackingGraph = incrementEdgeWeight(predAlgTrackingGraph, src,dst)
        
        if len(offlineAlgMatching) > 0:
            if t == offlineAlgMatching[0][1]:
                (offMatching, PrevTime) = offlineAlgMatching.pop(0)
        
        if predAlgMatching.has_edge(src, dst):
            cost = cost + 0
        else:
            cost = cost + 1
            # Find the maximum weight maximal matching
            foundMax, matchingWeight, matching = matching_with_weight_sum(predAlgTrackingGraph, alpha/3, True)
            
            # Remove the maximal matching
            if weight_outside_matching(predAlgTrackingGraph, matching) >= alpha/3:
                # print("Found")
                # Get prediction and then reconfigure
                if len(offMatching) > 0:
                    # print(len(offMatching))
                    predAlgMatching = initializeMatchingPred(numNodes,list(offMatching), error)
                    cost = cost + alpha
                    predAlgTrackingGraph = initializeTrackingGraph(numNodes)

        # Early exit based on maxRequests
        if t >= maxRequests:
            break
    with lock:
        with open(outfile, 'a') as file:
            print(trace, "pred", alpha, error, cost,num_nodes_filter,file=file)

# Prediction augmented algorithm with a history-based prediction.
if alg in ("pred-history", "PRED-History"):
    predAlgWeights = np.zeros((numNodes, numNodes))
    predAlgMatching = initializeMatching(numNodes,10)
    
    t = 0
    cost = 0
    
    # Run
    for t, request in data.iterrows():
        src = request["srcip"]
        dst = request["dstip"]
        
        predAlgWeights = incrementWeightMatrix(predAlgWeights, src,dst)
        
        if predAlgMatching.has_edge(src, dst):
            cost = cost + 0
        else:
            cost = cost + 1
            # Find the maximum weight matching of the current request weights.
            foundMax, matchingWeight, matching = matching_from_weight_matrix(predAlgWeights, alpha/3)
            
            # Remove the maximal matching
            if weight_outside_matrix_matching(predAlgWeights, matching) >= alpha/3:
                # Send the request-history matching to PRED, then reset interval weights.
                if len(matching) > 0:
                    predAlgMatching = initializeMatchingPred(numNodes,list(matching), error)
                    cost = cost + alpha
                    predAlgWeights = np.zeros((numNodes, numNodes))

        # Early exit based on maxRequests
        if t >= maxRequests:
            break
    with lock:
        with open(outfile, 'a') as file:
            print(trace, "pred-history", alpha, error, cost,num_nodes_filter,file=file)
