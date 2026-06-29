from pydantic import Field, BaseModel, model_validator, ValidationError
from typing import Any, Optional
import json

class ParsingError(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class Hub_MetaData(BaseModel):
    zone: Optional[str] = Field(default="normal")
    color: int = Field(ge=1)
    max_drones: int = Field(ge=1)


class Connections(BaseModel):
    connection_name: str = Field(ge=1)
    color: int = Field(ge=1)
    max_link_capacity: Optional[int] = Field(ge=1)


class Hub(BaseModel):
    hub_cords: tuple[int, int]
    hub_name: str = Field(min_length=1, max_length=100)
    hub_meta_data: Optional[Hub_MetaData] = Field(min_length=1, max_length=100)


class MapData(BaseModel):
    nb_drones: tuple[int, int]
    start_hub_cords: tuple = Field(ge=0)
    start_hub_name: str = Field(min_length=1, max_length=100)
    start_hub_meta_data: Optional[Hub_MetaData] = Field(default=None)
    end_hub: tuple[int, int]
    end_hub_name: str = Field(min_length=1, max_length=100)
    end_hub_meta_data: Optional[Hub_MetaData] = Field(default=None)
    hubs: list[Hub]
    connections: list[Connections]

    

    @classmethod
    def parsing_from_file(cls,file_path:str):
        try:
            with open(file_path,"r",encoding="utf-8") as file:
                data = file.read()
            print(data)
        except Exception:
            pass


if __name__ == "__main__":
    MapData.parsing_from_file("maps/challenger/01_the_impossible_dream.txt")