"""
experiment.py - Executes the full experimental suite across all four play grids (a) - (d)
and generates comparative figures and statistics workbook.

Experiments:
  a) Baseline: 2 rooms, 6 players, 10 rounds, 3 timesteps/round
  b) Triangular Pyramid: 4 rooms (K4), 12 players, 25 rounds, 5 timesteps/round
  c) The Hexagon: 6 rooms (C6), 18 players, 50 rounds, 8 timesteps/round
  d) Sudoku Grid: 9 rooms (3x3), 27 players, 100 rounds, 10 timesteps/round

Outputs:
  plots/stats.xlsx
  plots/high_score_cdf.png
  plots/med_score_cdf.png
  plots/med_score_vs_time.png
  plots/max_score_vs_time.png

Usage:
  python experiment.py
  python experiment.py --seed 12345 --output-dir plots/
"""

import argparse
import os
import sys
import time
from typing import Dict, Optional
import numpy as np
import pandas as pd

from grid_factory import DEFAULT_CONFIGS, get_game_config
from make_figures import generate_all_figures_and_tables
from simulate import run_simulation
from stat_tracker import StatTracker


# The canonical order of experiments specified in README.md Section 3
EXPERIMENT_ORDER = [
    "baseline",
    "triangular_pyramid",
    "hexagon",
    "sudoku_grid",
]


def run_all_experiments(
    base_seed: int = 42,
    output_dir: str = "plots",
    policy: str = "strategic",
    verbose: bool = True,
) -> Dict[str, StatTracker]:
    """
    Runs all 4 simulation games using a coordinated RNG seed sequence,
    collects all statistics, and outputs the comparison charts and Excel workbook.

    Args:
        base_seed: Master seed for the experiment RNG stream.
        output_dir: Directory where figures and spreadsheet will be saved.
        policy: Player movement policy ('strategic' or 'random').
        verbose: If True, prints progress updates and summary tables.

    Returns:
        Dict mapping canonical game key to its completed StatTracker.
    """
    start_time = time.time()
    ss = np.random.SeedSequence(base_seed)
    child_seeds = ss.spawn(len(EXPERIMENT_ORDER))

    trackers: Dict[str, StatTracker] = {}

    if verbose:
        print("\n" + "=" * 80)
        print("🚀 STARTING FULL HIDE AND SEEK EXPERIMENT SUITE")
        print(f"Master Seed: {base_seed} | Policy: {policy} | Output Directory: {output_dir}")
        print("=" * 80)

    for idx, key in enumerate(EXPERIMENT_ORDER):
        seed_val = int(child_seeds[idx].generate_state(1)[0])
        config = get_game_config(key, seed=seed_val)

        if verbose:
            print(f"\n[{idx + 1}/4] Running Simulation: {config.display_name} (seed={seed_val}) ...")

        # Run the simulation for this configuration
        tracker = run_simulation(
            grid_name_or_config=config,
            seed=seed_val,
            policy=policy,
            verbose=False,  # Keep inner round logs compact during full pipeline
        )
        trackers[key] = tracker

        if verbose:
            summary = tracker.get_game_summary()
            print(
                f"   ✓ Finished {config.display_name}: "
                f"Rounds={config.num_rounds}, Players={config.num_players}, "
                f"MaxScore={summary['max_score_attained']}, "
                f"Winners={summary['winner_ids']} (Score {summary['winning_score']})"
            )

    if verbose:
        print("\n" + "-" * 80)
        print("📊 Generating Visualizations and Comparison Spreadsheet...")
        print("-" * 80)

    # Generate all plots and the stats.xlsx file
    artifacts = generate_all_figures_and_tables(trackers, output_dir=output_dir)

    elapsed = time.time() - start_time
    if verbose:
        print("\n" + "=" * 80)
        print("🎉 EXPERIMENT SUITE COMPLETED SUCCESSFULLY!")
        print(f"Total Elapsed Time: {elapsed:.2f} seconds")
        print("\nGenerated Artifacts:")
        for name, path in artifacts.items():
            print(f"  • {name:18s} -> {path}")

        # Print comparison summary table
        print("\n" + "=" * 80)
        print("📈 EXPERIMENT COMPARISON SUMMARY")
        print("=" * 80)
        summary_rows = [t.get_game_summary() for t in trackers.values()]
        summary_df = pd.DataFrame(summary_rows)
        # Select concise display columns
        display_cols = [
            "game_name", "num_rooms" if "num_rooms" in summary_df else "num_players",
            "num_rounds", "timesteps_per_round", "max_score_attained",
            "avg_player_score", "total_eliminations", "total_upgrades", "winning_score"
        ]
        valid_cols = [c for c in display_cols if c in summary_df.columns]
        print(summary_df[valid_cols].to_string(index=False))
        print("=" * 80 + "\n")

    return trackers


def build_cli_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser for experiment.py."""
    parser = argparse.ArgumentParser(
        description="Run the full Hide and Seek experiment pipeline across all 4 play grids."
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=42,
        help="Master RNG seed for experiment reproducibility (default: 42).",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default="plots",
        help="Target directory for generated figures and stats.xlsx (default: plots).",
    )
    parser.add_argument(
        "--policy",
        type=str,
        default="strategic",
        choices=["strategic", "random"],
        help="Movement policy for simulated players (default: strategic).",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress console output.",
    )
    return parser


def main():
    parser = build_cli_parser()
    args = parser.parse_args()

    run_all_experiments(
        base_seed=args.seed,
        output_dir=args.output_dir,
        policy=args.policy,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()

