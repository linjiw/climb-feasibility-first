"""Require exact numbers despite Python tuple versus JSON array representation."""
import hashlib
import json
from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from replay_serialized_confirmation import replay


@pytest.fixture
def setup(tmp_path,monkeypatch):
    campaign=tmp_path/'campaign';campaign.mkdir()
    contract={'path':'unused','sha256':'0'*64}
    (campaign/'campaign_manifest.json').write_text(json.dumps({'contract':contract}))
    (campaign/'terminal_status.json').write_text(json.dumps({'status':'completed','completed_jobs':[{}]*60}))
    saved={'status':'inconclusive','analysis':{'seed_order':[21,22,23]},'mean':.001}
    (campaign/'analysis.json').write_text(json.dumps(saved))
    binding={'campaign':str(campaign),'contract':contract,'sources':{}}
    path=tmp_path/'binding.json';path.write_text(json.dumps(binding))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    result={'status':'inconclusive','analysis':{'seed_order':(21,22,23)},'mean':.001}
    calls=[]
    fake=types.ModuleType('analyze_relative_campaign')
    fake.analyze=lambda p:(calls.append(p) or result)
    efficiency=types.ModuleType('analyze_icra_efficiency');efficiency.summarize=lambda d:{'status':'synthetic'}
    monkeypatch.setitem(sys.modules,'analyze_relative_campaign',fake)
    monkeypatch.setitem(sys.modules,'analyze_icra_efficiency',efficiency)
    return tmp_path,campaign,path,digest,result,calls


def test_tuple_array_difference_is_reported(setup):
    root,campaign,binding,digest,result,calls=setup
    checked=replay(root,campaign,binding,digest,root/'out')
    assert checked['representation_differences']==[{'path':'$.analysis.seed_order','recomputed_type':'tuple','saved_type':'list'}]
    assert len(calls)==1


@pytest.mark.parametrize('value',[.00100000000000001,float('nan'),float('inf')])
def test_changed_or_nonfinite_number_is_rejected(setup,value):
    root,campaign,binding,digest,result,calls=setup;result['mean']=value
    with pytest.raises(ValueError):replay(root,campaign,binding,digest,root/'out')


def test_incomplete_campaign_blocks_analysis(setup):
    root,campaign,binding,digest,result,calls=setup
    (campaign/'terminal_status.json').write_text(json.dumps({'status':'completed','completed_jobs':[{}]*59}))
    with pytest.raises(ValueError,match='incomplete'):replay(root,campaign,binding,digest,root/'out')
    assert not calls
