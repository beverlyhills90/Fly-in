from pydantic import Field, BaseModel, model_validator, ValidationError, field_validator
from parser import Hub, Connection, MapData
from graphs import Graph
from visualization import vizualizer
from path_finding import Simulation,WorldState

def main():
    map_data = MapData.parsing_from_file(
        "/Users/og/myubuntu/42repo/Fly-in/maps/challenger/01_the_impossible_dream.txt"
    )
    g: "Graph" = Graph.load_from_map_data(map_data)
    world_s = WorldState.build(g, map_data=map_data)
    simulation = Simulation.build(world_s.drones, world_s, g, map_data)
    solve_log = simulation.simulation()
    vizualizer(g,solve_log,map_data.nb_drones,map_data)


if __name__ == "__main__":
    main()
