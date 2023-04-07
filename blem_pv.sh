#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"

# Source Python3.7 to use Matlab 2020a w/ python's matlab.engine
source $PACKAGE_TOP/anaconda/envs/python3.7env/bin/activate
export PYTHONPATH=$TOOLS/python/toolbox
export LD_LIBRARY_PATH=/usr/local/lcls/package/anaconda/envs/python3.7env/epics/lib/linux-x86_64:$LD_LIBRARY_PATH


# Send a kill signal to each python process started by this script
close(){
    for pid in "${pids[@]}"; do
        if ps -p $pid > /dev/null; then
            kill $pid
        fi
    done
}
trap close SIGINT SIGTERM


# Run each script in the background and store their process IDs
b_paths=("CU_HXR" "CU_SXR" "SC_HXR" "SC_SXR" "SC_DIAG0" "SC_BSYD")
p_types=("LIVE" "DESIGN")
pids=()
for arg1 in "${b_paths[@]}"; do
    for arg2 in "${p_types[@]}"; do
        python blem_pv.py $arg1 $arg2 & 
        pids+=($!)
    done
done

wait
