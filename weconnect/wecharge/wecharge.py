from __future__ import annotations
from typing import Dict, List, Set, Tuple, Callable, Any, Optional

import os
import string
import locale
import logging
import json
from datetime import datetime, timedelta

import requests

from weconnect.auth.session_manager import SessionManager, Service, SessionUser
from weconnect.elements.vehicle import Vehicle
from weconnect.domain import Domain
from weconnect.elements.charging_station import ChargingStation
from weconnect.addressable import AddressableLeaf, AddressableObject, AddressableDict
from weconnect.errors import RetrievalError
from weconnect.weconnect_errors import ErrorEventType
from weconnect.util import ExtendedEncoder

LOG = logging.getLogger("weconnect")


class WeCharge(AddressableObject):  # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """Main class used to interact with WeConnect Mobile App API"""

    def __init__(  # noqa: C901 # pylint: disable=too-many-arguments
        self,
        core: 'WeConnectCore',
        username: str,
        password: str,
        updateAfterLogin: bool = True,
        loginOnInit: bool = False,
        fixAPI: bool = True,
        updateCapabilities: bool = True,
        updatePictures: bool = True,
        numRetries: int = 3,
        timeout: bool = None,
        selective: Optional[list[Domain]] = None
    ) -> None:
        """Initialize WeConnect interface. If loginOnInit is true the user will be tried to login.
           If loginOnInit is true also an initial fetch of data is performed.

        Args:
            username (str): Username used with WeConnect. This is your volkswagen user.
            password (str): Password used with WeConnect. This is your volkswagen password.
            tokenfile (str, optional): Optional file to read/write token from/to. Defaults to None.
            updateAfterLogin (bool, optional): Update data from WeConnect after logging in (If set to false, update needs to be called manually).
            Defaults to True.
            loginOnInit (bool, optional): Login after initialization (If set to false, login needs to be called manually). Defaults to True.
            fixAPI (bool, optional): Automatically fix known issues with the WeConnect responses. Defaults to True.
            Defaults to None.
            updateCapabilities (bool, optional): Also update the information about the cars capabilities. Defaults to True.
            updatePictures (bool, optional):  Also fetch and update pictures. Defaults to True.
            numRetries (int, optional): Number of retries when http requests are failing. Defaults to 3.
            timeout (bool, optional, optional): Timeout in seconds used for http connections to the VW servers
            selective (list[Domain], optional): Domains to request data for
        """
        super().__init__(localAddress='WeConnect', parent=core)
        self.core = core
        self.username: str = username
        self.password: str = password

        self.__userId: Optional[str] = None  # pylint: disable=unused-private-member
        self.__session: requests.Session = requests.Session()

        self.__vehicles: AddressableDict[str, Vehicle] = AddressableDict(localAddress='vehicles', parent=self)
        self.__stations: AddressableDict[str, ChargingStation] = AddressableDict(localAddress='chargingStations', parent=self)
        self.fixAPI: bool = fixAPI
        self.latitude: Optional[float] = None
        self.longitude: Optional[float] = None
        self.searchRadius: Optional[int] = None
        self.market: Optional[str] = None
        self.useLocale: Optional[str] = locale.getlocale()[0]
        self.__elapsed: List[timedelta] = []

        self.__enableTracker: bool = False

        self.__errorObservers: Set[Tuple[Callable[[Optional[Any], ErrorEventType], None], ErrorEventType]] = set()

        self.__session = core.manager.getSession(Service.WE_CHARGE, SessionUser(username=username, password=password))
        self.__session.timeout = timeout
        self.__session.retries = numRetries

        if loginOnInit:
            self.__session.login()

        if updateAfterLogin:
            self.update(updateCapabilities=updateCapabilities, updatePictures=updatePictures, selective=selective)

    def __del__(self) -> None:
        self.disconnect()
        return super().__del__()

    def disconnect(self) -> None:
        pass

    @property
    def session(self) -> requests.Session:
        return self.__session

    @property
    def cache(self) -> Dict[str, Any]:
        return self.core.cache

    def enableTracker(self) -> None:
        self.__enableTracker = True
        for vehicle in self.vehicles:
            vehicle.enableTracker()

    def disableTracker(self) -> None:
        self.__enableTracker = True
        for vehicle in self.vehicles:
            vehicle.disableTracker()

    def login(self) -> None:
        self.__session.login()

    @property
    def vehicles(self) -> AddressableDict[str, Vehicle]:
        return self.__vehicles

    def update(self, updateCapabilities: bool = True, updatePictures: bool = True, force: bool = False,
               selective: Optional[list[Domain]] = None) -> None:
        self.__elapsed.clear()
        self.updateVehicles(updateCapabilities=updateCapabilities, updatePictures=updatePictures, force=force, selective=selective)
        self.updateComplete()

    def updateVehicles(self, updateCapabilities: bool = True, updatePictures: bool = True, force: bool = False,  # noqa: C901
                       selective: Optional[list[Domain]] = None) -> None:
        url = 'https://wecharge.apps.emea.vwapps.io/charge-and-pay/v1/charging/records?limit=25&offset=0'
        data = self.fetchData(url, force)
        print(data)
        exit(1)

    def __str__(self) -> str:
        returnString: str = ''
        for vin, vehicle in self.__vehicles.items():
            returnString += f'Vehicle: {vin}\n{vehicle}\n'
        for stationId, station in sorted(self.__stations.items(), key=lambda x: x[1].distance.value, reverse=False):
            returnString += f'Charging Station: {stationId}\n{station}\n'
        return returnString

    def fetchData(self, url, force=False, allowEmpty=False, allowHttpError=False, allowedErrors=None) -> Optional[Dict[str, Any]]:
        return self.core.fetchData(self.__session, url, force, allowEmpty, allowHttpError, allowedErrors)
