from parser import MapData, ParsingError
from graphs import Graph
from visualization import vizualizer
from path_finding import Simulation, WorldState
from pathlib import Path


def choos_map() -> str:
    directory = input("Map files directory: ").strip()
    current_dir = Path(directory)
    while not current_dir.exists() or not current_dir.is_dir():
        print("Invalid directory! Please try again.")
        current_dir = Path(input("Map files directory: ").strip())
    while True:
        directories = [p for p in current_dir.iterdir() if p.is_dir()]
        files = [p for p in current_dir.iterdir() if p.is_file()]

        items_map = {}
        index = 0

        for d in directories:
            print(f"[{index}] [DIR] {d.name}")
            items_map[index] = ("DIR", d)
            index += 1
        for f in files:
            print(f"[{index}] {f.name}")
            items_map[index] = ("FILE", f)
            index += 1
        if len(items_map) == 1:
            print("(Directory is empty)")

        choice_input = input("\nSelect index (or 'q' to quit): ").strip()
        if choice_input.lower() == "q":
            return ""
        if not choice_input.isdigit():
            print("Please enter a valid number!")
            continue
        choice = int(choice_input)
        if choice not in items_map:
            print("\033[31m", "Index out of range!", "\033[0m")
            continue
        item_type, item_path = items_map[choice]
        if item_type == "UP":
            current_dir = item_path
        elif item_type == "DIR":
            current_dir = item_path
        elif item_type == "FILE":
            return str(item_path.resolve())


def main() -> None:
    """main"""
    map_file = choos_map()
    if map_file == "":
        print("Bye bye")
        return
    try:
        map_data = MapData.parsing_from_file(map_file)
    except ParsingError as e:
        print("\033[31m", f"Error: {e}", "\033[0m")
        return
    try:
        graph: "Graph" = Graph.load_from_map_data(map_data)
        world_s = WorldState.build(graph, map_data=map_data)
        simulation = Simulation.build(world_s.drones, world_s, graph, map_data)
        solve_log = simulation.simulation()
        vizualizer(graph, solve_log, map_data.nb_drones, map_data)
    except Exception as e:
        print("\033[31m", f"Ops something went wrong...: {e}", "\033[0m")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(" Bye bye")
