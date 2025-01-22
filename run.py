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
#%%
alpha = 100
maxRequests = 10000 # set it to a lower value for small test cases
numNodes = 64
traces=["HPC"]

tracefiles={}
# tracefiles["HPC"]="hpc_cesar_mocfe.csv"
tracefiles["HPC"]="hpc_cesar_nekbone.csv"

outfile = "results.csv"
with open(outfile, 'w') as file:
    file.write("alg,alpha,error,cost\n")
#%%

trace = "HPC"
df = pd.read_csv("data/"+tracefiles[trace])
data = df[(df['srcip'] < numNodes) & (df['dstip'] < numNodes)]
src_set = set(data["srcip"])
dst_set = set(data["dstip"])
nodes_set = np.arange(max(len(src_set),len(dst_set)))
numNodes = len(nodes_set)

#%%
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



#%%
# Online Deterministic Algorithm
onlineAlgTrackingGraph = initializeTrackingGraph(len(nodes_set))
onlineAlgMatching = initializeMatching(len(nodes_set),0)
with open(outfile, 'a') as file:
    for alpha in np.arange(1,11)*numNodes:
        t = 0
        cost = 0
        for t, request in data.iterrows():
            # print(request["srcip"], request["dstip"])
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
                
                # onlineAlgTrackingGraph = incrementEdgeWeight(onlineAlgTrackingGraph, src, dst)
                # found, matchingWeight, matching = matching_with_weight_sum(onlineAlgTrackingGraph, alpha)
                # if found == True:
                #     onlineAlgMatching = matching
                #     cost = cost + alpha
            # Early exit based on maxRequests
            if t >= maxRequests:
                break
            
        print("deterministic", alpha, 0, cost,file=file)

#%%
# Oblivious Algorithm
# Reconfigure blindly after every timeslot
onlineAlgMatching = initializeMatching(len(nodes_set),0)
with open(outfile, 'a') as file:
    for alpha in np.arange(1,11)*numNodes:
        t = 0
        cost = 0
        for t, request in data.iterrows():
            # print(request["srcip"], request["dstip"])
            src = request["srcip"]
            dst = request["dstip"]
            if onlineAlgMatching.has_edge(src,dst):
                cost = cost + 0 # Nothing to do. Just for readablity
            else:
                cost = cost + 1
            onlineAlgMatching = initializeMatching(len(nodes_set),t)
            cost = cost + alpha
            
            # Early exit based on maxRequests
            if t >= maxRequests:
                break
            
        print("oblivious", alpha, 0, cost,file=file)

#%%

# Static Optimal Offline Algorithm
staticAlgTrackingGraph = initializeTrackingGraph(len(nodes_set))
with open(outfile, 'a') as file:
    for alpha in np.arange(1,11)*numNodes:
        t = 0
        cost = 0
        for t, request in data.iterrows():
            # print(request["srcip"], request["dstip"])
            src = request["srcip"]
            dst = request["dstip"]
            staticAlgTrackingGraph = incrementEdgeWeight(staticAlgTrackingGraph, src,dst)
            
            # Early exit based on maxRequests
            if t >= maxRequests:
                break
        found, matchingWeight, matching = matching_with_weight_sum(staticAlgTrackingGraph, alpha, True)
        
        cost = 0
        for t, request in data.iterrows():
            # print(request["srcip"], request["dstip"])
            src = request["srcip"]
            dst = request["dstip"]
            if (src,dst) in matching or (dst,src) in matching:
                cost = cost + 0
            else:
                cost = cost + 1
            # Early exit based on maxRequests
            if t >= maxRequests:
                break
        print("static", alpha, 0, cost,file=file)
    
#%%

# Offline Algorithm

for alpha in np.arange(1,11)*numNodes:
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
        
        # found = False
        # matchingWeight = 0
        # matching = list()
        # if foundMax:
        #     found, matchingWeight, matching = matching_with_weight_sum(tempGraph, alpha, True)
        # if found == True:
        #     offlineAlgMatching.append((matchingOFF, prevTime))
        #     prevTime = t
        #     offlineAlgTrackingGraph = initializeTrackingGraph(len(nodes_set))
        # Early exit based on maxRequests
        if t >= maxRequests:
            break
        print("Constructing OFF timeslot =",t, " for alpha = ", alpha)
    
    with open('offline-matching-'+str(alpha)+'.pkl','wb') as f:
        pickle.dump(offlineAlgMatching, f)
        print("dump", alpha)
    
#%%
with open(outfile, 'a') as file:
    for alpha in np.arange(1,11)*numNodes:
        cost = 0
        offlineAlgMatching = list()
        with open('offline-matching-'+str(alpha)+'.pkl', 'rb') as f:
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
            # print(t,"run")
        print("offline", alpha, 0, cost,file=file)
        # print("offline", alpha, 0, cost)
    
#%%

# Prediction augmented algorithm

def initializeMatchingPred(numNodes, offMatching, error):
    if numNodes % 2 != 0:
        exit("Error: Number of nodes must be even")
    G = nx.Graph()
    G.add_nodes_from(range(0,numNodes))
    G.add_edges_from(offMatching)
    for i in range(error):
        e1 = offMatching[(i*2)%(len(offMatching))]
        e2 = offMatching[(i*2+int(numNodes/2)-1)%(len(offMatching))]
        # print((i*2)%(len(offMatching)),(i*2+int(numNodes/2)-1)%(len(offMatching)))
        G.remove_edge(e1[0],e1[1])
        G.remove_edge(e2[0],e2[1])
        G.add_edge(e1[0],e2[0])
        G.add_edge(e1[1],e2[1])
        
    return G


for alpha in np.arange(1,11)*numNodes:
    for error in [0, 2, 4, 8, 16]:
        
        predAlgTrackingGraph = initializeTrackingGraph(len(nodes_set))
        predAlgMatching = initializeMatching(len(nodes_set),0)
        
        offlineAlgMatching = list()
        with open('offline-matching-'+str(alpha)+'.pkl', 'rb') as f:
            offlineAlgMatching = pickle.load(f)
        
        t = 0
        cost = 0
        
        # Run
        (offMatching, prevTime) = offlineAlgMatching.pop(0)
        predAlgMatching = initializeMatchingPred(len(nodes_set),list(offMatching), error)
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
                tempGraph = predAlgTrackingGraph.copy()
                for (u,v) in matching:
                    tempGraph[u][v]['weight']=0
                
                edge_weights = nx.get_edge_attributes(tempGraph, "weight")
                if np.sum(list(edge_weights.values())) >= alpha/3:
                    print("Found")
                    # Get prediction and then reconfigure
                    if len(offMatching) > 0:
                        print(len(offMatching))
                        predAlgMatching = initializeMatchingPred(len(nodes_set),list(offMatching), error)
                        cost = cost + alpha
                        predAlgTrackingGraph = initializeTrackingGraph(len(nodes_set))
                
                # found, matchingWeight, matching = matching_with_weight_sum(tempGraph, alpha/3, False)
                # if found == True:
                #     print("Found")
                #     # Get prediction and then reconfigure
                #     if len(offMatching) > 0:
                #         print(len(offMatching))
                #         predAlgMatching = initializeMatchingPred(len(nodes_set),list(offMatching), error)
                #         cost = cost + alpha
                #         predAlgTrackingGraph = initializeTrackingGraph(len(nodes_set))
            
            # Early exit based on maxRequests
            if t >= maxRequests:
                break
            print("alpha", alpha, "error", error, "time",t,"cost",cost)
        
        with open(outfile, 'a') as file:
            print("pred", alpha, error, cost,file=file)
        # print("pred", alpha, error, cost)