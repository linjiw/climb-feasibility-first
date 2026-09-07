"""Configuration parity and prelaunch refusal without a simulator or outcomes."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import relative_confirmation_setup as setup
import train_relative_policy as development


@pytest.fixture
def inputs(monkeypatch):
    values = {"bank": str(ROOT / "bank/amass"),
              "training_clips": {"path": str(ROOT / "bank/tiers/tier_800.txt")},
              "unit_table": {"path": str(ROOT / "reports/g_segment/unit_table.json")}}
    for name, value in (("CLIMB_BANK", values["bank"]), ("CLIMB_CLIPS", values["training_clips"]["path"]),
                        ("CLIMB_SEGMENT_MANIFEST", values["unit_table"]["path"])):
        monkeypatch.setenv(name, value)
    return values


@pytest.mark.parametrize("arm", ("U", "A", "R", "D"))
def test_complete_environment_matches_existing_development_factory(inputs, arm):
    profiles = setup.fixed_profiles(setup.PROFILE_PATH)
    env, runner = setup.build_configs(arm, 21, profiles, inputs)
    old = development.config(arm, "smoke", 41)
    old.seed = 21
    old.commands["motion"].sampler_seed = 21
    old.scene.num_envs = 512
    assert setup.canonical(env) == setup.canonical(old)
    assert (runner.seed, runner.max_iterations, runner.save_interval, runner.resume) == (21, 4000, 100, False)
    assert setup.config_digest(env, runner) == setup.config_digest(*setup.build_configs(arm, 21, profiles, inputs))


def test_all_arms_share_nonsampler_config(inputs):
    profiles = setup.fixed_profiles(setup.PROFILE_PATH)
    baselines = []
    for arm in ("U", "A", "R", "D"):
        env, agent = setup.build_configs(arm, 21, profiles, inputs)
        env.commands["motion"] = None
        agent.run_name = "comparison"
        baselines.append(setup.canonical({"env": env, "agent": agent}))
    assert all(value == baselines[0] for value in baselines)


def test_configuration_digest_detects_reward_change(inputs):
    env, agent = setup.build_configs("R", 21, setup.fixed_profiles(setup.PROFILE_PATH), inputs)
    before = setup.config_digest(env, agent)
    env.rewards["failure_terminal"].weight *= 2
    assert setup.config_digest(env, agent) != before


@pytest.mark.parametrize("arm,seed", [("R", 11), ("D", 31), ("X", 21)])
def test_training_cannot_reuse_development_seeds(inputs, arm, seed):
    with pytest.raises(ValueError, match="fixed confirmation"):
        setup.build_configs(arm, seed, setup.fixed_profiles(setup.PROFILE_PATH), inputs)


def test_fixed_profiles_allow_enablement_but_no_retuning(tmp_path):
    profiles = json.loads(setup.PROFILE_PATH.read_text())
    profiles["confirmation"]["enabled"] = True
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(profiles))
    assert setup.fixed_profiles(path)["confirmation"]["enabled"] is True
    profiles["arms"]["D"]["exploration_ratio"] = 0.9
    path.write_text(json.dumps(profiles))
    with pytest.raises(ValueError, match="fixed profile"):
        setup.fixed_profiles(path)


def test_draft_contract_refused_before_runtime_or_simulator(tmp_path, monkeypatch):
    path = tmp_path / "draft.json"
    path.write_text(json.dumps({"schema_version": "relative_confirmation_contract/1", "status": "draft"}))
    def unexpected():
        pytest.fail("runtime checked before draft refusal")
    monkeypatch.setattr(setup, "runtime_inventory", unexpected)
    with pytest.raises(ValueError, match="prospective frozen"):
        setup.verify_contract(path, setup.sha256(path))


def test_cli_draft_cannot_create_training_directory(tmp_path):
    path = tmp_path / "draft.json"
    path.write_text(json.dumps({"schema_version": "relative_confirmation_contract/1", "status": "draft"}))
    output = tmp_path / "run"
    process = subprocess.run([sys.executable, str(ROOT / "tools/train_relative_confirmation.py"),
                              "--contract", str(path), "--contract-sha256", setup.sha256(path),
                              "--arm", "R", "--seed", "21", "--out-dir", str(output)],
                             capture_output=True, text=True)
    assert process.returncode != 0
    assert "prospective frozen" in process.stderr
    assert not output.exists()
