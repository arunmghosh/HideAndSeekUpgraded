"""
tests/test_experiment.py - Validates that the experiment pipeline, statistics dataframes,
Excel workbook generation, and figure generation produce correct outputs and formats.
"""

import os
import shutil
import tempfile
import unittest
import openpyxl

from grid_factory import get_game_config
from make_figures import (
    export_stats_to_excel,
    generate_all_figures_and_tables,
    plot_high_score_cdf,
    plot_max_score_vs_time,
    plot_median_score_cdf,
    plot_median_score_vs_time,
)
from simulate import run_simulation


class TestExperimentPipeline(unittest.TestCase):
    """Verifies dataframe formats, Excel output schema, and visualization files."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_single_game_simulation_and_dataframe_structure(self):
        """Run mini game and assert all required columns exist in DataFrames."""
        config = get_game_config("baseline", seed=42, num_players=4, num_rounds=3, timesteps_per_round=2)
        tracker = run_simulation(config, seed=42, verbose=False)

        # 1. Player DataFrame verification
        pdf = tracker.get_player_stats_df()
        expected_player_cols = [
            "player_id",
            "highest_score",
            "average_score",
            "times_eliminated",
            "rounds_eliminated_others",
            "rounds_as_seeker",
            "longest_streak_not_eliminated",
            "longest_streak_score_upgraded",
            "longest_streak_as_seeker",
            "final_score",
            "is_winner",
            "rounds_sat_out",
        ]
        for col in expected_player_cols:
            self.assertIn(col, pdf.columns, f"Missing player column: {col}")
        self.assertEqual(len(pdf), 4)

        # 2. Round DataFrame verification
        rdf = tracker.get_round_stats_df()
        expected_round_cols = [
            "round",
            "num_seekers",
            "seeker_score",
            "median_active_score",
            "median_all_score",
            "sum_player_scores",
            "num_players_score_1",
            "num_eliminated",
            "num_upgraded",
            "max_score",
            "min_active_score",
            "active_player_count",
            "chest_room",
            "num_coins_awarded",
        ]
        for col in expected_round_cols:
            self.assertIn(col, rdf.columns, f"Missing round column: {col}")
        self.assertEqual(len(rdf), 3)

    def test_excel_export_schema(self):
        """Verify Excel workbook is created with all expected sheets and valid tables."""
        config_a = get_game_config("baseline", seed=42, num_players=4, num_rounds=2, timesteps_per_round=2)
        config_b = get_game_config("triangular_pyramid", seed=43, num_players=4, num_rounds=2, timesteps_per_round=2)

        tracker_a = run_simulation(config_a, seed=42, verbose=False)
        tracker_b = run_simulation(config_b, seed=43, verbose=False)

        trackers = {"baseline": tracker_a, "triangular_pyramid": tracker_b}
        excel_path = os.path.join(self.temp_dir, "test_stats.xlsx")
        export_stats_to_excel(trackers, excel_path)

        self.assertTrue(os.path.exists(excel_path))
        wb = openpyxl.load_workbook(excel_path)
        sheet_names = wb.sheetnames
        self.assertIn("Game_Summaries", sheet_names)
        self.assertIn("All_Players_Comparison", sheet_names)
        self.assertIn("All_Rounds_Comparison", sheet_names)
        wb.close()

    def test_figure_generation(self):
        """Verify all 4 plot functions produce non-empty image files."""
        config_a = get_game_config("baseline", seed=42, num_players=4, num_rounds=2, timesteps_per_round=2)
        config_b = get_game_config("hexagon", seed=43, num_players=6, num_rounds=2, timesteps_per_round=2)

        tracker_a = run_simulation(config_a, seed=42, verbose=False)
        tracker_b = run_simulation(config_b, seed=43, verbose=False)
        trackers = {"baseline": tracker_a, "hexagon": tracker_b}

        artifacts = generate_all_figures_and_tables(trackers, output_dir=self.temp_dir)

        expected_keys = ["excel", "high_score_cdf", "med_score_cdf", "med_score_vs_time", "max_score_vs_time"]
        for k in expected_keys:
            self.assertIn(k, artifacts)
            file_path = artifacts[k]
            self.assertTrue(os.path.exists(file_path), f"File {file_path} was not created.")
            self.assertGreater(os.path.getsize(file_path), 0, f"File {file_path} is empty.")


if __name__ == "__main__":
    unittest.main()

