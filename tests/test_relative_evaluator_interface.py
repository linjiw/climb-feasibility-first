"""Exercise actual evaluator CLI/configuration until the simulator boundary."""

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import eval_relative_confirmation as evaluator
import mjlab.envs
from mjlab.tasks.registry import load_rl_cfg
from relative_confirmation_setup import build_configs, canonical, fixed_profiles
from run_relative_confirmation import schedule


class ReachedSimulator(Exception):
    """Stop before simulator construction, checkpoint loading or outcome access."""


@pytest.fixture(scope='module')
def prepared():
    return json.loads((ROOT / 'reports/relative_progress_2026-09-05/confirmation_preparation/draft_contract.json').read_text())


@pytest.mark.parametrize('arm', ('U', 'A', 'R', 'D'))
def test_scheduled_evaluator_preserves_training_policy_interface(prepared, arm, tmp_path, monkeypatch):
    jobs = schedule(prepared, tmp_path / 'draft.json', 'not-a-launch', tmp_path)
    job = next(job for job in jobs if job['stage'] == 'evaluate' and job['arm'] == arm)
    captured = {}
    def stop_before_simulator(*, cfg, device):
        captured.update(cfg=cfg, device=device)
        raise ReachedSimulator
    monkeypatch.setattr(mjlab.envs, 'ManagerBasedRlEnv', stop_before_simulator)
    monkeypatch.setattr(sys, 'argv', job['argv'][1:])
    with pytest.raises(ReachedSimulator):
        evaluator.main()
    evaluation = captured['cfg']
    profiles = fixed_profiles(Path(prepared['profiles']['path']))
    training, agent = build_configs(arm, job['seed'], profiles, prepared)
    for group in training.observations.values():
        group.enable_corruption = False
    assert canonical(training.observations) == canonical(evaluation.observations)
    assert canonical(training.actions) == canonical(evaluation.actions)
    assert canonical(training.scene.entities) == canonical(evaluation.scene.entities)
    assert training.decimation == evaluation.decimation
    assert training.sim.mujoco.timestep == evaluation.sim.mujoco.timestep
    for key in ('body_names', 'anchor_body_name'):
        assert getattr(training.commands['motion'], key) == getattr(evaluation.commands['motion'], key)
    registered = load_rl_cfg('Climb-Tracking-Flat-Unitree-G1')
    for key in ('actor', 'obs_groups', 'clip_actions'):
        assert canonical(getattr(agent, key)) == canonical(getattr(registered, key))
    conditions = json.loads(Path(prepared['conditions']['path']).read_text())
    assert evaluation.scene.num_envs == 2800
    assert evaluation.seed == conditions['environment_seed']
    assert evaluation.auto_reset is False
    assert evaluation.sim.nconmax == conditions['nconmax_per_world']
    assert captured['device'] == 'cuda:0'
    assert not Path(job['csv']).exists()
