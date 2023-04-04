#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")"

# Source Python3.7 to use Matlab 2020a w/ python's matlab.engine
source $PACKAGE_TOP/anaconda/envs/python3.7env/bin/activate
export PYTHONPATH=$TOOLS/python/toolbox
export LD_LIBRARY_PATH=/usr/local/lcls/package/anaconda/envs/python3.7env/epics/lib/linux-x86_64:$LD_LIBRARY_PATH

# Update LIVE PVs
python blem_pv.py CU_HXR LIVE &
python blem_pv.py CU_SXR LIVE &
python blem_pv.py SC_HXR LIVE &
python blem_pv.py SC_SXR LIVE &
python blem_pv.py SC_DIAG0 LIVE &
python blem_pv.py SC_BSYD LIVE &

# Update DESIGN PVs
python blem_pv.py CU_HXR DESIGN &
python blem_pv.py CU_SXR DESIGN &
python blem_pv.py SC_HXR DESIGN &
python blem_pv.py SC_SXR DESIGN &
python blem_pv.py SC_DIAG0 DESIGN &
python blem_pv.py SC_BSYD DESIGN &

exit 0