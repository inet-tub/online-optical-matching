# online-optical-matching

This repository contains the source code for the paper (under submission) `Leveraging Predictions for Optical Interconnect Reconfiguration`.

## Algorithms

The python file `run-algorithm.py` contains the implementation of the following algorithms:

- Offline (Algorithm 2. in the paper)
- Static offline
- Online greedy (Algorithm 1. in the paper)
- Online greedy with predictions (Algorithm 3. in the paper). Here, predictions are based on the offline solution and by introducing a prediction error.
- Oblivious


## Datasets

`run-experiments.sh` automatically downloads the necessary datasets hosted on our university servers. These datasets can also be obtained from the following locations:

- [https://trace-collection.net/](https://trace-collection.net/)
- [https://portal.nersc.gov/project/CAL/cesar.htm](https://portal.nersc.gov/project/CAL/cesar.htm)

Each tracefile consists of a sequence of requests that specifies the source and destination nodes.

# Reproducibility

The code is written in Python3 (3.11.11) and tested on Linux (Fedora 41).
To reproduce the results, please follow these steps:

- Clone the repository:
```bash
git clone https://github.com/inet-tub/online-optical-matching.git
cd online-optical-matching
```
- Install the required dependencies:
```bash
pip install -r requirements.txt
```

- Run the experiments
```bash
./chmod +x ./run-experiments.sh
./run-experiments.sh
```

- The results will be saved in the `results` directory. Plot the figures using the `plot.py` script. The figures will be saved in the `plots` directory.
```bash
python3 plot.py
```