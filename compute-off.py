#!/usr/bin/env python3
import argparse
import os
import pickle

import numpy as np
import pandas as pd
import networkx as nx
from multiprocessing import Pool
from scipy.optimize import linear_sum_assignment


TRACEFILES = {
    "HPC-Mocfe": "hpc_cesar_mocfe-orig.csv",
    "HPC-Nekbone": "hpc_cesar_nekbone-orig.csv",
    "HPC-Boxlib": "hpc_exact_boxlib_multigrid_c_large-orig.csv",
    "HPC-Combined": "hpc_combined.csv",
    "pFabric": "pfabric01.csv",
}


def initialize_tracking_graph(n: int) -> nx.Graph:
    G = nx.complete_graph(n)
    nx.set_edge_attributes(G, 0, "weight")
    return G


def max_weight_matching_and_weight(G: nx.Graph, maxcardinality: bool = True):
    
    # This is using blossom, really slow!!!
    # M = nx.algorithms.matching.max_weight_matching(
    #     G, maxcardinality=maxcardinality, weight="weight"
    # )
    # w = 0
    # for u, v in M:
    #     w += G[u][v]["weight"]

    # Hungarian
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

    return M, w


def run_one(trace: str, alpha: float, max_requests: int, num_nodes_filter: int,
            data_dir: str, out_dir: str):
    path = os.path.join(data_dir, TRACEFILES[trace])
    df = pd.read_csv(
        path,
        usecols=["srcip", "dstip"],
        dtype={"srcip": np.int32, "dstip": np.int32},
    )

    data = df[(df["srcip"] < num_nodes_filter) & (df["dstip"] < num_nodes_filter)].reset_index(drop=True)

    if len(data) == 0:
        raise RuntimeError(f"{trace}: no rows left after filtering with numNodes={num_nodes_filter}")

    max_id = int(max(int(data["srcip"].max()), int(data["dstip"].max())))
    n = max_id + 1

    G = initialize_tracking_graph(n)

    total_weight = 0

    offline = []
    prev_time = 0

    for t, request in enumerate(data.itertuples(index=False)):
        if t >= max_requests:
            break

        if t%10000 == 0:
            print("OffProgress",trace,alpha,t,len(data))

        src = int(request.srcip)
        dst = int(request.dstip)

        if src == dst:
            continue

        G[src][dst]["weight"] += 1
        total_weight += 1

        if total_weight > (alpha / 3.0):
            M, matching_weight = max_weight_matching_and_weight(G, maxcardinality=True)
            # print(t,len(data))

            cost = total_weight - matching_weight

            if cost >= (alpha / 3.0):
                offline.append((M, prev_time))
                prev_time = t

                nx.set_edge_attributes(G, 0, "weight")
                total_weight = 0

    if len(offline) == 0:
        M, _ = max_weight_matching_and_weight(G, maxcardinality=True)
        offline.append((M, prev_time))

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"offline-matching-{trace}-{int(alpha)}-{num_nodes_filter}.pkl")
    with open(out_path, "wb") as f:
        pickle.dump(offline, f)

    return (trace, out_path, n, len(data), len(offline))


def _worker(args):
    return run_one(*args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default="pFabric", choices=list(TRACEFILES.keys()) + ["ALL"])
    ap.add_argument("--alpha", type=float, required=True)
    ap.add_argument("--maxRequests", type=int, required=True)
    ap.add_argument("--numNodes", type=int, required=True, help="filter threshold (srcip,dstip < numNodes)")
    ap.add_argument("--dataDir", default="data")
    ap.add_argument("--outDir", default="offline")
    ap.add_argument("--workers", type=int, default=1, help="parallelize across traces (or alpha sweeps)")
    args = ap.parse_args()

    traces = list(TRACEFILES.keys()) if args.trace == "ALL" else [args.trace]

    jobs = [
        (tr, args.alpha, args.maxRequests, args.numNodes, args.dataDir, args.outDir)
        for tr in traces
    ]

    if args.workers > 1 and len(jobs) > 1:
        with Pool(processes=args.workers) as pool:
            results = pool.map(_worker, jobs)
    else:
        results = [run_one(*jobs[0])] if len(jobs) == 1 else [run_one(*j) for j in jobs]

    for trace, out_path, n, nrows, nsegments in results:
        print(f"{trace}: n={n}, rows={nrows}, segments={nsegments}, wrote {out_path}")


if __name__ == "__main__":
    main()