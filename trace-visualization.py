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
maxRequests = 10000 # set it to a lower value for small test cases
numNodes = 64

plots_dir = "plots/"

traces=["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib"]

compress = 1 #int(sys.argv[1])
k={}
if compress == 1:
    k["HPC-Mocfe"]=100
    k["HPC-Nekbone"]=50
    k["HPC-Boxlib"]=10

tracefiles={}
tracefiles["HPC-Mocfe"]="hpc_cesar_mocfe.csv"
tracefiles["HPC-Nekbone"]="hpc_cesar_nekbone.csv"
tracefiles["HPC-Boxlib"]="hpc_exact_boxlib_multigrid_c_large.csv"
rcParams.update({'font.size': 24})

def process_part(part):
    grouped = part.groupby(['srcip', 'dstip']).size().reset_index(name='count')
    return grouped

for trace in traces:
    df = pd.read_csv("data/"+tracefiles[trace])
    data = df[(df['srcip'] < numNodes) & (df['dstip'] < numNodes)]
    
    if compress == 1:
        K = k[trace]
        split_size = len(data) // K
        parts = [data.iloc[i * split_size:(i + 1) * split_size] for i in range(K)]
        if len(data) % K != 0:
            parts.append(data.iloc[K * split_size:])

        processed_parts = [process_part(part) for part in parts]
        data = pd.concat(processed_parts, ignore_index=True)

    # print (len(data))
    src_set = set(data["srcip"])
    dst_set = set(data["dstip"])
    nodes_set = np.arange(max(len(src_set),len(dst_set)))
    numNodes = len(nodes_set)
    requestMatrix = np.zeros((numNodes,numNodes))
    for t, request in data.iterrows():
        src = request["srcip"]
        dst = request["dstip"]
        requestMatrix[src][dst] += 1
    
        
    with open('data/'+str(trace)+'-'+str(alpha)+'.pkl','wb') as f:
        pickle.dump(requestMatrix, f)
        print("dump", trace)
    # cmap = 'CMRmap_r'
    # maxValue = np.max(requestMatrix)
    # fig, ax = plt.subplots(1,1, figsize=(8, 6))
    # plt.imshow(requestMatrix, cmap=cmap,norm=colors.LogNorm(vmin=1,vmax=maxValue,clip=True), aspect='auto')
    # plt.colorbar(label='Number of Requests')
    # # plt.title(trace)
    # plt.xlabel('Destination Index')
    # plt.ylabel('Source Index')
    # fig.tight_layout()
    # fig.savefig(plots_dir+trace+'.pdf')