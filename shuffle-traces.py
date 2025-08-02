import numpy as np
import pandas as pd
#%%

numNodes = 32
traces=["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib"]
# traces=["HPC-Boxlib"]

tracefiles={}
tracefiles["HPC-Mocfe"]="hpc_cesar_mocfe.csv"
tracefiles["HPC-Nekbone"]="hpc_cesar_nekbone.csv"
tracefiles["HPC-Boxlib"]="hpc_exact_boxlib_multigrid_c_large.csv"

for trace in traces:
    df = pd.read_csv("data/"+tracefiles[trace])
    
    unique_nodes = np.arange(numNodes)
    shuffled_nodes = np.random.permutation(unique_nodes)
    mapping = dict(zip(unique_nodes, shuffled_nodes))
    def remap_node(x):
        return mapping.get(x, x)
    
    df['srcip'] = df['srcip'].apply(remap_node)
    df['dstip'] = df['dstip'].apply(remap_node)
    
    data = df[(df['srcip'] < numNodes) & (df['dstip'] < numNodes)]

    data.to_csv("data/"+tracefiles[trace], index=False)