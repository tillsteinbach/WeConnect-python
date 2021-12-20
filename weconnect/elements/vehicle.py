from __future__ import annotations
from typing import Dict, Set, Any, Type, Optional, cast, TYPE_CHECKING
import os
from enum import Enum
from datetime import datetime, timedelta
import base64
import io
import logging
import json
from weconnect.elements.generic_status import GenericStatus

from requests import Response, exceptions, codes
from PIL import Image  # type: ignore

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
from weconnect.elements.parking_position import ParkingPosition
from weconnect.elements.plug_status import PlugStatus
from weconnect.elements.range_status import RangeStatus
from weconnect.elements.window_heating_status import WindowHeatingStatus
from weconnect.elements.odometer_measurement import OdometerMeasurement
from weconnect.elements.range_measurements import RangeMeasurements
from weconnect.elements.readiness_status import ReadinessStatus
from weconnect.errors import APICompatibilityError, RetrievalError, APIError
from weconnect.util import toBool
from weconnect.weconnect_errors import ErrorEventType

LOG: logging.Logger = logging.getLogger("weconnect")


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
        self.statuses: AddressableDict[str, GenericStatus] = AddressableDict(localAddress='status', parent=self)
        self.images: AddressableAttribute[Dict[str, str]] = AddressableAttribute(localAddress='images', parent=self, value=None, valueType=dict)
        self.coUsers: AddressableList[Vehicle.User] = AddressableList(localAddress='coUsers', parent=self)
        self.controls: Controls = Controls(localAddress='controls', vehicle=self, parent=self)
        self.fixAPI: bool = fixAPI

        self.__carImages: Dict[str, Image.Image] = {}
        self.__badges: Dict[Vehicle.Badge, Image.Image] = {}
        self.pictures: AddressableDict[str, Image.Image] = AddressableDict(localAddress='pictures', parent=self)

        self.update(fromDict, updateCapabilities=updateCapabilities, updatePictures=updatePictures)

    def update(  # noqa: C901  # pylint: disable=too-many-branches
        self,
        fromDict: Dict[str, Any] = None,
        updateCapabilities: bool = True,
        updatePictures: bool = True,
        force: bool = False,
    ) -> None:
        if fromDict is not None:
            LOG.debug('Create /update vehicle')
            if 'vin' in fromDict:
                self.vin.setValueWithCarTime(fromDict['vin'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.vin.enabled = False

            if 'role' in fromDict and fromDict['role']:
                try:
                    self.role.setValueWithCarTime(Vehicle.User.Role(fromDict['role']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.role.setValueWithCarTime(Vehicle.User.Role.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported role: %s was provided, please report this as a bug', fromDict['role'])
            else:
                self.role.enabled = False

            if 'enrollmentStatus' in fromDict and fromDict['enrollmentStatus']:
                try:
                    self.enrollmentStatus.setValueWithCarTime(Vehicle.User.EnrollmentStatus(fromDict['enrollmentStatus']), lastUpdateFromCar=None,
                                                              fromServer=True)
                    if self.enrollmentStatus.value == Vehicle.User.EnrollmentStatus.GDC_MISSING:
                        LOG.warning('WeConnect reported enrollmentStatus GDC_MISSING. This means you have to login at'
                                    ' myvolkswagen.de website and accept the terms and conditions')
                except ValueError:
                    self.enrollmentStatus.setValueWithCarTime(Vehicle.User.EnrollmentStatus.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported enrollment Status: %s was provided, please report this as a bug', fromDict['enrollmentStatus'])
            else:
                self.enrollmentStatus.enabled = False

            if 'userRoleStatus' in fromDict and fromDict['userRoleStatus']:
                try:
                    self.userRoleStatus.setValueWithCarTime(Vehicle.User.UserRoleStatus(fromDict['userRoleStatus']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.userRoleStatus.setValueWithCarTime(Vehicle.User.UserRoleStatus.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported userRoleStatus: %s was provided, please report this as a bug', fromDict['userRoleStatus'])
            else:
                self.userRoleStatus.enabled = False

            if 'model' in fromDict:
                self.model.setValueWithCarTime(fromDict['model'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.model.enabled = False

            if 'devicePlatform' in fromDict and fromDict['devicePlatform']:
                try:
                    self.devicePlatform.setValueWithCarTime(Vehicle.DevicePlatform(fromDict['devicePlatform']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.devicePlatform.setValueWithCarTime(Vehicle.DevicePlatform.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported devicePlatform: %s was provided, please report this as a bug', fromDict['devicePlatform'])
            else:
                self.devicePlatform.enabled = False

            if 'nickname' in fromDict:
                self.nickname.setValueWithCarTime(fromDict['nickname'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.nickname.enabled = False

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
                                              'coUsers']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        self.updateStatus(updateCapabilities=updateCapabilities, force=force)
        if updatePictures:
            for badge in Vehicle.Badge:
                badgeImg: Image = Image.open(f'{os.path.dirname(__file__)}/../badges/{badge.value}.png')
                badgeImg.thumbnail((100, 100))
                self.__badges[badge] = badgeImg

            self.updatePictures()

    def updateStatus(self, updateCapabilities: bool = True, force: bool = False):  # noqa: C901 # pylint: disable=too-many-branches
        data: Optional[Dict[str, Any]] = None
        cacheDate: Optional[datetime] = None
        if self.vin.value is None:
            raise APIError('')
        url: str = 'https://mobileapi.apps.emea.vwapps.io/vehicles/' + self.vin.value + '/status'
        if not force and (self.weConnect.maxAge is not None and self.weConnect.cache is not None and url in self.weConnect.cache):
            data, cacheDateString = self.weConnect.cache[url]
            cacheDate = datetime.fromisoformat(cacheDateString)
        if data is None or self.weConnect.maxAge is None \
                or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.weConnect.maxAge))):
            try:
                statusResponse: Response = self.weConnect.session.get(url, allow_redirects=False)
                self.weConnect.recordElapsed(statusResponse.elapsed)
            except exceptions.ConnectionError as connectionError:
                self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'connection', 'Could not fetch vehicle status due to connection problem')
                raise RetrievalError from connectionError
            except exceptions.ChunkedEncodingError as chunkedEncodingError:
                self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                           'Could not refresh token due to connection problem with chunked encoding')
                raise RetrievalError from chunkedEncodingError
            except exceptions.ReadTimeout as timeoutError:
                self.weConnect.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch vehicle status due to timeout')
                raise RetrievalError from timeoutError
            except exceptions.RetryError as retryError:
                raise RetrievalError from retryError
            if statusResponse.status_code in (codes['ok'], codes['multiple_status']):
                data = statusResponse.json()
                if self.weConnect.cache is not None:
                    self.weConnect.cache[url] = (data, str(datetime.utcnow()))
            elif statusResponse.status_code == codes['unauthorized']:
                LOG.info('Server asks for new authorization')
                self.weConnect.login()
                try:
                    statusResponse = self.weConnect.session.get(url, allow_redirects=False)
                    self.weConnect.recordElapsed(statusResponse.elapsed)
                except exceptions.ConnectionError as connectionError:
                    self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'connection',
                                               'Could not fetch vehicle status due to connection problem')
                    raise RetrievalError from connectionError
                except exceptions.ChunkedEncodingError as chunkedEncodingError:
                    self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                               'Could not refresh token due to connection problem with chunked encoding')
                    raise RetrievalError from chunkedEncodingError
                except exceptions.ReadTimeout as timeoutError:
                    self.weConnect.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch vehicle status due to timeout')
                    raise RetrievalError from timeoutError
                except exceptions.RetryError as retryError:
                    raise RetrievalError from retryError
                if statusResponse.status_code == codes['ok']:
                    data = statusResponse.json()
                    if self.weConnect.cache is not None:
                        self.weConnect.cache[url] = (data, str(datetime.utcnow()))
                else:
                    self.weConnect.notifyError(self, ErrorEventType.HTTP, str(statusResponse.status_code),
                                               'Could not fetch vehicle status due to server error')
                    raise RetrievalError('Could not retrieve vehicle status data even after re-authorization.'
                                         f' Status Code was: {statusResponse.status_code}')
            else:
                self.weConnect.notifyError(self, ErrorEventType.HTTP, str(statusResponse.status_code),
                                           'Could not fetch vehicle status due to server error')
                raise RetrievalError(f'Could not retrieve vehicle status data. Status Code was: {statusResponse.status_code}')

            if self.weConnect.cache is not None:
                self.weConnect.cache[url] = (data, str(datetime.utcnow()))
        keyClassMap: Dict[str, Type[GenericStatus]] = {'accessStatus': AccessStatus,
                                                       'batteryStatus': BatteryStatus,
                                                       'lvBatteryStatus': LVBatteryStatus,
                                                       'chargingStatus': ChargingStatus,
                                                       'chargingSettings': ChargingSettings,
                                                       'chargeMode': ChargeMode,
                                                       'plugStatus': PlugStatus,
                                                       'climatisationStatus': ClimatizationStatus,
                                                       'climatisationSettings': ClimatizationSettings,
                                                       'windowHeatingStatus': WindowHeatingStatus,
                                                       'lightsStatus': LightsStatus,
                                                       'maintenanceStatus': MaintenanceStatus,
                                                       'rangeStatus': RangeStatus,
                                                       'capabilityStatus': CapabilityStatus,
                                                       'capabilitiesStatus': GenericStatus,
                                                       'climatisationTimer': ClimatizationTimer,
                                                       'climatisationRequestStatus': GenericRequestStatus,
                                                       'chargingSettingsRequestStatus': GenericRequestStatus,
                                                       'climatisationSettingsRequestStatus': GenericRequestStatus,
                                                       'climatisationTimersRequestStatus': GenericRequestStatus,
                                                       'chargingRequestStatus': GenericRequestStatus,
                                                       'rangeMeasurements': RangeMeasurements,
                                                       'odometerMeasurement': OdometerMeasurement,
                                                       'oilLevelStatus': GenericStatus,
                                                       'measurements': GenericStatus,
                                                       'readinessBatterySupportStatus': GenericStatus,
                                                       'readinessStatus': ReadinessStatus
                                                       }
        if data is not None and 'data' in data and data['data']:
            for key, className in keyClassMap.items():
                if key == 'capabilityStatus' and not updateCapabilities:
                    continue
                if key in data['data']:
                    if key in self.statuses:
                        LOG.debug('Status %s exists, updating it', key)
                        self.statuses[key].update(fromDict=data['data'][key])
                    else:
                        LOG.debug('Status %s does not exist, creating it', key)
                        self.statuses[key] = className(vehicle=self, parent=self.statuses, statusId=key,
                                                       fromDict=data['data'][key], fixAPI=self.fixAPI)

            # check that there is no additional status than the configured ones, except for "target" that we merge into
            # the known ones
            for key, value in {key: value for key, value in data['data'].items()
                               if key not in list(keyClassMap.keys()) + ['target']}.items():
                # TODO GenericStatus(parent=self.statuses, statusId=statusId, fromDict=statusDict)
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            for status in self.statuses.values():
                status.updateTarget(fromDict=None)
            # target handling (we merge the target state into the statuses)
            if 'target' in data['data']:
                statusId: str
                for statusId, target in data['data']['target'].items():
                    if self.weConnect.fixAPI:
                        statusAliasMap = {'climatisationTimersStatus': 'climatisationTimer'}
                        statusId = statusAliasMap.get(statusId, statusId)
                    if statusId in self.statuses:
                        self.statuses[statusId].updateTarget(fromDict=target)
                    else:
                        LOG.warning('%s: got target %s with value %s for not existing status',
                                    self.getGlobalAddress(), statusId, target)

        # error handling
        if data is not None and 'error' in data and data['error']:
            if isinstance(data['error'], Dict):
                error: Dict[str, Any]
                for statusId, error in data['error'].items():
                    if statusId in self.statuses:
                        self.statuses[statusId].updateError(fromDict=error)
                    elif statusId in keyClassMap:
                        self.statuses[statusId] = keyClassMap[statusId](vehicle=self, parent=self.statuses, statusId=statusId,
                                                                        fromDict=None, fixAPI=self.fixAPI)
                        self.statuses[statusId].updateError(fromDict=error)
                    else:
                        LOG.warning('%s: Unknown attribute %s with value %s in error section', self.getGlobalAddress(), statusId, error)
                for statusId, status in {statusId: status for statusId, status in self.statuses.items()
                                         if statusId not in data['error']}.items():
                    status.error.reset()
            else:
                raise RetrievalError(data['error'])
        else:
            for statusId, status in self.statuses.items():
                status.error.reset()

        # Controls
        self.controls.update()

        if not updateCapabilities or ('parkingPosition' in self.capabilities and self.capabilities['parkingPosition'].status.value is None):
            data = None
            cacheDate = None
            url = 'https://mobileapi.apps.emea.vwapps.io/vehicles/' + self.vin.value + '/parkingposition'
            if not force and (self.weConnect.maxAge is not None and self.weConnect.cache is not None and url in self.weConnect.cache):
                data, cacheDateString = self.weConnect.cache[url]
                cacheDate = datetime.fromisoformat(cacheDateString)
            if data is None or self.weConnect.maxAge is None \
                    or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.weConnect.maxAge))):
                try:
                    statusResponse = self.weConnect.session.get(url, allow_redirects=False)
                    self.weConnect.recordElapsed(statusResponse.elapsed)
                except exceptions.ConnectionError as connectionError:
                    self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'connection',
                                               'Could not fetch parking position due to connection problem')
                    raise RetrievalError from connectionError
                except exceptions.ChunkedEncodingError as chunkedEncodingError:
                    self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                               'Could not refresh token due to connection problem with chunked encoding')
                    raise RetrievalError from chunkedEncodingError
                except exceptions.ReadTimeout as timeoutError:
                    self.weConnect.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch parking position due to timeout')
                    raise RetrievalError from timeoutError
                except exceptions.RetryError as retryError:
                    raise RetrievalError from retryError
                if statusResponse.status_code == codes['ok']:
                    data = statusResponse.json()
                    if self.weConnect.cache is not None:
                        self.weConnect.cache[url] = (data, str(datetime.utcnow()))
                elif statusResponse.status_code == codes['unauthorized']:
                    LOG.info('Server asks for new authorization')
                    self.weConnect.login()
                    try:
                        statusResponse = self.weConnect.session.get(url, allow_redirects=False)
                        self.weConnect.recordElapsed(statusResponse.elapsed)
                    except exceptions.ConnectionError as connectionError:
                        self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'connection',
                                                   'Could not fetch parking position due to connection problem')
                        raise RetrievalError from connectionError
                    except exceptions.ChunkedEncodingError as chunkedEncodingError:
                        self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                                   'Could not refresh token due to connection problem with chunked encoding')
                        raise RetrievalError from chunkedEncodingError
                    except exceptions.ReadTimeout as timeoutError:
                        self.weConnect.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch parking position due to timeout')
                        raise RetrievalError from timeoutError
                    except exceptions.RetryError as retryError:
                        raise RetrievalError from retryError
                    if statusResponse.status_code == codes['ok']:
                        data = statusResponse.json()
                        if self.weConnect.cache is not None:
                            self.weConnect.cache[url] = (data, str(datetime.utcnow()))
                    else:
                        self.weConnect.notifyError(self, ErrorEventType.HTTP, str(statusResponse.status_code),
                                                   'Could not fetch parking position due to server error')
                        raise RetrievalError('Could not retrieve parking position even after re-authorization.'
                                             f' Status Code was: {statusResponse.status_code}')
                elif statusResponse.status_code == codes['bad_request'] \
                        or statusResponse.status_code == codes['no_content'] \
                        or statusResponse.status_code == codes['not_found'] \
                        or statusResponse.status_code == codes['bad_gateway'] \
                        or statusResponse.status_code == codes['forbidden']:
                    try:
                        data = statusResponse.json()
                    except json.JSONDecodeError:
                        data = None
                else:
                    self.weConnect.notifyError(self, ErrorEventType.HTTP, str(statusResponse.status_code),
                                               'Could not fetch parking position due to server error')
                    raise RetrievalError(f'Could not retrieve parking position. Status Code was: {statusResponse.status_code}')

            if data is not None and 'data' in data:
                if 'parkingPosition' in self.statuses:
                    self.statuses['parkingPosition'].update(fromDict=data['data'])
                else:
                    self.statuses['parkingPosition'] = ParkingPosition(vehicle=self,
                                                                       parent=self.statuses,
                                                                       statusId='parkingPosition',
                                                                       fromDict=data['data'])
            elif 'parkingPosition' in self.statuses:
                parkingPosition: ParkingPosition = cast(ParkingPosition, self.statuses['parkingPosition'])
                parkingPosition.latitude.enabled = False
                parkingPosition.longitude.enabled = False
                parkingPosition.carCapturedTimestamp.setValueWithCarTime(None, fromServer=True)
                parkingPosition.carCapturedTimestamp.enabled = False
                parkingPosition.enabled = False

        # error handling
        if data is not None and 'error' in data and data['error']:
            if isinstance(data['error'], Dict):
                if 'parkingPosition' in self.statuses:
                    self.statuses['parkingPosition'].updateError(fromDict=data['error'])
                else:
                    self.statuses['parkingPosition'] = ParkingPosition(vehicle=self,
                                                                       parent=self.statuses,
                                                                       statusId='parkingPosition',
                                                                       fromDict=None)
                    self.statuses['parkingPosition'].updateError(fromDict=data['error'])
            else:
                raise RetrievalError(data['error'])
        else:
            if 'parkingPosition' in self.statuses:
                self.statuses['parkingPosition'].error.reset()

    def updatePictures(self) -> None:  # noqa: C901
        data: Optional[Dict[str, Any]] = None
        cacheDate: Optional[datetime] = None
        url: str = f'https://vehicle-images-service.apps.emea.vwapps.io/v2/vehicle-images/{self.vin.value}?resolution=2x'
        if self.weConnect.maxAge is not None and self.weConnect.cache is not None and url in self.weConnect.cache:
            data, cacheDateString = self.weConnect.cache[url]
            cacheDate = datetime.fromisoformat(cacheDateString)
        if data is None or self.weConnect.maxAge is None \
                or (cacheDate is not None and cacheDate < (datetime.utcnow() - timedelta(seconds=self.weConnect.maxAgePictures))):
            try:
                imageResponse: Response = self.weConnect.session.get(url, allow_redirects=False)
                self.weConnect.recordElapsed(imageResponse.elapsed)
            except exceptions.ConnectionError as connectionError:
                self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'connection',
                                           'Could not fetch vehicle image list due to connection problem')
                raise RetrievalError from connectionError
            except exceptions.ChunkedEncodingError as chunkedEncodingError:
                self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                           'Could not refresh token due to connection problem with chunked encoding')
                raise RetrievalError from chunkedEncodingError
            except exceptions.ReadTimeout as timeoutError:
                self.weConnect.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch vehicle image list due to timeout')
                raise RetrievalError from timeoutError
            except exceptions.RetryError as retryError:
                raise RetrievalError from retryError
            if imageResponse.status_code == codes['ok']:
                data = imageResponse.json()
                if self.weConnect.cache is not None:
                    self.weConnect.cache[url] = (data, str(datetime.utcnow()))
            elif imageResponse.status_code == codes['unauthorized']:
                LOG.info('Server asks for new authorization')
                self.weConnect.login()
                try:
                    imageResponse = self.weConnect.session.get(url, allow_redirects=False)
                    self.weConnect.recordElapsed(imageResponse.elapsed)
                except exceptions.ConnectionError as connectionError:
                    self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'connection',
                                               'Could not fetch vehicle image list due to connection problem')
                    raise RetrievalError from connectionError
                except exceptions.ChunkedEncodingError as chunkedEncodingError:
                    self.weConnect.notifyError(self, ErrorEventType.CONNECTION, 'chunked encoding error',
                                               'Could not refresh token due to connection problem with chunked encoding')
                    raise RetrievalError from chunkedEncodingError
                except exceptions.ReadTimeout as timeoutError:
                    self.weConnect.notifyError(self, ErrorEventType.TIMEOUT, 'timeout', 'Could not fetch vehicle image list due to timeout')
                    raise RetrievalError from timeoutError
                except exceptions.RetryError as retryError:
                    raise RetrievalError from retryError
                if imageResponse.status_code == codes['ok']:
                    data = imageResponse.json()
                    if self.weConnect.cache is not None:
                        self.weConnect.cache[url] = (data, str(datetime.utcnow()))
                else:
                    self.weConnect.notifyError(self, ErrorEventType.HTTP, str(imageResponse.status_code),
                                               'Could not fetch vehicle image list due to server error')
                    raise RetrievalError('Could not retrieve vehicle images even after re-authorization.'
                                         f' Status Code was: {imageResponse.status_code}')
                self.weConnect.notifyError(self, ErrorEventType.HTTP, str(imageResponse.status_code),
                                           'Could not fetch vehicle image list due to server error')
                raise RetrievalError(f'Could not retrieve vehicle images. Status Code was: {imageResponse.status_code}')
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
                        try:
                            imageDownloadResponse = self.weConnect.session.get(imageurl, stream=True)
                            self.weConnect.recordElapsed(imageDownloadResponse.elapsed)
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
        if 'car_birdview' in self.__carImages:
            img: Image = self.__carImages['car_birdview']

            badges: Set[Vehicle.Badge] = set()

            if 'accessStatus' in self.statuses:
                accessStatus: AccessStatus = cast(AccessStatus, self.statuses['accessStatus'])

                if accessStatus.overallStatus.enabled:
                    if accessStatus.overallStatus.value == AccessStatus.OverallState.SAFE:
                        badges.add(Vehicle.Badge.LOCKED)
                    elif accessStatus.overallStatus.value == AccessStatus.OverallState.UNSAFE:
                        badges.add(Vehicle.Badge.UNLOCKED)
                    else:
                        badges.add(Vehicle.Badge.WARNING)

                for name, door in accessStatus.doors.items():
                    doorNameMap: Dict[str, str] = {'frontLeft': 'door_left_front',
                                                   'frontRight': 'door_right_front',
                                                   'rearLeft': 'door_left_back',
                                                   'rearRight': 'door_right_back'}
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
                    windowNameMap: Dict[str, str] = {'frontLeft': 'window_left_front',
                                                     'frontRight': 'window_right_front',
                                                     'rearLeft': 'window_left_back',
                                                     'rearRight': 'window_right_back',
                                                     'sunRoof': 'sunroof'}
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

            if 'lightsStatus' in self.statuses:
                lightsStatus: LightsStatus = cast(LightsStatus, self.statuses['lightsStatus'])
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

            if 'chargingStatus' in self.statuses:
                chargingStatus: ChargingStatus = cast(ChargingStatus, self.statuses['chargingStatus'])
                if chargingStatus.chargingState.value == ChargingStatus.ChargingState.CHARGING:
                    badges.add(Vehicle.Badge.CHARGING)

            if 'plugStatus' in self.statuses:
                plugStatus: PlugStatus = cast(PlugStatus, self.statuses['plugStatus'])
                if plugStatus.plugConnectionState.value == PlugStatus.PlugConnectionState.CONNECTED:
                    badges.add(Vehicle.Badge.CONNECTED)

            if 'climatisationStatus' in self.statuses:
                climatisationStatus: ClimatizationStatus = cast(ClimatizationStatus, self.statuses['climatisationStatus'])
                if climatisationStatus.climatisationState.value == ClimatizationStatus.ClimatizationState.COOLING:
                    badges.add(Vehicle.Badge.COOLING)
                elif climatisationStatus.climatisationState.value == ClimatizationStatus.ClimatizationState.HEATING:
                    badges.add(Vehicle.Badge.HEATING)
                elif climatisationStatus.climatisationState.value == ClimatizationStatus.ClimatizationState.VENTILATION:
                    badges.add(Vehicle.Badge.VENTILATING)

            if 'parkingPosition' in self.statuses:
                parkingPosition: ParkingPosition = cast(ParkingPosition, self.statuses['parkingPosition'])
                if parkingPosition.latitude.enabled and parkingPosition.latitude.value is not None:
                    badges.add(Vehicle.Badge.PARKING)

            self.__carImages['status'] = img

            imgWithBadges = img.copy()
            badgeoffset = 0
            for badge in badges:
                badgeImage = self.__badges[badge].convert("RGBA")
                imgWithBadges.paste(badgeImage, (0, badgeoffset), badgeImage)
                badgeoffset += 110

            self.__carImages['statusWithBadge'] = imgWithBadges

            # Car with badges
            if 'car_34view' in self.__carImages:
                carWithBadges = self.__carImages['car_34view'].copy()

                badgeoffset = 0
                for badge in badges:
                    badgeImage = self.__badges[badge].convert("RGBA")
                    carWithBadges.paste(badgeImage, (0, badgeoffset), badgeImage)
                    badgeoffset += 110

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
        if self.capabilities.enabled:
            returnString += f'Capabilities: {len(self.capabilities)} items\n'
            for capability in self.capabilities.values():
                if capability.enabled:
                    returnString += ''.join(['\t' + line for line in str(capability).splitlines(True)]) + '\n'
        if self.statuses.enabled:
            returnString += f'Statuses: {len(self.statuses)} items\n'
            for status in self.statuses.values():
                if status.enabled:
                    returnString += ''.join(['\t' + line for line in str(status).splitlines(True)]) + '\n'
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
