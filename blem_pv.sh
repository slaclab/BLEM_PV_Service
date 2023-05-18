#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"

# Source Python3.7 to use Matlab 2020a w/ python's matlab.engine
source $PACKAGE_TOP/anaconda/envs/python3.7env/bin/activate
export PYTHONPATH=$TOOLS/python/toolbox
export LD_LIBRARY_PATH=/usr/local/lcls/package/anaconda/envs/python3.7env/epics/lib/linux-x86_64:$LD_LIBRARY_PATH

python blem_pv.py $*
