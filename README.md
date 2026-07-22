
# Fly-in

## Description

Fly-in is a drone routing simulation. The network of zones is modeled as a
graph, and the goal is to move a fleet of drones from a start zone to an end
zone in the fewest possible simulation turns, while respecting zone and
connection capacity constraints, movement costs, and restricted-zone transit
rules.

Unlike a purely centralized planner that precomputes one global schedule for
all drones, this implementation takes a **decentralized, simulation-driven**
approach: on every turn, each drone independently decides its next move based
on the current state of the world. This makes the project behave more like a
live simulation than a one-shot optimization problem — drones react to
congestion and blocked paths turn by turn, the same way autonomous agents
would in a real deployment.

## Instructions

```bash
make install   # install dependencies
make run       # run the simulation
make debug     # run with pdb
make clean     # remove caches and temporary files
make lint      # flake8 + mypy
```

Run the visualizer and press `S` to start/pause the simulation playback.
Use the mouse wheel to zoom and click-and-drag to pan the camera.

## Algorithm

### Pathfinding — A* per drone, per turn

Each drone recalculates its next step every turn using A*, rather than
following a path computed once at the start. This is what makes the
simulation decentralized: no drone commits to a full route in advance,
because the state of the world (which zones/connections are occupied) can
change from turn to turn as other drones move.

The core building blocks:

- **`g`** — the real, turn-based cost accumulated from the drone's current
  position to a given zone. Movement cost depends on the destination zone
  type: `normal`/`priority` = 1 turn, `restricted` = 2 turns, `blocked` =
  infinite (impassable).
- **`h`** — a heuristic estimate of the remaining distance to the goal,
  computed via Euclidean distance between zone coordinates. `priority` zones
  receive a small bonus applied to the final priority score `f`, so that
  when multiple paths cost the same in turns, the one running through
  priority zones is explored first — without distorting the actual turn
  count used for `g`.
- **`f = g + h`** — the priority used by the min-heap (`heapq`) to decide
  which zone to expand next.
- **`came_from`** — records which zone each zone was reached from, used to
  reconstruct the path once the goal is popped from the heap.
- **`visited`** — zones that have already been fully expanded, to avoid
  reprocessing stale heap entries.

`decide_next_step` returns only the **immediate next zone**, not the full
path — because by the time the drone would take a second step, the world may
have already changed.

### Conflict resolution and retry

Every turn, all active drones propose a next move. Proposals are sorted by
drone ID (numeric, not lexicographic) to establish a deterministic
priority order. Each proposal is then checked against the current
`WorldState` (zone occupancy + reservations, connection capacity +
reservations):

- If available, the move is reserved and approved.
- If not, instead of simply waiting, the drone retries: A* is rerun with the
  specific blocked **edge** (`current_zone -> target`) excluded, so the
  algorithm searches for an alternative route rather than blindly repeating
  the same blocked proposal. This is retried, excluding each newly-blocked
  edge, until either an available move is found or no alternative exists
  (in which case the drone waits this turn).

### Restricted zones

Entering a `restricted` zone costs 2 turns and cannot be interrupted: once a
drone commits to the connection, it must arrive next turn (it cannot wait
mid-flight). This is modeled with a dedicated drone status (`IN_RESTRICTED`)
that bypasses decision-making entirely for that turn — the drone is locked
into its previously chosen destination.

### Simulation loop

Each turn: reset per-turn reservations → collect proposals from all active
drones → sort by priority → resolve conflicts with retry → apply approved
moves (updating drone position/status) → log the turn in the required
`D<ID>-<zone>` / `D<ID>-<connection>` format → repeat until all drones are
delivered.

## Performance


| Map                | Drones | Turns |
|--------------------|--------|-------|
| Easy 1             | 2      | 4     |
| Easy 2             | 4      | 4     |
| Easy 3             | 4      | 4     |
| Medium 1           | 5      | 8     |
| Medium 2           | 6      | 10    |
| Medium 3           | 5      | 8     |
| Hard 1             | 8      | 11    |
| Hard 2             | 12     | 10    |
| Hard 3             | 15     | 26    |
| Challenger (bonus) | 25     | 67    |

The algorithm recalculates a full A* search per active drone per turn, so
the practical cost scales with the number of drones, the number of turns
until delivery, and graph size (each A* call visits at most every zone
once). No exact Big-O figure has been measured; the table above is used as
the practical benchmark instead, as suggested by the subject.

## Visual Representation

The simulation is rendered with **pygame**:

- Zones are drawn as colored circles at their graph coordinates (color taken
  from each zone's metadata), connected by lines representing connections.
- Drones are rendered as small labeled squares, grouped and spread around a
  zone when multiple drones share it.
- Drones in transit through a restricted zone are shown interpolated
  halfway between their origin and destination, so in-flight movement is
  visually distinguishable from an instant hop.
- **Zoom** (mouse wheel) and **camera pan** (click-and-drag) let you inspect
  dense/large maps like the Challenger map.
- Pressing **S** starts/pauses turn-by-turn playback of the simulation log,
  so each step can be inspected individually rather than only watching the
  final result.

## Resources

A*_search_algorithm - https://en.wikipedia.org/wiki/A*_search_algorithm

Exploring Algorithms - https://medium.com/@kamilmatejuk/exploring-algorithms-heuristic-analysis-of-a-pathfinding-for-puzzle15-2a9dfda87e1f
## AI Usage

AI was used throughout development as a learning and debugging aid, not as
a code generator:

- Explaining core concepts before implementation: graphs and adjacency
  lists, Dijkstra's algorithm, and A* (the roles of `g`, `h`, `f`,
  `came_from`, and `visited`), heaps/priority queues via `heapq`, and why
  Euclidean distance via the Pythagorean theorem works as a heuristic.
- Reviewing and debugging hand-written code: catching bugs such as
  `came_from` being reset inside the main loop instead of once before it,
  an inverted `came_from[a] = b` assignment, a missing `**2` in the
  heuristic computation, a `list.pop()` used instead of `heapq.heappop()`,
  a `DELIVERED` status being set in one loop but the drone's move being
  skipped in a later loop (causing a drone to vanish from the output on its
  final turn), and a `WorldState.reload()` that wiped reservation/occupancy
  dictionaries without rebuilding them.
- Discussing algorithmic trade-offs: why a decentralized per-turn A*
  approach differs from a centralized K-shortest-paths planner, why the
  retry mechanism needed to exclude a specific blocked *edge*
  (`current_zone -> target`) rather than the destination zone globally, and
  why a priority-zone bonus only affects heap ordering (`f`) and not the
  real turn cost (`g`).
- Clarifying that `nb_drones` and turn cost are simulated sequentially (a
  discrete per-turn loop), not with `threading`/`asyncio`, since there is no
  I/O to wait on.

The pygame visualizer was implemented independently, without AI assistance.
All code in this repository was written by me; AI was used for conceptual
explanation and code review, and every generated explanation was verified
by testing before being relied on.