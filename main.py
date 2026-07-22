from parser import Hub, Connection, MapData, ParsingError
from graphs import Graph
from visualization import vizualizer
from path_finding import Simulation, WorldState


def main() -> None:
    try:
        map_data = MapData.parsing_from_file(
            "/Users/og/myubuntu/42repo/Fly-in/maps/hard/03_ultimate_challenge.txt"
        )
    except ParsingError as e:
        print("\033[31m", f"Error: {e}", "\033[0m")
        return

    graph: "Graph" = Graph.load_from_map_data(map_data)
    world_s = WorldState.build(graph, map_data=map_data)
    simulation = Simulation.build(world_s.drones, world_s, graph, map_data)
    solve_log = simulation.simulation()
    vizualizer(graph, solve_log, map_data.nb_drones, map_data)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(" Bye bye")
