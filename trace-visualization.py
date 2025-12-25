import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.colors as colors
from matplotlib import rcParams
import sys
import pickle
#%%
alpha = 100
maxRequests = 100000000 # set it to a lower value for small test cases
numNodes = 1024*16

plots_dir = "plots/"

traces=["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib", "HPC-Combined", "pFabric"]
# traces=["pFabric"]

tracefiles={}
tracefiles["HPC-Mocfe"]="hpc_cesar_mocfe-orig.csv"
tracefiles["HPC-Nekbone"]="hpc_cesar_nekbone-orig.csv"
tracefiles["HPC-Boxlib"]="hpc_exact_boxlib_multigrid_c_large-orig.csv"
tracefiles["HPC-Combined"]="hpc_combined.csv"
tracefiles["pFabric"]="pfabric01.csv"

rcParams.update({'font.size': 24})

for trace in traces:
    df = pd.read_csv("data/"+tracefiles[trace])
    
    n = max(df["srcip"].max(), df["dstip"].max()) + 1
    data = df[(df['srcip'] < n) & (df['dstip'] < n)]

    # print (len(data))
    src = data["srcip"].to_numpy()
    dst = data["dstip"].to_numpy()
    
    requestMatrix = np.zeros((n, n), dtype=np.int32)
    np.add.at(requestMatrix, (src, dst), 1)
    row_sum = requestMatrix.sum(axis=1)
    col_sum = requestMatrix.sum(axis=0)
    active = (row_sum > 1) | (col_sum > 1)
    compact = requestMatrix[np.ix_(active, active)]
    
    cmap = 'CMRmap_r'
    maxValue = np.max(requestMatrix)
    fig, ax = plt.subplots(1,1, figsize=(8, 6))
    plt.imshow(compact, cmap=cmap,norm=colors.LogNorm(vmin=1,vmax=maxValue), aspect='auto')
    plt.colorbar(label='Number of Requests')
    # plt.title(trace)
    plt.xlabel('Destination Index')
    plt.ylabel('Source Index')
    fig.tight_layout()
    fig.savefig(plots_dir+trace+'.pdf')