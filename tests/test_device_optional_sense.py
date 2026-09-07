"""Require actual dynamics graphs while distinguishing an absent sensing pipeline."""
from copy import deepcopy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from device_optional_sense import verify_graphs

BASE={'device':'cuda:0','use_cuda_graph':True,'sensor_context_present':False,
      'graphs':{'step':True,'forward':True,'reset':True,'sense':False},
      'launches':{'step':600,'forward':4,'reset':2,'sense':0}}

def test_contact_only_model_has_no_camera_raycast_graph():
    verify_graphs(BASE,'cuda:0',600)

def test_sensor_context_requires_executed_graph():
    d=deepcopy(BASE);d['sensor_context_present']=True;d['graphs']['sense']=True;d['launches']['sense']=150
    verify_graphs(d,'cuda:0',600)

@pytest.mark.parametrize('fault',['step_count','missing_reset','no_forward','unexpected_sense','missing_sensor_graph'])
def test_incomplete_or_inconsistent_graphs_fail(fault):
    d=deepcopy(BASE)
    if fault=='step_count':d['launches']['step']-=1
    elif fault=='missing_reset':d['graphs']['reset']=False
    elif fault=='no_forward':d['launches']['forward']=0
    elif fault=='unexpected_sense':d['launches']['sense']=1
    else:d['sensor_context_present']=True
    with pytest.raises(ValueError):verify_graphs(d,'cuda:0',600)
