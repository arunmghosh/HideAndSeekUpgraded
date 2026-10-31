"""
simulate.py - Executes a single Hide and Seek game simulation on a chosen play grid.

Usage Examples:
    # Run default baseline game
    python simulate.py --grid baseline

    # Run hexagon grid with custom seed and round count
    python simulate.py --grid hexagon --rounds 30 --seed 42

    # Run sudoku grid and export single-game stats
    python simulate.py --grid sudoku_grid --export-excel plots/sudoku_single.xlsx
"""

import argparse
import sys
from typing import Optional, Union
import numpy as np

from grid_factory import (
    DEFAULT_CONFIGS,
    GameConfig,
    get_game_config,
    list_available_grids,
    normalize_grid_name,
)
from rules import GameEngine
from stat_tracker import StatTracker


def run_simulation(
    grid_name_or_config: Union[str, GameConfig],
    seed: Optional[int] = 42,
    num_players: Optional[int] = None,
    num_rounds: Optional[int] = None,
    timesteps_per_round: Optional[int] = None,
    policy: str = "strategic",
    verbose: bool = True,
) -> StatTracker:
    """
    Runs a single Hide and Seek game simulation to completion and returns the StatTracker.

    Args:
        grid_name_or_config: Canonical grid name (e.g. 'baseline', 'hexagon') or GameConfig object.
        seed: Random number generator seed for deterministic simulation.
        num_players: Optional override for player count.
        num_rounds: Optional override for round count.
        timesteps_per_round: Optional override for timesteps per round.
        policy: Movement decision policy ('strategic' or 'random').
        verbose: If True, prints round-by-round progress and game summary.

    Returns:
        StatTracker populated with all player-level, round-level, and time-series statistics.
    """
    if isinstance(grid_name_or_config, str):
        config = get_game_config(
            grid_name_or_config,
            seed=seed,
            num_players=num_players,
            num_rounds=num_rounds,
            timesteps_per_round=timesteps_per_round,
        )
    else:
        config = grid_name_or_config
        if seed is not None:
            config.seed = seed

    rng = np.random.default_rng(config.seed if config.seed is not None else 42)
    engine = GameEngine(config=config, policy=policy, rng=rng)
    tracker = StatTracker(
        game_name=config.display_name,
        num_players=config.num_players,
        num_rounds=config.num_rounds,
        timesteps_per_round=config.timesteps_per_round,
    )

    if verbose:
        print("=" * 72)
        print(f"Starting Simulation: {config.display_name}")
        print(f"  Rooms: {config.grid.num_rooms} | Hallways: {len(config.grid.edges)}")
        print(f"  Players: {config.num_players} | Rounds: {config.num_rounds} | Timesteps/Round: {config.timesteps_per_round}")
        print(f"  RNG Seed: {config.seed} | Policy: {policy}")
        print("=" * 72)

    for r in range(1, config.num_rounds + 1):
        round_res = engine.run_round(r)
        tracker.record_round(round_res)

        if verbose:
            active_count = len(round_res.scores_during_round) - len(round_res.sitting_out_players)
            print(
                f"Round {r:3d}/{config.num_rounds:3d} | "
                f"Active: {active_count:2d} | "
                f"Seekers: {len(round_res.seekers):2d} (score {round_res.seeker_score}) | "
                f"Coins: {len(round_res.coin_recipients)} | "
                f"Eliminated: {len(round_res.eliminated_player_ids):2d} | "
                f"Upgraded: {len(round_res.upgraded_player_ids):2d}"
            )

    tracker.finalize(engine)

    if verbose:
        print("\n" + "=" * 72)
        print("Simulation Completed Successfully!")
        summary = tracker.get_game_summary()
        print(f"  Winners: Player(s) {summary['winner_ids']} with Winning Score: {summary['winning_score']}")
        print(f"  Max Score Attained: {summary['max_score_attained']}")
        print(f"  Average Player Score: {summary['avg_player_score']:.4f}")
        print(f"  Total Eliminations: {summary['total_eliminations']}")
        print(f"  Total Upgrades: {summary['total_upgrades']}")
        print("=" * 72 + "\n")

    return tracker


def build_cli_parser() -> argparse.ArgumentParser:
    """Builds the command-line argument parser for simulate.py."""
    parser = argparse.ArgumentParser(
        description="Run a single Hide and Seek game simulation with a chosen play grid."
    )
    parser.add_argument(
        "-g", "--grid",
        type=str,
        default="baseline",
        choices=list(DEFAULT_CONFIGS.keys()) + ["pyramid", "sudoku", "hex"],
        help="Play grid configuration to simulate (default: baseline).",
    )
    parser.add_argument(
        "-p", "--players",
        type=int,
        default=None,
        help="Override total number of players.",
    )
    parser.add_argument(
        "-r", "--rounds",
        type=int,
        default=None,
        help="Override total number of rounds.",
    )
    parser.add_argument(
        "-t", "--timesteps",
        type=int,
        default=None,
        help="Override timesteps per round.",
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=42,
        help="RNG seed for deterministic replay (default: 42).",
    )
    parser.add_argument(
        "--policy",
        type=str,
        default="strategic",
        choices=["strategic", "random"],
        help="Movement policy for agents (default: strategic).",
    )
    parser.add_argument(
        "--export-excel",
        type=str,
        default=None,
        help="Optional file path to export single game statistics to Excel.",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress round-by-round logging.",
    )
    return parser


def main():
    parser = build_cli_parser()
    args = parser.parse_args()

    tracker = run_simulation(
        grid_name_or_config=args.grid,
        seed=args.seed,
        num_players=args.players,
        num_rounds=args.rounds,
        timesteps_per_round=args.timesteps,
        policy=args.policy,
        verbose=not args.quiet,
    )

    if args.export_excel:
        from make_figures import export_stats_to_excel
        canonical = normalize_grid_name(args.grid)
        export_stats_to_excel({canonical: tracker}, args.export_excel)
        print(f"Exported single-game statistics to: {args.export_excel}")


if __name__ == "__main__":
    main()

