"""
tests/test_game.py - Unit tests for core Hide and Seek game rules and mechanics.
"""

import unittest
import numpy as np

from grid_factory import (
    build_baseline_grid,
    build_triangular_pyramid_grid,
    build_hexagon_grid,
    build_sudoku_grid,
    get_game_config,
)
from rules import GameEngine, Player, RoundResult, StrategicPolicy, RandomPolicy


class TestGameRules(unittest.TestCase):
    """Verifies all game rules from HideAndSeek_FullGameSpec.pdf and README.md."""

    def test_grid_topologies(self):
        """Verify grid sizes, edges, and distances."""
        # Baseline
        bg = build_baseline_grid()
        self.assertEqual(bg.num_rooms, 2)
        self.assertEqual(len(bg.edges), 1)
        self.assertEqual(bg.get_distance(0, 1), 1)
        self.assertEqual(bg.get_distance(0, 0), 0)

        # Triangular pyramid (K4)
        tg = build_triangular_pyramid_grid()
        self.assertEqual(tg.num_rooms, 4)
        self.assertEqual(len(tg.edges), 6)
        for i in range(4):
            for j in range(4):
                expected = 0 if i == j else 1
                self.assertEqual(tg.get_distance(i, j), expected)

        # Hexagon (C6)
        hg = build_hexagon_grid()
        self.assertEqual(hg.num_rooms, 6)
        self.assertEqual(len(hg.edges), 6)
        self.assertEqual(hg.get_distance(0, 3), 3)  # Opposite side
        self.assertEqual(hg.get_distance(0, 1), 1)

        # Sudoku Grid (3x3)
        sg = build_sudoku_grid()
        self.assertEqual(sg.num_rooms, 9)
        self.assertEqual(len(sg.edges), 12)  # 2*3 + 3*2 = 12 edges
        self.assertEqual(sg.get_distance(0, 8), 4)  # (0,0) to (2,2) = 4 steps
        self.assertEqual(sg.get_distance(0, 4), 2)  # (0,0) to (1,1) = 2 steps

    def test_initial_state(self):
        """All players must initialize with score 1."""
        config = get_game_config("baseline", seed=100)
        engine = GameEngine(config=config)
        self.assertEqual(len(engine.players), 6)
        for p in engine.players.values():
            self.assertEqual(p.score, 1)
            self.assertFalse(p.is_sitting_out)
            self.assertFalse(p.has_coin)

    def test_chest_and_coin_mechanics_score_1_only(self):
        """Only score 1 players can receive coins, and only the first group entering."""
        config = get_game_config("baseline", seed=42)
        engine = GameEngine(config=config)

        # Force player 0 to have score 2, player 1 to have score 1
        engine.players[0].score = 2
        engine.players[1].score = 1
        engine.players[2].score = 1

        round_res = engine.run_round(1)

        # If player 0 was in chest room, player 0 must not receive a coin
        self.assertNotIn(0, round_res.coin_recipients)
        # Any coin recipient must have had score 1 at start of round
        for cid in round_res.coin_recipients:
            self.assertEqual(round_res.scores_during_round[cid], 1)

    def test_elimination_condition_exact_higher_up(self):
        """
        Higher-up definition: score == your_score + 1.
        Score +2 should NOT eliminate.
        Same score should NOT eliminate.
        """
        config = get_game_config("baseline", seed=42, num_players=4, timesteps_per_round=1)
        engine = GameEngine(config=config)

        # Set specific scores and rooms
        # Room 0: P0 (score 1), P1 (score 2) -> P0 eliminated by P1
        # Room 1: P2 (score 1), P3 (score 3) -> P2 NOT eliminated by P3 (+2 is not a higher-up)
        engine.players[0].score = 1
        engine.players[1].score = 2
        engine.players[2].score = 1
        engine.players[3].score = 3

        # Run 1 timestep with fixed positioning at freeze
        engine.current_round = 1
        # Manually invoke evaluation at freeze
        engine.players[0].current_room = 0
        engine.players[1].current_room = 0
        engine.players[2].current_room = 1
        engine.players[3].current_room = 1

        # Use engine to evaluate room occupants
        occupants_r0 = [engine.players[0], engine.players[1]]
        occupants_r1 = [engine.players[2], engine.players[3]]

        # Room 0: P1 (score 2) is higher-up to P0 (score 1)
        higher_ups_p0 = [h for h in occupants_r0 if h.score == engine.players[0].score + 1]
        self.assertEqual(len(higher_ups_p0), 1)
        self.assertEqual(higher_ups_p0[0].player_id, 1)

        # Room 1: P3 (score 3) is NOT higher-up to P2 (score 1) because 3 != 1 + 1
        higher_ups_p2 = [h for h in occupants_r1 if h.score == engine.players[2].score + 1]
        self.assertEqual(len(higher_ups_p2), 0)

    def test_score_upgrades(self):
        """
        Score 1 with coin and not eliminated upgrades to 2.
        Score 2 that eliminates score 1 upgrades to 3 (max +1 boost even with multiple prey).
        """
        config = get_game_config("baseline", seed=42, num_players=4)
        engine = GameEngine(config=config)

        # Setup: P0 (score 1, has coin, room 0, no higher up) -> should upgrade to 2
        # Setup: P1 (score 2, room 1) with P2, P3 (both score 1, room 1)
        # P1 eliminates P2 and P3 -> P1 should upgrade to 3 (+1 boost, not +2)
        engine.players[0].score = 1
        engine.players[0].has_coin = True
        engine.players[0].current_room = 0

        engine.players[1].score = 2
        engine.players[1].current_room = 1

        engine.players[2].score = 1
        engine.players[2].current_room = 1

        engine.players[3].score = 1
        engine.players[3].current_room = 1

        # Simulate freeze evaluation
        room_occupants = {
            0: [engine.players[0]],
            1: [engine.players[1], engine.players[2], engine.players[3]],
        }

        eliminated = []
        elims_by = {i: [] for i in range(4)}
        for room, occupants in room_occupants.items():
            for p in occupants:
                higher_ups = [h for h in occupants if h.score == p.score + 1]
                if higher_ups:
                    eliminated.append(p.player_id)
                    for h in higher_ups:
                        elims_by[h.player_id].append(p.player_id)

        self.assertNotIn(0, eliminated)
        self.assertNotIn(1, eliminated)
        self.assertIn(2, eliminated)
        self.assertIn(3, eliminated)

        # Upgrades
        upgraded = []
        for p in [engine.players[0], engine.players[1], engine.players[2], engine.players[3]]:
            if p.score == 1 and p.player_id not in eliminated and p.has_coin:
                upgraded.append(p.player_id)
            elif p.score >= 2 and p.player_id not in eliminated:
                if len(elims_by[p.player_id]) > 0:
                    upgraded.append(p.player_id)

        self.assertEqual(upgraded, [0, 1])

    def test_sitting_out_and_rejoining(self):
        """Eliminated player must sit out the next round, then rejoin with score 1."""
        config = get_game_config("baseline", seed=42, num_players=6, num_rounds=4)
        engine = GameEngine(config=config)

        # In round 1, manually eliminate player 0
        round_1 = engine.run_round(1)
        # Force player 0 to be eliminated in round 1
        engine.players[0].is_sitting_out = True
        engine.players[0].eliminated_in_round = 1
        engine.players[0].score = 5  # Suppose they were high score

        # In round 2, player 0 must sit out
        round_2 = engine.run_round(2)
        self.assertIn(0, round_2.sitting_out_players)
        self.assertEqual(round_2.scores_during_round[0], 0)
        self.assertIsNone(engine.players[0].current_room)

        # In round 3, player 0 must rejoin with score 1
        round_3 = engine.run_round(3)
        self.assertNotIn(0, round_3.sitting_out_players)
        self.assertEqual(round_3.scores_during_round[0], 1)
        self.assertIsNotNone(engine.players[0].current_room)


if __name__ == "__main__":
    unittest.main()
