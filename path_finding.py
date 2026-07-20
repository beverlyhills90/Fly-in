from pydantic import Field, BaseModel, model_validator, ValidationError, field_validator
from parser import Hub, Connection, MapData
from graphs import Graph
from enum import Enum
from pydantic_core import to_json
from math import sqrt
import heapq


class Status(Enum):
    ACTIVE = 0
    IN_RESTRICTED = 1
    DELIVERED = 2


class Drone(BaseModel):
    drone_id: str = Field(min_length=1)
    current_zone: str = Field(min_length=1)
    status: Status = Field(default=Status.ACTIVE)
    dron_score: int = Field(ge=0)
    drone_transit_destination: str | None = Field(default=None)

    @classmethod
    def build(cls, id: int, start_zone: str) -> "Drone":
        tmp = {"drone_id": f"D{id}", "current_zone": start_zone, "dron_score": 0}
        return cls.model_validate(tmp)

    def decide_next_step(
        self, graph: Graph, map_data: MapData, world_state: "WorldState"
    ) -> str:
        g = {}
        heap = []
        if self.current_zone == map_data.end_hub_name:
            self.status = Status.DELIVERED
            return map_data.end_hub_name
        for name in graph.zones.keys():  # init the g
            if name != self.current_zone:
                g[name] = float("inf")
                continue
            g[name] = 0
            heap.append((0, name))

        came_from = {}
        visited = set()
        heapq.heapify(heap)
        while len(heap) != 0:
            f, active_zone = heapq.heappop(heap)
            if active_zone in visited:
                continue
            elif active_zone == map_data.end_hub_name:
                path = []
                hub = map_data.end_hub_name
                while hub in came_from.keys():
                    path.append(hub)
                    hub = came_from[hub]
                path.append(self.current_zone)
                path.reverse()
                # print(path)
                return path[1]
            visited.add(active_zone)

            for neighbor in graph.get_neighbors(active_zone):
                if world_state.is_available(neighbor, graph) != True:
                    continue
                cost = graph.get_cost(neighbor)

                new_g = g[active_zone] + cost
                if new_g < g[neighbor]:
                    g[neighbor] = new_g
                    came_from[neighbor] = active_zone

                    (zone_x, zone_y) = graph.get_zone(neighbor).hub_cords
                    (fin_x, fin_y) = map_data.end_hub_cords
                    h = round(sqrt((fin_x - zone_x) ** 2 + (fin_y - zone_y) ** 2), 2)
                    f = new_g + h
                    if graph.get_zone(neighbor).hub_meta_data["zone"] == "priority":
                        h -= 0.1
                    heapq.heappush(heap, (f, neighbor))


class WorldState(BaseModel):
    zone_info: dict
    zone_reservations: dict
    connection_info: dict
    connection_reservations: dict
    drones: list[Drone]

    @classmethod
    def build(cls, graph: Graph, map_data: MapData) -> "WorldState":
        drones = []
        for i in range(map_data.nb_drones):
            drones.append(Drone.build(i, map_data.start_hub_name))
        zone_info = {map_data.start_hub_name: len(drones)}
        for zone in map_data.hubs[1:]:
            zone_info[zone.hub_name] = 0
        connection_info = {}
        for connection in map_data.connections:
            connection_info[
                f"{connection.connection_from}-{connection.connection_to}"
            ] = 0
        connection_reservations = {}
        for connection in map_data.connections:
            connection_reservations[
                f"{connection.connection_from}-{connection.connection_to}"
            ] = 0
        zone_reservations = {}
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
        self.zone_reservations[to_zone] = self.zone_reservations.get(to_zone, 0) + 1
        key = f"{from_zone}-{to_zone}"
        if key not in self.connection_reservations:
            key = f"{to_zone}-{from_zone}"

        self.connection_reservations[key] = self.connection_reservations.get(key, 0) + 1

    def reload(self) -> None:
        self.zone_reservations = {}
        self.connection_reservations = {}
        self.zone_info = {}

    def is_available(self, zone: str, graph: Graph) -> bool:
        return graph.is_zone_available(
            zone, self.zone_info.get(zone, 0) + self.zone_reservations.get(zone, 0)
        )


class Simulation(BaseModel):
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
        return cls(
            drones=drones, graph=graph, world_state=world_state, map_data=map_data
        )

    def simulation(self) -> list[str]:
        output = []
        move_counter = 0
        while not all(drone.status == Status.DELIVERED for drone in self.drones):
            drones_g = []  # grones guess
            move_counter += 1
            self.world_state.reload()
            for drone in self.drones:
                if drone.status == Status.DELIVERED:
                    continue
                elif drone.status == Status.IN_RESTRICTED:
                    guess = drone.drone_transit_destination
                    drones_g.append((drone, guess))
                else:  # Status.ACTIVE
                    drone_guess = drone.decide_next_step(
                        self.graph, self.map_data, self.world_state
                    )
                    drones_g.append((drone, drone_guess))
            drones_g = sorted(drones_g, key=lambda drid: int(drid[0].drone_id[1:]))
            allowed = []
            for drone, target in drones_g:
                if self.world_state.is_available(target, self.graph):
                    self.world_state.reserve(target, drone.current_zone)
                    allowed.append((drone, target))
                else:
                    continue
            log = []
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
            output.append(" ".join(log))
        print(move_counter)
        return output


if __name__ == "__main__":
    # drone = Drone.build(1,"gate_hell1")
    map_data = MapData.parsing_from_file(
        "/Users/og/myubuntu/42repo/Fly-in/maps/challenger/01_the_impossible_dream.txt"
    )
    g: "Graph" = Graph.load_from_map_data(map_data)
    world_s = WorldState.build(g, map_data=map_data)
    # print(world_s.model_dump_json(indent=2))
    # print(drone.decide_next_step(g,map_data,world_s))
    simulation = Simulation.build(world_s.drones, world_s, g, map_data)
    print(simulation.simulation())
