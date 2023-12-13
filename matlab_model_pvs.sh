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

python matlab_model_pvs.py
