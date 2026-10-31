"""
tests/test_smoke.py - Rapid end-to-end smoke test validating all components and configurations.
"""

import unittest
from grid_factory import DEFAULT_CONFIGS, get_game_config
from simulate import run_simulation


class TestSmoke(unittest.TestCase):
    """Rapid smoke test running minimal simulations across all 4 grid types."""

    def test_all_four_grids_smoke(self):
        """Runs a 1-round, 2-timestep smoke simulation for every supported play grid."""
        for grid_name in ["baseline", "triangular_pyramid", "hexagon", "sudoku_grid"]:
            with self.subTest(grid=grid_name):
                # Scaled-down mini config for ultra-fast verification
                config = get_game_config(
                    grid_name,
                    seed=42,
                    num_players=6,
                    num_rounds=1,
                    timesteps_per_round=2,
                )
                tracker = run_simulation(config, seed=42, verbose=False)
                self.assertTrue(tracker.is_finalized)
                self.assertEqual(len(tracker.round_results), 1)
                self.assertGreaterEqual(len(tracker.winners), 1)


if __name__ == "__main__":
    unittest.main()

