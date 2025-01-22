#!/bin/bash

# Get absolute path to the directory of this file realpath
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR

# check if data directory exists, if not craete
if [ ! -d "$DIR/data" ]; then
	mkdir $DIR/data
fi

if [[ $1 -eq 1 ]];then
	cd $DIR/data
	wget https://nextcloud.inet.tu-berlin.de/s/mm5BBsDAHgb5wTR/download/hpc_cesar_nekbone.zip
	unzip hpc_cesar_nekbone.zip
	wget https://nextcloud.inet.tu-berlin.de/s/BiDe8RHzXcMWDbm/download/hpc_cesar_mocfe.zip
	unzip hpc_cesar_mocfe.zip
	wget https://nextcloud.inet.tu-berlin.de/s/WcFsd5NweRDjSWr/download/hpc_exact_boxlib_multigrid_c_large.zip
	unzip hpc_exact_boxlib_multigrid_c_large.zip
	cd $DIR
fi

# Compute OFF first
ALPHAS=(2 4 6 8 10)
TRACES=("HPC-Mocfe" "HPC-Nekbone" "HPC-Boxlib")
# TRACES=("HPC-Boxlib")
MAXREQUESTS=10000000000
NUMNODES=64
COMPRESS=1

for TRACE in ${TRACES[@]};do
	for ALPHA in ${ALPHAS[@]};do
		while [[ $(ps aux| grep compute-off | wc -l) -gt $(nproc) ]];do
			sleep 5
			echo "waiting for cores"
		done
		(python3 compute-off.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES $COMPRESS) &
	done
done


while [[ $(ps aux| grep compute-off | wc -l) -gt 1 ]];do
	sleep 5
	echo "waiting for off computations..."
done

ALGS=("det" "oblivious" "staticoff" "offline")
OUTFILE=$DIR/results/results.csv

echo "trace alg alpha error cost" > $OUTFILE

for TRACE in ${TRACES[@]};do
	for ALG in ${ALGS[@]};do
		for ALPHA in ${ALPHAS[@]};do
			while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(nproc) ]];do
				sleep 5
				echo "waiting for cores to run $TRACE $ALG $ALPHA"
			done
			(python3 run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES 0 $OUTFILE $ALG $COMPRESS) &
		done
	done
done

ALG="pred"
ERRORS=(0 2 4 8 16)
for TRACE in ${TRACES[@]};do
	for ERROR in ${ERRORS[@]};do
		for ALPHA in ${ALPHAS[@]};do
			while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(nproc) ]];do
				sleep 5
				echo "waiting for cores to run $TRACE $ALG $ALPHA"
			done
			(python3 run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES $ERROR $OUTFILE $ALG $COMPRESS > /dev/null 2> /dev/null) &
		done
	done
done