from __future__ import annotations
from typing import Dict, List, Set, Any, Type, Optional, cast, TYPE_CHECKING
import os
from enum import Enum
from datetime import datetime, timedelta
import base64
import io
import logging

from weconnect.elements.generic_settings import GenericSettings
from weconnect.elements.generic_status import GenericStatus

from requests import exceptions, codes

from weconnect.addressable import AddressableObject, AddressableAttribute, AddressableDict, AddressableList
if TYPE_CHECKING:
    from weconnect.weconnect import WeConnect
from weconnect.elements.generic_capability import GenericCapability
from weconnect.elements.generic_request_status import GenericRequestStatus
from weconnect.elements.controls import Controls
from weconnect.elements.access_status import AccessStatus
from weconnect.elements.battery_status import BatteryStatus
from weconnect.elements.lv_battery_status import LVBatteryStatus
from weconnect.elements.capability_status import CapabilityStatus
from weconnect.elements.charging_status import ChargingStatus
from weconnect.elements.charging_settings import ChargingSettings
from weconnect.elements.charge_mode import ChargeMode
from weconnect.elements.climatization_status import ClimatizationStatus
from weconnect.elements.climatization_settings import ClimatizationSettings
from weconnect.elements.climatization_timer import ClimatizationTimer
from weconnect.elements.lights_status import LightsStatus
from weconnect.elements.maintenance_status import MaintenanceStatus
from weconnect.elements.warning_lights_status import WarningLightsStatus
from weconnect.elements.parking_position import ParkingPosition
from weconnect.elements.plug_status import PlugStatus
from weconnect.elements.range_status import RangeStatus
from weconnect.elements.window_heating_status import WindowHeatingStatus
from weconnect.elements.odometer_measurement import OdometerMeasurement
from weconnect.elements.range_measurements import RangeMeasurements
from weconnect.elements.readiness_status import ReadinessStatus
from weconnect.elements.charging_profiles import ChargingProfiles
from weconnect.errors import APICompatibilityError, RetrievalError, APIError
from weconnect.util import toBool
from weconnect.weconnect_errors import ErrorEventType
from weconnect.domain import Domain
from weconnect.elements.error import Error

from weconnect.elements.helpers.request_tracker import RequestTracker

SUPPORT_IMAGES = False
try:
    from PIL import Image, ImageDraw  # type: ignore
    SUPPORT_IMAGES = True
except ImportError:
    pass

LOG: logging.Logger = logging.getLogger("weconnect")


class DomainDict(AddressableDict):
    def __init__(self, **kwargs):
        self.error: Error = Error(localAddress='error', parent=self)
        super(DomainDict, self).__init__(**kwargs)

    def updateError(self, fromDict: Dict[str, Any]):
        if 'error' in fromDict:
            self.error.update(fromDict['error'])
        else:
            self.error.reset()

    def hasError(self) -> bool:
        return self.error.enabled


class Vehicle(AddressableObject):  # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        weConnect: WeConnect,
        vin: str,
        parent: AddressableDict[str, Vehicle],
        fromDict: Dict[str, Any],
        fixAPI: bool = True,
        updateCapabilities: bool = True,
        updatePictures: bool = True,
        selective: Optional[list[Domain]] = None,
        enableTracker: bool = False
    ) -> None:
        self.weConnect: WeConnect = weConnect
        super().__init__(localAddress=vin, parent=parent)
        self.vin: AddressableAttribute[str] = AddressableAttribute(localAddress='vin', parent=self, value=None, valueType=str)
        self.role: AddressableAttribute[Vehicle.User.Role] = AddressableAttribute(localAddress='role', parent=self, value=None, valueType=Vehicle.User.Role)
        self.enrollmentStatus: AddressableAttribute[Vehicle.User.EnrollmentStatus] = AddressableAttribute(localAddress='enrollmentStatus', parent=self,
                                                                                                          value=None,
                                                                                                          valueType=Vehicle.User.EnrollmentStatus)
        self.userRoleStatus: AddressableAttribute[Vehicle.User.UserRoleStatus] = AddressableAttribute(localAddress='userRoleStatus', parent=self,
                                                                                                      value=None,
                                                                                                      valueType=Vehicle.User.UserRoleStatus)
        self.model: AddressableAttribute[str] = AddressableAttribute(localAddress='model', parent=self, value=None, valueType=str)
        self.devicePlatform: AddressableAttribute[Vehicle.DevicePlatform] = AddressableAttribute(localAddress='devicePlatform', parent=self,
                                                                                                 value=None,
                                                                                                 valueType=Vehicle.DevicePlatform)
        self.nickname: AddressableAttribute[str] = AddressableAttribute(localAddress='nickname', parent=self, value=None, valueType=str)
        self.capabilities: AddressableDict[str, GenericCapability] = AddressableDict(localAddress='capabilities', parent=self)
        self.domains: AddressableDict[str, DomainDict[str, GenericStatus]] = AddressableDict(localAddress='domains', parent=self)
        self.images: AddressableAttribute[Dict[str, str]] = AddressableAttribute(localAddress='images', parent=self, value=None, valueType=dict)
        self.tags: AddressableAttribute[List[str]] = AddressableAttribute(localAddress='tags', parent=self, value=None, valueType=list)
        self.coUsers: AddressableList[Vehicle.User] = AddressableList(localAddress='coUsers', parent=self)
        self.controls: Controls = Controls(localAddress='controls', vehicle=self, parent=self)
        self.fixAPI: bool = fixAPI

        if SUPPORT_IMAGES:
            self.__carImages: Dict[str, Image.Image] = {}
            self.__badges: Dict[Vehicle.Badge, Image.Image] = {}
            self.pictures: AddressableDict[str, Image.Image] = AddressableDict(localAddress='pictures', parent=self)

        self.requestTracker: Optional[RequestTracker] = None
        if enableTracker:
            self.requestTracker = RequestTracker(self)

        self.update(fromDict, updateCapabilities=updateCapabilities, updatePictures=updatePictures, selective=selective)

    def enableTracker(self) -> None:
        if self.requestTracker is None:
            self.requestTracker = RequestTracker(self)

    def disableTracker(self) -> None:
        self.requestTracker.clear()
        self.requestTracker = None

    def statusExists(self, domain: str, status: str) -> bool:
        if domain in self.domains and status in self.domains[domain]:
            return True
        return False

    def update(  # noqa: C901  # pylint: disable=too-many-branches
        self,
        fromDict: Dict[str, Any] = None,
        updateCapabilities: bool = True,
        updatePictures: bool = True,
        force: bool = False,
        selective: Optional[list[Domain]] = None
    ) -> None:
        if fromDict is not None:
            LOG.debug('Create /update vehicle')

            self.vin.fromDict(fromDict, 'vin')
            self.role.fromDict(fromDict, 'role')
            self.enrollmentStatus.fromDict(fromDict, 'enrollmentStatus')
            self.userRoleStatus.fromDict(fromDict, 'userRoleStatus')
            self.model.fromDict(fromDict, 'model')
            self.devicePlatform.fromDict(fromDict, 'devicePlatform')
            self.nickname.fromDict(fromDict, 'nickname')

            if updateCapabilities and 'capabilities' in fromDict and fromDict['capabilities'] is not None:
                for capDict in fromDict['capabilities']:
                    if 'id' in capDict:
                        if capDict['id'] in self.capabilities:
                            self.capabilities[capDict['id']].update(fromDict=capDict)
                        else:
                            self.capabilities[capDict['id']] = GenericCapability(
                                capabilityId=capDict['id'], parent=self.capabilities, fromDict=capDict,
                                fixAPI=self.fixAPI)
                for capabilityId in [capabilityId for capabilityId in self.capabilities.keys()
                                     if capabilityId not in [capability['id']
                                     for capability in fromDict['capabilities'] if 'id' in capability]]:
                    del self.capabilities[capabilityId]
            else:
                self.capabilities.clear()
                self.capabilities.enabled = False

            if 'images' in fromDict:
                self.images.setValueWithCarTime(fromDict['images'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.images.enabled = False

            if 'tags' in fromDict:
                self.tags.setValueWithCarTime(fromDict['tags'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.tags.enabled = False

            if 'coUsers' in fromDict and fromDict['coUsers'] is not None:
                for user in fromDict['coUsers']:
                    if 'id' in user:
                        usersWithId = [x for x in self.coUsers if x.id.value == user['id']]
                        if len(usersWithId) > 0:
                            usersWithId[0].update(fromDict=user)
                        else:
                            self.coUsers.append(Vehicle.User(localAddress=str(len(self.coUsers)), parent=self.coUsers, fromDict=user))
                    else:
                        raise APICompatibilityError('User is missing id field')
                # Remove all users that are not in list anymore
                for user in [user for user in self.coUsers if user.id.value not in [x['id'] for x in fromDict['coUsers']]]:
                    self.coUsers.remove(user)
            else:
                self.coUsers.enabled = False
                self.coUsers.clear()

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['vin',
                                              'role',
                                              'enrollmentStatus',
                                              'userRoleStatus',
                                              'model',
                                              'devicePlatform',
                                              'nickname',
                                              'capabilities',
                                              'images',
                                              'tags',
                                              'coUsers']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        self.updateStatus(updateCapabilities=updateCapabilities, force=force, selective=selective)
        if SUPPORT_IMAGES and updatePictures:
            for badge in Vehicle.Badge:
                badgeImg: Image = Image.open(f'{os.path.dirname(__file__)}/../badges/{badge.value}.png')
                badgeImg.thumbnail((100, 100))
                self.__badges[badge] = badgeImg

            self.updatePictures()

    def updateStatus(self, updateCapabilities: bool = True, force: bool = False,  # noqa: C901 # pylint: disable=too-many-branches
                     selective: Optional[list[Domain]] = None):
        jobKeyClassMap: Dict[Domain, Dict[str, Type[GenericStatus]]] = {
            Domain.ACCESS: {
                'accessStatus': AccessStatus
            },
            Domain.AUTOMATION: {
                'climatisationTimer': ClimatizationTimer,
                'climatisationTimersRequestStatus': GenericRequestStatus,
                'chargingProfiles': ChargingProfiles,
            },
            Domain.USER_CAPABILITIES: {
                'capabilitiesStatus': CapabilityStatus,
            },
            Domain.CHARGING: {
                'batteryStatus': BatteryStatus,
                'chargingStatus': ChargingStatus,
                'chargingSettings': ChargingSettings,
                'chargeMode': ChargeMode,
                'plugStatus': PlugStatus,
                'chargingRequestStatus': GenericRequestStatus,
                'chargingSettingsRequestStatus': GenericRequestStatus,
                'chargingCareSettings': GenericSettings,
            },
            Domain.CLIMATISATION: {
                'climatisationStatus': ClimatizationStatus,
                'climatisationSettings': ClimatizationSettings,
                'windowHeatingStatus': WindowHeatingStatus,
                'climatisationRequestStatus': GenericRequestStatus,
                'climatisationSettingsRequestStatus': GenericRequestStatus,
            },
            Domain.FUEL_STATUS: {
                'rangeStatus': RangeStatus,
            },
            Domain.VEHICLE_LIGHTS: {
                'lightsStatus': LightsStatus,
            },
            Domain.LV_BATTERY: {
                'lvBatteryStatus': LVBatteryStatus,
            },
            Domain.READINESS: {
                'readinessStatus': ReadinessStatus,
                'readinessBatterySupportStatus': GenericStatus,
            },
            Domain.VEHICLE_HEALTH_INSPECTION: {
                'maintenanceStatus': MaintenanceStatus,
            },
            Domain.VEHICLE_HEALTH_WARNINGS: {
                'warningLights': WarningLightsStatus,
            },
            Domain.OIL_LEVEL: {
                'oilLevelStatus': GenericStatus,
            },
            Domain.MEASUREMENTS: {
                'rangeStatus': RangeMeasurements,
                'odometerStatus': OdometerMeasurement,
                'oilLevelStatus': GenericStatus,
                'measurements': GenericStatus,
            },
            Domain.BATTERY_SUPPORT: {
                'batterySupportStatus': GenericStatus,
            }
        }
        if self.vin.value is None:
            raise APIError('')
        if selective is None:
            jobs = [domain.value for domain in Domain if domain != Domain.ALL and domain != Domain.ALL_CAPABLE and domain != Domain.PARKING]
        elif Domain.ALL_CAPABLE in selective:
            if self.capabilities:
                jobs = []
                for dom in [domain for domain in Domain if domain != Domain.ALL and domain != Domain.ALL_CAPABLE and domain != Domain.PARKING]:
                    if dom.value in self.capabilities and self.capabilities[dom.value].enabled and not self.capabilities[dom.value].status.enabled:
                        jobs.append(dom.value)
                if updateCapabilities:
                    jobs.append(Domain.USER_CAPABILITIES.value)
            else:
                jobs = ['all']
        elif Domain.ALL in selective:
            jobs = ['all']
        else:
            jobs = [domain.value for domain in selective]
        url: str = 'https://mobileapi.apps.emea.vwapps.io/vehicles/' + self.vin.value + '/selectivestatus?jobs=' + ','.join(jobs)
        data: Optional[Dict[str, Any]] = self.weConnect.fetchData(url, force)
        if data is not None:
            for domain, keyClassMap in jobKeyClassMap.items():
                if not updateCapabilities and domain == Domain.USER_CAPABILITIES:
                    continue
                if domain.value in data:
                    if domain.value not in self.domains:
                        self.domains[domain.value] = DomainDict(localAddress=domain.value, parent=self.domains)
                    for key, className in keyClassMap.items():
                        if key in data[domain.value]:
                            if key in self.domains[domain.value]:
                                LOG.debug('Status %s exists, updating it', key)
                                self.domains[domain.value][key].update(fromDict=data[domain.value][key])
                            else:
                                LOG.debug('Status %s does not exist, creating it', key)
                                self.domains[domain.value][key] = className(vehicle=self, parent=self.domains[domain.value], statusId=key,
                                                                            fromDict=data[domain.value][key], fixAPI=self.fixAPI)
                    if 'error' in data[domain.value]:
                        self.domains[domain.value].updateError(data[domain.value])

                    # check that there is no additional status than the configured ones, except for "target" that we merge into
                    # the known ones
                    for key, value in {key: value for key, value in data[domain.value].items()
                                       if key not in list(keyClassMap.keys()) and key not in ['error']}.items():
                        LOG.warning('%s: Unknown attribute %s with value %s in domain %s', self.getGlobalAddress(), key, value, domain.value)
            # check that there is no additional domain than the configured ones
            for key, value in {key: value for key, value in data.items() if key not in list([domain.value for domain in jobKeyClassMap.keys()])}.items():
                LOG.warning('%s: Unknown domain %s with value %s', self.getGlobalAddress(), key, value)

        # Controls
        self.controls.update()

        if (selective is None or any(x in selective for x in [Domain.ALL, Domain.ALL_CAPABLE, Domain.PARKING])) \
                and (not updateCapabilities or ('parkingPosition' in self.capabilities and self.capabilities['parkingPosition'].status.value is None)):
            url = 'https://mobileapi.apps.emea.vwapps.io/vehicles/' + self.vin.value + '/parkingposition'
            data = self.weConnect.fetchData(url, force, allowEmpty=True, allowHttpError=True, allowedErrors=[codes['not_found'],
                                                                                                             codes['no_content'],
                                                                                                             codes['bad_gateway'],
                                                                                                             codes['forbidden']])

            if data is not None:
                if 'parking' not in self.domains:
                    self.domains['parking'] = DomainDict(localAddress='parking', parent=self)
                if 'parkingPosition' in self.domains['parking']:
                    self.domains['parking']['parkingPosition'].update(fromDict=data)
                else:
                    self.domains['parking']['parkingPosition'] = ParkingPosition(vehicle=self,
                                                                                 parent=self.domains['parking'],
                                                                                 statusId='parkingPosition',
                                                                                 fromDict=data)
            else:
                if self.statusExists('parking', 'parkingPosition'):
                    parkingPosition: ParkingPosition = cast(ParkingPosition, self.domains['parking']['parkingPosition'])
                    parkingPosition.latitude.enabled = False
                    parkingPosition.longitude.enabled = False
                    parkingPosition.carCapturedTimestamp.setValueWithCarTime(None, fromServer=True)
                    parkingPosition.carCapturedTimestamp.enabled = False
                    parkingPosition.enabled = False

    def updatePictures(self) -> None:  # noqa: C901
        if not SUPPORT_IMAGES:
            return
        url: str = f'https://vehicle-images-service.apps.emea.vwapps.io/v2/vehicle-images/{self.vin.value}?resolution=2x'
        data = self.weConnect.fetchData(url, allowHttpError=True)
        if data is not None and 'data' in data:  # pylint: disable=too-many-nested-blocks
            for image in data['data']:
                img = None
                cacheDate = None
                imageurl: str = image['url']
                if self.weConnect.maxAgePictures is not None and self.weConnect.cache is not None and imageurl in self.weConnect.cache:
                    img, cacheDateString = self.weConnect.cache[imageurl]
                    img = base64.b64decode(img)
                    img = Image.open(io.BytesIO(img))
                    cacheDate = datetime.fromisoformat(cacheDateString)
                if img is None or self.weConnect.maxAgePictures is None \
                        or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.weConnect.maxAgePictures))):
                    try:
                        imageDownloadResponse = self.weConnect.session.get(imageurl, stream=True)
                        self.weConnect.recordElapsed(imageDownloadResponse.elapsed)
                        if imageDownloadResponse.status_code == codes['ok']:
                            img = Image.open(imageDownloadResponse.raw)
                            if self.weConnect.cache is not None:
                                buffered = io.BytesIO()
                                img.save(buffered, format="PNG")
                                imgStr = base64.b64encode(buffered.getvalue()).decode("utf-8")
                                self.weConnect.cache[imageurl] = (imgStr, str(datetime.utcnow()))
                        elif imageDownloadResponse.status_code == codes['unauthorized']:
                            LOG.info('Server asks for new authorization')
                            self.weConnect.login()
                            imageDownloadResponse = self.weConnect.session.get(imageurl, stream=True)
                            self.weConnect.recordElapsed(imageDownloadResponse.elapsed)
                            if imageDownloadResponse.status_code == codes['ok']:
                                img = Image.open(imageDownloadResponse.raw)
                                if self.weConnect.cache is not None:
                                    buffered = io.BytesIO()
                                    img.save(buffered, format="PNG")
                                    imgStr = base64.b64encode(buffered.getvalue()).decode("utf-8")
                                    self.weConnect.cache[imageurl] = (imgStr, str(datetime.utcnow()))
                            else:
                                self.weConnect.notifyError(self, ErrorEventType.HTTP, str(imageDownloadResponse.status_code),
                                                           'Could not fetch vehicle image due to server error')
                                raise RetrievalError('Could not retrieve vehicle image even after re-authorization.'
                                                     f' Status Code was: {imageDownloadResponse.status_code}')
                            self.weConnect.notifyError(self, ErrorEventType.HTTP, str(imageDownloadResponse.status_code),
                                                       'Could not fetch vehicle image due to server error')
                            raise RetrievalError(f'Could not retrieve vehicle image. Status Code was: {imageDownloadResponse.status_code}')
                        else:
                            LOG.warning('Failed downloading picture %s with status code %d will try again in next update', image['id'],
                                        imageDownloadResponse.status_code)
                    except exceptions.ConnectionError as connectionError:
                        self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'connection',
                                                   'Could not fetch vehicle image due to connection problem')
                        raise RetrievalError from connectionError
                    except exceptions.ChunkedEncodingError as chunkedEncodingError:
                        self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                                   'Could not refresh token due to connection problem with chunked encoding')
                        raise RetrievalError from chunkedEncodingError
                    except exceptions.ReadTimeout as timeoutError:
                        self.weConnect.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch vehicle image due to timeout')
                        raise RetrievalError from timeoutError
                    except exceptions.RetryError as retryError:
                        raise RetrievalError from retryError

                if img is not None:
                    self.__carImages[image['id']] = img
                    if image['id'] == 'car_34view':
                        if 'car' in self.pictures:
                            self.pictures['car'].setValueWithCarTime(self.__carImages['car_34view'], lastUpdateFromCar=None, fromServer=True)
                        else:
                            self.pictures['car'] = AddressableAttribute(localAddress='car', parent=self.pictures, value=self.__carImages['car_34view'],
                                                                        valueType=Image.Image)

            self.updateStatusPicture()

    def updateStatusPicture(self) -> None:  # noqa: C901
        if not SUPPORT_IMAGES:
            return
        if 'car_birdview' in self.__carImages:
            img: Image = self.__carImages['car_birdview']

            badges: Set[Vehicle.Badge] = set()

            doorNameMap: Dict[str, str] = {'frontLeft': 'door_left_front',
                                           'frontRight': 'door_right_front',
                                           'rearLeft': 'door_left_back',
                                           'rearRight': 'door_right_back'}
            windowNameMap: Dict[str, str] = {'frontLeft': 'window_left_front',
                                             'frontRight': 'window_right_front',
                                             'rearLeft': 'window_left_back',
                                             'rearRight': 'window_right_back',
                                             'sunRoof': 'sunroof'}
            if 'access' in self.domains and 'accessStatus' in self.domains['access'] and not self.domains['access']['accessStatus'].error.enabled:
                accessStatus: AccessStatus = cast(AccessStatus, self.domains['access']['accessStatus'])

                if accessStatus.overallStatus.enabled:
                    if accessStatus.overallStatus.value == AccessStatus.OverallState.SAFE:
                        badges.add(Vehicle.Badge.LOCKED)
                    elif accessStatus.overallStatus.value == AccessStatus.OverallState.UNSAFE:
                        badges.add(Vehicle.Badge.UNLOCKED)
                    else:
                        badges.add(Vehicle.Badge.WARNING)

                for name, door in accessStatus.doors.items():
                    name = doorNameMap.get(name, name)
                    doorImageName: Optional[str] = None

                    if door.openState.value == AccessStatus.Door.OpenState.OPEN:
                        doorImageName = f'{name}_overlay'
                    elif door.openState.value == AccessStatus.Door.OpenState.CLOSED:
                        doorImageName = name
                    elif door.openState.value in (AccessStatus.Door.OpenState.INVALID, AccessStatus.Door.OpenState.UNKNOWN):
                        doorImageName = name
                        badges.add(Vehicle.Badge.WARNING)

                    if doorImageName is not None and doorImageName in self.__carImages:
                        doorImage = self.__carImages[doorImageName].convert("RGBA")
                        img.paste(doorImage, (0, 0), doorImage)

                for name, window in accessStatus.windows.items():
                    name = windowNameMap.get(name, name)
                    windowImageName: Optional[str] = None

                    if window.openState.value == AccessStatus.Window.OpenState.OPEN:
                        windowImageName = f'{name}_overlay'
                    elif window.openState.value == AccessStatus.Window.OpenState.CLOSED:
                        windowImageName = name
                    elif window.openState.value in (AccessStatus.Window.OpenState.INVALID, AccessStatus.Window.OpenState.UNKNOWN):
                        windowImageName = name
                        badges.add(Vehicle.Badge.WARNING)

                    if windowImageName is not None and windowImageName in self.__carImages:
                        windowImage = self.__carImages[windowImageName].convert("RGBA")
                        img.paste(windowImage, (0, 0), windowImage)
            else:
                for name in doorNameMap.values():
                    if name in self.__carImages:
                        doorImage = self.__carImages[name].convert("RGBA")
                        img.paste(doorImage, (0, 0), doorImage)
                for name in windowNameMap.values():
                    if name != 'sunroof' and name in self.__carImages:
                        windowImage = self.__carImages[name].convert("RGBA")
                        img.paste(windowImage, (0, 0), windowImage)

            if 'vehicleLights' in self.domains and 'lightsStatus' in self.domains['vehicleLights']:
                lightsStatus: LightsStatus = cast(LightsStatus, self.domains['vehicleLights']['lightsStatus'])
                for name, light in lightsStatus.lights.items():
                    lightNameMap = {'frontLeft': 'door_left_front',
                                    'frontRight': 'door_right_front',
                                    'rearLeft': 'door_left_back',
                                    'rearRight': 'door_right_back'}
                    name = lightNameMap.get(name, name)
                    lightImageName: Optional[str] = None

                    if light.status.value == LightsStatus.Light.LightState.ON:
                        lightImageName = f'light_{name}'
                        if lightImageName in self.__carImages:
                            lightImage = self.__carImages[lightImageName].convert("RGBA")
                            img.paste(lightImage, (0, 0), lightImage)

            if 'charging' in self.domains and 'chargingStatus' in self.domains['charging']:
                chargingStatus: ChargingStatus = cast(ChargingStatus, self.domains['charging']['chargingStatus'])
                if chargingStatus.chargingState.value in (ChargingStatus.ChargingState.CHARGING,
                                                          ChargingStatus.ChargingState.CHARGE_PURPOSE_REACHED_CONSERVATION,
                                                          ChargingStatus.ChargingState.CONSERVATION):
                    badges.add(Vehicle.Badge.CHARGING)
                elif chargingStatus.chargingState.value == ChargingStatus.ChargingState.ERROR:
                    badges.add(Vehicle.Badge.WARNING)

            if 'charging' in self.domains and 'plugStatus' in self.domains['charging']:
                plugStatus: PlugStatus = cast(PlugStatus, self.domains['charging']['plugStatus'])
                if plugStatus.plugConnectionState.value == PlugStatus.PlugConnectionState.CONNECTED:
                    badges.add(Vehicle.Badge.CONNECTED)

            if 'climatisation' in self.domains and 'climatisationStatus' in self.domains['climatisation']:
                climatisationStatus: ClimatizationStatus = cast(ClimatizationStatus, self.domains['climatisation']['climatisationStatus'])
                if climatisationStatus.climatisationState.value == ClimatizationStatus.ClimatizationState.COOLING:
                    badges.add(Vehicle.Badge.COOLING)
                elif climatisationStatus.climatisationState.value == ClimatizationStatus.ClimatizationState.HEATING:
                    badges.add(Vehicle.Badge.HEATING)
                elif climatisationStatus.climatisationState.value == ClimatizationStatus.ClimatizationState.VENTILATION:
                    badges.add(Vehicle.Badge.VENTILATING)

            if 'parking' in self.domains and 'parkingPosition' in self.domains['parking']:
                parkingPosition: ParkingPosition = cast(ParkingPosition, self.domains['parking']['parkingPosition'])
                if parkingPosition.latitude.enabled and parkingPosition.latitude.value is not None:
                    badges.add(Vehicle.Badge.PARKING)

            self.__carImages['status'] = img

            imgWithBadges = img.copy()
            badgeoffset = 0
            for badge in badges:
                badgeImage = self.__badges[badge].convert("RGBA")
                imgWithBadges.paste(badgeImage, (0, badgeoffset), badgeImage)
                badgeoffset += 110

            warningLightoffset = 0
            imgWidth, _ = imgWithBadges.size
            if 'vehicleHealthWarnings' in self.domains and 'warningLights' in self.domains['vehicleHealthWarnings']:
                warningLightsStatus = self.domains['vehicleHealthWarnings']['warningLights']
                if warningLightsStatus.warningLights.enabled:
                    for warningLight in warningLightsStatus.warningLights.values():
                        if warningLight.icon.enabled:
                            draw = ImageDraw.Draw(imgWithBadges)
                            draw.ellipse(((imgWidth - 100), warningLightoffset, (imgWidth - 1), (warningLightoffset + 100)), fill=(0, 0, 0, 200))
                            lightImage = warningLight.icon.value
                            lightImage = lightImage.resize((64, 64), Image.ANTIALIAS)
                            imgWithBadges.paste(lightImage, ((imgWidth - 82), warningLightoffset + 18), lightImage)
                            warningLightoffset += 110

            self.__carImages['statusWithBadge'] = imgWithBadges

            # Car with badges
            if 'car_34view' in self.__carImages:
                carWithBadges = self.__carImages['car_34view'].copy()

                badgeoffset = 0
                for badge in badges:
                    badgeImage = self.__badges[badge].convert("RGBA")
                    carWithBadges.paste(badgeImage, (0, badgeoffset), badgeImage)
                    badgeoffset += 110

                warningLightoffset = 0
                imgWidth, _ = carWithBadges.size
                if 'vehicleHealthWarnings' in self.domains and 'warningLights' in self.domains['vehicleHealthWarnings']:
                    warningLightsStatus = self.domains['vehicleHealthWarnings']['warningLights']
                    if warningLightsStatus.warningLights.enabled:
                        for warningLight in warningLightsStatus.warningLights.values():
                            if warningLight.icon.enabled:
                                draw = ImageDraw.Draw(carWithBadges)
                                draw.ellipse(((imgWidth - 100), warningLightoffset, (imgWidth - 1), (warningLightoffset + 100)), fill=(0, 0, 0, 200))
                                lightImage = warningLight.icon.value
                                lightImage = lightImage.resize((64, 64), Image.ANTIALIAS)
                                carWithBadges.paste(lightImage, ((imgWidth - 82), warningLightoffset + 18), lightImage)
                                warningLightoffset += 110

                self.__carImages['carWithBadge'] = carWithBadges

        else:
            LOG.info('Could not update status picture as birdview image could not be retrieved')
            if 'status' in self.__carImages:
                self.__carImages.pop("status")

        if 'status' in self.pictures:
            if 'status' in self.__carImages:
                self.pictures['status'].setValueWithCarTime(self.__carImages['status'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.pictures['status'].setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
                self.pictures['status'].enabled = False
        else:
            if 'status' in self.__carImages:
                self.pictures['status'] = AddressableAttribute(localAddress='status', parent=self.pictures, value=self.__carImages['status'],
                                                               valueType=Image.Image)

        if 'statusWithBadge' in self.pictures:
            if 'statusWithBadge' in self.__carImages:
                self.pictures['statusWithBadge'].setValueWithCarTime(self.__carImages['statusWithBadge'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.pictures['statusWithBadge'].setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
                self.pictures['statusWithBadge'].enabled = False
        else:
            if 'statusWithBadge' in self.__carImages:
                self.pictures['statusWithBadge'] = AddressableAttribute(localAddress='statusWithBadge', parent=self.pictures,
                                                                        value=self.__carImages['statusWithBadge'],
                                                                        valueType=Image.Image)

        if 'carWithBadge' in self.pictures:
            if 'carWithBadge' in self.__carImages:
                self.pictures['carWithBadge'].setValueWithCarTime(self.__carImages['carWithBadge'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.pictures['carWithBadge'].setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
                self.pictures['carWithBadge'].enabled = False
        else:
            if 'carWithBadge' in self.__carImages:
                self.pictures['carWithBadge'] = AddressableAttribute(localAddress='carWithBadge', parent=self.pictures,
                                                                     value=self.__carImages['carWithBadge'],
                                                                     valueType=Image.Image)

    def __str__(self) -> str:  # noqa: C901
        returnString: str = ''
        if self.vin.enabled and self.vin.value is not None:
            returnString += f'VIN:               {self.vin.value}\n'
        if self.model.enabled and self.model.value is not None:
            returnString += f'Model:             {self.model.value}\n'
        if self.devicePlatform.enabled and self.devicePlatform.value is not None:
            returnString += f'Device Platform:   {self.devicePlatform.value.value}\n'
        if self.nickname.enabled and self.nickname.value is not None:
            returnString += f'Nickname:          {self.nickname.value}\n'
        if self.role.enabled and self.role.value is not None:
            returnString += f'Role:              {self.role.value.value}\n'  # pylint: disable=no-member
        if self.enrollmentStatus.enabled and self.enrollmentStatus.value is not None:
            returnString += f'Enrollment Status: {self.enrollmentStatus.value.value}\n'  # pylint: disable=no-member
        if self.userRoleStatus.enabled and self.userRoleStatus.value is not None:
            returnString += f'User Role Status:  {self.userRoleStatus.value.value}\n'  # pylint: disable=no-member
        if self.coUsers.enabled:
            returnString += f'Co-Users: {len(self.coUsers)} items\n'
            for coUser in self.coUsers:
                if coUser.enabled:
                    returnString += ''.join(['\t' + line for line in str(coUser).splitlines(True)]) + '\n'
        if self.tags.enabled and self.tags.value:
            returnString += 'Tags:               ' + ', '.join(self.tags.value) + '\n'
        if self.capabilities.enabled:
            returnString += f'Capabilities: {len(self.capabilities)} items\n'
            for capability in self.capabilities.values():
                if capability.enabled:
                    returnString += ''.join(['\t' + line for line in str(capability).splitlines(True)]) + '\n'
        if self.domains.enabled:
            returnString += f'Domains: {len(self.domains)} items\n'
            for domain in self.domains:
                returnString += f'[{domain}] Elements: {len(self.domains[domain])} items\n'
                for status in self.domains[domain].values():
                    if status.enabled:
                        returnString += ''.join(['\t' + line for line in str(status).splitlines(True)]) + '\n'
                if self.domains[domain].hasError():
                    returnString += ''.join(['\t' + line for line in f'Error: {self.domains[domain].error}'.splitlines(True)]) + '\n'
        return returnString

    class Badge(Enum):
        CHARGING = 'charging'
        CONNECTED = 'connected'
        COOLING = 'cooling'
        HEATING = 'heating'
        LOCKED = 'locked'
        PARKING = 'parking'
        UNLOCKED = 'unlocked'
        VENTILATING = 'ventilating'
        WARNING = 'warning'

    class DevicePlatform(Enum,):
        MBB = 'MBB'
        MBB_ODP = 'MBB_ODP'
        WCAR = 'WCAR'
        UNKNOWN = 'UNKNOWN'

    class User(AddressableObject):
        def __init__(
            self,
            localAddress: str,
            parent: AddressableObject,
            fromDict: Dict[str, str] = None,
        ) -> None:
            super().__init__(localAddress=localAddress, parent=parent)
            self.id: AddressableAttribute[str] = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=str)
            self.role: AddressableAttribute[Vehicle.User.Role] = AddressableAttribute(localAddress='role', parent=self, value=None, valueType=Vehicle.User.Role)
            self.roleReseted: AddressableAttribute[bool] = AddressableAttribute(localAddress='roleReseted', parent=self, value=None, valueType=bool)
            self.enrollmentStatus: AddressableAttribute[Vehicle.User.EnrollmentStatus] = AddressableAttribute(localAddress='enrollmentStatus', parent=self,
                                                                                                              value=None,
                                                                                                              valueType=Vehicle.User.EnrollmentStatus)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict) -> None:
            LOG.debug('Update User from dict')

            if 'id' in fromDict:
                self.id.setValueWithCarTime(fromDict['id'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.id.enabled = False

            if 'role' in fromDict and fromDict['role']:
                try:
                    self.role.setValueWithCarTime(Vehicle.User.Role(fromDict['role']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.role.setValueWithCarTime(Vehicle.User.Role.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported role: %s was provided, please report this as a bug', fromDict['role'])
            else:
                self.role.enabled = False

            if 'roleReseted' in fromDict:
                self.roleReseted.setValueWithCarTime(toBool(fromDict['roleReseted']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.roleReseted.enabled = False

            if 'enrollmentStatus' in fromDict and fromDict['enrollmentStatus']:
                try:
                    self.enrollmentStatus.setValueWithCarTime(Vehicle.User.EnrollmentStatus(fromDict['enrollmentStatus']), lastUpdateFromCar=None,
                                                              fromServer=True)
                except ValueError:
                    self.enrollmentStatus.setValueWithCarTime(Vehicle.User.EnrollmentStatus.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported target operation: %s was provided, please report this as a bug', fromDict['enrollmentStatus'])
            else:
                self.enrollmentStatus.enabled = False

        def __str__(self) -> str:
            returnValue: str = ''
            if self.id.enabled and self.id.value is not None:
                returnValue += f'Id: {self.id.value}, '
            if self.role.enabled and self.role.value is not None:
                returnValue += f' Role: {self.role.value.value}, '  # pylint: disable=no-member
            if self.roleReseted.enabled and self.roleReseted.value is not None:
                returnValue += f' Reseted: {self.roleReseted.value}, '
            if self.enrollmentStatus.enabled and self.enrollmentStatus.value is not None:
                returnValue += f' Enrollment Status: {self.enrollmentStatus.value.value}'  # pylint: disable=no-member
            return returnValue

        class Role(Enum,):
            PRIMARY_USER = 'PRIMARY_USER'
            SECONDARY_USER = 'SECONDARY_USER'
            GUEST_USER = 'GUEST_USER'
            UNKNOWN = 'UNKNOWN'

            def __str__(self) -> str:
                return self.value

        class EnrollmentStatus(Enum,):
            STARTED = 'STARTED'
            NOT_STARTED = 'NOT_STARTED'
            COMPLETED = 'COMPLETED'
            GDC_MISSING = 'GDC_MISSING'
            INACTIVE = 'INACTIVE'
            UNKNOWN = 'UNKNOWN'

        class UserRoleStatus(Enum,):
            ENABLED = 'ENABLED'
            UNKNOWN = 'UNKNOWN'
