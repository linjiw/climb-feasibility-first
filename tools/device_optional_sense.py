#!/usr/bin/env python3
"""Record optional camera/raycast graphs without requiring absent sensor pipelines."""
from __future__ import annotations
from contextlib import contextmanager
import os
import json
from pathlib import Path
import sys
import torch
import eval_device_lifecycle as original


@contextmanager
def observe_graphs(payload: dict):
    import mjlab.envs
    import warp as wp
    base_env, base_launch = mjlab.envs.ManagerBasedRlEnv, wp.capture_launch
    observed = []
    payload['launches'] = {k:0 for k in ('step','forward','reset','sense')}
    class Environment(base_env):
        def __init__(self, *, cfg, device):
            super().__init__(cfg=cfg,device=device)
            observed.append(self.sim)
            payload.update(device=str(self.device),use_cuda_graph=bool(self.sim.use_cuda_graph),
                           sensor_context_present=self.sim._sensor_context is not None,
                           graphs={k:getattr(self.sim,f'{k}_graph') is not None for k in payload['launches']})
    def launch(graph,*args,**kwargs):
        for sim in observed:
            for key in payload['launches']:
                if graph is getattr(sim,f'{key}_graph'):
                    payload['launches'][key]+=1
        return base_launch(graph,*args,**kwargs)
    mjlab.envs.ManagerBasedRlEnv=Environment;wp.capture_launch=launch
    try:
        yield
    finally:
        mjlab.envs.ManagerBasedRlEnv=base_env;wp.capture_launch=base_launch


def verify_graphs(payload: dict, device: str, physics_steps: int) -> None:
    if payload['device'] != device:
        raise ValueError('device identity mismatch')
    if device == 'cpu':
        if payload['use_cuda_graph'] or any(payload['graphs'].values()) or any(payload['launches'].values()):
            raise ValueError('CPU reports CUDA graph execution')
        return
    if device != 'cuda:0' or not payload['use_cuda_graph']:
        raise ValueError('CUDA graph execution is required')
    if not all(payload['graphs'][k] for k in ('step','forward','reset')):
        raise ValueError('required dynamics graph absent')
    if payload['launches']['step'] != physics_steps or any(payload['launches'][k] <= 0 for k in ('forward','reset')):
        raise ValueError('incomplete dynamics graph execution')
    sensor = payload['sensor_context_present']
    if type(sensor) is not bool or payload['graphs']['sense'] != sensor:
        raise ValueError('sensor context and graph disagree')
    if (sensor and payload['launches']['sense'] <= 0) or (not sensor and payload['launches']['sense'] != 0):
        raise ValueError('sensor graph execution disagrees with actual context')


if __name__ == '__main__':
    design_path=Path(sys.argv[sys.argv.index('--design')+1])
    design=json.loads(design_path.read_text())
    if design.get('graph_protocol') != 'optional_sensor_context/1' or design['bindings'].get(str(Path(__file__).resolve())) != original.sha256(Path(__file__)):
        raise ValueError('requires a separately bound optional-sensor graph design')
    os.environ.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',WANDB_MODE='offline',MUJOCO_GL='egl')
    torch.set_num_threads(1)
    original.observe_graphs=observe_graphs
    original.verify_graphs=verify_graphs
    original.main()
