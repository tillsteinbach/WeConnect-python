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


class WeConnect(AddressableObject):  # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """Main class used to interact with WeConnect"""

    def __init__(  # noqa: C901 # pylint: disable=too-many-arguments
        self,
        username: str,
        password: str,
        tokenfile: Optional[str] = None,
        updateAfterLogin: bool = True,
        loginOnInit: bool = False,
        fixAPI: bool = True,
        maxAge: Optional[int] = None,
        maxAgePictures: Optional[int] = None,
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
            maxAge (int, optional): Maximum age of the cache before date is fetched again. None means no caching. Defaults to None.
            maxAgePictures (Optional[int], optional):  Maximum age of the pictures in the cache before date is fetched again. None means no caching.
            Defaults to None.
            updateCapabilities (bool, optional): Also update the information about the cars capabilities. Defaults to True.
            updatePictures (bool, optional):  Also fetch and update pictures. Defaults to True.
            numRetries (int, optional): Number of retries when http requests are failing. Defaults to 3.
            timeout (bool, optional, optional): Timeout in seconds used for http connections to the VW servers
            selective (list[Domain], optional): Domains to request data for
        """
        super().__init__(localAddress='', parent=None)
        self.username: str = username
        self.password: str = password

        self.__userId: Optional[str] = None  # pylint: disable=unused-private-member
        self.__session: requests.Session = requests.Session()

        self.__vehicles: AddressableDict[str, Vehicle] = AddressableDict(localAddress='vehicles', parent=self)
        self.__stations: AddressableDict[str, ChargingStation] = AddressableDict(localAddress='chargingStations', parent=self)
        self.__cache: Dict[str, Any] = {}
        self.fixAPI: bool = fixAPI
        self.maxAge: Optional[int] = maxAge
        self.maxAgePictures: Optional[int] = maxAgePictures
        self.latitude: Optional[float] = None
        self.longitude: Optional[float] = None
        self.searchRadius: Optional[int] = None
        self.market: Optional[str] = None
        self.useLocale: Optional[str] = locale.getlocale()[0]
        self.__elapsed: List[timedelta] = []

        self.__enableTracker: bool = False

        self.__errorObservers: Set[Tuple[Callable[[Optional[Any], ErrorEventType], None], ErrorEventType]] = set()

        self.tokenfile = tokenfile

        self.__manager = SessionManager(tokenstorefile=tokenfile)
        self.__session = self.__manager.getSession(Service.WE_CONNECT, SessionUser(username=username, password=password))
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
        return self.__cache

    def persistTokens(self) -> None:
        if self.__manager is not None and self.tokenfile is not None:
            self.__manager.saveTokenstore(self.tokenfile)

    def persistCacheAsJson(self, filename: str) -> None:
        with open(filename, 'w', encoding='utf8') as file:
            json.dump(self.__cache, file, cls=ExtendedEncoder)
        LOG.info('Writing cachefile %s', filename)

    def fillCacheFromJson(self, filename: str, maxAge: int, maxAgePictures: Optional[int] = None) -> None:
        self.maxAge = maxAge
        if maxAgePictures is None:
            self.maxAgePictures = maxAge
        else:
            self.maxAgePictures = maxAgePictures

        try:
            with open(filename, 'r', encoding='utf8') as file:
                self.__cache = json.load(file)
        except json.decoder.JSONDecodeError:
            LOG.error('Cachefile %s seems corrupted will delete it and try to create a new one. '
                      'If this problem persists please check if a problem with your disk exists.', filename)
            os.remove(filename)
        LOG.info('Reading cachefile %s', filename)

    def fillCacheFromJsonString(self, jsonString, maxAge: int, maxAgePictures: Optional[int] = None) -> None:
        self.maxAge = maxAge
        if maxAgePictures is None:
            self.maxAgePictures = maxAge
        else:
            self.maxAgePictures = maxAgePictures

        self.__cache = json.loads(jsonString)
        LOG.info('Reading cache from string')

    def clearCache(self) -> None:
        self.__cache.clear()
        LOG.info('Clearing cache')

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
        self.updateChargingStations(force=force)
        self.updateComplete()

    def updateVehicles(self, updateCapabilities: bool = True, updatePictures: bool = True, force: bool = False,  # noqa: C901
                       selective: Optional[list[Domain]] = None) -> None:
        url = 'https://mobileapi.apps.emea.vwapps.io/vehicles'
        data = self.fetchData(url, force)
        if data is not None:
            if 'data' in data and data['data']:
                vins: List[str] = []
                for vehicleDict in data['data']:
                    if 'vin' not in vehicleDict:
                        break
                    vin: str = vehicleDict['vin']
                    vins.append(vin)
                    try:
                        if vin not in self.__vehicles:
                            vehicle = Vehicle(weConnect=self, vin=vin, parent=self.__vehicles, fromDict=vehicleDict, fixAPI=self.fixAPI,
                                              updateCapabilities=updateCapabilities, updatePictures=updatePictures, selective=selective,
                                              enableTracker=self.__enableTracker)
                            self.__vehicles[vin] = vehicle
                        else:
                            self.__vehicles[vin].update(fromDict=vehicleDict, updateCapabilities=updateCapabilities, updatePictures=updatePictures,
                                                        selective=selective)
                    except RetrievalError as retrievalError:
                        LOG.error('Failed to retrieve data for VIN %s: %s', vin, retrievalError)
                # delete those vins that are not anymore available
                for vin in [vin for vin in self.__vehicles if vin not in vins]:
                    del self.__vehicles[vin]

                self.__cache[url] = (data, str(datetime.utcnow()))

    def setChargingStationSearchParameters(self, latitude: float, longitude: float, searchRadius: Optional[int] = None, market: Optional[str] = None,
                                           useLocale: Optional[str] = locale.getlocale()[0]) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.searchRadius = searchRadius
        self.market = market
        self.useLocale = useLocale

    def getChargingStations(self, latitude, longitude, searchRadius=None, market=None, useLocale=None,  # noqa: C901
                            force=False) -> AddressableDict[str, ChargingStation]:
        chargingStationMap: AddressableDict[str, ChargingStation] = AddressableDict(localAddress='', parent=None)
        url: str = f'https://mobileapi.apps.emea.vwapps.io/charging-stations/v2?latitude={latitude}&longitude={longitude}'
        if market is not None:
            url += f'&market={market}'
        if useLocale is not None:
            url += f'&locale={useLocale}'
        if searchRadius is not None:
            url += f'&searchRadius={searchRadius}'
        if self.__userId is not None:
            url += f'&userId={self.__userId}'
        data = self.fetchData(url, force)
        if data is not None:
            if 'chargingStations' in data and data['chargingStations']:
                for stationDict in data['chargingStations']:
                    if 'id' not in stationDict:
                        break
                    stationId: str = stationDict['id']
                    station: ChargingStation = ChargingStation(weConnect=self, stationId=stationId, parent=chargingStationMap, fromDict=stationDict,
                                                               fixAPI=self.fixAPI)
                    chargingStationMap[stationId] = station

                self.__cache[url] = (data, str(datetime.utcnow()))
        return chargingStationMap

    def updateChargingStations(self, force: bool = False) -> None:  # noqa: C901 # pylint: disable=too-many-branches
        if self.latitude is not None and self.longitude is not None:
            url: str = f'https://mobileapi.apps.emea.vwapps.io/charging-stations/v2?latitude={self.latitude}&longitude={self.longitude}'
            if self.market is not None:
                url += f'&market={self.market}'
            if self.useLocale is not None:
                url += f'&locale={self.useLocale}'
            if self.searchRadius is not None:
                url += f'&searchRadius={self.searchRadius}'
            if self.__userId is not None:
                url += f'&userId={self.__userId}'
            data = self.fetchData(url, force)
            if data is not None:
                if 'chargingStations' in data and data['chargingStations']:
                    ids: List[str] = []
                    for stationDict in data['chargingStations']:
                        if 'id' not in stationDict:
                            break
                        stationId: str = stationDict['id']
                        ids.append(stationId)
                        if stationId not in self.__stations:
                            station: ChargingStation = ChargingStation(weConnect=self, stationId=stationId, parent=self.__stations, fromDict=stationDict,
                                                                       fixAPI=self.fixAPI)
                            self.__stations[stationId] = station
                        else:
                            self.__stations[stationId].update(fromDict=stationDict)
                    # delete those vins that are not anymore available
                    for stationId in [stationId for stationId in ids if stationId not in self.__stations]:
                        del self.__stations[stationId]

                    self.__cache[url] = (data, str(datetime.utcnow()))

    def getLeafChildren(self) -> List[AddressableLeaf]:
        return [children for vehicle in self.__vehicles.values() for children in vehicle.getLeafChildren()] \
            + [children for station in self.__stations.values() for children in station.getLeafChildren()]

    def __str__(self) -> str:
        returnString: str = ''
        for vin, vehicle in self.__vehicles.items():
            returnString += f'Vehicle: {vin}\n{vehicle}\n'
        for stationId, station in sorted(self.__stations.items(), key=lambda x: x[1].distance.value, reverse=False):
            returnString += f'Charging Station: {stationId}\n{station}\n'
        return returnString

    def addErrorObserver(self, observer: Callable, errortype: ErrorEventType) -> None:
        self.__errorObservers.add((observer, errortype))
        LOG.debug('%s: Error event observer added for type: %s', self.getGlobalAddress(), errortype)

    def removeErrorObserver(self, observer: Callable, errortype: Optional[ErrorEventType] = None) -> None:
        self.__errorObservers = filter(lambda observerEntry: observerEntry[0] == observer
                                       or (errortype is not None and observerEntry[1] == errortype), self.__errorObservers)

    def getErrorObservers(self, errortype) -> List[Any]:
        return [observerEntry[0] for observerEntry in self.getErrorObserverEntries(errortype)]

    def getErrorObserverEntries(self, errortype: ErrorEventType) -> List[Any]:
        observers: Set[Tuple[Callable, ErrorEventType]] = set()
        for observerEntry in self.__errorObservers:
            observer, observertype = observerEntry
            del observer
            if errortype & observertype:
                observers.add(observerEntry)
        return observers

    def notifyError(self, element, errortype: ErrorEventType, detail: string, message: string = None) -> None:
        observers: List[Callable] = self.getErrorObservers(errortype)
        for observer in observers:
            observer(element=element, errortype=errortype, detail=detail, message=message)
        LOG.debug('%s: Notify called for errors with type: %s for %d observers', self.getGlobalAddress(), errortype, len(observers))

    def recordElapsed(self, elapsed: timedelta) -> None:
        self.__elapsed.append(elapsed)

    def getMinElapsed(self) -> timedelta:
        if len(self.__elapsed) == 0:
            return None
        return min(self.__elapsed)

    def getMaxElapsed(self) -> timedelta:
        if len(self.__elapsed) == 0:
            return None
        return max(self.__elapsed)

    def getAvgElapsed(self) -> timedelta:
        if len(self.__elapsed) == 0:
            return None
        return sum(self.__elapsed, timedelta()) / len(self.__elapsed)

    def getTotalElapsed(self) -> timedelta:
        if len(self.__elapsed) == 0:
            return None
        return sum(self.__elapsed, timedelta())

    def fetchData(self, url, force=False, allowEmpty=False, allowHttpError=False, allowedErrors=None) -> Optional[Dict[str, Any]]:  # noqa: C901
        data: Optional[Dict[str, Any]] = None
        cacheDate: Optional[datetime] = None
        if not force and (self.maxAge is not None and self.cache is not None and url in self.cache):
            data, cacheDateString = self.cache[url]
            cacheDate = datetime.fromisoformat(cacheDateString)
        if data is None or self.maxAge is None \
                or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.maxAge))):
            try:
                statusResponse: requests.Response = self.session.get(url, allow_redirects=False)
                self.recordElapsed(statusResponse.elapsed)
                if statusResponse.status_code in (requests.codes['ok'], requests.codes['multiple_status']):
                    data = statusResponse.json()
                    if self.cache is not None:
                        self.cache[url] = (data, str(datetime.utcnow()))
                elif statusResponse.status_code == requests.codes['unauthorized']:
                    LOG.info('Server asks for new authorization')
                    self.login()
                    statusResponse = self.session.get(url, allow_redirects=False)
                    self.recordElapsed(statusResponse.elapsed)

                    if statusResponse.status_code in (requests.codes['ok'], requests.codes['multiple_status']):
                        data = statusResponse.json()
                        if self.cache is not None:
                            self.cache[url] = (data, str(datetime.utcnow()))
                    elif not allowHttpError or (allowedErrors is not None and statusResponse.status_code not in allowedErrors):
                        self.notifyError(self, ErrorEventType.HTTP, str(statusResponse.status_code), 'Could not fetch data due to server error')
                        raise RetrievalError(f'Could not fetch data even after re-authorization. Status Code was: {statusResponse.status_code}')
                elif not allowHttpError or (allowedErrors is not None and statusResponse.status_code not in allowedErrors):
                    self.notifyError(self, ErrorEventType.HTTP, str(statusResponse.status_code), 'Could not fetch data due to server error')
                    raise RetrievalError(f'Could not fetch data. Status Code was: {statusResponse.status_code}')
            except requests.exceptions.ConnectionError as connectionError:
                self.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not fetch data due to connection problem')
                raise RetrievalError from connectionError
            except requests.exceptions.ChunkedEncodingError as chunkedEncodingError:
                self.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                 'Could not fetch data due to connection problem with chunked encoding')
                raise RetrievalError from chunkedEncodingError
            except requests.exceptions.ReadTimeout as timeoutError:
                self.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch data due to timeout')
                raise RetrievalError from timeoutError
            except requests.exceptions.RetryError as retryError:
                raise RetrievalError from retryError
            except requests.exceptions.JSONDecodeError as jsonError:
                if allowEmpty:
                    data = None
                else:
                    self.notifyError(self, ErrorEventType.JSON, 'json', 'Could not fetch data due to error in returned data')
                    raise RetrievalError from jsonError
        return data
