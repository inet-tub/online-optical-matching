#!/bin/bash

# set this to a lower value to limit the number of parallel processes, or reduce RAM usage
# With 128 cores, the script consumes ~80GB RAM. With 32 cores, about 20-28GB RAM.
NCORES=$(nproc)

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
	rm ./*.csv
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
ALPHAS=(0 1 2 4 6 8 10 12 14 16 18 20 32 64 256 512 1024)
# ALPHAS=(32 64 128 256)
TRACES=("HPC-Mocfe" "HPC-Nekbone" "HPC-Boxlib" "HPC-Combined" "pFabric")
MAXREQUESTS=10000000000
SIZES=(32)

for NUMNODES in ${SIZES[@]};do
	for ALPHA in ${ALPHAS[@]};do
		while [[ $(ps aux| grep compute-off | wc -l) -gt $(( $NCORES -2 )) ]];do
			sleep 5
			echo "waiting for cores"
		done
		echo "$NUMNODES, $ALPHA"
		(python compute-off.py --trace ALL --alpha $ALPHA --maxRequests $MAXREQUESTS --numNodes $NUMNODES --workers 1) &
		# (python3 compute-off.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES) &
	done
done

while [[ $(ps aux| grep compute-off | wc -l) -gt 1 ]];do
	sleep 5
	echo "waiting for off computations..."
done

# exit
####################### Run algorithms #############################
# ALPHAS=(0 1 2 4 6 8 10 12 14 16 18 20)
# ALPHAS=(32 64 128 256)
ALPHAS=(0 1 2 4 6 8 10 12 14 16 18 20 32 64 256 512 1024)
ALGS=("det" "oblivious" "staticoff" "offline")

OUTFILE=$DIR/results/results.csv

echo "trace alg alpha error cost" > $OUTFILE
for NUMNODES in ${SIZES[@]};do
	for TRACE in ${TRACES[@]};do
		for ALG in ${ALGS[@]};do
			for ALPHA in ${ALPHAS[@]};do
				while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(( $NCORES -2 )) ]];do
					sleep 5
					echo "waiting for cores to run $TRACE $ALG $ALPHA"
				done
				echo "running $ALG with $TRACE"
				(python3 run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES 0 $OUTFILE $ALG 0 1) &
			done
		done
	done
done

# ####################### Run oblivious #############################

OBLS=(2 4 16 64)
for NUMNODES in ${SIZES[@]};do
	for TRACE in ${TRACES[@]};do
		for ALG in ${OBLS[@]};do
			for ALPHA in ${ALPHAS[@]};do
				while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(( $NCORES -2 )) ]];do
					sleep 5
					echo "waiting for cores to run $TRACE $ALG $ALPHA"
				done
				echo "running oblivious with $ALG"
				(python3 run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES 0 $OUTFILE "oblivious" 0 $ALG) &
			done
		done
	done
done

####################### Run PRED #############################
PRED_ALGS=("pred" "pred-history")
ERRORS=(0 1 2 3 4 5 6 7 8 16)
N=0
for NUMNODES in ${SIZES[@]};do
	for TRACE in ${TRACES[@]};do
		for ALG in ${PRED_ALGS[@]};do
			for ERROR in ${ERRORS[@]};do
				if [[ $ERROR -gt $(( $NUMNODES/4 )) ]];then
					echo "Skipping $ERROR -gt $(( $NUMNODES/4 ))"
					continue
				fi
				for ALPHA in ${ALPHAS[@]};do
					while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(( $NCORES -2 )) ]];do
						sleep 5
						echo "waiting for cores to run $TRACE $ALG $ALPHA"
					done
					N=$(( N+1 ))
					echo "pred $TRACE with $ALG, $NUMNODES, $ERROR, $ALPHA, $N"
					(python3 run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES $ERROR $OUTFILE $ALG 0 1) &
				done
			done
		done
	done
done

while [[ $(ps aux| grep run-algorithm | wc -l) -gt 1 ]];do
	sleep 5
	echo "waiting for experiments to finish..."
done

./extract-pred-history.error.sh

echo "Finished $N experiments"
echo "All experiments finished, results in $OUTFILE"
# ########################### Plot results ########################
python3 plots.py
echo "Plots generated in $DIR/plots"