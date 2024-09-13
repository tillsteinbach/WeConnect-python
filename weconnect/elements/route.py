from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class Address:
    country: str
    street: str
    zipCode: str
    city: str

    def to_dict(self) -> dict[str, str]:
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

    def to_dict(self) -> dict[str, float]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
        }

    @property
    def valid(self) -> bool:
        return (
            isinstance(self.latitude, float)
            and isinstance(self.longitude, float)
        )


class Destination:

    def __init__(
        self,
        geoCoordinate: Optional[GeoCoordinate],
        name: str = "Destination",
        address: Optional[Address] = None,
        poiProvider: str = "unknown",
    ):
        """
        A single destination on a route.

        Args:
            geoCoordinate (GeoCoordinate): A GeoCoordinate instance containing the coordinates of the destination (Required).
            name (str): A name for the destination to be displayed in the car (Optional, defaults to "Destination").
            address (Address): The address of the destination, for display purposes only, not used for navigation (Optional).
            poiProvider (str): The source of the location (Optional, defaults to "unknown").
        """
        if geoCoordinate is None or not isinstance(geoCoordinate, GeoCoordinate):
            raise ValueError('geoCoordinate is required and must be a GeoCoordinate object')

        self.address = address
        self.geoCoordinate = geoCoordinate
        self.name = name
        self.poiProvider = poiProvider

    @property
    def valid(self) -> bool:
        return (
            self.geoCoordinate is not None
            and self.geoCoordinate.valid
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "poiProvider": self.poiProvider,
            "destinationName": self.name,
            "destinationSource": "MobileApp",
        }

        if self.address is not None:
            data["address"] = self.address.to_dict()
        elif self.geoCoordinate is not None:
            data["geoCoordinate"] = self.geoCoordinate.to_dict()

        return data


class Route:
    def __init__(self, destinations: list[Destination] = []):
        if (
            destinations is None
            or not isinstance(destinations, list)
            or not all(isinstance(dest, Destination) for dest in destinations)
        ):
            raise ValueError("destinations must be a list of Destination objects.")

        self.destinations = destinations

    @property
    def valid(self) -> bool:
        return bool(self.destinations) and all(
            isinstance(dest, Destination) and dest.valid for dest in self.destinations
        )

    def to_list(self) -> list[dict[str, Any]]:
        route = []
        for i, destination in enumerate(self.destinations):
            data = destination.to_dict()
            if i < len(self.destinations) - 1:
                data["destinationType"] = "stopover"
            route.append(data)

        return route
