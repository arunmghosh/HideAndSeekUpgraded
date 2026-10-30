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

## 5. How To Replicate This Experiment
(TBD, use RNG stream)
(Commands to install dependencies, clone repo, and run code)
