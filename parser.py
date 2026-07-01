from pydantic import Field, BaseModel, model_validator, ValidationError
from pydantic_core import to_jsonable_python
from typing import Any, Optional
import json
import re
from enum import Enum


class ParsingError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class HUBS(Enum):
    START = 0
    NORMAL = 1
    END = 2


class Hub_MetaData(BaseModel):
    zone: Optional[str] = Field(default="normal")
    color: Optional[str] = Field(default=None)
    max_drones: Optional[int] = Field(ge=1)


class Connections(BaseModel):
    connection_from: str = Field(min_length=1)
    connection_to: str = Field(min_length=1)
    max_link_capacity: Optional[int] = Field(default=None,ge=1)


class Hub(BaseModel):
    hub_name: str = Field(min_length=1, max_length=100)
    hub_cords: tuple[int, int]
    hub_meta_data:dict


class MapData(BaseModel):
    nb_drones: tuple[int, int]
    start_hub_name: str = Field(min_length=1, max_length=100)
    start_hub_cords: tuple = Field(ge=0)
    start_hub_meta_data: dict
    end_hub: tuple[int, int]
    end_hub_name: tuple[int, int]
    end_hub_meta_data: dict
    hubs: list[Hub]
    connections: list[Connections]

    @staticmethod
    def parsing_from_file(file_path: str):
        errors = []
        allowed_zones = ["normal", "blocked", "restricted", "priority"]
        main_data: dict[str, Any] = {}
        hubs = []
        connections = []
        start_marker = False
        finish_marker = False

        def load_hubs_to_dict(
            hub_name: str,
            hub_cord: tuple,
            color: Optional[str],
            max_drones: Optional[int],
            zone: Optional[str],
            hub_t: "HUBS",
        ) -> None:
            if hub_t == HUBS.START:
                main_data["start_hub_name"] = hub_name
                main_data["start_hub_cords"] = hub_cord
                main_data["start_hub_meta_data"] = vars(Hub_MetaData(zone=zone, max_drones=max_drones, color=color))
            elif hub_t == HUBS.END:
                main_data["end_hub_name"] = hub_name
                main_data["end_hub"] = hub_cord
                main_data["end_hub"] = vars(Hub_MetaData(zone=zone, max_drones=max_drones, color=color))
            else:
                metadata = vars(Hub_MetaData(zone=zone, max_drones=max_drones, color=color))
                tmp = Hub(hub_name=hub_name,hub_cords=hub_cord,hub_meta_data=metadata)
                hubs.append(tmp)
        def load_connections_to_list(connections_lst:list[str],max_link_capacity:int | None) -> None:
            conn = Connections(connection_from=connections_lst[0],connection_to=connections_lst[1],max_link_capacity=max_link_capacity)
            connections.append(conn)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if line.startswith("#"):
                        continue
                    if "nb_drones" in line:  # nb_drones_line parsing
                        main_data["nb_drones"] = line.split(":")[1].strip()
                        continue
                    if "hub" in line:  # hub logic parsing
                        hub_t = HUBS.NORMAL
                        if "start_hub" in line:
                            if not start_marker:
                                hub_t = HUBS.START
                                start_marker = True
                            else:
                                errors.append(
                                    ParsingError("We need only one start hub")
                                )
                                continue
                        elif "end_hub" in line:
                            if not finish_marker:
                                hub_t = HUBS.END
                                finish_marker = True
                            else:
                                errors.append(
                                    ParsingError("We need only one finish hub")
                                )
                                continue
                        tmp = line.split(":")[1].split()
                        hub_name = tmp[0]
                        try:
                            if int(tmp[1]) < 0 or int(tmp[2]) < 0:
                                errors.append(
                                    ParsingError(f"Cords in {tmp[0]} is negative")
                                )
                                continue
                            else:
                                hub_cords = (int(tmp[1]), int(tmp[2]))
                        except ValueError:
                            errors.append(
                                ParsingError(f"Invalid cords format in {hub_name}")
                            )
                        color = None
                        max_drones = None
                        zone = None
                        if len(tmp) > 3:
                            if len(tmp) > 6:
                                errors.append(
                                    ParsingError(f"Too much metadata in {hub_name}")
                                )
                                continue
                            color_str = next(
                                (item for item in tmp[1:] if "color" in item), None
                            )
                            max_drones_str = next(
                                (item for item in tmp[1:] if "max_drones" in item), None
                            )
                            zone_str = next(
                                (item for item in tmp[1:] if "zone" in item), None
                            )

                            total_incoming_params = len(tmp) - 3
                            successfully_parsed = sum(
                                [
                                    color_str is not None,
                                    max_drones_str is not None,
                                    zone_str is not None,
                                ]
                            )
                            if successfully_parsed != total_incoming_params:
                                errors.append(
                                    ParsingError(
                                        f"Invalid or unknown metadata in {hub_name}"
                                    )
                                )
                                continue
                            if color_str is not None:
                                color = color_str.split("=")[1].replace("]", "")
                            if max_drones_str is not None:
                                try:
                                    max_drones = int(
                                        max_drones_str.split("=")[1].replace("]", "")
                                    )
                                    if max_drones < 0:
                                        errors.append(
                                            f"Invalid metadata in {tmp[0]}: max_drones is negative"
                                        )
                                except (IndexError, ValueError) as e:
                                    errors.append(
                                        ParsingError(
                                            f"Invalid metadata in {tmp[0]}: {e}"
                                        )
                                    )
                                    continue
                            if zone_str is not None:
                                zone = zone_str.split("=")[1]
                                if zone not in allowed_zones:
                                    errors.append(
                                        ParsingError(
                                            f"Invalid metadata in {tmp[0]}: zone type is invalid"
                                        )
                                    )
                                    continue
                            #print(hub_name, hub_cords, color, max_drones, zone)
                            load_hubs_to_dict(
                                hub_name, hub_cords, color, max_drones, zone, hub_t
                            )
                    if "connection" in line:
                        tmp = line.split(":")[1].split()
                        connections_lst = tmp[0].split("-")
                        max_link_capacity = None
                        if len(tmp) > 2:
                            errors.append(ParsingError(f"Too much data for connection {tmp[0]}"))
                            continue
                        if len(tmp) > 1:
                            max_link_capacity_str = tmp[1]
                            try:
                                max_link_capacity = int(max_link_capacity_str.split("=")[1].replace("]",""))
                            except ValueError:
                                errors.append(ParsingError(f"max_link_capacity in {tmp[0]} is invalid"))
                        #print(connections_lst,max_link_capacity)
                        load_connections_to_list(connections_lst,max_link_capacity)
            main_data["hubs"] = hubs
            main_data["connections"] = connections
            # clean_data = to_jsonable_python(main_data)
            # print(json.dumps(clean_data, indent=2))
        except (FileNotFoundError,PermissionError,IsADirectoryError,FileExistsError,UnicodeDecodeError) as e:
            print(f"File Erorr: {e}")


if __name__ == "__main__":
    MapData.parsing_from_file("maps/challenger/01_the_impossible_dream.txt")
