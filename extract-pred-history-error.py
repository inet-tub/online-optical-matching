import argparse
import multiprocessing as mp
import os
import pickle
from collections import Counter

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment


TRACEFILES = {
    "HPC-Mocfe": "hpc_cesar_mocfe-orig.csv",
    "HPC-Nekbone": "hpc_cesar_nekbone-orig.csv",
    "HPC-Boxlib": "hpc_exact_boxlib_multigrid_c_large-orig.csv",
    "HPC-Combined": "hpc_combined.csv",
    "pFabric": "pfabric01.csv",
}

_WORKER_STATE = {}


def canonical_edge(u, v):
    u = int(u)
    v = int(v)
    if u < v:
        return (u, v)
    return (v, u)


def canonical_matching(matching):
    return {canonical_edge(u, v) for u, v in matching if int(u) != int(v)}


def initialize_matching(num_nodes, offset):
    if num_nodes % 2 != 0:
        raise RuntimeError("Error: Number of nodes must be even")

    matching = set()
    for i in range(num_nodes):
        if i % 2 == 0:
            matching.add(canonical_edge(i, (i + 1 + offset) % num_nodes))
    return matching


def increment_weight_matrix(weight_matrix, u, v):
    weight_matrix[u][v] += 1
    weight_matrix[v][u] += 1


def matching_from_weight_matrix(weight_matrix):
    cost = -weight_matrix.astype(float, copy=True)
    np.fill_diagonal(cost, np.inf)
    row, col = linear_sum_assignment(cost)
    matching = [(i, j) for i, j in zip(row, col) if i < j]
    weight = sum(weight_matrix[u][v] for u, v in matching)
    return matching, weight


def weight_outside_matching(weight_matrix, matching):
    total_weight = np.sum(np.triu(weight_matrix, 1))
    matching_weight = sum(weight_matrix[u][v] for u, v in matching)
    return total_weight - matching_weight


def load_trace(trace, num_nodes_filter, max_requests, data_dir):
    path = os.path.join(data_dir, TRACEFILES[trace])
    df = pd.read_csv(
        path,
        usecols=["srcip", "dstip"],
        dtype={"srcip": np.int32, "dstip": np.int32},
    )
    data = df[
        (df["srcip"] < num_nodes_filter) & (df["dstip"] < num_nodes_filter)
    ].reset_index(drop=True)

    if len(data) == 0:
        raise RuntimeError(f"{trace}: no rows left after filtering with numNodes={num_nodes_filter}")

    if max_requests < len(data):
        data = data.iloc[:max_requests + 1].reset_index(drop=True)

    max_id = int(max(int(data["srcip"].max()), int(data["dstip"].max())))
    return data, max_id + 1


def advance_offline_index(offline_matchings, offline_index, t):
    while (
        offline_index + 1 < len(offline_matchings)
        and int(offline_matchings[offline_index + 1][1]) <= t
    ):
        offline_index += 1
    return offline_index


def summarize_errors(errors):
    if len(errors) == 0:
        return {
            "event_count": 0,
            "average_error": np.nan,
            "median_error": np.nan,
            "std_error": np.nan,
            "min_error": np.nan,
            "max_error": np.nan,
        }

    values = np.array(errors, dtype=float)
    return {
        "event_count": len(errors),
        "average_error": float(np.mean(values)),
        "median_error": float(np.median(values)),
        "std_error": float(np.std(values)),
        "min_error": int(np.min(values)),
        "max_error": int(np.max(values)),
    }


def run_alpha(trace, alpha, max_requests, num_nodes_filter, offline_dir, data, num_nodes):
    offline_path = os.path.join(
        offline_dir,
        f"offline-matching-{trace}-{int(alpha)}-{num_nodes_filter}.pkl",
    )
    with open(offline_path, "rb") as f:
        offline_matchings = pickle.load(f)

    offline_index = 0
    pred_matching = initialize_matching(num_nodes, 10)
    pred_weights = np.zeros((num_nodes, num_nodes))

    event_rows = []
    errors = []
    histogram = Counter()
    cost = 0

    for t, request in enumerate(data.itertuples(index=False)):
        src = int(request.srcip)
        dst = int(request.dstip)

        increment_weight_matrix(pred_weights, src, dst)
        offline_index = advance_offline_index(offline_matchings, offline_index, t)

        if canonical_edge(src, dst) in pred_matching:
            continue

        cost += 1
        history_matching, history_weight = matching_from_weight_matrix(pred_weights)

        if weight_outside_matching(pred_weights, history_matching) < alpha / 3.0:
            continue

        history_edges = canonical_matching(history_matching)
        off_edges = canonical_matching(offline_matchings[offline_index][0])
        real_error = len(off_edges - history_edges)
        pred_only_edges = len(history_edges - off_edges)
        symmetric_diff_edges = len(off_edges ^ history_edges)

        errors.append(real_error)
        histogram[real_error] += 1
        event_rows.append(
            {
                "trace": trace,
                "alpha": int(alpha),
                "numNodes": int(num_nodes_filter),
                "dummy_error": 0,
                "event_index": len(event_rows),
                "time": int(t),
                "off_time": int(offline_matchings[offline_index][1]),
                "real_error": int(real_error),
                "pred_only_edges": int(pred_only_edges),
                "symmetric_diff_edges": int(symmetric_diff_edges),
                "history_matching_size": int(len(history_edges)),
                "off_matching_size": int(len(off_edges)),
                "history_matching_weight": float(history_weight),
            }
        )

        pred_matching = history_edges
        cost += alpha
        pred_weights = np.zeros((num_nodes, num_nodes))

    summary = {
        "trace": trace,
        "alpha": int(alpha),
        "numNodes": int(num_nodes_filter),
        "dummy_error": 0,
        "cost": int(cost),
    }
    summary.update(summarize_errors(errors))

    hist_rows = [
        {
            "trace": trace,
            "alpha": int(alpha),
            "numNodes": int(num_nodes_filter),
            "dummy_error": 0,
            "real_error": int(error),
            "count": int(count),
        }
        for error, count in sorted(histogram.items())
    ]

    return event_rows, summary, hist_rows


def _run_alpha_from_worker_state(alpha):
    return run_alpha(
        _WORKER_STATE["trace"],
        alpha,
        _WORKER_STATE["max_requests"],
        _WORKER_STATE["num_nodes_filter"],
        _WORKER_STATE["offline_dir"],
        _WORKER_STATE["data"],
        _WORKER_STATE["num_nodes"],
    )


def run_trace_size(args):
    trace, alphas, max_requests, num_nodes_filter, data_dir, offline_dir, workers = args
    data, num_nodes = load_trace(trace, num_nodes_filter, max_requests, data_dir)

    _WORKER_STATE.clear()
    _WORKER_STATE.update(
        {
            "trace": trace,
            "max_requests": max_requests,
            "num_nodes_filter": num_nodes_filter,
            "offline_dir": offline_dir,
            "data": data,
            "num_nodes": num_nodes,
        }
    )

    event_rows = []
    summary_rows = []
    hist_rows = []

    if workers > 1 and len(alphas) > 1:
        ctx = mp.get_context("fork")
        pool_size = min(workers, len(alphas))
        with ctx.Pool(processes=pool_size) as pool:
            results = pool.map(_run_alpha_from_worker_state, alphas)
    else:
        results = [_run_alpha_from_worker_state(alpha) for alpha in alphas]

    for events, summary, hist in results:
        event_rows.extend(events)
        summary_rows.append(summary)
        hist_rows.extend(hist)

    return event_rows, summary_rows, hist_rows


def expand_traces(trace_args):
    if "ALL" in trace_args:
        return list(TRACEFILES.keys())
    return trace_args


def write_csv(path, rows, columns):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = pd.DataFrame(rows, columns=columns)
    df.to_csv(path, index=False)


def main():
    parser = argparse.ArgumentParser(
        description="Extract the real PRED-History matching-error distribution against OFF."
    )
    parser.add_argument("--traces", nargs="+", default=["ALL"], choices=list(TRACEFILES.keys()) + ["ALL"])
    parser.add_argument("--alphas", nargs="+", type=int, required=True)
    parser.add_argument("--numNodes", nargs="+", type=int, default=[32])
    parser.add_argument("--maxRequests", type=int, default=10000000000)
    parser.add_argument("--dataDir", default="data")
    parser.add_argument("--offlineDir", default="offline")
    parser.add_argument("--outDir", default="results")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = parser.parse_args()

    jobs = [
        (
            trace,
            args.alphas,
            args.maxRequests,
            num_nodes,
            args.dataDir,
            args.offlineDir,
            args.workers,
        )
        for num_nodes in args.numNodes
        for trace in expand_traces(args.traces)
    ]

    results = [run_trace_size(job) for job in jobs]

    event_rows = []
    summary_rows = []
    hist_rows = []
    for events, summaries, hist in results:
        event_rows.extend(events)
        summary_rows.extend(summaries)
        hist_rows.extend(hist)

    event_columns = [
        "trace",
        "alpha",
        "numNodes",
        "dummy_error",
        "event_index",
        "time",
        "off_time",
        "real_error",
        "pred_only_edges",
        "symmetric_diff_edges",
        "history_matching_size",
        "off_matching_size",
        "history_matching_weight",
    ]
    summary_columns = [
        "trace",
        "alpha",
        "numNodes",
        "dummy_error",
        "cost",
        "event_count",
        "average_error",
        "median_error",
        "std_error",
        "min_error",
        "max_error",
    ]
    hist_columns = ["trace", "alpha", "numNodes", "dummy_error", "real_error", "count"]

    write_csv(
        os.path.join(args.outDir, "pred-history-real-error-events.csv"),
        event_rows,
        event_columns,
    )
    write_csv(
        os.path.join(args.outDir, "pred-history-real-error-summary.csv"),
        summary_rows,
        summary_columns,
    )
    write_csv(
        os.path.join(args.outDir, "pred-history-real-error-histogram.csv"),
        hist_rows,
        hist_columns,
    )

    print(f"wrote {len(event_rows)} event rows for {len(summary_rows)} trace/alpha runs")


if __name__ == "__main__":
    main()
