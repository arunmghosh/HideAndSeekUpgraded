"""
rules.py - Core game mechanics, player state, movement logic, and round lifecycle.

Implements all specifications from HideAndSeek_FullGameSpec.pdf and README.md:
- Initial score 1 for all players in round 1
- Higher-up: player with score exactly (your_score + 1)
- Prey: player with score exactly (your_score - 1)
- Chest & coin mechanics for score 1 players
- Freeze at end of round (timestep T)
- Elimination when sharing room with a higher-up at freeze
- Elimination consequences: sit out the next round, return with score 1
- Score upgrade: score 1 with coin promotes to 2; score >= 2 promotes by +1 if eliminating prey
- Seeker: player with sole or tied highest score
- Winners: seekers after scores are updated at the end of the final round
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from grid_factory import GameConfig, PlayGrid


@dataclass
class Player:
    """Tracks state and history for an individual player."""
    player_id: int
    score: int = 1
    current_room: Optional[int] = None
    has_coin: bool = False
    is_sitting_out: bool = False
    eliminated_in_round: Optional[int] = None

    def reset_for_rejoin(self):
        """Reset player state when rejoining after sitting out."""
        self.score = 1
        self.is_sitting_out = False
        self.current_room = None
        self.has_coin = False
        self.eliminated_in_round = None


@dataclass
class FreezeFrame:
    """State of the play grid (player locations and status) at any given timestep."""
    round_idx: int
    timestep: int
    is_freeze: bool
    player_rooms: Dict[int, Optional[int]]
    player_scores: Dict[int, int]
    chest_room: int
    chest_claimed: bool
    coin_holders: List[int]


@dataclass
class RoundResult:
    """Complete summary of outcomes at the end of a round."""
    round_idx: int
    chest_room: int
    coin_recipients: List[int]
    eliminated_player_ids: List[int]
    upgraded_player_ids: List[int]
    eliminations_by_player: Dict[int, List[int]]  # player_id -> list of victims
    eliminated_by_player: Dict[int, List[int]]    # victim_id -> list of higher-ups in room
    seekers: List[int]                            # seekers during this round (pre-freeze)
    seeker_score: int                             # score of seekers during round
    scores_during_round: Dict[int, int]           # player_id -> score during round (0 if sitting out)
    scores_after_round: Dict[int, int]            # player_id -> score after upgrades/eliminations
    sitting_out_players: List[int]                # players who sat out this round
    freezeframes: List[FreezeFrame]               # frame at each timestep 0..T


class StrategicPolicy:
    """
    Intelligent agent decision policy implementing:
    - Score 1 players seek chest until claimed, and avoid score 2 higher-ups.
    - Score >= 2 players chase prey (score - 1) and avoid higher-ups (score + 1).
    - Seekers have no higher-ups, so they purely chase prey.
    - Urgency of threat evasion increases as the round approaches the freeze (timestep T).
    """

    @staticmethod
    def choose_move(
        player: Player,
        players: Dict[int, Player],
        grid: PlayGrid,
        chest_room: int,
        chest_claimed: bool,
        current_timestep: int,
        total_timesteps: int,
        rng: np.random.Generator,
    ) -> int:
        valid_moves = grid.get_valid_moves(player.current_room)
        if len(valid_moves) == 1:
            return valid_moves[0]

        # Remaining steps until freeze (including current step)
        steps_to_freeze = total_timesteps - current_timestep
        urgency = 1.0 + (3.0 / (steps_to_freeze + 1.0))

        my_score = player.score
        candidate_scores: Dict[int, float] = {}

        # Precompute positions of active prey and higher-ups
        higher_up_rooms = [
            other.current_room
            for other in players.values()
            if not other.is_sitting_out
            and other.current_room is not None
            and other.player_id != player.player_id
            and other.score == my_score + 1
        ]

        prey_rooms = [
            other.current_room
            for other in players.values()
            if not other.is_sitting_out
            and other.current_room is not None
            and other.player_id != player.player_id
            and other.score == my_score - 1
        ]

        for cand in valid_moves:
            utility = 0.0

            # 1. Threat avoidance (higher-ups)
            if higher_up_rooms:
                min_threat_dist = min(grid.get_distance(cand, hr) for hr in higher_up_rooms)
                if min_threat_dist == 0:
                    # Dire danger of elimination at freeze
                    utility -= 200.0 * urgency
                elif min_threat_dist == 1:
                    utility -= 50.0 * urgency
                else:
                    utility += 10.0 * min_threat_dist

            # 2. Score 1 Chest pursuit
            if my_score == 1:
                if not player.has_coin and not chest_claimed:
                    dist_to_chest = grid.get_distance(cand, chest_room)
                    utility += 80.0 / (dist_to_chest + 1.0)
                elif player.has_coin:
                    # Player already has coin: survival until freeze is paramount
                    # Extra preference to keep distance from any potential threat
                    pass

            # 3. Prey pursuit (score >= 2)
            if my_score >= 2 and prey_rooms:
                min_prey_dist = min(grid.get_distance(cand, pr) for pr in prey_rooms)
                if min_prey_dist == 0:
                    # Opportunity to eliminate prey at freeze
                    utility += 100.0 * urgency
                else:
                    utility += 40.0 / (min_prey_dist + 1.0)

            # Small random noise for tie-breaking and exploration
            utility += float(rng.uniform(-0.05, 0.05))
            candidate_scores[cand] = utility

        # Select move with highest utility
        best_cand = max(valid_moves, key=lambda c: candidate_scores[c])
        return best_cand


class RandomPolicy:
    """Random movement policy: uniformly choose among valid moves."""

    @staticmethod
    def choose_move(
        player: Player,
        players: Dict[int, Player],
        grid: PlayGrid,
        chest_room: int,
        chest_claimed: bool,
        current_timestep: int,
        total_timesteps: int,
        rng: np.random.Generator,
    ) -> int:
        valid_moves = grid.get_valid_moves(player.current_room)
        return int(rng.choice(valid_moves))


class GameEngine:
    """
    Manages the full execution of a Hide and Seek game simulation.
    """

    def __init__(
        self,
        config: GameConfig,
        policy: str = "strategic",
        rng: Optional[np.random.Generator] = None,
    ):
        self.config = config
        self.grid = config.grid
        self.rng = (
            rng
            if rng is not None
            else np.random.default_rng(config.seed if config.seed is not None else 42)
        )
        self.policy_name = policy
        self.policy = (
            StrategicPolicy if policy == "strategic" else RandomPolicy
        )

        # Initialize all players with score 1
        self.players: Dict[int, Player] = {
            i: Player(player_id=i, score=1) for i in range(config.num_players)
        }
        self.current_round: int = 0
        self.is_game_over: bool = False
        self.winners: List[int] = []

    def get_active_players(self) -> List[Player]:
        """Returns list of players participating in the current round."""
        return [p for p in self.players.values() if not p.is_sitting_out]

    def run_round(self, round_idx: int) -> RoundResult:
        """
        Executes a single round from start to freeze.
        """
        self.current_round = round_idx

        # 1. Update sitting out / rejoining players
        for p in self.players.values():
            if p.is_sitting_out:
                # If eliminated in previous round, they sit out this round
                if p.eliminated_in_round == round_idx - 1:
                    p.current_room = None
                    p.has_coin = False
                # If they already sat out the required round, they rejoin with score 1
                elif p.eliminated_in_round is not None and p.eliminated_in_round < round_idx - 1:
                    p.reset_for_rejoin()

        active_players = self.get_active_players()
        sitting_out_players = [p.player_id for p in self.players.values() if p.is_sitting_out]

        # Record scores at start of round
        scores_during_round: Dict[int, int] = {}
        for p in self.players.values():
            scores_during_round[p.player_id] = 0 if p.is_sitting_out else p.score

        # Identify seekers during this round
        active_scores = [p.score for p in active_players]
        max_active_score = max(active_scores) if active_scores else 1
        seekers = [p.player_id for p in active_players if p.score == max_active_score]

        # 2. Chest placement (uniform random across rooms)
        chest_room = int(self.rng.integers(0, self.grid.num_rooms))
        chest_claimed = False
        coin_recipients: List[int] = []

        # 3. Initial player placement at timestep 0
        for p in active_players:
            p.current_room = int(self.rng.integers(0, self.grid.num_rooms))
            p.has_coin = False

        freezeframes: List[FreezeFrame] = []

        # Check timestep 0 chest claim
        score_1_in_chest = [
            p.player_id
            for p in active_players
            if p.score == 1 and p.current_room == chest_room
        ]
        if score_1_in_chest:
            chest_claimed = True
            for pid in score_1_in_chest:
                self.players[pid].has_coin = True
                coin_recipients.append(pid)

        # Record timestep 0 freezeframe
        freezeframes.append(
            FreezeFrame(
                round_idx=round_idx,
                timestep=0,
                is_freeze=False,
                player_rooms={
                    pid: p.current_room for pid, p in self.players.items()
                },
                player_scores={
                    pid: scores_during_round[pid] for pid in self.players
                },
                chest_room=chest_room,
                chest_claimed=chest_claimed,
                coin_holders=list(coin_recipients),
            )
        )

        # 4. Timestep movement loop (1 to timesteps_per_round)
        total_steps = self.config.timesteps_per_round
        for t in range(1, total_steps + 1):
            is_freeze_step = (t == total_steps)

            # Players decide moves
            next_positions: Dict[int, int] = {}
            for p in active_players:
                next_room = self.policy.choose_move(
                    player=p,
                    players=self.players,
                    grid=self.grid,
                    chest_room=chest_room,
                    chest_claimed=chest_claimed,
                    current_timestep=t,
                    total_timesteps=total_steps,
                    rng=self.rng,
                )
                next_positions[p.player_id] = next_room

            # Update positions simultaneously
            for p in active_players:
                p.current_room = next_positions[p.player_id]

            # Chest claim check at this timestep (if not previously claimed)
            if not chest_claimed:
                first_group = [
                    p.player_id
                    for p in active_players
                    if p.score == 1 and p.current_room == chest_room
                ]
                if first_group:
                    chest_claimed = True
                    for pid in first_group:
                        self.players[pid].has_coin = True
                        coin_recipients.append(pid)

            # Record frame
            freezeframes.append(
                FreezeFrame(
                    round_idx=round_idx,
                    timestep=t,
                    is_freeze=is_freeze_step,
                    player_rooms={
                        pid: p.current_room for pid, p in self.players.items()
                    },
                    player_scores={
                        pid: scores_during_round[pid] for pid in self.players
                    },
                    chest_room=chest_room,
                    chest_claimed=chest_claimed,
                    coin_holders=[p.player_id for p in active_players if p.has_coin],
                )
            )

        # 5. Evaluate Freeze at timestep T
        eliminated_player_ids: List[int] = []
        upgraded_player_ids: List[int] = []
        eliminations_by_player: Dict[int, List[int]] = {
            p.player_id: [] for p in self.players.values()
        }
        eliminated_by_player: Dict[int, List[int]] = {
            p.player_id: [] for p in self.players.values()
        }

        # Group active players by room
        room_occupants: Dict[int, List[Player]] = {
            r: [] for r in range(self.grid.num_rooms)
        }
        for p in active_players:
            if p.current_room is not None:
                room_occupants[p.current_room].append(p)

        # Determine eliminations
        for room, occupants in room_occupants.items():
            for p in occupants:
                higher_ups = [
                    h for h in occupants if h.score == p.score + 1
                ]
                if higher_ups:
                    eliminated_player_ids.append(p.player_id)
                    for h in higher_ups:
                        eliminations_by_player[h.player_id].append(p.player_id)
                        eliminated_by_player[p.player_id].append(h.player_id)

        eliminated_set = set(eliminated_player_ids)

        # Determine score upgrades:
        # A. Score 1 player: has coin AND was not eliminated -> upgrades to 2
        for p in active_players:
            if p.score == 1 and p.player_id not in eliminated_set and p.has_coin:
                upgraded_player_ids.append(p.player_id)

        # B. Score >= 2 player: eliminated at least one player AND was not eliminated -> score + 1
        for p in active_players:
            if p.score >= 2 and p.player_id not in eliminated_set:
                if len(eliminations_by_player[p.player_id]) > 0:
                    upgraded_player_ids.append(p.player_id)

        upgraded_set = set(upgraded_player_ids)

        # Apply state changes for next round
        scores_after_round: Dict[int, int] = {}
        for p in self.players.values():
            if p.player_id in eliminated_set:
                p.is_sitting_out = True
                p.eliminated_in_round = round_idx
                p.has_coin = False
                # Score upon rejoining will be 1
                scores_after_round[p.player_id] = 1
            elif p.player_id in upgraded_set:
                p.score += 1
                p.has_coin = False
                scores_after_round[p.player_id] = p.score
            else:
                p.has_coin = False
                scores_after_round[p.player_id] = p.score

        # Check if game is over (final round completed)
        if round_idx == self.config.num_rounds:
            self.is_game_over = True
            final_scores = [self.players[pid].score for pid in self.players]
            max_final_score = max(final_scores)
            self.winners = [
                pid for pid in self.players if self.players[pid].score == max_final_score
            ]

        return RoundResult(
            round_idx=round_idx,
            chest_room=chest_room,
            coin_recipients=coin_recipients,
            eliminated_player_ids=eliminated_player_ids,
            upgraded_player_ids=upgraded_player_ids,
            eliminations_by_player=eliminations_by_player,
            eliminated_by_player=eliminated_by_player,
            seekers=seekers,
            seeker_score=max_active_score,
            scores_during_round=scores_during_round,
            scores_after_round=scores_after_round,
            sitting_out_players=sitting_out_players,
            freezeframes=freezeframes,
        )

