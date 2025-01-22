#!/bin/bash

# Get absolute path to the directory of this file realpath
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR

# check if data directory exists, if not craete
if [ ! -d "$DIR/data" ]; then
	mkdir $DIR/data
fi

cd $DIR/data
wget https://nextcloud.inet.tu-berlin.de/s/mm5BBsDAHgb5wTR/download/hpc_cesar_nekbone.zip
unzip hpc_cesar_nekbone.zip
wget https://nextcloud.inet.tu-berlin.de/s/BiDe8RHzXcMWDbm/download/hpc_cesar_mocfe.zip
unzip hpc_cesar_mocfe.zip
cd $DIR

# Compute OFF first
ALPHAS=(1 2 3 4 5 6 7 8 9 10)
TRACES=("HPC-Mocfe" "HPC-Nekbone")
MAXREQUESTS=10000
NUMNODES=64

# for TRACE in ${TRACES[@]};do
# 	for ALPHA in ${ALPHAS[@]};do
# 		while [[ $(ps aux| grep compute-off | wc -l) -gt $(nproc) ]];do
# 			sleep 5
# 			echo "waiting for cores"
# 		done
# 		(python compute-off.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES > /dev/null 2> /dev/null) &
# 	done
# done


# while [[ $(ps aux| grep compute-off | wc -l) -gt 1 ]];do
# 	sleep 5
# 	echo "waiting for off computations..."
# done

ALGS=("det" "oblivious" "staticoff" "offline")
OUTFILE=$DIR/results/results.csv

echo "alg,alpha,error,cost" > $OUTFILE

for TRACE in ${TRACES[@]};do
	for ALG in ${ALGS[@]};do
		for ALPHA in ${ALPHAS[@]};do
			while [[ $(ps aux| grep run-algorithm | wc -l) -gt $(nproc) ]];do
				sleep 5
				echo "waiting for cores to run $TRACE $ALG $ALPHA"
			done
			(python run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES 0 $OUTFILE $ALG ) &
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
			(python run-algorithm.py $TRACE $ALPHA $MAXREQUESTS $NUMNODES $ERROR $OUTFILE $ALG > /dev/null 2> /dev/null) &
		done
	done
done