"""Scale invariance and unchanged exact-support behavior for the new probe."""

import pytest
import torch

from climb.relative_progress import RelativeProgressSampler, relative_weights
from test_segment_runtime import write_manifest


def test_relative_weights_scale_invariant():
    g = torch.tensor([0.1, 0.002, 0.3], dtype=torch.float64)
    mass = torch.tensor([2.0, 7.0, 3.0], dtype=torch.float64)
    for scale in (1e-12, 1e-4, 10, 1e6):
        torch.testing.assert_close(relative_weights(g, mass, 2), relative_weights(g * scale, mass, 2))


def test_zero_progress_is_uniform_rank():
    assert torch.equal(relative_weights(torch.zeros(3), torch.ones(3), 2), torch.ones(3))


@pytest.mark.parametrize("g,mass,factor", [
    ([-1.0], [1.0], 2), ([1.0], [0.0], 2), ([1.0], [1.0], -1),
    ([float("nan")], [1.0], 2), ([1.0], [1.0], float("inf")),
])
def test_invalid_rank_inputs_rejected(g, mass, factor):
    with pytest.raises(ValueError):
        relative_weights(torch.tensor(g), torch.tensor(mass), factor)


def test_relative_sampler_exact_support_and_resume(tmp_path):
    manifest = tmp_path / "units.json"
    write_manifest(manifest)
    kwargs = dict(mode="adaptive", seed=11, rank="learning_progress", difficulty_power=0.0,
                  progress_window=1, progress_floor=0.0, relative_factor=2.0)
    sampler = RelativeProgressSampler(manifest, **kwargs)
    sampler.record_completed_trials(torch.tensor([0, 1]), torch.tensor([1, 0]))
    sampler.advance_clock()
    restored = RelativeProgressSampler(manifest, **kwargs)
    restored.load_state_dict(sampler.state_dict())
    first, second = sampler.sample(1000), restored.sample(1000)
    assert torch.equal(first.local_starts, second.local_starts)
    assert torch.equal(first.unit_ids, second.unit_ids)
    assert (first.local_trial_ends < first.local_segment_stops).all()
    mismatch = RelativeProgressSampler(manifest, **{**kwargs, "relative_factor": 1.0})
    with pytest.raises(ValueError, match="resume"):
        mismatch.load_state_dict(sampler.state_dict())


def test_absolute_floor_cannot_silently_mix_with_relative(tmp_path):
    with pytest.raises(ValueError, match="zero absolute floor"):
        RelativeProgressSampler(tmp_path / "absent", mode="adaptive", seed=1,
                                rank="learning_progress", progress_floor=0.05)
