# Hide And Seek Simulation
## 1. How the game works
### a) Setup & General Mechanics
The hiding area, called the play grid, consists of rooms and hallways. Rooms are where people hide, and hallways connect the rooms so people can move around. The game consists of a pre-defined number of rounds. At the start of each round, a chest of coins is hidden in one of the rooms. Each round has a set duration (constant for the whole game) in which players can move freely around the play grid. At the end of each round, everyone goes into a freeze, where they can't move.  

### b) Scoring & Elimination
Everyone starts the round with a positive integer score (in the initial round, everyone has score 1). You are hiding from people with a score exactly one higher than yours (those players are called higher-ups), and seeking people with a score exactly one lower than yours (you are a higher-up to them). If you are in the same room as a higher-up during a freeze, you are eliminated. That means you sit out the next round, and then return to the game with score 1. 

There are two ways to increase your score. If you have score 1, your only option is to be among the first group of players to enter the room with the chest. In that case, you receive a coin. If you get through the round without being eliminated at the freeze, you get promoted to score 2. No one who has a score higher than 1 going into a round can take a coin. If you are already at score 2 or higher, you must be in the same room as someone with a score exactly one lower than yours to upgrade your score (add one to it). If you are a higher-up to multiple other players in the same room as you during a freeze, you still only get a 1 point boost. 

## 2. Statistics I Want To Collect
### a) Player-level Statistics
- Highest score attained in the game
- Average score throughout the game (sum of round scores / number of rounds, rounds they sat out are treated as score 0)
- Number of times they were eliminated
- Number of rounds in which they eliminated at least one player
- Number of rounds in which they were a seeker (had the sole highest score or tied for the highest score)
- Longest streak of consecutive rounds in which they were not eliminated
- Longest streak of consecutive rounds in which their score was upgraded
- Longest streak of consecutive rounds as a seeker

### b) Round-level Statistics
- Number of seekers in the round
- Score of those seekers during the round
- Median player score during the round
- Sum of all player scores for that round
- Number of players with score 1 during the round
- Number of players eliminated that round
- Number of players whose score was upgraded that round

### c) Game-level Statistics
- Empirical CDF over all players of highest score attained in the game
- Empirical CDF over all players of average score throughout the game
- Median player score versus time plot
- Max player score versus time plot

## 3. Simulations I Want To Run
### a) Baseline 
- A play grid of two rooms connected by one hallway
- A total of 6 players
- A total of 10 rounds
- A total of 3 timesteps per round

### b) Triangular Pyramid 
- A play grid of four rooms fully connected by hallways
- A total of 12 players
- A total of 25 rounds
- A total of 5 timesteps per round

### c) The Hexagon 
- A play grid of six rooms arranged in a hexagon with hallways only connecting adjacent rooms
- A total of 18 players
- A total of 50 rounds
- A total of 8 timesteps per round

### d) Sudoku Grid 
- A play grid of nine rooms arranged in a 3x3 grid with hallways connecting vertically and horizontally adjacent rooms (no diagonals)
- A total of 27 players
- A total of 100 rounds
- A total of 10 timesteps per round

## 4. Codebase Architecture
```
Hide_And_Seek/
├── rules.py                  # Stores game logic, including setup, elimination, scoring, etc
├── grid_factory.py           # Set up the play grids (options (a) - (d) above)
├── simulate.py               # Runs one game with a chosen grid / initial configuration
├── experiment.py             # Runs one game with each grid / config (a) - (d)
├── stat_tracker.py           # Tracks all desired statistics throughout the experiment
├── make_figures.py           # Generates plots of statistics
├── HideAndSeek_FullGameSpec.pdf   # Original game specification
├── plots/                    # Directory for generated experiment visualizations
│   ├── stats.xlsx            # Writes desired stats for all games in the experiment to a spreadsheet
│   ├── high_score_cdf.png    # Empirical CDF of high scores of each player over the course of each game (overlayed)
│   ├── med_score_cdf.png     # Empirical CDF of median scores of each player over the course of each game (overlayed)
│   ├── med_score_vs_time.png # Plot of median player score at each timestep in each game (overlayed)
│   ├── max_score_vs_time.png # Plot of max player score at each timestep in each game (overlayed)
├── tests/                    # Automated unit and integration test suite
│   ├── test_game.py          # Tests the logic of the game
│   ├── test_math.py          # Ensure that all of the calculations are mathematically correct
│   ├── test_experiment.py    # Ensure that the pipeline runs correctly and outputs are in the correct format
│   └── test_smoke.py         # Rapid end-to-end integration smoke test
└── README.md                 # Project specification, experiment documentation, architecture, and usage
```

## 5. How To Run The Simulation & Replicate The Experiment

### a) Environment Setup & Dependencies
This codebase requires Python 3.9+ with standard scientific computing packages:
```bash
pip install numpy pandas matplotlib openpyxl
```

### b) Running a Single Game Simulation (`simulate.py`)
To run a single game simulation, execute `simulate.py` and specify your desired play grid using the `--grid` (or `-g`) argument:

```bash
# Run Baseline (2 rooms, 6 players, 10 rounds, 3 timesteps/round)
python3 simulate.py --grid baseline

# Run Triangular Pyramid (4 rooms K4, 12 players, 25 rounds, 5 timesteps/round)
python3 simulate.py --grid triangular_pyramid

# Run The Hexagon (6 rooms C6, 18 players, 50 rounds, 8 timesteps/round)
python3 simulate.py --grid hexagon

# Run Sudoku Grid (9 rooms 3x3, 27 players, 100 rounds, 10 timesteps/round)
python3 simulate.py --grid sudoku_grid
```

#### Customization Options for Single Games
You can customize the game parameters using optional flags:
```bash
# Run Hexagon with 15 rounds, 12 players, and a fixed random seed
python3 simulate.py --grid hexagon --rounds 15 --players 12 --timesteps 6 --seed 42

# Export single-game statistics directly to Excel
python3 simulate.py --grid sudoku_grid --export-excel plots/sudoku_single.xlsx

# Run with quiet mode (suppresses round-by-round logs, prints final summary only)
python3 simulate.py --grid baseline --quiet
```

Available CLI arguments for `simulate.py`:
- `-g, --grid`: Name of play grid (`baseline`, `triangular_pyramid`, `hexagon`, `sudoku_grid`).
- `-p, --players`: Override the total number of players.
- `-r, --rounds`: Override the total number of rounds.
- `-t, --timesteps`: Override the duration (timesteps per round).
- `-s, --seed`: RNG seed for reproducible agent movement and chest placement (default: `42`).
- `--policy`: Player movement policy (`strategic` [default] or `random`).
- `--export-excel`: Optional filepath to write single game statistics to an Excel spreadsheet.
- `-q, --quiet`: Suppress per-round console output.

---

### c) Running the Full Experiment Pipeline (`experiment.py`)
To run the full experimental pipeline across all four play grids ((a) Baseline, (b) Triangular Pyramid, (c) The Hexagon, and (d) Sudoku Grid) and generate all comparison figures and the consolidated Excel spreadsheet, run:

```bash
python3 experiment.py
```

#### Deterministic RNG Stream & Replication
The experiment uses NumPy's `SeedSequence` to derive statistically independent, reproducible pseudo-random streams for each of the four games. You can customize the master seed or output folder:

```bash
# Run with a custom master seed and target output directory
python3 experiment.py --seed 42 --output-dir plots/
```

#### Generated Outputs in `plots/`:
Running `experiment.py` generates the following files:
1. `plots/stats.xlsx`: Multi-sheet workbook containing:
   - `Game_Summaries`: Comparative summary of all 4 games (players, rounds, max scores, average score, total eliminations, total upgrades, winners).
   - `All_Players_Comparison`: Consolidated player-level statistics across all games.
   - `All_Rounds_Comparison`: Consolidated round-level statistics across all games.
   - Individual detail sheets for each game (e.g. `baseline_Players`, `baseline_Rounds`, etc.).
2. `plots/high_score_cdf.png`: Overlayed Empirical CDF of the highest scores attained by players in each game.
3. `plots/med_score_cdf.png`: Overlayed Empirical CDF of each player's median round score across each game.
4. `plots/med_score_vs_time.png`: Overlayed plot of median player score across timesteps over the course of each game.
5. `plots/max_score_vs_time.png`: Overlayed plot of maximum player score across timesteps over the course of each game.

---

### d) Running the Automated Test Suite
To run all automated unit and integration tests:
```bash
python3 -m unittest discover tests
```
The test suite validates:
- `tests/test_game.py`: Grid topologies, chest discovery, coin claiming, higher-up elimination, score upgrades, and sitting-out/rejoining logic.
- `tests/test_math.py`: Average score calculation with zero-weight for sit-out rounds, streak calculations, median calculations, and empirical CDF mathematical properties.
- `tests/test_experiment.py`: DataFrame schemas, multi-sheet Excel export, and plot generation.
- `tests/test_smoke.py`: Rapid end-to-end integration test across all four play grids.
