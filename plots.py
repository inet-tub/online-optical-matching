#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 23 00:36:46 2025

@author: vamsi
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import matplotlib.colors as colors
from matplotlib import rcParams
import sys
#%%
plots_dir = "plots/"
# plots_dir = "/home/vamsi/src/phd/writings/rematching/0-current/plots/"

results_dir="results/"

df = pd.read_csv(results_dir+'results.csv',delimiter=' ')
minValue = np.min(df['cost'])
maxValue = np.max(df['cost'])
#%%
traces = ["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib", "HPC-Combined"]

algs = ["deterministic", "oblivious", "static" , "offline"]

algNames = ["Greedy", "OBL", "S-OFF", "OFF"]

numNodes = 64
alphas = [2, 4, 6, 8, 10]
alphas=[i*numNodes for i in alphas]
errors = [0, 2, 4, 8, 16]

rcParams.update({'font.size': 24})

for trace in traces:
    print(trace)
    dft = df[(df['trace']==trace)&(df['alg']!="pred")]
    arr = np.zeros((len(algs),len(alphas)))
    for index, row in dft.iterrows():
        i = algs.index(row['alg'])
        j = alphas.index(row['alpha'])
        arr[i,j] = row['cost']

    cmap = 'Blues'
    # cmap = 'BrBG_r'
    # cmap = 'hot_r'
    # maxValue = np.max(arr)
    # minValue = np.min(arr)
    fig, ax = plt.subplots(1,1, figsize=(8, 6))
    cax = ax.imshow(arr/minValue, cmap=cmap,norm=colors.LogNorm(vmin=1,vmax=maxValue/minValue,clip=True), aspect='auto')
    
    # Add rounded annotations to each cell
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            text = str(int(np.ceil(arr[i,j]/minValue)))
            ax.text(j, i, text, ha="center", va="center", color="black")
    
    fig.colorbar(cax, ax=ax, label='Noramlized Cost')
    ax.set_title(trace)
    ax.set_xlabel("Reconfiguration cost (" + r'$\alpha = x \cdot n$' + ")")
    ax.set_xticks(np.arange(len(alphas)))
    ax.set_xticklabels(np.arange(1,len(alphas)+1)*2)
    ax.set_yticks(np.arange(len(algs)))
    ax.set_yticklabels(algNames)
    fig.tight_layout()
    fig.savefig(plots_dir+'algs-'+trace+'.pdf')
    # plt.show()
    
    
#%%
traces = ["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib", "HPC-Combined"]

algs = ["pred"]

algNames = ["PRED"]

numNodes = 64
alphas = [2, 4, 6, 8, 10]
alphas=[i*numNodes for i in alphas]
errors = [0, 2, 4, 8, 16]

rcParams.update({'font.size': 25})

for trace in traces:
    dft = df[(df['trace']==trace)&(df['alg']=="pred")]
    arr = np.zeros((len(errors),len(alphas)))
    for index, row in dft.iterrows():
        i = errors.index(row['error'])
        j = alphas.index(row['alpha'])
        arr[i,j] = row['cost']

    cmap = 'Blues'
    # cmap = 'BrBG_r'
    # cmap = 'hot_r'
    maxValue = np.max(arr)
    minValue = np.min(arr)
    fig, ax = plt.subplots(1,1, figsize=(8, 6))
    cax = ax.imshow(arr/minValue, cmap=cmap, aspect='auto')
    
    fig.colorbar(cax, ax=ax, label='Noramlized Cost')
    # ax.set_title(trace)
    ax.set_xlabel("Reconfiguration cost (" + r'$\alpha = x \cdot n$' + ")")
    ax.set_xticks(np.arange(len(alphas)))
    ax.set_xticklabels(np.arange(1,len(alphas)+1)*2)
    ax.set_ylabel('Error')
    ax.set_yticks(np.arange(len(errors)))
    ax.set_yticklabels(errors)
    fig.tight_layout()
    fig.savefig(plots_dir+'pred-'+trace+'.pdf')
    # plt.show()