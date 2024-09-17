from typing import Any, Optional, Union, Dict, List
from dataclasses import dataclass
import json


@dataclass
class Address:
    country: str
    street: str
    zipCode: str
    city: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "country": self.country,
            "street": self.street,
            "zipCode": self.zipCode,
            "city": self.city,
        }


@dataclass
class GeoCoordinate:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not isinstance(self.latitude, float) or not isinstance(
            self.longitude, float
        ):
            raise TypeError("Latitude and longitude must be floats")
        if not (-90.0 <= self.latitude <= 90.0 and -180.0 <= self.longitude <= 180.0):
            raise ValueError(
                "Latitude must be between -90 and 90 degrees, and longitude between -180 and 180 degrees."
            )

    def to_dict(self) -> Dict[str, float]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class Destination:
    def __init__(
        self,
        geoCoordinate: GeoCoordinate,
        name: Optional[str] = None,
        address: Optional[Address] = None,
        poiProvider: Optional[str] = None,
    ) -> None:
        """
        A single destination on a route.

        Args:
            geoCoordinate (GeoCoordinate): A GeoCoordinate instance containing the coordinates of the destination (Required).
            name (str): A name for the destination to be displayed in the car (Optional, defaults to "Destination").
            address (Address): The address of the destination, for display purposes only, not used for navigation (Optional).
            poiProvider (str): The source of the location (Optional, defaults to "unknown").
        """
        if not isinstance(geoCoordinate, GeoCoordinate):
            raise ValueError("geoCoordinate is required")

        self.geoCoordinate = geoCoordinate
        self.name = name or "Destination"
        self.address = address
        self.poiProvider = poiProvider or "unknown"

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "geoCoordinate": self.geoCoordinate.to_dict(),
            "destinationName": self.name,
            "poiProvider": self.poiProvider,
            "destinationSource": "MobileApp",
        }

        if self.address is not None:
            data["address"] = self.address.to_dict()

        return data

    @classmethod
    def from_dict(cls, dest_dict: Dict[str, Any]) -> "Destination":
        geoCoordinate: Optional[GeoCoordinate] = None
        address: Optional[Address] = None

        if "geoCoordinate" in dest_dict:
            geoCoordinate = GeoCoordinate(**dest_dict["geoCoordinate"])
        else:
            raise ValueError("geoCoordinate is required in destination data")

        if "address" in dest_dict:
            address = Address(**dest_dict["address"])

        return cls(
            geoCoordinate=geoCoordinate,
            name=dest_dict.get("name", "Destination"),
            address=address,
            poiProvider=dest_dict.get("poiProvider", "unknown"),
        )


class Route:
    def __init__(
        self, destinations: Union[List[Destination], Destination] = []
    ) -> None:
        if isinstance(destinations, Destination):
            destinations = [destinations]
        elif (
            destinations is None
            or not isinstance(destinations, list)
            or not all(isinstance(dest, Destination) for dest in destinations)
        ):
            raise TypeError(
                "destinations must be a single Destination or a list of Destination objects."
            )

        self.destinations = destinations

    def to_list(self) -> List[Dict[str, Any]]:
        route = []
        for i, destination in enumerate(self.destinations):
            data = destination.to_dict()
            if i < len(self.destinations) - 1:
                data["destinationType"] = "stopover"
            route.append(data)

        return route

    @classmethod
    def from_collection(cls, collection: Union[list, dict]) -> "Route":
        """
        Create a route from a dict or list of dicts containing destinations.

        Args:
            route_list (Union[list, dict]): A single destination dict or a list of destinations.

        Example:
            Route.from_collection([
                {
                    "name": "VW Museum",
                    "geoCoordinate": {
                        "latitude": 52.4278793,
                        "longitude": 10.8077433,
                    },
                },
                {
                    "name": "Autostadt",
                    "geoCoordinate": {
                        "latitude": 52.429380,
                        "longitude": 10.791520,
                    },
                    "address": {
                        "country": "Germany",
                        "street": "Stadtbrücke",
                        "zipCode": "38440",
                        "city": "Wolfsburg",
                    },
                },
            ])
        """
        destinations: List[Destination] = []

        if isinstance(collection, dict):
            destinations.append(Destination.from_dict(collection))
        else:
            for dest in collection:
                if isinstance(dest, Destination):
                    destinations.append(dest)
                else:
                    destinations.append(Destination.from_dict(dest))

        return cls(destinations)

    @classmethod
    def from_value(cls, value: Union[str, list, dict, Destination]) -> "Route":
        if isinstance(value, Destination):
            return cls([value])
        elif isinstance(value, (list, dict)):
            return cls.from_collection(value)
        elif isinstance(value, str):
            data = json.loads(value)
            return cls.from_collection(data)
        else:
            raise TypeError("Unsupported type for Route.from_value")
