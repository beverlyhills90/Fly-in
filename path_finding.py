from pydantic import Field, BaseModel
from parser import MapData
from graphs import Graph
from enum import Enum
from math import sqrt
import heapq


class Status(Enum):
    ACTIVE = 0
    IN_RESTRICTED = 1
    DELIVERED = 2


class Drone(BaseModel):
    """Represents an individual drone operating within the simulation graph."""

    drone_id: str = Field(min_length=1)
    current_zone: str = Field(min_length=1)
    status: Status = Field(default=Status.ACTIVE)
    dron_score: int = Field(ge=0)
    drone_transit_destination: str | None = Field(default=None)

    @classmethod
    def build(cls, id: int, start_zone: str) -> "Drone":
        """Factory method to construct a Drone instance with a formatted ID.

        Args:
            id: The numerical identifier for the drone.
            start_zone: The initial hub/zone where the drone is spawned.

        Returns:
            A validated Drone instance.
        """
        tmp = {"drone_id": f"D{id}", "current_zone": start_zone, "dron_score": 0}
        return cls.model_validate(tmp)

    def decide_next_step(
        self,
        graph: Graph,
        map_data: MapData,
        world_state: "WorldState",
        excluded: set[str],
    ) -> str | None:
        """Finds the optimal next step using the A* pathfinding algorithm.

        Args:
            graph: The network graph containing zones and connections.
            map_data: Map metadata including target/end hub coordinates.
            world_state: Current state of zones and reservations.
            excluded: Set of forbidden edges/zones in the format 'from_zone-to_zone' or 'zone_name'.

        Returns:
            The name of the next zone to move to, or None if no valid path exists.
        """
        g: dict[str, float] = {}
        came_from: dict[str, str] = {}
        visited: set[str] = set()

        # Heap contains tuples of (f_score, zone_name)
        heap: list[tuple[float, str]] = []

        for zone in graph.zones.keys():
            if zone == self.current_zone:
                g[zone] = 0.0
            else:
                g[zone] = float("inf")

        heapq.heappush(heap, (0.0, self.current_zone))

        while len(heap) != 0:
            cost, zone_name = heapq.heappop(heap)
            if zone_name in visited:
                continue

            if zone_name == map_data.end_hub_name:
                path: list[str] = []
                hub: str = map_data.end_hub_name
                while hub in came_from:
                    path.append(hub)
                    hub = came_from[hub]
                path.append(self.current_zone)
                path.reverse()
                return path[1] if len(path) > 1 else None

            visited.add(zone_name)
            for neighbor in graph.get_neighbors(zone_name):
                edge_key = f"{zone_name}-{neighbor}"
                if (
                    not world_state.is_available(neighbor, graph)
                    or edge_key in excluded
                    or neighbor in excluded
                ):
                    continue

                cost_to_neighbor = graph.get_cost(neighbor)
                new_g = cost_to_neighbor + g[zone_name]

                if new_g < g[neighbor]:
                    g[neighbor] = new_g
                    came_from[neighbor] = zone_name
                    zone_x, zone_y = graph.get_zone(neighbor).hub_cords
                    fin_x, fin_y = map_data.end_hub_cords

                    h = round(sqrt((fin_x - zone_x) ** 2 + (fin_y - zone_y) ** 2), 2)
                    f = new_g + h

                    if graph.get_zone(neighbor).hub_meta_data.get("zone") == "priority":
                        f -= 0.5

                    heapq.heappush(heap, (f, neighbor))

        return None


class WorldState(BaseModel):
    """Tracks the dynamic capacity, occupancy, and reservations of hubs and connections."""

    zone_info: dict[str, int]
    zone_reservations: dict[str, int]
    connection_info: dict[str, int]
    connection_reservations: dict[str, int]
    drones: list[Drone]

    @classmethod
    def build(cls, graph: Graph, map_data: MapData) -> "WorldState":
        """Constructs and initializes the global world state.

        Args:
            graph: The map graph topology.
            map_data: Contains general simulation configurations and parameters.

        Returns:
            An initialized WorldState instance.
        """
        drones: list[Drone] = []
        for i in range(1, map_data.nb_drones + 1):
            drones.append(Drone.build(i, map_data.start_hub_name))

        zone_info: dict[str, int] = {map_data.start_hub_name: len(drones)}
        for zone in map_data.hubs[1:]:
            zone_info[zone.hub_name] = 0

        connection_info: dict[str, int] = {}
        connection_reservations: dict[str, int] = {}
        for connection in map_data.connections:
            key = f"{connection.connection_from}-{connection.connection_to}"
            connection_info[key] = 0
            connection_reservations[key] = 0

        zone_reservations: dict[str, int] = {}
        for zone in map_data.hubs:
            zone_reservations[f"{zone.hub_name}"] = 0

        main_data = {
            "zone_info": zone_info,
            "zone_reservations": zone_reservations,
            "connection_info": connection_info,
            "connection_reservations": connection_reservations,
            "drones": drones,
        }
        return cls.model_validate(main_data)

    def reserve(self, to_zone: str, from_zone: str) -> None:
        """Reserves capacity for a drone moving between two zones.

        Args:
            to_zone: Destination zone name.
            from_zone: Origin zone name.
        """
        self.zone_reservations[to_zone] = self.zone_reservations.get(to_zone, 0) + 1
        key = f"{from_zone}-{to_zone}"
        if key not in self.connection_reservations:
            key = f"{to_zone}-{from_zone}"

        self.connection_reservations[key] = self.connection_reservations.get(key, 0) + 1

    def reload(self) -> None:
        """Clears all temporary reservations and occupancy info for a new step evaluation."""
        self.zone_reservations = {}
        self.connection_reservations = {}
        self.zone_info = {}

    def is_available(self, zone: str, graph: Graph) -> bool:
        """Checks if a target zone has enough free capacity to accept another drone.

        Args:
            zone: Target zone identifier.
            graph: Graph containing zone capacity constraints.

        Returns:
            True if capacity allows another drone, False otherwise.
        """
        return graph.is_zone_available(
            zone, self.zone_info.get(zone, 0) + self.zone_reservations.get(zone, 0)
        )


class Simulation(BaseModel):
    """Controls the step-by-step execution and logging of drone routing."""

    drones: list[Drone]
    graph: Graph
    world_state: WorldState
    map_data: MapData

    @classmethod
    def build(
        cls,
        drones: list[Drone],
        world_state: WorldState,
        graph: Graph,
        map_data: MapData,
    ) -> "Simulation":
        """Factory method for creating a Simulation instance.

        Args:
            drones: List of drones in the simulation.
            world_state: Global state manager.
            graph: Network graph.
            map_data: Simulation settings and targets.

        Returns:
            A ready-to-run Simulation object.
        """
        return cls(
            drones=drones, graph=graph, world_state=world_state, map_data=map_data
        )

    def simulation(self) -> list[list[str]]:
        """Executes the simulation steps until all drones arrive at the destination hub.

        Returns:
            A list of logs, where each log contains string representations of drone actions per step.
        """
        output: list[list[str]] = []

        while not all(drone.status == Status.DELIVERED for drone in self.drones):
            drones_g: list[tuple[Drone, str | None]] = []
            self.world_state.reload()

            for drone in self.drones:
                if drone.status == Status.DELIVERED:
                    continue
                elif drone.status == Status.IN_RESTRICTED:
                    guess = drone.drone_transit_destination
                    drones_g.append((drone, guess))
                else:  # Status.ACTIVE
                    drone_guess = drone.decide_next_step(
                        self.graph, self.map_data, self.world_state, set()
                    )
                    drones_g.append((drone, drone_guess))

            drones_g = sorted(drones_g, key=lambda item: int(item[0].drone_id[1:]))
            allowed: list[tuple[Drone, str]] = []

            for drone, target in drones_g:
                if target is None:
                    continue

                if self.world_state.is_available(target, self.graph):
                    self.world_state.reserve(target, drone.current_zone)
                    allowed.append((drone, target))
                else:
                    excluded: set[str] = {f"{drone.current_zone}-{target}"}
                    while True:
                        new_guess = drone.decide_next_step(
                            self.graph, self.map_data, self.world_state, excluded
                        )
                        if new_guess is not None:
                            if self.world_state.is_available(new_guess, self.graph):
                                self.world_state.reserve(new_guess, drone.current_zone)
                                allowed.append((drone, new_guess))
                                break
                            else:
                                excluded.add(new_guess)
                        else:
                            break

            log: list[str] = []
            for drone, target in allowed:
                cost = self.graph.get_cost(target)

                if drone.status == Status.DELIVERED:
                    continue

                if cost == 2 and drone.status == Status.ACTIVE:
                    drone.status = Status.IN_RESTRICTED
                    drone.drone_transit_destination = target
                    log.append(f"{drone.drone_id}-{drone.current_zone}-{target}")
                elif drone.status == Status.IN_RESTRICTED:
                    drone.status = Status.ACTIVE
                    drone.current_zone = target
                    log.append(f"{drone.drone_id}-{target}")
                else:
                    drone.current_zone = target
                    log.append(f"{drone.drone_id}-{target}")

                if drone.current_zone == self.map_data.end_hub_name:
                    drone.status = Status.DELIVERED

            output.append(log)

        return output


if __name__ == "__main__":
    # drone = Drone.build(1,"gate_hell1")
    map_data = MapData.parsing_from_file(
        "/Users/og/myubuntu/42repo/Fly-in/maps/challenger/01_the_impossible_dream.txt"
    )
    g: "Graph" = Graph.load_from_map_data(map_data)
    # print(g.zones)
    world_s = WorldState.build(g, map_data=map_data)
    # print(world_s.model_dump_json(indent=2))
    # print(drone.decide_next_step(g,map_data,world_s))
    simulation = Simulation.build(world_s.drones, world_s, g, map_data)
    simulation.simulation()
