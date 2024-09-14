import json
import pytest
from weconnect.elements.route import Address, GeoCoordinate, Destination, Route


def test_valid_coordinates():
    geo = GeoCoordinate(latitude=52.52, longitude=13.405)
    assert geo.to_dict() == {"latitude": 52.52, "longitude": 13.405}


def test_invalid_coordinate_types():
    with pytest.raises(TypeError):
        GeoCoordinate(latitude="invalid", longitude="invalid")


def test_invalid_coordinates():
    with pytest.raises(ValueError):
        GeoCoordinate(latitude=255.0, longitude=512.0)


def test_edge_case_coordinates():
    # Test with edge values like 0.0
    GeoCoordinate(latitude=0.0, longitude=0.0)


def test_address_to_dict():
    address = Address(
        country="Germany", street="Unter den Linden", zipCode="10117", city="Berlin"
    )
    expected_dict = {
        "country": "Germany",
        "street": "Unter den Linden",
        "zipCode": "10117",
        "city": "Berlin",
    }
    assert address.to_dict() == expected_dict


def test_valid_destination():
    geo = GeoCoordinate(latitude=52.52, longitude=13.405)
    dest = Destination(geoCoordinate=geo, name="Brandenburg Gate")
    expected_dict = {
        "geoCoordinate": {"latitude": 52.52, "longitude": 13.405},
        "destinationName": "Brandenburg Gate",
        "poiProvider": "unknown",
        "destinationSource": "MobileApp",
    }
    assert dest.to_dict() == expected_dict


def test_destination_missing_geo():
    with pytest.raises(ValueError):
        Destination(geoCoordinate=None)


def test_route_with_single_destination():
    geo = GeoCoordinate(latitude=52.52, longitude=13.405)
    dest = Destination(geoCoordinate=geo)
    route = Route(destinations=dest)
    expected_list = [
        {
            "geoCoordinate": {"latitude": 52.52, "longitude": 13.405},
            "destinationName": "Destination",
            "poiProvider": "unknown",
            "destinationSource": "MobileApp",
        }
    ]
    assert route.to_list() == expected_list


def test_route_with_multiple_destinations():
    geo1 = GeoCoordinate(latitude=52.52, longitude=13.405)
    dest1 = Destination(geoCoordinate=geo1)
    geo2 = GeoCoordinate(latitude=48.8566, longitude=2.3522)
    dest2 = Destination(geoCoordinate=geo2, name="Eiffel Tower")
    route = Route(destinations=[dest1, dest2])
    expected_list = [
        {
            "geoCoordinate": {"latitude": 52.52, "longitude": 13.405},
            "destinationName": "Destination",
            "poiProvider": "unknown",
            "destinationSource": "MobileApp",
            "destinationType": "stopover",
        },
        {
            "geoCoordinate": {"latitude": 48.8566, "longitude": 2.3522},
            "destinationName": "Eiffel Tower",
            "poiProvider": "unknown",
            "destinationSource": "MobileApp",
        },
    ]
    assert route.to_list() == expected_list


def test_route_from_collection():
    data = [
        {
            "geoCoordinate": {"latitude": 52.52, "longitude": 13.405},
            "name": "Brandenburg Gate",
        },
        {
            "geoCoordinate": {"latitude": 48.8566, "longitude": 2.3522},
            "name": "Eiffel Tower",
        },
    ]
    route = Route.from_collection(data)
    assert len(route.destinations) == 2


def test_invalid_destination_geo():
    with pytest.raises(ValueError):
        Destination(geoCoordinate=None)


def test_route_with_invalid_destinations():
    with pytest.raises(TypeError):
        Route(destinations="not a list")


def test_route_from_invalid_collection():
    with pytest.raises(ValueError):
        Route.from_collection("invalid data")


def test_route_from_value_with_destination():
    geo = GeoCoordinate(latitude=52.52, longitude=13.405)
    dest = Destination(geoCoordinate=geo, name="Brandenburg Gate")
    route = Route.from_value(dest)
    assert isinstance(route, Route)
    assert len(route.destinations) == 1
    assert route.destinations[0].name == "Brandenburg Gate"


def test_route_from_value_with_list_of_destinations():
    geo1 = GeoCoordinate(latitude=52.52, longitude=13.405)
    dest1 = Destination(geoCoordinate=geo1)
    geo2 = GeoCoordinate(latitude=48.8566, longitude=2.3522)
    dest2 = Destination(geoCoordinate=geo2, name="Eiffel Tower")
    route = Route.from_value([dest1, dest2])
    assert isinstance(route, Route)
    assert len(route.destinations) == 2


def test_route_from_value_with_dict():
    data = {
        "geoCoordinate": {"latitude": 52.52, "longitude": 13.405},
        "name": "Brandenburg Gate",
    }
    route = Route.from_value(data)
    assert isinstance(route, Route)
    assert len(route.destinations) == 1
    assert route.destinations[0].name == "Brandenburg Gate"


def test_route_from_value_with_list_of_dicts():
    data = [
        {
            "geoCoordinate": {"latitude": 52.52, "longitude": 13.405},
            "name": "Brandenburg Gate",
        },
        {
            "geoCoordinate": {"latitude": 48.8566, "longitude": 2.3522},
            "name": "Eiffel Tower",
        },
    ]
    route = Route.from_value(data)
    assert isinstance(route, Route)
    assert len(route.destinations) == 2
    assert route.destinations[1].name == "Eiffel Tower"


def test_route_from_value_with_json_string():
    data = [
        {
            "geoCoordinate": {"latitude": 52.52, "longitude": 13.405},
            "name": "Brandenburg Gate",
        },
        {
            "geoCoordinate": {"latitude": 48.8566, "longitude": 2.3522},
            "name": "Eiffel Tower",
        },
    ]
    json_data = json.dumps(data)
    route = Route.from_value(json_data)
    assert isinstance(route, Route)
    assert len(route.destinations) == 2
    assert route.destinations[0].name == "Brandenburg Gate"


def test_route_from_value_with_invalid_json_string():
    invalid_json = '{"geoCoordinate": {"latitude": 52.52, "longitude": 13.405}, "name": "Brandenburg Gate"'  # Missing closing brace
    with pytest.raises(json.JSONDecodeError):
        Route.from_value(invalid_json)


def test_route_from_value_with_invalid_type():
    with pytest.raises(TypeError):
        Route.from_value(12345)


def test_route_from_value_with_none():
    with pytest.raises(TypeError):
        Route.from_value(None)
