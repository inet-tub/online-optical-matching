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
	mv hpc_cesar_nekbone.csv hpc_cesar_nekbone-orig.csv
	# wget https://nextcloud.inet.tu-berlin.de/s/BiDe8RHzXcMWDbm/download/hpc_cesar_mocfe.zip
	unzip hpc_cesar_mocfe.zip
	mv hpc_cesar_mocfe.csv hpc_cesar_mocfe-orig.csv
	# wget https://nextcloud.inet.tu-berlin.de/s/WcFsd5NweRDjSWr/download/hpc_exact_boxlib_multigrid_c_large.zip
	unzip hpc_exact_boxlib_multigrid_c_large.zip
	mv hpc_exact_boxlib_multigrid_c_large.csv hpc_exact_boxlib_multigrid_c_large-orig.csv
	# wget https://nextcloud.inet.tu-berlin.de/s/qezbedodDj3SHDH/download/p_fabric_trace_0_1.zip
	unzip p_fabric_trace_0_1.zip
	mv p_fabric_trace_0_1.csv pfabric01.csv
	cd $DIR
	python3 shuffle-traces.py
	cd $DIR/data
	cat hpc_cesar_nekbone.csv > hpc_combined.csv
	cat hpc_cesar_mocfe.csv | tail -n +2 >> hpc_combined.csv
	cat hpc_exact_boxlib_multigrid_c_large.csv | tail -n +2 >> hpc_combined.csv
	cd $DIR
	python3 trace-visualization.py
fi
####################### Compute OFF first #############################
ALPHAS=(0 3 6 9 12 15 18 21 24 27 30 32 64 128 256 512 1024 2048 4096 8192 16384 32768)
TRACES=("HPC-Mocfe" "HPC-Nekbone" "HPC-Boxlib" "HPC-Combined" "pFabric")
MAXREQUESTS=1000000
SIZES=(32 64 128 256 1024)
COMPRESS=0

for NUMNODES in ${SIZES[@]};do
	for TRACE in ${TRACES[@]};do
		for ALPHA in ${ALPHAS[@]};do
			while [[ $(ps aux| grep compute-off | wc -l) -gt $(( $(nproc) -2 )) ]];do
				sleep 5
				echo "waiting for cores"
			done
			(python3 compute-off.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES $COMPRESS) &
		done
	done
done

while [[ $(ps aux| grep compute-off | wc -l) -gt 1 ]];do
	sleep 5
	echo "waiting for off computations..."
done

exit
####################### Run algorithms #############################

ALGS=("det" "oblivious" "staticoff" "offline")

OUTFILE=$DIR/results/results.csv

echo "trace alg alpha error cost" > $OUTFILE

for TRACE in ${TRACES[@]};do
	for ALG in ${ALGS[@]};do
		for ALPHA in ${ALPHAS[@]};do
			while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(( $(nproc) -2 )) ]];do
				sleep 5
				echo "waiting for cores to run $TRACE $ALG $ALPHA"
			done
			echo "running $ALG with $TRACE"
			(python3 run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES 0 $OUTFILE $ALG $COMPRESS 1) &
		done
	done
done

####################### Run oblivious #############################

OBLS=(2 4 16 64)
for TRACE in ${TRACES[@]};do
	for ALG in ${OBLS[@]};do
		for ALPHA in ${ALPHAS[@]};do
			while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(( $(nproc) -2 )) ]];do
				sleep 5
				echo "waiting for cores to run $TRACE $ALG $ALPHA"
			done
			echo "running oblivious with $ALG"
			(python3 run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES 0 $OUTFILE "oblivious" $COMPRESS $ALG) &
		done
	done
done

####################### Run PRED #############################
ALG="pred"
ERRORS=(0 1 2 3 4 5 6 7 8)
for TRACE in ${TRACES[@]};do
	for ERROR in ${ERRORS[@]};do
		for ALPHA in ${ALPHAS[@]};do
			while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(( $(nproc) -2 )) ]];do
				sleep 5
				echo "waiting for cores to run $TRACE $ALG $ALPHA"
			done
			echo "pred oblivious with $ALG"
			(python3 run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES $ERROR $OUTFILE $ALG $COMPRESS 1) &
		done
	done
done

########################### Plot results ########################
python3 plots.py