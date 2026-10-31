"""
make_figures.py - Generates comparison plots and multi-sheet Excel statistics workbook.

Produces:
- plots/stats.xlsx: Comprehensive multi-sheet workbook of game, player, and round statistics
- plots/high_score_cdf.png: Empirical CDF of highest scores of each player over each game (overlayed)
- plots/med_score_cdf.png: Empirical CDF of median scores of each player over each game (overlayed)
- plots/med_score_vs_time.png: Plot of median player score at each timestep in each game (overlayed)
- plots/max_score_vs_time.png: Plot of max player score at each timestep in each game (overlayed)
"""

import os
import sys
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

# Headless matplotlib configuration
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from stat_tracker import StatTracker


# Consistent visual styling for games
GAME_COLORS = {
    "baseline": "#1f77b4",            # Blue
    "triangular_pyramid": "#ff7f0e",  # Orange
    "hexagon": "#2ca02c",             # Green
    "sudoku_grid": "#d62728",         # Red
}

GAME_STYLES = {
    "baseline": {"marker": "o", "linestyle": "-"},
    "triangular_pyramid": {"marker": "s", "linestyle": "-"},
    "hexagon": {"marker": "^", "linestyle": "-"},
    "sudoku_grid": {"marker": "D", "linestyle": "-"},
}


def ensure_output_dir(output_dir: str = "plots") -> str:
    """Creates output directory if it does not already exist."""
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def export_stats_to_excel(
    trackers: Dict[str, StatTracker],
    output_path: str = "plots/stats.xlsx"
) -> str:
    """
    Exports all collected statistics from all games into a beautifully formatted
    multi-sheet Excel workbook.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    summary_rows = []
    all_player_rows = []
    all_round_rows = []

    for name, tracker in trackers.items():
        # High-level game summary
        summary = tracker.get_game_summary()
        summary_rows.append(summary)

        # Player stats with game label
        pdf = tracker.get_player_stats_df().copy()
        pdf.insert(0, "game", tracker.game_name)
        all_player_rows.append(pdf)

        # Round stats with game label
        rdf = tracker.get_round_stats_df().copy()
        rdf.insert(0, "game", tracker.game_name)
        all_round_rows.append(rdf)

    summary_df = pd.DataFrame(summary_rows)
    all_players_df = pd.concat(all_player_rows, ignore_index=True) if all_player_rows else pd.DataFrame()
    all_rounds_df = pd.concat(all_round_rows, ignore_index=True) if all_round_rows else pd.DataFrame()

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Game_Summaries", index=False)
        all_players_df.to_excel(writer, sheet_name="All_Players_Comparison", index=False)
        all_rounds_df.to_excel(writer, sheet_name="All_Rounds_Comparison", index=False)

        # Per-game detail sheets
        for name, tracker in trackers.items():
            short_name = name[:15]
            tracker.get_player_stats_df().to_excel(
                writer, sheet_name=f"{short_name}_Players"[:31], index=False
            )
            tracker.get_round_stats_df().to_excel(
                writer, sheet_name=f"{short_name}_Rounds"[:31], index=False
            )

    return output_path


def plot_high_score_cdf(
    trackers: Dict[str, StatTracker],
    output_path: str = "plots/high_score_cdf.png"
) -> str:
    """
    Plots the Empirical Cumulative Distribution Function (ECDF) of highest scores
    attained by each player across each game, overlayed on a single plot.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    plt.figure(figsize=(9, 6), dpi=300)

    for name, tracker in trackers.items():
        pdf = tracker.get_player_stats_df()
        scores = np.sort(pdf["highest_score"].values)
        n = len(scores)
        ecdf = np.arange(1, n + 1) / n

        # Prepend 0 at min_score - 1 for proper step visualization
        x_steps = np.concatenate([[scores[0]], scores])
        y_steps = np.concatenate([[0.0], ecdf])

        color = GAME_COLORS.get(name, None)
        label = f"{tracker.game_name} (N={tracker.num_players})"
        plt.step(
            x_steps,
            y_steps,
            where="post",
            label=label,
            color=color,
            linewidth=2.2,
        )
        plt.plot(scores, ecdf, "o", color=color, alpha=0.6, markersize=5)

    plt.title("Empirical CDF of Player High Scores Across Play Grids", fontsize=14, fontweight="bold")
    plt.xlabel("Highest Score Attained", fontsize=12)
    plt.ylabel("Cumulative Probability P(Score ≤ x)", fontsize=12)
    plt.ylim(-0.02, 1.05)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="lower right", fontsize=10, frameon=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    return output_path


def plot_median_score_cdf(
    trackers: Dict[str, StatTracker],
    output_path: str = "plots/med_score_cdf.png"
) -> str:
    """
    Plots the Empirical Cumulative Distribution Function (ECDF) of each player's
    median round score throughout the game, overlayed for all games.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    plt.figure(figsize=(9, 6), dpi=300)

    for name, tracker in trackers.items():
        # Compute median round score for each player
        player_medians = [
            float(np.median(tracker.player_round_scores[pid]))
            for pid in range(tracker.num_players)
        ]
        values = np.sort(player_medians)
        n = len(values)
        ecdf = np.arange(1, n + 1) / n

        x_steps = np.concatenate([[values[0]], values])
        y_steps = np.concatenate([[0.0], ecdf])

        color = GAME_COLORS.get(name, None)
        label = f"{tracker.game_name} (N={tracker.num_players})"
        plt.step(
            x_steps,
            y_steps,
            where="post",
            label=label,
            color=color,
            linewidth=2.2,
        )
        plt.plot(values, ecdf, "s", color=color, alpha=0.6, markersize=5)

    plt.title("Empirical CDF of Player Median Scores Across Play Grids", fontsize=14, fontweight="bold")
    plt.xlabel("Median Player Round Score", fontsize=12)
    plt.ylabel("Cumulative Probability P(Median ≤ x)", fontsize=12)
    plt.ylim(-0.02, 1.05)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="lower right", fontsize=10, frameon=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    return output_path


def plot_median_score_vs_time(
    trackers: Dict[str, StatTracker],
    output_path: str = "plots/med_score_vs_time.png",
    use_normalized_time: bool = True,
) -> str:
    """
    Plots median player score at each timestep throughout each game (overlayed).
    If use_normalized_time is True, plots against percentage game progress (0% - 100%)
    so games with varying round/timestep lengths can be compared on the same scale.
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    plt.figure(figsize=(10, 6), dpi=300)

    for name, tracker in trackers.items():
        series = tracker.timestep_median_scores
        total_steps = len(series)
        if total_steps == 0:
            continue

        if use_normalized_time:
            x_axis = np.linspace(0, 100, total_steps)
            x_label = "Game Progress (%)"
        else:
            x_axis = np.arange(total_steps)
            x_label = "Simulation Timestep"

        color = GAME_COLORS.get(name, None)
        label = f"{tracker.game_name} ({tracker.num_rounds} rds, {tracker.timesteps_per_round} steps/rd)"
        plt.plot(
            x_axis,
            series,
            label=label,
            color=color,
            linewidth=2.0,
            alpha=0.85,
        )

    plt.title("Median Player Score vs. Time (Overlayed)", fontsize=14, fontweight="bold")
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel("Median Player Score", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper left", fontsize=10, frameon=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    return output_path


def plot_max_score_vs_time(
    trackers: Dict[str, StatTracker],
    output_path: str = "plots/max_score_vs_time.png",
    use_normalized_time: bool = True,
) -> str:
    """
    Plots maximum player score at each timestep throughout each game (overlayed).
    """
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    plt.figure(figsize=(10, 6), dpi=300)

    for name, tracker in trackers.items():
        series = tracker.timestep_max_scores
        total_steps = len(series)
        if total_steps == 0:
            continue

        if use_normalized_time:
            x_axis = np.linspace(0, 100, total_steps)
            x_label = "Game Progress (%)"
        else:
            x_axis = np.arange(total_steps)
            x_label = "Simulation Timestep"

        color = GAME_COLORS.get(name, None)
        label = f"{tracker.game_name} ({tracker.num_rounds} rds, {tracker.timesteps_per_round} steps/rd)"
        plt.plot(
            x_axis,
            series,
            label=label,
            color=color,
            linewidth=2.0,
            alpha=0.85,
        )

    plt.title("Maximum Player Score vs. Time (Overlayed)", fontsize=14, fontweight="bold")
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel("Maximum Player Score", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper left", fontsize=10, frameon=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    return output_path


def generate_all_figures_and_tables(
    trackers: Dict[str, StatTracker],
    output_dir: str = "plots"
) -> Dict[str, str]:
    """
    Generates the complete set of required plots and the Excel spreadsheet.
    Returns dictionary mapping artifact names to their file paths.
    """
    ensure_output_dir(output_dir)

    outputs = {
        "excel": export_stats_to_excel(
            trackers, os.path.join(output_dir, "stats.xlsx")
        ),
        "high_score_cdf": plot_high_score_cdf(
            trackers, os.path.join(output_dir, "high_score_cdf.png")
        ),
        "med_score_cdf": plot_median_score_cdf(
            trackers, os.path.join(output_dir, "med_score_cdf.png")
        ),
        "med_score_vs_time": plot_median_score_vs_time(
            trackers, os.path.join(output_dir, "med_score_vs_time.png")
        ),
        "max_score_vs_time": plot_max_score_vs_time(
            trackers, os.path.join(output_dir, "max_score_vs_time.png")
        ),
    }

    return outputs

