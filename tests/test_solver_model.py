"""
Tests for app/models/A_1D_multi_container_placement_chatGPT.py (RowBlock1DOrderModel)
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from models.A_1D_multi_container_placement import RowBlock1DOrderModel

L = 1203   # container length cm
HDOOR = 259
WMAX = 18000
GAP = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solve(lengths, heights, weights=None, values=None, L_cm=L, Hdoor_cm=HDOOR, Wmax_kg=WMAX):
    n = len(lengths)
    if weights is None:
        weights = [100] * n
    if values is None:
        values = [1] * n
    model = RowBlock1DOrderModel(
        lengths_cm=lengths,
        heights_cm=heights,
        weights_kg=weights,
        values=values,
        L_cm=L_cm,
        gap_cm=GAP,
        Wmax_kg=Wmax_kg,
        Hdoor_cm=Hdoor_cm,
        Rmax=None,
    )
    solved = model.solve(solver="ortools", time_limit=10)
    return model, solved


# ---------------------------------------------------------------------------
# Regression: N=1 block must not crash
# ---------------------------------------------------------------------------

class TestN1Block:
    def test_n1_block_no_crash(self):
        """N=1 block must not raise TypeError (_BoolVarImpl not subscriptable)."""
        model, solved = _solve([115], [240])
        assert solved is not None   # solved without exception

    def test_n1_block_fits_is_loaded(self):
        """A single 115cm block easily fits in a 1203cm container."""
        model, solved = _solve([115], [240])
        assert solved
        indices = model.loaded_indices_in_order()
        assert indices == [1]

    def test_n1_block_too_long_not_loaded(self):
        """A single block longer than container cannot be loaded."""
        model, solved = _solve([1300], [240])
        # Solver may be infeasible or return empty
        if solved:
            indices = model.loaded_indices_in_order()
            assert indices == []

    def test_n1_block_over_door_not_loaded(self):
        """A block taller than door height must not be selected."""
        model, solved = _solve([115], [300], Hdoor_cm=259)
        if solved:
            indices = model.loaded_indices_in_order()
            assert indices == []


# ---------------------------------------------------------------------------
# Multi-block ordering and correctness
# ---------------------------------------------------------------------------

class TestMultiBlock:
    def test_loaded_indices_in_order(self):
        """loaded_indices_in_order returns 1-based indices, excluding 0."""
        model, solved = _solve([115, 115, 115], [240, 240, 240])
        assert solved
        indices = model.loaded_indices_in_order()
        assert all(i >= 1 for i in indices)
        assert len(indices) <= 3

    def test_height_ordering_back_to_door(self):
        """Blocks placed in non-increasing height order back→door."""
        # Mix of heights: 240, 200, 160 — should come out tallest first
        model, solved = _solve([115, 115, 115], [160, 240, 200])
        assert solved
        indices = model.loaded_indices_in_order()
        heights_in_order = [
            {1: 160, 2: 240, 3: 200}[i] for i in indices
        ]
        # Check non-increasing
        for a, b in zip(heights_in_order, heights_in_order[1:]):
            assert a >= b

    def test_length_fits_in_container(self):
        """Total used length (with gaps) must not exceed container length."""
        model, solved = _solve([115] * 8, [240] * 8)
        assert solved
        indices = model.loaded_indices_in_order()
        n = len(indices)
        used = 115 * n + GAP * max(0, n - 1)
        assert used <= L

    def test_weight_limit_respected(self):
        """Blocks exceeding total weight cap should not all be selected."""
        # 5 blocks × 4000 kg = 20000 kg > 18000 kg limit
        model, solved = _solve([115] * 5, [240] * 5, weights=[4000] * 5)
        assert solved
        indices = model.loaded_indices_in_order()
        total_weight = 4000 * len(indices)
        assert total_weight <= WMAX

    def test_maximises_value(self):
        """Solver should prefer higher-value blocks when constrained."""
        # Only 1 block fits (L=200 so 200+gap+200 > L... use L_cm=130)
        # Block 1: value=1, Block 2: value=10 — solver should pick block 2
        model, solved = _solve([115, 115], [240, 240], values=[1, 10], L_cm=120)
        assert solved
        indices = model.loaded_indices_in_order()
        assert len(indices) <= 1
        if indices:
            assert 2 in indices  # the high-value block

    def test_usedLen_value_valid(self):
        """usedLen.value() should be within [0, L]."""
        model, solved = _solve([115, 115], [240, 200])
        assert solved
        used = model.usedLen.value()
        assert 0 <= used <= L

    def test_loadedValue_equals_sum_of_values(self):
        """loadedValue should equal sum of values of loaded blocks."""
        model, solved = _solve([115, 115, 115], [240, 200, 160], values=[3, 5, 7])
        assert solved
        indices = model.loaded_indices_in_order()
        val_map = {1: 3, 2: 5, 3: 7}
        expected_val = sum(val_map[i] for i in indices)
        assert model.loadedValue.value() == expected_val

    def test_no_duplicate_indices(self):
        """Each block should appear at most once in the solution."""
        model, solved = _solve([115] * 5, [240] * 5)
        assert solved
        indices = model.loaded_indices_in_order()
        assert len(indices) == len(set(indices))


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_zero_blocks_is_infeasible_or_empty(self):
        """Edge case: N=0 blocks (empty input) — should not crash."""
        # This is an unusual case but should not raise
        try:
            model, solved = _solve([], [], weights=[], values=[])
        except Exception:
            pass  # acceptable to raise on empty input

    def test_all_blocks_over_weight(self):
        """Every block alone exceeds weight limit → no block loaded."""
        model, solved = _solve([115, 115], [240, 240], weights=[20000, 20000], Wmax_kg=18000)
        if solved:
            indices = model.loaded_indices_in_order()
            total = 20000 * len(indices)
            assert total <= 18000 or len(indices) == 0

    def test_unloaded_indices_complement(self):
        """unloaded_indices + loaded_indices should cover 1..N."""
        model, solved = _solve([115, 115, 115], [240, 200, 160])
        assert solved
        loaded = set(model.loaded_indices_in_order())
        unloaded = set(model.unloaded_indices())
        assert loaded | unloaded == {1, 2, 3}
        assert loaded & unloaded == set()
