#!/bin/bash

# Get absolute path to the directory of this file realpath
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR
source .venv/bin/activate
# check if data directory exists, if not craete
if [ ! -d "$DIR/data" ]; then
	mkdir $DIR/data
fi
# check if results directory exists, if not craete
if [ ! -d "$DIR/results" ]; then
	mkdir $DIR/results
fi
# check if offline directory exists, if not craete
if [ ! -d "$DIR/offline" ]; then
	mkdir $DIR/offline
fi
# check if plots directory exists, if not craete
if [ ! -d "$DIR/plots" ]; then
	mkdir $DIR/plots
fi

#################### Download and prepare data ####################

if [[ $1 -eq 1 ]];then
	cd $DIR/data
	# wget https://nextcloud.inet.tu-berlin.de/s/mm5BBsDAHgb5wTR/download/hpc_cesar_nekbone.zip
	unzip hpc_cesar_nekbone.zip
	cp hpc_cesar_nekbone.csv hpc_cesar_nekbone-orig.csv
	# wget https://nextcloud.inet.tu-berlin.de/s/BiDe8RHzXcMWDbm/download/hpc_cesar_mocfe.zip
	unzip hpc_cesar_mocfe.zip
	cp hpc_cesar_mocfe.csv hpc_cesar_mocfe-orig.csv
	# wget https://nextcloud.inet.tu-berlin.de/s/WcFsd5NweRDjSWr/download/hpc_exact_boxlib_multigrid_c_large.zip
	unzip hpc_exact_boxlib_multigrid_c_large.zip
	cp hpc_exact_boxlib_multigrid_c_large.csv hpc_exact_boxlib_multigrid_c_large-orig.csv
	# wget https://nextcloud.inet.tu-berlin.de/s/qezbedodDj3SHDH/download/p_fabric_trace_0_1.zip
	unzip p_fabric_trace_0_1.zip
	cp p_fabric_trace_0_1.csv pfabric01.csv
	# cd $DIR
	# python3 shuffle-traces.py
	cd $DIR/data
	cat hpc_cesar_nekbone.csv > hpc_combined.csv
	cat hpc_cesar_mocfe.csv | tail -n +2 >> hpc_combined.csv
	cat hpc_exact_boxlib_multigrid_c_large.csv | tail -n +2 >> hpc_combined.csv
	cd $DIR
	# python3 trace-visualization.py
fi
####################### Compute OFF first #############################
# ALPHAS=(0 3 6 9 12 15 18 21 24 27 30 32 64 128 256)
# ALPHAS=(0 1 2 4 6 8 10 12 14 16 18 20)
ALPHAS=(32 64 128 256)
TRACES=("HPC-Mocfe" "HPC-Nekbone" "HPC-Boxlib" "HPC-Combined" "pFabric")
MAXREQUESTS=10000000000
SIZES=(32)

for NUMNODES in ${SIZES[@]};do
	for ALPHA in ${ALPHAS[@]};do
		while [[ $(ps aux| grep compute-off | wc -l) -gt $(( $(nproc) -2 )) ]];do
			sleep 5
			echo "waiting for cores"
		done
		echo "$NUMNODES, $ALPHA"
		(python compute-off.py --trace ALL --alpha $ALPHA --maxRequests $MAXREQUESTS --numNodes $NUMNODES --workers 5) &
		# (python3 compute-off.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES) &
	done
done

while [[ $(ps aux| grep compute-off | wc -l) -gt 1 ]];do
	sleep 5
	echo "waiting for off computations..."
done

exit