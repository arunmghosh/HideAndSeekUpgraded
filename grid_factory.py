"""
grid_factory.py - Play grid definitions and factory functions for the Hide and Seek simulation.

Supported play grids:
1. Baseline: 2 rooms connected by 1 hallway (6 players, 10 rounds, 3 timesteps/round)
2. Triangular Pyramid: 4 rooms fully connected (K4) (12 players, 25 rounds, 5 timesteps/round)
3. The Hexagon: 6 rooms in a cycle (C6) (18 players, 50 rounds, 8 timesteps/round)
4. Sudoku Grid: 9 rooms in a 3x3 grid with horizontal and vertical connections (27 players, 100 rounds, 10 timesteps/round)
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class PlayGrid:
    """Represents a play grid graph consisting of rooms (nodes) and hallways (edges)."""
    name: str
    num_rooms: int
    edges: List[Tuple[int, int]]
    adjacency: Dict[int, List[int]] = field(default_factory=dict)
    distance_matrix: Dict[Tuple[int, int], int] = field(default_factory=dict)

    def __post_init__(self):
        # Build symmetric adjacency map
        self.adjacency = {i: [] for i in range(self.num_rooms)}
        for u, v in self.edges:
            if u not in self.adjacency[v]:
                self.adjacency[v].append(u)
            if v not in self.adjacency[u]:
                self.adjacency[u].append(v)
        for i in self.adjacency:
            self.adjacency[i].sort()

        # Compute all-pairs shortest paths via BFS
        self.distance_matrix = {}
        for start in range(self.num_rooms):
            distances = self._bfs_distances(start)
            for target, d in distances.items():
                self.distance_matrix[(start, target)] = d

    def _bfs_distances(self, start: int) -> Dict[int, int]:
        dist: Dict[int, int] = {start: 0}
        queue = deque([start])
        while queue:
            curr = queue.popleft()
            for neighbor in self.adjacency[curr]:
                if neighbor not in dist:
                    dist[neighbor] = dist[curr] + 1
                    queue.append(neighbor)
        return dist

    def get_neighbors(self, room: int) -> List[int]:
        """Returns adjacent rooms connected by hallways."""
        return list(self.adjacency.get(room, []))

    def get_valid_moves(self, current_room: int) -> List[int]:
        """Returns valid destination rooms: stay in place or move to an adjacent room."""
        return [current_room] + self.get_neighbors(current_room)

    def get_distance(self, u: int, v: int) -> int:
        """Returns shortest path distance between room u and room v."""
        return self.distance_matrix.get((u, v), float("inf"))


@dataclass
class GameConfig:
    """Configuration parameters for a Hide and Seek game simulation."""
    name: str
    display_name: str
    grid: PlayGrid
    num_players: int
    num_rounds: int
    timesteps_per_round: int
    seed: Optional[int] = None


def build_baseline_grid() -> PlayGrid:
    """Two rooms connected by one hallway."""
    return PlayGrid(
        name="baseline",
        num_rooms=2,
        edges=[(0, 1)]
    )


def build_triangular_pyramid_grid() -> PlayGrid:
    """Four rooms fully connected by hallways (complete graph K4)."""
    edges = [
        (0, 1), (0, 2), (0, 3),
        (1, 2), (1, 3),
        (2, 3)
    ]
    return PlayGrid(
        name="triangular_pyramid",
        num_rooms=4,
        edges=edges
    )


def build_hexagon_grid() -> PlayGrid:
    """Six rooms arranged in a hexagon cycle (C6) with hallways connecting adjacent rooms."""
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)
    ]
    return PlayGrid(
        name="hexagon",
        num_rooms=6,
        edges=edges
    )


def build_sudoku_grid() -> PlayGrid:
    """
    Nine rooms arranged in a 3x3 grid with hallways connecting vertically and horizontally adjacent rooms.
    No diagonal connections.
    Room indexing: row * 3 + col (0 to 8).
    """
    edges = []
    for r in range(3):
        for c in range(3):
            room = r * 3 + c
            # Horizontal connection (to right)
            if c < 2:
                edges.append((room, r * 3 + (c + 1)))
            # Vertical connection (downward)
            if r < 2:
                edges.append((room, (r + 1) * 3 + c))
    return PlayGrid(
        name="sudoku_grid",
        num_rooms=9,
        edges=edges
    )


# Grid presets matching experiment specification (a) - (d)
GRID_BUILDERS = {
    "baseline": build_baseline_grid,
    "triangular_pyramid": build_triangular_pyramid_grid,
    "pyramid": build_triangular_pyramid_grid,
    "hexagon": build_hexagon_grid,
    "sudoku": build_sudoku_grid,
    "sudoku_grid": build_sudoku_grid,
}

DEFAULT_CONFIGS = {
    "baseline": {
        "display_name": "Baseline",
        "builder": build_baseline_grid,
        "num_players": 6,
        "num_rounds": 10,
        "timesteps_per_round": 3,
    },
    "triangular_pyramid": {
        "display_name": "Triangular Pyramid",
        "builder": build_triangular_pyramid_grid,
        "num_players": 12,
        "num_rounds": 25,
        "timesteps_per_round": 5,
    },
    "hexagon": {
        "display_name": "The Hexagon",
        "builder": build_hexagon_grid,
        "num_players": 18,
        "num_rounds": 50,
        "timesteps_per_round": 8,
    },
    "sudoku_grid": {
        "display_name": "Sudoku Grid",
        "builder": build_sudoku_grid,
        "num_players": 27,
        "num_rounds": 100,
        "timesteps_per_round": 10,
    },
}


def normalize_grid_name(name: str) -> str:
    """Normalize input grid name to canonical key."""
    cleaned = name.strip().lower().replace(" ", "_").replace("-", "_")
    if cleaned in ("pyramid", "triangularpyramid", "triangle"):
        return "triangular_pyramid"
    if cleaned in ("sudoku", "sudokugrid", "grid_3x3"):
        return "sudoku_grid"
    if cleaned in ("the_hexagon", "hex"):
        return "hexagon"
    return cleaned


def create_play_grid(grid_name: str) -> PlayGrid:
    """Create a PlayGrid instance by canonical name or alias."""
    norm = normalize_grid_name(grid_name)
    if norm not in GRID_BUILDERS:
        valid = list(DEFAULT_CONFIGS.keys())
        raise ValueError(f"Unknown grid '{grid_name}'. Valid options: {valid}")
    return GRID_BUILDERS[norm]()


def get_game_config(
    name: str,
    seed: Optional[int] = None,
    num_players: Optional[int] = None,
    num_rounds: Optional[int] = None,
    timesteps_per_round: Optional[int] = None,
) -> GameConfig:
    """
    Get full game configuration for one of the standard games,
    allowing optional parameter overrides.
    """
    norm = normalize_grid_name(name)
    if norm not in DEFAULT_CONFIGS:
        valid = list(DEFAULT_CONFIGS.keys())
        raise ValueError(f"Unknown game config '{name}'. Valid options: {valid}")

    spec = DEFAULT_CONFIGS[norm]
    grid = spec["builder"]()

    return GameConfig(
        name=norm,
        display_name=spec["display_name"],
        grid=grid,
        num_players=num_players if num_players is not None else spec["num_players"],
        num_rounds=num_rounds if num_rounds is not None else spec["num_rounds"],
        timesteps_per_round=(
            timesteps_per_round
            if timesteps_per_round is not None
            else spec["timesteps_per_round"]
        ),
        seed=seed,
    )


def list_available_grids() -> List[str]:
    """Returns list of canonical grid configuration names."""
    return list(DEFAULT_CONFIGS.keys())

