from pydantic import Field, BaseModel, field_validator
from typing import Any, Optional
from enum import Enum
from typing import cast


class ParsingError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class HUBS(Enum):
    START = 0
    NORMAL = 1
    END = 2


class Hub_MetaData(BaseModel):
    zone: Optional[str] = Field(default="normal")
    color: Optional[str] = Field(default="Green")
    max_drones: Optional[int] = Field(ge=1, default=1)

    @field_validator("zone", mode="before")
    @classmethod
    def set_default_zone(cls, value: Optional[str]) -> str:
        if value is None:
            return "normal"
        return value

    @field_validator("max_drones", mode="before")
    @classmethod
    def set_default_max_drones(cls, value: Optional[int]) -> int:
        if value is None:
            return 1
        return value

    @field_validator("color", mode="before")
    @classmethod
    def set_default_color(cls, value: Optional[str]) -> str:
        if value is None:
            return "white"
        return value


class Connection(BaseModel):
    connection_from: str = Field(min_length=1)
    connection_to: str = Field(min_length=1)
    max_link_capacity: Optional[int] = Field(default=1, ge=1)

    @field_validator("max_link_capacity", mode="before")
    @classmethod
    def set_default_max_drones(cls, value: Optional[int]) -> int:
        if value is None:
            return 1
        return value


class Hub(BaseModel):
    hub_name: str = Field(min_length=1, max_length=100)
    hub_cords: tuple[int, int]
    hub_meta_data: dict


class MapData(BaseModel):
    nb_drones: int = Field(ge=1)
    start_hub_name: str = Field(min_length=1, max_length=100)
    start_hub_cords: tuple[int, int]
    start_hub_meta_data: dict
    end_hub_cords: tuple[int, int]
    end_hub_name: str
    end_hub_meta_data: dict
    hubs: list[Hub]
    connections: list[Connection]

    @classmethod
    def parsing_from_file(cls, file_path: str) -> "MapData":
        """Parses a map configuration file to build and validate a MapData instance.

        Reads drone count, hub metadata (coordinates, restrictions, coloring),
        and link capacities from a text file, enforcing data constraints
        and structural integrity throughout the process.
        """
        allowed_zones = ["normal", "blocked", "restricted", "priority"]

        main_data: dict[str, Any] = {}
        hubs = []
        connections = []
        req_args = [
            "start_hub_name",
            "start_hub_cords",
            "start_hub_meta_data",
            "end_hub_name",
            "end_hub_cords",
            "end_hub_meta_data",
            "nb_drones",
        ]

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
            """Processes a parsed hub and registers it into the corresponding collection.

            Identifies start or end hubs to assign them directly to the map's root properties,
            or converts standard nodes into validated Hub models to append to the global hubs list.
            """
            if hub_t == HUBS.START:
                main_data["start_hub_name"] = hub_name
                main_data["start_hub_cords"] = hub_cord
                main_data["start_hub_meta_data"] = vars(
                    Hub_MetaData(zone=zone, max_drones=max_drones, color=color)
                )
            elif hub_t == HUBS.END:
                main_data["end_hub_name"] = hub_name
                main_data["end_hub_cords"] = hub_cord
                main_data["end_hub_meta_data"] = vars(
                    Hub_MetaData(zone=zone, max_drones=max_drones, color=color)
                )
            else:
                metadata = vars(
                    Hub_MetaData(zone=zone, max_drones=max_drones, color=color)
                )
                tmp = Hub(hub_name=hub_name, hub_cords=hub_cord, hub_meta_data=metadata)
                hubs.append(tmp)

        def load_connections_to_list(
            connections_lst: list[str], max_link_capacity: int | None
        ) -> None:
            """Creates a new Connections model instance
            and appends it to the global connections list."""
            conn = Connection(
                connection_from=connections_lst[0],
                connection_to=connections_lst[1],
                max_link_capacity=max_link_capacity,
            )
            connections.append(conn)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line in file:
                    if line.startswith("#"):
                        continue
                    if "nb_drones" in line:  # nb_drones_line parsing
                        try:
                            main_data["nb_drones"] = int(line.split(":")[1].strip())
                            if int(line.split(":")[1].strip()) < 1:
                                raise ParsingError("nb_drones can not be negative")
                        except ValueError:
                            raise ParsingError("nb_drones is invalid")
                        continue
                    if "hub" in line.split(":")[0]:  # hub logic parsing
                        hub_t = HUBS.NORMAL
                        if "start_hub" in line:
                            if not start_marker:
                                hub_t = HUBS.START
                                start_marker = True
                            else:
                                raise ParsingError("We need only one start hub")
                        elif "end_hub" in line:
                            if not finish_marker:
                                hub_t = HUBS.END
                                finish_marker = True
                            else:
                                raise ParsingError("We need only one finish hub")
                        tmp = line.split(":")[1].split()
                        if len(tmp) != 4 and "[]" in line:
                            raise ParsingError(f"Data for hub: {line.split(":")[0]} is invalid")
                        hub_name = tmp[0]
                        try:
                            hub_cords = (int(tmp[1]), int(tmp[2]))
                        except ValueError:
                            raise ParsingError(f"Invalid cords format in {hub_name}")
                        color = None
                        max_drones = None
                        zone = None
                        if len(tmp) > 3:
                            if len(tmp) > 6:
                                raise ParsingError(f"Too much metadata in {hub_name}")
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
                                raise ParsingError(
                                    f"Invalid or unknown metadata in {hub_name}"
                                )
                            if color_str is not None:
                                color = color_str.split("=")[1].replace("]", "")
                                if not color.isalnum():
                                    raise ParsingError(f"Invalid meatadata in {line}")

                            if max_drones_str is not None:
                                try:
                                    max_drones = int(
                                        max_drones_str.split("=")[1]
                                        .replace("]", "")
                                        .strip()
                                    )
                                    if max_drones < 0:
                                        raise ParsingError(
                                            f"Invalid metadata in {tmp[0]}: max_drones is negative"
                                        )
                                except (IndexError, ValueError) as e:
                                    raise ParsingError(
                                        f"Invalid metadata in {tmp[0]}: {e}"
                                    )
                            if zone_str is not None:
                                zone = zone_str.split("=")[1]
                                if zone not in allowed_zones:
                                    raise ParsingError(
                                        "Invalid metadata in"
                                        f"{tmp[0]}: zone type is invalid"
                                    )
                            # print(hub_name, hub_cords, color, max_drones, zone)
                            load_hubs_to_dict(
                                hub_name, hub_cords, color, max_drones, zone, hub_t
                            )
                        elif len(tmp) == 3:
                            load_hubs_to_dict(
                                hub_name, hub_cords, color, max_drones, zone, hub_t
                            )

                    if "connection" in line.split(":")[0]:
                        tmp = line.split(":")[1].split()
                        connections_lst = tmp[0].split("-")
                        max_link_capacity = None
                        if len(tmp) > 2:
                            raise ParsingError(f"Connection is invalid {tmp[0]}")
                        if len(connections_lst) < 2 or connections_lst[1] == "":
                            raise ParsingError(f"Connection is invalid {tmp[0]}")
                        if len(tmp) > 1:
                            max_link_capacity_str = tmp[1]
                            if "max_link_capacity" not in max_link_capacity_str:
                                raise ParsingError("Invalid metadata for connection"
                                                   f"{"-".join(connections_lst)}")
                            try:
                                max_link_capacity = int(
                                    max_link_capacity_str.split("=")[1]
                                    .replace("]", "")
                                    .strip()
                                )
                            except ValueError:
                                raise ParsingError(
                                    f"max_link_capacity in {tmp[0]} is invalid"
                                )
                        # print(connections_lst,max_link_capacity)
                        load_connections_to_list(connections_lst, max_link_capacity)
            main_data["hubs"] = hubs
            main_data["connections"] = connections
            for el in req_args:
                if el not in main_data.keys():
                    raise ParsingError(f"Add pls {el} argument to map data")
            return cast("MapData", cls.model_validate(main_data))
        except OSError as e:
            raise ParsingError(f"Parsing Error: {e}")


# test parsing
if __name__ == "__main__":
    map_data = MapData.parsing_from_file(
        "/Users/og/myubuntu/42repo/Fly-in/maps/medium/02_circular_loop.txt"
    )
    clean_data = map_data.model_dump_json(indent=2)
    print(clean_data)
