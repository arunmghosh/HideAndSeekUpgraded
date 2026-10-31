"""
stat_tracker.py - Statistics collection, aggregation, and analysis for Hide and Seek simulations.

Implements all Player-level, Round-level, and Game-level statistics from README.md Section 2:
- Player-level:
  * Highest score attained
  * Average score throughout the game (rounds sat out = 0)
  * Number of times eliminated
  * Number of rounds where they eliminated at least one player
  * Number of rounds as seeker
  * Longest streak not eliminated
  * Longest streak score upgraded
  * Longest streak as seeker
- Round-level:
  * Number of seekers
  * Seeker score
  * Median player score
  * Sum of all player scores
  * Number of players with score 1
  * Number of players eliminated
  * Number of players upgraded
- Game-level:
  * Empirical CDF distributions
  * Median and max score vs time curves
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from rules import GameEngine, RoundResult


@dataclass
class PlayerStats:
    """Aggregated statistics for a single player over a game."""
    player_id: int
    highest_score: int = 1
    average_score: float = 0.0
    total_eliminations_suffered: int = 0
    rounds_eliminated_others: int = 0
    rounds_as_seeker: int = 0
    longest_streak_not_eliminated: int = 0
    longest_streak_score_upgraded: int = 0
    longest_streak_as_seeker: int = 0
    final_score: int = 1
    is_winner: bool = False
    rounds_sat_out: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "highest_score": self.highest_score,
            "average_score": round(self.average_score, 4),
            "times_eliminated": self.total_eliminations_suffered,
            "rounds_eliminated_others": self.rounds_eliminated_others,
            "rounds_as_seeker": self.rounds_as_seeker,
            "longest_streak_not_eliminated": self.longest_streak_not_eliminated,
            "longest_streak_score_upgraded": self.longest_streak_score_upgraded,
            "longest_streak_as_seeker": self.longest_streak_as_seeker,
            "final_score": self.final_score,
            "is_winner": self.is_winner,
            "rounds_sat_out": self.rounds_sat_out,
        }


@dataclass
class RoundStats:
    """Statistics for a single round of the game."""
    round_idx: int
    num_seekers: int
    seeker_score: int
    median_active_score: float
    median_all_score: float
    sum_player_scores: int
    num_players_score_1: int
    num_eliminated: int
    num_upgraded: int
    max_score: int
    min_active_score: int
    active_player_count: int
    chest_room: int
    num_coins_awarded: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round": self.round_idx,
            "num_seekers": self.num_seekers,
            "seeker_score": self.seeker_score,
            "median_active_score": self.median_active_score,
            "median_all_score": self.median_all_score,
            "sum_player_scores": self.sum_player_scores,
            "num_players_score_1": self.num_players_score_1,
            "num_eliminated": self.num_eliminated,
            "num_upgraded": self.num_upgraded,
            "max_score": self.max_score,
            "min_active_score": self.min_active_score,
            "active_player_count": self.active_player_count,
            "chest_room": self.chest_room,
            "num_coins_awarded": self.num_coins_awarded,
        }


class StatTracker:
    """
    Collects, updates, and formats all required statistics during game execution.
    """

    def __init__(self, game_name: str, num_players: int, num_rounds: int, timesteps_per_round: int):
        self.game_name = game_name
        self.num_players = num_players
        self.num_rounds = num_rounds
        self.timesteps_per_round = timesteps_per_round

        # Round history
        self.round_results: List[RoundResult] = []
        self.round_stats_list: List[RoundStats] = []

        # Per-player per-round trajectory: player_id -> list of scores [r1, r2, ..., rR]
        self.player_round_scores: Dict[int, List[int]] = {i: [] for i in range(num_players)}
        self.player_eliminated_rounds: Dict[int, List[bool]] = {i: [] for i in range(num_players)}
        self.player_upgraded_rounds: Dict[int, List[bool]] = {i: [] for i in range(num_players)}
        self.player_seeker_rounds: Dict[int, List[bool]] = {i: [] for i in range(num_players)}
        self.player_eliminated_others_rounds: Dict[int, List[bool]] = {i: [] for i in range(num_players)}
        self.player_sat_out_rounds: Dict[int, List[bool]] = {i: [] for i in range(num_players)}

        # Timestep time series: global_step -> (median, max)
        self.timestep_median_scores: List[float] = []
        self.timestep_max_scores: List[int] = []

        # Winners
        self.winners: List[int] = []
        self.is_finalized: bool = False
        self.player_stats_map: Dict[int, PlayerStats] = {}

    def record_round(self, round_result: RoundResult):
        """Processes and archives the result of a single round."""
        self.round_results.append(round_result)
        r = round_result.round_idx

        # Scores during round (0 for sitting out)
        scores_during = round_result.scores_during_round
        all_scores = list(scores_during.values())
        active_scores = [
            scores_during[pid]
            for pid in scores_during
            if pid not in round_result.sitting_out_players
        ]

        # Calculate medians
        median_active = float(np.median(active_scores)) if active_scores else 0.0
        median_all = float(np.median(all_scores))
        sum_scores = sum(all_scores)
        max_score = max(all_scores) if all_scores else 0
        min_active = min(active_scores) if active_scores else 0
        num_score_1 = sum(1 for pid, s in scores_during.items() if s == 1 and pid not in round_result.sitting_out_players)

        # Round stats
        r_stat = RoundStats(
            round_idx=r,
            num_seekers=len(round_result.seekers),
            seeker_score=round_result.seeker_score,
            median_active_score=median_active,
            median_all_score=median_all,
            sum_player_scores=sum_scores,
            num_players_score_1=num_score_1,
            num_eliminated=len(round_result.eliminated_player_ids),
            num_upgraded=len(round_result.upgraded_player_ids),
            max_score=max_score,
            min_active_score=min_active,
            active_player_count=len(active_scores),
            chest_room=round_result.chest_room,
            num_coins_awarded=len(round_result.coin_recipients),
        )
        self.round_stats_list.append(r_stat)

        # Update per-player history
        elim_set = set(round_result.eliminated_player_ids)
        upg_set = set(round_result.upgraded_player_ids)
        seeker_set = set(round_result.seekers)
        sat_out_set = set(round_result.sitting_out_players)

        for pid in range(self.num_players):
            self.player_round_scores[pid].append(scores_during[pid])
            self.player_eliminated_rounds[pid].append(pid in elim_set)
            self.player_upgraded_rounds[pid].append(pid in upg_set)
            self.player_seeker_rounds[pid].append(pid in seeker_set)
            self.player_sat_out_rounds[pid].append(pid in sat_out_set)

            # Did player eliminate anyone this round?
            elim_others = len(round_result.eliminations_by_player.get(pid, [])) > 0
            self.player_eliminated_others_rounds[pid].append(elim_others)

        # Record timestep series from freezeframes
        for frame in round_result.freezeframes:
            frame_scores = [
                s for pid, s in frame.player_scores.items()
                if pid not in round_result.sitting_out_players
            ]
            if frame_scores:
                self.timestep_median_scores.append(float(np.median(frame_scores)))
                self.timestep_max_scores.append(int(max(frame_scores)))
            else:
                self.timestep_median_scores.append(0.0)
                self.timestep_max_scores.append(0)

    def finalize(self, engine: GameEngine):
        """Computes all final aggregated statistics once simulation is complete."""
        self.winners = list(engine.winners)
        self.player_stats_map = {}

        for pid in range(self.num_players):
            round_scores = self.player_round_scores[pid]
            final_player_score = engine.players[pid].score

            # Highest score attained (during rounds or final post-round update)
            highest_score = max(round_scores + [final_player_score]) if round_scores else final_player_score

            # Average score throughout the game (rounds sat out treated as score 0)
            avg_score = float(np.mean(round_scores)) if round_scores else 0.0

            # Counts
            times_elim = sum(self.player_eliminated_rounds[pid])
            rounds_elim_others = sum(self.player_eliminated_others_rounds[pid])
            rounds_as_seeker = sum(self.player_seeker_rounds[pid])
            rounds_sat_out = sum(self.player_sat_out_rounds[pid])

            # Streaks
            streak_not_elim = self._calculate_longest_streak(
                [not e and not s for e, s in zip(self.player_eliminated_rounds[pid], self.player_sat_out_rounds[pid])]
            )
            streak_upgraded = self._calculate_longest_streak(self.player_upgraded_rounds[pid])
            streak_seeker = self._calculate_longest_streak(self.player_seeker_rounds[pid])

            self.player_stats_map[pid] = PlayerStats(
                player_id=pid,
                highest_score=highest_score,
                average_score=avg_score,
                total_eliminations_suffered=times_elim,
                rounds_eliminated_others=rounds_elim_others,
                rounds_as_seeker=rounds_as_seeker,
                longest_streak_not_eliminated=streak_not_elim,
                longest_streak_score_upgraded=streak_upgraded,
                longest_streak_as_seeker=streak_seeker,
                final_score=final_player_score,
                is_winner=(pid in self.winners),
                rounds_sat_out=rounds_sat_out,
            )

        self.is_finalized = True

    @staticmethod
    def _calculate_longest_streak(bool_sequence: List[bool]) -> int:
        """Computes the maximum consecutive True elements in a list."""
        max_streak = 0
        current_streak = 0
        for val in bool_sequence:
            if val:
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0
        return max_streak

    def get_player_stats_df(self) -> pd.DataFrame:
        """Returns player statistics as a pandas DataFrame."""
        if not self.is_finalized:
            raise RuntimeError("StatTracker must be finalized before generating DataFrame.")
        rows = [self.player_stats_map[pid].to_dict() for pid in range(self.num_players)]
        df = pd.DataFrame(rows)
        return df

    def get_round_stats_df(self) -> pd.DataFrame:
        """Returns round statistics as a pandas DataFrame."""
        rows = [rs.to_dict() for rs in self.round_stats_list]
        return pd.DataFrame(rows)

    def get_game_summary(self) -> Dict[str, Any]:
        """Returns high-level summary metrics of the entire game."""
        player_df = self.get_player_stats_df()
        round_df = self.get_round_stats_df()

        return {
            "game_name": self.game_name,
            "num_players": self.num_players,
            "num_rounds": self.num_rounds,
            "timesteps_per_round": self.timesteps_per_round,
            "max_score_attained": int(player_df["highest_score"].max()),
            "avg_player_score": float(round(player_df["average_score"].mean(), 4)),
            "total_eliminations": int(player_df["times_eliminated"].sum()),
            "total_upgrades": int(round_df["num_upgraded"].sum()),
            "winner_ids": self.winners,
            "num_winners": len(self.winners),
            "winning_score": int(player_df[player_df["is_winner"]]["final_score"].iloc[0]) if len(self.winners) > 0 else 1,
        }

    # Empirical CDF helper
    def get_ecdf(self, column: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes the empirical cumulative distribution function (ECDF) for a player stat column.
        Returns: (sorted_values, cdf_probabilities)
        """
        df = self.get_player_stats_df()
        values = np.sort(df[column].values)
        n = len(values)
        if n == 0:
            return np.array([]), np.array([])
        ecdf = np.arange(1, n + 1) / n
        return values, ecdf

