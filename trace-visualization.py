import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.colors as colors
from matplotlib import rcParams
#%%
alpha = 100
maxRequests = 10000 # set it to a lower value for small test cases
numNodes = 64
traces=["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib"]

tracefiles={}
tracefiles["HPC-Mocfe"]="hpc_cesar_mocfe.csv"
tracefiles["HPC-Nekbone"]="hpc_cesar_nekbone.csv"
tracefiles["HPC-Boxlib"]="hpc_exact_boxlib_multigrid_c_large.csv"
rcParams.update({'font.size': 18})
for trace in traces:
    df = pd.read_csv("data/"+tracefiles[trace])
    data = df[(df['srcip'] < numNodes) & (df['dstip'] < numNodes)]
    src_set = set(data["srcip"])
    dst_set = set(data["dstip"])
    nodes_set = np.arange(max(len(src_set),len(dst_set)))
    numNodes = len(nodes_set)
    requestMatrix = np.zeros((numNodes,numNodes))
    for t, request in data.iterrows():
        src = request["srcip"]
        dst = request["dstip"]
        requestMatrix[src][dst] += 1

    cmap = 'CMRmap_r'
    maxValue = np.max(requestMatrix)
    fig, ax = plt.subplots(1,1, figsize=(8, 6))
    plt.imshow(requestMatrix, cmap=cmap,norm=colors.LogNorm(vmin=1,vmax=maxValue,clip=True), aspect='auto')
    plt.colorbar(label='Number of Requests')
    plt.title(trace)
    plt.xlabel('Destination Index')
    plt.ylabel('Source Index')
    fig.tight_layout()
    fig.savefig('plots/'+trace+'.pdf')