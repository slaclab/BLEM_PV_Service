#!/bin/bash

# Source Default Environment & Python3.7 to use Matlab 2020a w/ python's matlab.engine
if [ -d /afs/slac/g/lcls ]; then
    source /afs/slac/g/lcls/tools/script/ENVS64.bash
elif [ -d /usr/local/lcls ]; then
    source /usr/local/lcls/tools/script/ENVS64.bash
fi
source $PACKAGE_TOP/anaconda/envs/python3.7env/bin/activate
export PYTHONPATH=$TOOLS/python/toolbox
export LD_LIBRARY_PATH=/usr/local/lcls/package/anaconda/envs/python3.7env/epics/lib/linux-x86_64:$LD_LIBRARY_PATH

# Change Directory to the directory that contains the necessary python file
cd "$(dirname "${BASH_SOURCE[0]}")"

# Run each script in the background and store their process IDs
b_paths=("CU_HXR" "CU_SXR" "SC_HXR" "SC_SXR" "SC_DIAG0" "SC_BSYD")
p_types=("LIVE" "DESIGN")

error_message(){
    msg="This is an automated email notification from the cron job monitoring the "
    msg+="execution of the BLEM PV Service. The script encountered an error due to "
    msg+="a duplicate process running with the same Beam Path & PV Type arguments.\n\n"

    msg+="Error Details:\n\n"
    msg+="  - Timestamp:\t\t`date +"%Y-%m-%d %T"`\n"
    msg+="  - Beam Path:\t\t$1\n"
    msg+="  - PV Type:\t\t$2\n"
    msg+="  - Process PID:\t$3\n"
    msg+="  - Script Name:\tpython blem_pv.py $1 $2\n\n"

    msg+="Action Required:\n"
    msg+="Please investigate and resolve the duplicate process to prevent conflicts "
    msg+="and ensure the smooth execution of subsequent runs.\n"
}

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

            kill -9 $pgrep_out

            error_pv="BLEM:SYS0:1:$arg1:$arg2:ERR_CNT"
            err_cnt=$(caget -t $error_pv)
            caput $error_pv $(($err_cnt + 1))

            error_message $arg1 $arg2 $pgrep_out
            printf %b "$msg" | mailx -s "Cron Job Error - Duplicate BLEM PV Process" zdomke@slac.stanford.edu
        fi

        python blem_pv.py $arg1 $arg2 &
    done
done
