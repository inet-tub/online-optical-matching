#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 23 00:36:46 2025

@author: vamsi
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib
import sys
#%%
plots_dir = "plots/"

results_dir="results/"

df = pd.read_csv(results_dir+'results.csv',delimiter=' ',header=0,usecols=[0,1,2,3,4,5],names=["trace","alg","alpha","error","cost","numNodes"])
df = df[df['alpha']!=0]

#%%
markers = (['o', 's', '^', 'D', 'v', 'x', '*', 'P', 'h'])

traces = ["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib", "HPC-Combined", "pFabric"]
minValue={}
maxValue={}
# traces = ["pFabric"]
# algs = ["deterministic", "oblivious-1","oblivious-2","oblivious-4","oblivious-16","oblivious-64", "static" , "offline"]
algs = ["deterministic", "offline", "static", "oblivious-1"]
labels = algs

# algNames = ["Greedy", "OBL", "OBL-2", "OBL-4", "OBL-16", "OBL-64", "S-OFF", "OFF"]
algNames = ["Greedy", "OBL", "S-OFF", "OFF"]
algNames = {}
algNames["deterministic"]="Greedy"
algNames["oblivious-1"]="Oblivious (OBL)"
algNames["static"]="Static Offline (S-OFF)"
algNames["offline"]="Offline (OFF)"

numNodes = 32
# lowalpha = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30]
lowalpha = [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
alphas = [1, 2, 8, 16, 32]
alphas=[i*numNodes for i in alphas]
alphas = lowalpha + alphas
# alphas = lowalpha
errors = [0, 1, 2, 3, 4, 5, 6, 7, 8]

rcParams.update({'font.size': 40})

for trace in traces:
    markerindex=0
    print(trace)
    dft = df[(df['trace']==trace)&(df['alg']!="pred")&(df['alg']!="oblivious-2")&(df['alg']!="oblivious-4")&(df['alg']!="oblivious-16")&(df['alg']!="oblivious-64")&(df["alpha"]!=0)&(df['alpha']<=1024)]
    minValue[trace] = np.min(dft[(dft['trace']==trace)]['cost'])
    maxValue[trace] = np.max(dft[(dft['trace']==trace)]['cost'])
    
    fig, ax = plt.subplots(1,1, figsize=(9, 9))
    for alg in algs:
        d = dft[(dft["alg"]==alg)]
        d = d.sort_values(by="alpha", ascending=True)
        ax.plot(d["alpha"], d['cost'],label=algNames[alg], lw = 4,marker=markers[markerindex],markersize=20)
        markerindex=markerindex+1
    ax.set_yscale('log')
    ax.set_xscale('log')
    ax.set_ylim(10**4,10**10)
    ax.set_xticks([1,10,100,1000])
    ax.set_xticklabels(["1","10","100","1000"])
    ax.set_yticks([10**4,10**6,10**8,10**10])
    ax.set_yticklabels(["10K","1M","100M","10T"],rotation=0)
    ax.xaxis.grid(True,ls='--')
    ax.yaxis.grid(True,ls='--')
    ax.set_xlabel('Reconfiguration cost ('+r'$\alpha$'+')')
    ax.set_ylabel('Total cost')
    # ax.legend(framealpha=0.1)
    
    fig_width = 3*len(labels)
    fig_legend = plt.figure(figsize=(fig_width, 1))
    
    handles, labels = ax.get_legend_handles_labels()
    legend = fig_legend.legend(
        handles, labels,
        loc='center',
        ncol=len(labels),
        frameon=False,
        fontsize=18,
        handlelength=2.5,
        markerscale=1
    )
    fig_legend.tight_layout()

    fig_legend.savefig(plots_dir+'algs-legend.pdf')
    
    fig.tight_layout()
    fig.savefig(plots_dir+'algs-'+trace+'.pdf')

#%%
markers = ['o', 's', '^', 'D', 'v', 'x', '*', 'P', 'h', 'd']

traces = ["HPC-Mocfe", "HPC-Nekbone", "HPC-Boxlib", "HPC-Combined", "pFabric"]
# traces = ["pFabric"]

algs = ["pred"]

algNames = ["PRED"]
numNodes = 32
# lowalpha = [3, 6, 9, 12, 15, 18, 21, 24, 27, 30]
# lowalpha = [1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
# alphas = [1, 2, 8, 16, 32]
# alphas=[i*numNodes for i in alphas]
# alphas = lowalpha + alphas
alphas = [1,4, 8, 16, 32, 64, 256, 512, 1024]
# alphas = lowalpha
errors = [0, 1, 2, 3, 4, 5, 6, 7, 8]

rcParams.update({'font.size': 40})

for trace in traces:
    markerindex=0
    dft = df[(df['trace']==trace)&(df['alg']=="pred")&(df['alpha']<=1024)]
    dfSoff = df[(df['trace']==trace)&(df['alg']!="pred")&(df['alg']!="oblivious-2")&(df['alg']!="oblivious-4")&(df['alg']!="oblivious-16")&(df['alg']!="oblivious-64")&(df["alpha"]!=0)&(df['alpha']<=1024)]
    dprime = dfSoff[(dfSoff["alg"]=="static")]
    soff = list(dprime["cost"])[0]/10**3
    fig, ax = plt.subplots(1,1, figsize=(10, 9))
    ax.set_prop_cycle(color=plt.cm.Greys(np.linspace(0.4, 0.9, 10)))
    for alpha in alphas:
        d = dft[(dft["alpha"]==alpha)]
        d = d.sort_values(by="error", ascending=True)
        print(d,alpha)
        ax.plot(2*d["error"], d['cost']/10**3,label=r'$\alpha =$'+str(alpha), lw = 4,marker=markers[markerindex],markersize=20)
        markerindex=markerindex+1
        # print(markerindex)
    ax.set_yscale('log')
    if trace == "HPC-Mocfe":
        ax.set_yticks([40,60,100,200])
        ax.set_yticklabels(["40K","60K","100K","200K"])
    elif trace == "HPC-Nekbone":
        ax.set_yticks([100,200,300,400, 500])
        ax.set_yticklabels(["100K","200K","300K","400K","500k"])
    elif trace == "HPC-Boxlib":
        ax.set_yticks([300,400,600,1000, 1200])
        ax.set_yticklabels(["300K","400K","600K","1M","1.2M"])
    elif trace == "HPC-Combined":
        ax.set_yticks([400,600,1000, 1500,1800])
        ax.set_yticklabels(["400K","600K","1M","1.5M","1.8M"])
    elif trace == "pFabric":
        ax.set_yticks([50,100,500, 1000])
        ax.set_yticklabels(["50K","100K","500K","1M"])
    # ax.set_xscale('log')
    # ax.set_ylim(10**4,10**7)
    # ax.set_ylim(10**4,10**10)
    # ax.set_yticks([10**4,10**6,10**8,10**10])
    ax.xaxis.grid(True,ls='--')
    ax.yaxis.grid(True,ls='--')
    ax.set_xlabel('Error')
    ax.set_ylabel(r'Total cost')
    ax.set_xticks(2*d["error"])
    ax.set_xticklabels(2*d["error"],rotation=40)
    
    ax.axhline(soff,ls='--',c='r',label="Static Offline (S-OFF)")
    # ax.legend(framealpha=0.1)
    fig.tight_layout()
    
    handles, labels = ax.get_legend_handles_labels()
    fig_width = 2*len(labels)
    fig_legend = plt.figure(figsize=(fig_width, 1))

    legend = fig_legend.legend(
        handles, labels,
        loc='center',
        ncol=len(labels),
        frameon=False,
        fontsize=18,
        handlelength=1.2,
        markerscale=1
    )
    fig_legend.tight_layout()

    fig_legend.savefig(plots_dir+'pred-legend.pdf')
    fig.savefig(plots_dir+'pred-'+trace+'.pdf')

#%%