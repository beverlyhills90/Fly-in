from pydantic import Field, BaseModel, model_validator, ValidationError,field_validator
from pydantic_core import to_jsonable_python
from typing import Any, Optional
import json
import re
from enum import Enum
from parser import Hub,Connections,MapData


class Graph(BaseModel):
    zones: dict[str,Hub] = Field(default_factory=dict)
    adjacency:dict[str,list] = Field(default_factory=dict)
    connections:dict[tuple,tuple] = Field(default_factory=dict)

    @classmethod
    def load_from_map_data(cls,map_data:"MapData") -> None:
        """
        Creates and initializes a Graph instance from raw MapData.

        Builds the underlying dictionaries for zones, adjacency lists, and 
        connections, then returns a fully populated Graph object.
        """
        zones_dict = {}
        adjacency_dict = {}
        connections_dict = {}
        def load_zones() -> None:
            """
            Loads all map hubs into the centralized `zones_dict`.

            Combines the start, end, and intermediate hubs into a single list, 
            then indexes them by their `hub_name` for fast lookup.
            """
            start_hub = Hub(hub_name=map_data.start_hub_name,hub_cords=map_data.start_hub_cords,hub_meta_data=map_data.start_hub_meta_data)
            end_hub = Hub(hub_name=map_data.end_hub_name,hub_cords=map_data.end_hub_cords,hub_meta_data=map_data.end_hub_meta_data)
            zones_lst = [start_hub, end_hub] + map_data.hubs
            zones_lst[0:0] = [start_hub,end_hub]
            
            for zone in zones_lst:
                zones_dict.update({zone.hub_name:zone})

        def load_adjacency() -> None:
            """
            Constructs the graph's adjacency list inside `adjacency_dict`.

            Iterates through map connections to map each node to its direct neighbors, 
            ensuring the resulting graph representation is bidirectional (undirected).
            """
            connections_lst = map_data.connections
            for conn in connections_lst:
                fr = conn.connection_from
                to = conn.connection_to
                if fr in adjacency_dict:
                    adjacency_dict.update({fr:adjacency_dict[fr]+[to]})
                else:
                    adjacency_dict[fr] = [to]
                if to in adjacency_dict:
                    adjacency_dict.update({to:adjacency_dict[to]+[fr]})
                else:
                    adjacency_dict[to] = [fr]
        
        
        def load_connections() -> None:
            """
            Maps edge names to their corresponding Hub objects inside `connections_dict`.

            Looks up matching Hub records for each connection's source and destination, 
            storing them as a key-value pair of `(from_node, to_node) -> (Hub_A, Hub_B)`.
            """
            start_hub = Hub(hub_name=map_data.start_hub_name,hub_cords=map_data.start_hub_cords,hub_meta_data=map_data.start_hub_meta_data)
            end_hub = Hub(hub_name=map_data.end_hub_name,hub_cords=map_data.end_hub_cords,hub_meta_data=map_data.end_hub_meta_data)
            zones_lst = [start_hub, end_hub] + map_data.hubs
            zones_lst[0:0] = [start_hub,end_hub]
            connections_lst = map_data.connections
            tmp = [vars(zone) for zone in zones_lst]
             
            for conn in connections_lst:
                fr = conn.connection_from
                to = conn.connection_to
                key = (fr,to)
                target_zone_1 = next((zone for zone in tmp if zone["hub_name"] == fr), None)
                target_zone_2 = next((zone for zone in tmp if zone["hub_name"] == to), None)
                value = (Hub.model_validate(target_zone_1),Hub.model_validate(target_zone_2))
                connections_dict[key] = value
    
        load_adjacency()
        load_zones()
        load_connections()
        return cls(zones=zones_dict,adjacency=adjacency_dict,connections=connections_dict)



#test Graphs
if __name__ == "__main__":
    map_data = MapData.parsing_from_file("maps/challenger/01_the_impossible_dream.txt")
    g = Graph().load_from_map_data(map_data)
    print(g)
        
