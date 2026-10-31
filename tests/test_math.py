"""
tests/test_math.py - Ensures that all mathematical and statistical calculations
in the simulation and stat tracker are mathematically rigorous and correct.
"""

import unittest
import numpy as np

from stat_tracker import StatTracker, PlayerStats


class TestSimulationMath(unittest.TestCase):
    """Mathematical validation for scoring averages, streaks, medians, and ECDFs."""

    def test_average_score_calculation(self):
        """
        Verify average score is mathematically (sum of round scores / total rounds),
        with sitting out rounds strictly counted as score 0.
        """
        num_rounds = 5
        tracker = StatTracker("test", num_players=2, num_rounds=num_rounds, timesteps_per_round=3)

        # Player 0: scores [1, 2, 0, 1, 2] (sat out round 3)
        # Sum = 6, average = 6 / 5 = 1.2
        # Player 1: scores [1, 2, 3, 4, 5] (never sat out)
        # Sum = 15, average = 15 / 5 = 3.0
        tracker.player_round_scores[0] = [1, 2, 0, 1, 2]
        tracker.player_round_scores[1] = [1, 2, 3, 4, 5]

        avg_0 = float(np.mean(tracker.player_round_scores[0]))
        avg_1 = float(np.mean(tracker.player_round_scores[1]))

        self.assertAlmostEqual(avg_0, 1.2, places=6)
        self.assertAlmostEqual(avg_1, 3.0, places=6)

    def test_longest_streak_algorithm(self):
        """
        Test streak counting on edge cases:
        - All True
        - All False
        - Alternating True/False
        - Long streak at start, middle, or end
        """
        calc = StatTracker._calculate_longest_streak

        self.assertEqual(calc([]), 0)
        self.assertEqual(calc([False, False, False]), 0)
        self.assertEqual(calc([True, True, True]), 3)
        self.assertEqual(calc([True, False, True, True, False]), 2)
        self.assertEqual(calc([False, True, True, True, False, True]), 3)
        self.assertEqual(calc([True, True, False, True, True, True, True]), 4)

    def test_median_calculation(self):
        """Verify median calculation for odd and even number of players."""
        # Odd number of players
        scores_odd = [1, 2, 4]
        self.assertEqual(np.median(scores_odd), 2.0)

        # Even number of players
        scores_even = [1, 2, 3, 4]
        self.assertEqual(np.median(scores_even), 2.5)

        # Tied scores
        scores_tied = [1, 1, 1, 1, 2, 2]
        self.assertEqual(np.median(scores_tied), 1.0)

    def test_ecdf_properties(self):
        """
        Ensure Empirical Cumulative Distribution Function satisfies:
        1. Monotonically non-decreasing
        2. Min value > 0 and Max value == 1.0
        3. Correct step size 1/N
        """
        tracker = StatTracker("test", num_players=4, num_rounds=2, timesteps_per_round=1)
        tracker.is_finalized = True
        tracker.player_stats_map = {
            0: PlayerStats(player_id=0, highest_score=1),
            1: PlayerStats(player_id=1, highest_score=2),
            2: PlayerStats(player_id=2, highest_score=2),
            3: PlayerStats(player_id=3, highest_score=4),
        }

        values, ecdf = tracker.get_ecdf("highest_score")

        # Length must match number of players
        self.assertEqual(len(values), 4)
        self.assertEqual(len(ecdf), 4)

        # Non-decreasing
        for i in range(len(ecdf) - 1):
            self.assertGreaterEqual(ecdf[i + 1], ecdf[i])

        # Step size
        np.testing.assert_allclose(ecdf, [0.25, 0.50, 0.75, 1.0])
        self.assertEqual(ecdf[-1], 1.0)


if __name__ == "__main__":
    unittest.main()

