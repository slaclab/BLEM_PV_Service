#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"

# Source Python3.7 to use Matlab 2020a w/ python's matlab.engine
source $PACKAGE_TOP/anaconda/envs/python3.7env/bin/activate
export PYTHONPATH=$TOOLS/python/toolbox
export LD_LIBRARY_PATH=/usr/local/lcls/package/anaconda/envs/python3.7env/epics/lib/linux-x86_64:$LD_LIBRARY_PATH


# Run each script in the background and store their process IDs
b_paths=("CU_HXR" "CU_SXR" "SC_HXR" "SC_SXR" "SC_DIAG0" "SC_BSYD")
p_types=("LIVE" "DESIGN")

# Start the python script for every path & type combination if it is not running or stuck on exit
for arg1 in "${b_paths[@]}"; do
    for arg2 in "${p_types[@]}"; do

        # Check if the python script is running for the given path & type
        if pgrep_out=$(pgrep -f "python blem_pv.py $arg1 $arg2"); then

            # Check :STAT PV and continue to the next process if it is running correctly
            status_pv="BLEM:SYS0:1:$arg1:$arg2:STAT"
            status=$(caget -t $status_pv)
            if ! [[ "$status" = "[INFO] - Ending script" ]]; then
                continue
            fi

            kill $pgrep_out

            error_pv="BLEM:SYS0:1:$arg1:$arg2:ERR_CNT"
            err_cnt=$(caget -t $error_pv)
            caput $error_pv $(($err_cnt + 1)) > /dev/null
        fi

        python blem_pv.py $arg1 $arg2 &
    done
done
