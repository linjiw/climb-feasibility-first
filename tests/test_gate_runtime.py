"""Validate matched gate support, capped allocation and configuration parity."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from climb.gate_ablation import file_digest, rejection_telemetry, sampler_for, verified_manifest
from prepare_gate_runtime import build_views
from relative_confirmation_setup import canonical
from train_gate_smoke import configs

ORIGINAL = Path("/home/linjiw/climb-feasibility-first")
MANIFESTS = ROOT / "reports/gate_runtime_2026-09-06/manifests"


def test_on_view_reproduces_original_D_probabilities():
    reference = sampler_for(ORIGINAL / "reports/g_segment/unit_table.json", 71)
    gated = sampler_for(MANIFESTS / "gate_on.json", 71)
    assert torch.equal(reference.intervals.unit_ids, gated.intervals.unit_ids)
    assert torch.equal(reference.intervals.first, gated.intervals.first)
    assert torch.equal(reference.intervals.stop, gated.intervals.stop)
    assert torch.equal(reference.probabilities, gated.probabilities)


def test_only_support_and_its_bindings_differ_in_configs():
    values = []
    for arm in ("on", "off"):
        path = MANIFESTS / f"gate_{arm}.json"
        cfg, agent = configs(path, file_digest(path), arm,
                             ORIGINAL / "bank/tiers/tier_800.txt", ORIGINAL / "bank/amass")
        cfg, agent = canonical(cfg), canonical(agent)
        for name in ("segment_manifest", "gate_manifest_sha256", "gate_admission"):
            del cfg["fields"]["commands"]["motion"]["fields"][name]
        del agent["fields"]["run_name"]
        values.append((cfg, agent))
    assert values[0] == values[1]


@pytest.mark.parametrize("arm", ("on", "off"))
def test_draws_obey_exact_candidate_starts_and_clip_bounds(arm):
    sampler = sampler_for(MANIFESTS / f"gate_{arm}.json", 71)
    sample = sampler.sample(20000)
    indices = sample.table_indices
    assert (sample.local_starts >= sampler.intervals.first[indices]).all()
    assert (sample.local_starts < sampler.intervals.stop[indices]).all()
    assert (sample.local_trial_ends < sample.local_segment_stops).all()
    lengths = torch.tensor([r["frames"] for r in sampler.manifest["sources"]])
    assert (sample.local_trial_ends < lengths[sample.clip_ids]).all()
    rejected = torch.tensor([not r["gate_admitted"] for r in sampler.manifest["admissible_units"]])
    assert bool(rejected[indices].any()) == (arm == "off")


@pytest.mark.parametrize("arm", ("on", "off"))
def test_fixed_failure_profile_retains_floor_and_caps_after_concentrated_outcomes(arm):
    sampler = sampler_for(MANIFESTS / f"gate_{arm}.json", 71)
    sampler.failure_mass.zero_()
    sampler.attempt_mass.fill_(1000)
    clip = torch.bincount(sampler.intervals.clip_ids).argmax()
    sampler.failure_mass[sampler.intervals.clip_ids == clip] = 1000
    sampler.probabilities = sampler._compute_probabilities()
    base = sampler.deployment_mass.double()
    base /= base.sum()
    assert (sampler.probabilities >= 0.8*base-1e-12).all()
    assert sampler.probabilities.max() <= 0.05+1e-12
    assert torch.bincount(sampler.intervals.clip_ids, weights=sampler.probabilities).max() <= 0.25+1e-12
    if arm == "on":
        assert rejection_telemetry(sampler)["post_cap_rejected_mass"] == 0


def test_corrupted_mask_and_relabelled_profile_are_rejected(tmp_path):
    data = json.loads((MANIFESTS / "gate_on.json").read_text())
    path = tmp_path / "tampered.json"
    data["admissible_units"].pop()
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="mask"):
        verified_manifest(path, file_digest(path), "on")
    with pytest.raises(ValueError, match="profile"):
        verified_manifest(MANIFESTS / "gate_on.json", file_digest(MANIFESTS / "gate_on.json"), "off")


def test_missing_candidate_interval_cannot_build_views():
    original = json.loads((ORIGINAL / "reports/g_segment/unit_table.json").read_text())
    candidate = Path("/home/linjiw/climb-signal-quality-2026-09-06/reports/gate_candidate_audit_2026-09-06/candidate_start_intervals.json")
    partition = json.loads(candidate.read_text())
    partition.pop(next(i for i, row in enumerate(partition) if not row["gate_admitted"]))
    with pytest.raises(ValueError, match="gap|exhaust"):
        build_views(original, partition, file_digest(candidate))


@pytest.mark.parametrize("focus", ("rejected", "admitted", "all_success"))
def test_rejected_probability_has_prior_floor_even_without_informative_rank(focus):
    sampler = sampler_for(MANIFESTS / "gate_off.json", 71)
    rejected = torch.tensor([not r["gate_admitted"] for r in sampler.manifest["admissible_units"]])
    sampler.attempt_mass.fill_(1000)
    sampler.failure_mass.zero_()
    if focus != "all_success":
        sampler.failure_mass[rejected if focus == "rejected" else ~rejected] = 1000
    sampler.probabilities = sampler._compute_probabilities()
    base = sampler.deployment_mass.double()
    fraction = float(base[rejected].sum()/base.sum())
    actual = float(sampler.probabilities[rejected].sum())
    assert 0.8*fraction-1e-12 <= actual <= 0.8*fraction+0.2+1e-12
