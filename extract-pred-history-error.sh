#!/bin/bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$DIR"
source .venv/bin/activate

mkdir -p "$DIR/results"
mkdir -p "$DIR/plots"

ALPHAS=(1 2 4 6 8 10 12 14 16 18 20 32 64 256 512 1024)
TRACES=("HPC-Mocfe" "HPC-Nekbone" "HPC-Boxlib" "HPC-Combined" "pFabric")
SIZES=(32)
MAXREQUESTS=10000000000
NCORES=$(nproc)
WORKERS=${WORKERS:-$(( NCORES > 2 ? NCORES - 2 : 1 ))}
TRACE_JOBS=${TRACE_JOBS:-${#TRACES[@]}}
PER_TRACE_WORKERS=${PER_TRACE_WORKERS:-$(( (WORKERS + TRACE_JOBS - 1) / TRACE_JOBS ))}
PARTS_DIR="$DIR/results/pred-history-real-error-parts"

rm -rf "$PARTS_DIR"
mkdir -p "$PARTS_DIR"

for TRACE in "${TRACES[@]}"; do
	while [[ $(jobs -pr | wc -l) -ge $TRACE_JOBS ]]; do
		wait -n
	done

	(
		python3 extract-pred-history-error.py \
			--traces "$TRACE" \
			--alphas "${ALPHAS[@]}" \
			--numNodes "${SIZES[@]}" \
			--maxRequests "$MAXREQUESTS" \
			--outDir "$PARTS_DIR/$TRACE" \
			--workers "$PER_TRACE_WORKERS"
	) &
done

wait

python3 - "$PARTS_DIR" "$DIR/results" <<'PY'
import os
import sys

import pandas as pd

parts_dir = sys.argv[1]
out_dir = sys.argv[2]
files = [
    "pred-history-real-error-events.csv",
    "pred-history-real-error-summary.csv",
    "pred-history-real-error-histogram.csv",
]

for filename in files:
    frames = []
    for root, _, names in os.walk(parts_dir):
        if filename in names:
            frames.append(pd.read_csv(os.path.join(root, filename)))
    if frames:
        df = pd.concat(frames, ignore_index=True)
    else:
        df = pd.DataFrame()
    df.to_csv(os.path.join(out_dir, filename), index=False)
PY

python3 plots.py
