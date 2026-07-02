from pydantic import Field, BaseModel, model_validator, ValidationError,field_validator
from pydantic_core import to_jsonable_python
from typing import Any, Optional
import json
import re
from enum import Enum
from parser import Hub,Connection,MapData


class Graph(BaseModel):
    zones: dict[str,Hub] = Field(default_factory=dict)
    adjacency:dict[str,list] = Field(default_factory=dict)
    connections:dict[tuple,"Connection"] = Field(default_factory=dict)

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
                # target_zone_1 = next((zone for zone in tmp if zone["hub_name"] == fr), None)
                # target_zone_2 = next((zone for zone in tmp if zone["hub_name"] == to), None)
                # value = (Hub.model_validate(target_zone_1),Hub.model_validate(target_zone_2))
                connections_dict[key] = conn
    
        load_adjacency()
        load_zones()
        load_connections()
        return cls(zones=zones_dict,adjacency=adjacency_dict,connections=connections_dict)
    
    def get_neighbors(self,zone_name:str) -> list[str]:
        return self.adjacency.get(zone_name)
    
    def get_connection(self,from_name:str, to_name:str) -> "Connection":
        return self.connections.get((from_name,to_name))
    
    def is_zone_available(self,zone_name:str, current_occupancy:int) -> bool:
        target_zone = self.zones.get(zone_name)
        target_zone_max_drones = target_zone.hub_meta_data.get("max_drones",None)
        if target_zone_max_drones is None:
            return True
        elif target_zone_max_drones < current_occupancy:
            return False
        return True
    
    def is_connection_available(self,from_name:str, to_name:str, current_usage) -> bool:
        target_connection = self.get_connection(from_name,to_name)
        target_max_link_capacity = target_connection.max_link_capacity
        if target_max_link_capacity is None:
            return True
        elif target_max_link_capacity < current_usage:
            return False
        return True


#TODO am i need None in geter methods?
#test Graphs
if __name__ == "__main__":
    map_data = MapData.parsing_from_file("maps/challenger/01_the_impossible_dream.txt")
    g:"Graph" = Graph().load_from_map_data(map_data)
    #print(g.get_connection("overflow_hell3","false_hope1"))
    #print(g.get_neighbors("overflow_hell3"))
    #print(g.is_zone_available("priority_trap1",10))
    print(g.is_connection_available("start","gate_hell1",2))
        
