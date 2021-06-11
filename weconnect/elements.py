# pylint: disable=too-many-lines
import logging
import json
from enum import Enum
from datetime import datetime, timedelta, timezone

import requests

from .util import robustTimeParse, toBool
from .addressable import AddressableLeaf, AddressableObject, AddressableAttribute, AddressableDict, AddressableList, \
    ChangeableAttribute
from .errors import APICompatibilityError, ControlError, SetterError


LOG = logging.getLogger("weconnect")


class ControlInputEnum(Enum):
    @classmethod
    def allowedValues(cls):
        return []


class Vehicle(AddressableObject):  # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        weConnect,
        vin,
        parent,
        fromDict,
        fixAPI=True,
    ):
        self.weConnect = weConnect
        super().__init__(localAddress=vin, parent=parent)
        self.vin = AddressableAttribute(localAddress='vin', parent=self, value=None, valueType=str)
        self.role = AddressableAttribute(localAddress='role', parent=self, value=None, valueType=Vehicle.User.Role)
        self.enrollmentStatus = AddressableAttribute(localAddress='enrollmentStatus', parent=self, value=None,
                                                     valueType=Vehicle.User.EnrollmentStatus)
        self.model = AddressableAttribute(localAddress='model', parent=self, value=None, valueType=str)
        self.nickname = AddressableAttribute(localAddress='nickname', parent=self, value=None, valueType=str)
        self.capabilities = AddressableDict(localAddress='capabilities', parent=self)
        self.statuses = AddressableDict(localAddress='status', parent=self)
        self.images = AddressableAttribute(localAddress='images', parent=self, value=None, valueType=dict)
        self.coUsers = AddressableList(localAddress='coUsers', parent=self)
        self.controls = Controls(localAddress='controls', vehicle=self, parent=self)
        self.fixAPI = fixAPI

        self.update(fromDict)

    def update(  # noqa: C901  # pylint: disable=too-many-branches
        self,
        fromDict=None,
        updateCapabilities=True,
        force=False,
    ):
        if fromDict is not None:
            LOG.debug('Create /update vehicle')
            if 'vin' in fromDict:
                self.vin.setValueWithCarTime(fromDict['vin'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.vin.enabled = False

            if 'role' in fromDict:
                try:
                    self.role.setValueWithCarTime(Vehicle.User.Role(fromDict['role']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.role.setValueWithCarTime(Vehicle.User.Role.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported role: %s was provided, please report this as a bug', fromDict['role'])
            else:
                self.role.enabled = False

            if 'enrollmentStatus' in fromDict:
                try:
                    self.enrollmentStatus.setValueWithCarTime(Vehicle.User.EnrollmentStatus(fromDict['enrollmentStatus']), lastUpdateFromCar=None,
                                                              fromServer=True)
                    if self.enrollmentStatus.value == Vehicle.User.EnrollmentStatus.GDC_MISSING:
                        LOG.warning('WeConnect reported enrollmentStatus GDC_MISSING. This means you have to login at'
                                    ' myvolkswagen.de website and accept the terms and conditions')
                except ValueError:
                    self.enrollmentStatus.setValueWithCarTime(Vehicle.User.EnrollmentStatus.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported target operation: %s was provided, please report this as a bug', fromDict['enrollmentStatus'])
            else:
                self.enrollmentStatus.enabled = False

            if 'model' in fromDict:
                self.model.setValueWithCarTime(fromDict['model'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.model.enabled = False

            if 'nickname' in fromDict:
                self.nickname.setValueWithCarTime(fromDict['nickname'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.nickname.enabled = False

            if updateCapabilities and 'capabilities' in fromDict:
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

            if 'coUsers' in fromDict:
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
                                              'model',
                                              'nickname',
                                              'capabilities',
                                              'images',
                                              'coUsers']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        self.updateStatus(updateCapabilities=updateCapabilities, force=force)
        # self.test()

    def updateStatus(self, updateCapabilities=True, force=False):  # noqa: C901 # pylint: disable=too-many-branches
        data = None
        cacheDate = None
        url = 'https://mobileapi.apps.emea.vwapps.io/vehicles/' + self.vin.value + '/status'
        if force or (self.weConnect.maxAge is not None and self.weConnect.cache is not None and url in self.weConnect.cache):
            data, cacheDateString = self.weConnect.cache[url]
            cacheDate = datetime.fromisoformat(cacheDateString)
        if data is None or (cacheDate is not None
                            and cacheDate < (datetime.utcnow() - timedelta(seconds=self.weConnect.maxAge))):
            statusResponse = self.weConnect.session.get(url, allow_redirects=False)
            data = statusResponse.json()
            if self.weConnect.cache is not None:
                self.weConnect.cache[url] = (data, str(datetime.utcnow()))
        keyClassMap = {'accessStatus': AccessStatus,
                       'batteryStatus': BatteryStatus,
                       'chargingStatus': ChargingStatus,
                       'chargingSettings': ChargingSettings,
                       'plugStatus': PlugStatus,
                       'climatisationStatus': ClimatizationStatus,
                       'climatisationSettings': ClimatizationSettings,
                       'windowHeatingStatus': WindowHeatingStatus,
                       'lightsStatus': LightsStatus,
                       'rangeStatus': RangeStatus,
                       'capabilityStatus': CapabilityStatus,
                       'climatisationTimer': ClimatizationTimer,
                       'climatisationRequestStatus': ClimatisationRequestStatus,
                       'chargingSettingsRequestStatus': ChargingSettingsRequestStatus,
                       }
        if 'data' in data and data['data']:
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
                for statusId, target in data['data']['target'].items():
                    if statusId in self.statuses:
                        self.statuses[statusId].updateTarget(fromDict=target)
                    else:
                        LOG.warning('%s: got target %s with value %s for not existing status',
                                    self.getGlobalAddress(), statusId, target)

        # error handling
        if 'error' in data and data['error']:
            for status, error in data['error'].items():
                if status in self.statuses:
                    self.statuses[status].updateError(fromDict=error)
                else:
                    self.statuses[status] = keyClassMap[status](vehicle=self, parent=self.statuses, statusId=status,
                                                                fromDict=None, fixAPI=self.fixAPI)
                    self.statuses[status].updateError(fromDict=error)
        for statusId, status in {statusId: status for statusId, status in self.statuses.items()
                                 if statusId not in data['error']}.items():
            status.error.reset()

        # Controls
        self.controls.update()

        data = None
        cacheDate = None
        url = 'https://mobileapi.apps.emea.vwapps.io/vehicles/' + self.vin.value + '/parkingposition'
        if self.weConnect.maxAge is not None and self.weConnect.cache is not None and url in self.weConnect.cache:
            data, cacheDateString = self.weConnect.cache[url]
            cacheDate = datetime.fromisoformat(cacheDateString)
        if data is None or (cacheDate is not None
                            and cacheDate < (datetime.utcnow() - timedelta(seconds=self.weConnect.maxAge))):
            statusResponse = self.weConnect.session.get(url, allow_redirects=False)
            if statusResponse.status_code == 200:
                data = statusResponse.json()
                if self.weConnect.cache is not None:
                    self.weConnect.cache[url] = (data, str(datetime.utcnow()))
        if data is not None:
            if 'data' in data:
                if 'parkingPosition' in self.statuses:
                    self.statuses['parkingPosition'].update(fromDict=data['data'])
                else:
                    self.statuses['parkingPosition'] = ParkingPosition(vehicle=self,
                                                                       parent=self.statuses,
                                                                       statusId='parkingPosition',
                                                                       fromDict=data['data'])
            return
        if 'parkingPosition' in self.statuses:
            del self.statuses['parkingPosition']

    def __str__(self):  # noqa: C901
        returnString = ''
        if self.vin.enabled:
            returnString += f'VIN:               {self.vin.value}\n'
        if self.model.enabled:
            returnString += f'Model:             {self.model.value}\n'
        if self.nickname.enabled:
            returnString += f'Nickname:          {self.nickname.value}\n'
        if self.role.enabled:
            returnString += f'Role:              {self.role.value.value}\n'
        if self.enrollmentStatus.enabled:
            returnString += f'Enrollment Status: {self.enrollmentStatus.value.value}\n'
        if self.coUsers.enabled:
            returnString += f'Co-Users: {len(self.coUsers)} items\n'
            for coUser in self.coUsers:
                returnString += ''.join(['\t' + line for line in str(coUser).splitlines(True)]) + '\n'
        if self.capabilities.enabled:
            returnString += f'Capabilities: {len(self.capabilities)} items\n'
            for capability in self.capabilities.values():
                returnString += ''.join(['\t' + line for line in str(capability).splitlines(True)]) + '\n'
        if self.statuses.enabled:
            returnString += f'Statuses: {len(self.statuses)} items\n'
            for status in self.statuses.values():
                returnString += ''.join(['\t' + line for line in str(status).splitlines(True)]) + '\n'
        return returnString

    class User(AddressableObject):
        def __init__(
            self,
            localAddress,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=localAddress, parent=parent)
            self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=str)
            self.role = AddressableAttribute(localAddress='role', parent=self, value=None, valueType=Vehicle.User.Role)
            self.roleReseted = AddressableAttribute(localAddress='roleReseted', parent=self, value=None, valueType=bool)
            self.enrollmentStatus = AddressableAttribute(localAddress='enrollmentStatus', parent=self, value=None, valueType=Vehicle.User.EnrollmentStatus)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update User from dict')

            if 'id' in fromDict:
                self.id.setValueWithCarTime(fromDict['id'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.id.enabled = False

            if 'role' in fromDict:
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

            if 'enrollmentStatus' in fromDict:
                try:
                    self.enrollmentStatus.setValueWithCarTime(Vehicle.User.EnrollmentStatus(fromDict['enrollmentStatus']), lastUpdateFromCar=None,
                                                              fromServer=True)
                except ValueError:
                    self.enrollmentStatus.setValueWithCarTime(Vehicle.User.EnrollmentStatus.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported target operation: %s was provided, please report this as a bug', fromDict['enrollmentStatus'])
            else:
                self.enrollmentStatus.enabled = False

        def __str__(self):
            returnValue = ''
            if self.id.enabled:
                returnValue += f'Id: {self.id.value}, '
            if self.role.enabled:
                returnValue += f' Role: {self.role.value.value}, '
            if self.roleReseted.enabled:
                returnValue += f' Reseted: {self.roleReseted.value}, '
            if self.enrollmentStatus.enabled:
                returnValue += f' Enrollment Status: {self.enrollmentStatus.value.value}'
            return returnValue

        class Role(Enum,):
            PRIMARY_USER = 'PRIMARY_USER'
            SECONDARY_USER = 'SECONDARY_USER'
            UNKNOWN = 'unknown role'

        class EnrollmentStatus(Enum,):
            NOT_STARTED = 'NOT_STARTED'
            COMPLETED = 'COMPLETED'
            GDC_MISSING = 'GDC_MISSING'
            UNKNOWN = 'unknown enrollment status'


class GenericCapability(AddressableObject):
    def __init__(
        self,
        capabilityId,
        parent,
        fromDict=None,
        fixAPI=True,
    ):
        self.fixAPI = fixAPI
        super().__init__(localAddress=capabilityId, parent=parent)
        self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=str)
        self.status = AddressableAttribute(localAddress='status', parent=self, value=None, valueType=list)
        self.expirationDate = AddressableAttribute(
            localAddress='expirationDate', parent=self, value=None, valueType=datetime)
        self.userDisablingAllowed = AddressableAttribute(
            localAddress='userDisablingAllowed', parent=self, value=None, valueType=bool)
        LOG.debug('Create capability from dict')
        if fromDict is not None:
            self.update(fromDict=fromDict)

    def update(self, fromDict):
        LOG.debug('Update capability from dict')

        if 'id' in fromDict:
            self.id.setValueWithCarTime(fromDict['id'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.id.enabled = False

        if 'status' in fromDict:
            self.status.setValueWithCarTime(fromDict['status'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.status.enabled = False

        if 'expirationDate' in fromDict:
            self.expirationDate.setValueWithCarTime(robustTimeParse(
                fromDict['expirationDate']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.expirationDate.enabled = False

        if 'userDisablingAllowed' in fromDict:
            self.userDisablingAllowed.setValueWithCarTime(
                fromDict['userDisablingAllowed'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.userDisablingAllowed.enabled = False

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in ['id', 'status', 'expirationDate', 'userDisablingAllowed']}.items():
            LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    def __str__(self):
        returnString = f'[{self.id.value}] Status: {self.status.value} disabling: {self.userDisablingAllowed.value}'
        if self.expirationDate.enabled:
            returnString += f' (expires {self.expirationDate.value.isoformat()})'
        return returnString


class GenericStatus(AddressableObject):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.vehicle = vehicle
        self.fixAPI = fixAPI
        super().__init__(localAddress=None, parent=parent)
        self.id = statusId
        self.address = self.id
        self.carCapturedTimestamp = AddressableAttribute(
            localAddress='carCapturedTimestamp', parent=self, value=None, valueType=datetime)
        self.error = GenericStatus.StatusError(localAddress='error', parent=self)
        self.target = AddressableList(localAddress='target', parent=self)

        if fromDict is not None:
            self.update(fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update status from dict')

        if 'carCapturedTimestamp' in fromDict:
            carCapturedTimestamp = robustTimeParse(fromDict['carCapturedTimestamp'])
            if self.fixAPI:
                # Looks like for some cars the calculation of the carCapturedTimestamp does not account for the timezone
                # Unfortunatly it is unknown what the timezone of the car is. So the best we can do is substract 30
                # minutes as long as the timestamp is in the future. This will create false results when the query
                # interval is large
                fixed = timedelta(hours=0, minutes=0)
                while carCapturedTimestamp > datetime.utcnow().replace(tzinfo=timezone.utc):
                    carCapturedTimestamp -= timedelta(hours=0, minutes=30)
                    fixed -= timedelta(hours=0, minutes=30)
                if fixed > timedelta(hours=0, minutes=0):
                    LOG.warning('%s: Attribute carCapturedTimestamp was in the future. Substracted %s to fix this.'
                                ' This is a problem of the weconnect API and might be fixed in the future',
                                self.getGlobalAddress(), fixed)
                if carCapturedTimestamp == datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0,
                                                    tzinfo=timezone.utc):
                    carCapturedTimestamp = None

            self.carCapturedTimestamp.setValueWithCarTime(carCapturedTimestamp, lastUpdateFromCar=None, fromServer=True)
            if self.carCapturedTimestamp.value is None:
                self.carCapturedTimestamp.enabled = False
        else:
            self.carCapturedTimestamp.enabled = False

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in (['carCapturedTimestamp'] + ignoreAttributes)   # pylint: disable=C0325
                           }.items():
            LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    def updateError(self, fromDict):
        if fromDict is None:
            self.error.reset()
        else:
            self.error.update(fromDict)

    def updateTarget(self, fromDict):
        if fromDict is None:
            self.target.clear()
            self.target.enabled = False
        else:
            for target in fromDict:
                self.target.append(GenericStatus.Target(localAddress=str(
                    len(self.target)), parent=self.target, fromDict=target))

    def __str__(self):
        returnString = f'[{self.id}]'
        if self.carCapturedTimestamp.enabled:
            returnString += f' (last captured {self.carCapturedTimestamp.value.isoformat()})'
        if self.error.enabled:
            returnString += f'\nError: {self.error}'
        for target in self.target:
            returnString += f'\nTarget: {target}'
        return returnString

    class Target(AddressableObject):
        def __init__(
            self,
            localAddress,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=localAddress, parent=parent)
            self.status = AddressableAttribute(localAddress='status', parent=self,
                                               value=None, valueType=GenericStatus.Target.Status)
            self.operation = AddressableAttribute(
                localAddress='operation', parent=self, value=None, valueType=Controls.Operation)
            self.body = AddressableAttribute(localAddress='body', parent=self, value=None, valueType=str)
            self.group = AddressableAttribute(localAddress='group', parent=self, value=None, valueType=int)
            self.info = AddressableAttribute(localAddress='info', parent=self, value=None, valueType=str)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update Status Target from dict')

            if 'status' in fromDict:
                try:
                    self.status.setValueWithCarTime(GenericStatus.Target.Status(
                        fromDict['status']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.status.setValueWithCarTime(GenericStatus.Target.Status.UNKNOWN,
                                                    lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported target status: %s was provided,'
                                ' please report this as a bug', fromDict['status'])
            else:
                self.status.enabled = False

            if 'operation' in fromDict:
                try:
                    self.operation.setValueWithCarTime(Controls.Operation(
                        fromDict['operation']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.operation.setValueWithCarTime(Controls.Operation.UNKNOWN,
                                                       lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported target operation: %s was provided,'
                                ' please report this as a bug', fromDict['operation'])
            else:
                self.operation.enabled = False

            if 'body' in fromDict:
                self.body.setValueWithCarTime(str(fromDict['body']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.body.enabled = False

            if 'group' in fromDict:
                self.group.setValueWithCarTime(int(fromDict['group']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.group.enabled = False

            if 'info' in fromDict:
                self.info.setValueWithCarTime(fromDict['info'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.info.enabled = False

        def __str__(self):
            returnValue = ''
            if self.operation.enabled:
                returnValue += f'{self.operation.value.value} operation,'
            if self.status.enabled:
                returnValue += f' status {self.status.value.value} '
            if self.info.enabled:
                returnValue += f' information: {self.info.value}'
            return returnValue

        class Status(Enum,):
            SUCCESSFULL = 'successful'
            POLLING_TIMEOUT = 'polling_timeout'
            IN_PROGRESS = 'in_progress'
            QUEUED = 'queued'
            UNKNOWN = 'unknown status'

    class StatusError(AddressableObject):
        def __init__(
            self,
            localAddress,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=localAddress, parent=parent)
            self.code = AddressableAttribute(localAddress='code', parent=self, value=None, valueType=int)
            self.message = AddressableAttribute(localAddress='message', parent=self, value=None, valueType=str)
            self.group = AddressableAttribute(localAddress='group', parent=self, value=None, valueType=int)
            self.info = AddressableAttribute(localAddress='info', parent=self, value=None, valueType=str)
            self.retry = AddressableAttribute(localAddress='retry', parent=self, value=None, valueType=bool)

            if fromDict is not None:
                self.update(fromDict)

        def reset(self):
            self.code.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.code.enabled = False
            self.message.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.message.enabled = False
            self.group.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.group.enabled = False
            self.info.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.info.enabled = False
            self.retry.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.retry.enabled = False
            self.enabled = False

        def update(self, fromDict):
            LOG.debug('Update Status Error from dict')

            if 'code' in fromDict:
                self.code.setValueWithCarTime(int(fromDict['code']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.code.enabled = False

            if 'message' in fromDict:
                self.message.setValueWithCarTime(fromDict['message'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.message.enabled = False

            if 'group' in fromDict:
                self.group.setValueWithCarTime(int(fromDict['group']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.code.enabled = False

            if 'info' in fromDict:
                self.info.setValueWithCarTime(fromDict['info'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.info.enabled = False

            if 'retry' in fromDict:
                self.retry.setValueWithCarTime(toBool(fromDict['retry']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.retry.enabled = False

            if not self.code.enabled and not self.message.enabled and not self.code.enabled and not self.info.enabled \
                    and not self.retry.enabled:
                self.enabled = False
            else:
                self.enabled = True

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['code', 'message', 'group', 'info', 'retry']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            return f'Error {self.code.value}: {self.message.value} info: {self.info.value}'


class GenericSettings(GenericStatus):
    def valueChanged(self, element, flags):
        del element
        if flags & AddressableLeaf.ObserverEvent.VALUE_CHANGED \
                and not flags & AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER:
            setting = self.id.partition('Settings')[0]
            url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/{setting}/settings'
            settingsDict = dict()
            for child in self.getLeafChildren():
                if isinstance(child, ChangeableAttribute):
                    if isinstance(child.value, Enum):  # pylint: disable=no-member # this is a fales positive
                        settingsDict[child.getLocalAddress()] = child.value.value  # pylint: disable=no-member # this is a fales positive
                    else:
                        settingsDict[child.getLocalAddress()] = child.value  # pylint: disable=no-member # this is a fales positive
            data = json.dumps(settingsDict)
            putResponse = self.vehicle.weConnect.session.put(url, data=data, allow_redirects=True)
            if putResponse.status_code != requests.codes['ok']:
                raise SetterError(f'Could not set value ({putResponse.status_code})')


class AccessStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.overallStatus = AddressableAttribute(localAddress='overallStatus', parent=self, value=None, valueType=str)
        self.doors = AddressableDict(localAddress='doors', parent=self)
        self.windows = AddressableDict(localAddress='windows', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):  # noqa: C901
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update access status from dict')

        if 'overallStatus' in fromDict:
            self.overallStatus.setValueWithCarTime(fromDict['overallStatus'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.overallStatus.enabled = False

        if 'doors' in fromDict:
            for doorDict in fromDict['doors']:
                if 'name' in doorDict:
                    if doorDict['name'] in self.doors:
                        self.doors[doorDict['name']].update(fromDict=doorDict)
                    else:
                        self.doors[doorDict['name']] = AccessStatus.Door(fromDict=doorDict, parent=self.doors)
            for doorName in [doorName for doorName in self.doors.keys()
                             if doorName not in [door['name'] for door in fromDict['doors'] if 'name' in door]]:
                del self.doors[doorName]
        else:
            self.doors.clear()
            self.doors.enabled = False

        if 'windows' in fromDict:
            for windowDict in fromDict['windows']:
                if 'name' in windowDict:
                    if windowDict['name'] in self.windows:
                        self.windows[windowDict['name']].update(fromDict=windowDict)
                    else:
                        self.windows[windowDict['name']] = AccessStatus.Window(fromDict=windowDict, parent=self.windows)
            for windowName in [windowName for windowName in self.windows.keys()
                               if windowName not in [window['name']
                               for window in fromDict['windows'] if 'name' in window]]:
                del self.doors[windowName]
        else:
            self.windows.clear()
            self.windows.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['overallStatus', 'doors', 'windows']))

    def __str__(self):
        string = super().__str__() + '\n'
        string += f'\tOverall Status: {self.overallStatus.value}\n'
        string += f'\tDoors: {len(self.doors)} items\n'
        for door in self.doors.values():
            string += f'\t\t{door}\n'
        string += f'\tWindows: {len(self.windows)} items\n'
        for window in self.windows.values():
            string += f'\t\t{window}\n'
        return string

    class Door(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.openState = AddressableAttribute(
                localAddress='openState', parent=self, value=None, valueType=AccessStatus.Door.OpenState)
            self.lockState = AddressableAttribute(
                localAddress='lockState', parent=self, value=None, valueType=AccessStatus.Door.LockState)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update door from dict')

            if 'name' in fromDict:
                self.id = fromDict['name']
                self.address = self.id
            else:
                LOG.error('Door is missing name attribute')

            if 'status' in fromDict:
                if 'locked' in fromDict['status']:
                    self.lockState.setValueWithCarTime(
                        AccessStatus.Door.LockState.LOCKED, lastUpdateFromCar=None, fromServer=True)
                elif 'unlocked' in fromDict['status']:
                    self.lockState.setValueWithCarTime(
                        AccessStatus.Door.LockState.UNLOCKED, lastUpdateFromCar=None, fromServer=True)
                else:
                    self.lockState.setValueWithCarTime(
                        AccessStatus.Door.LockState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)

                if 'open' in fromDict['status']:
                    self.openState.setValueWithCarTime(AccessStatus.Door.OpenState.OPEN,
                                                       lastUpdateFromCar=None, fromServer=True)
                elif 'closed' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Door.OpenState.CLOSED, lastUpdateFromCar=None, fromServer=True)
                elif 'unsupported' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Door.OpenState.UNSUPPORTED, lastUpdateFromCar=None, fromServer=True)
                elif 'invalid' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Door.OpenState.INVALID, lastUpdateFromCar=None, fromServer=True)
                else:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Door.OpenState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
            else:
                self.lockState.enabled = False
                self.openState.enabled = False

            for key, value in {key: value for key, value in fromDict.items() if key not in ['name', 'status']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnString = f'{self.id}: '
            if self.openState.enabled:
                returnString += f'{self.openState.value.value}'
            elif self.lockState.enabled:
                returnString += f', {self.lockState.value.value}'
            return returnString

        class OpenState(Enum):
            OPEN = 'open'
            CLOSED = 'closed'
            UNSUPPORTED = 'unsupported'
            INVALID = 'invalid'
            UNKNOWN = 'unknown open state'

        class LockState(Enum):
            LOCKED = 'locked'
            UNLOCKED = 'unlocked'
            UNKNOWN = 'unknown lock state'

    class Window(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.openState = AddressableAttribute(
                localAddress='openState', parent=self, value=None, valueType=AccessStatus.Window.OpenState)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update window from dict')

            if 'name' in fromDict:
                self.id = fromDict['name']
                self.address = self.id
            else:
                LOG.error('Window is missing name attribute')

            if 'status' in fromDict:
                if 'open' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Window.OpenState.OPEN, lastUpdateFromCar=None, fromServer=True)
                elif 'closed' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Window.OpenState.CLOSED, lastUpdateFromCar=None, fromServer=True)
                elif 'unsupported' in fromDict['status']:
                    self.openState.setValueWithCarTime(AccessStatus.Window.OpenState.UNSUPPORTED, lastUpdateFromCar=None)
                elif 'invalid' in fromDict['status']:
                    self.openState.setValueWithCarTime(AccessStatus.Window.OpenState.INVALID, lastUpdateFromCar=None)
                else:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Window.OpenState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('No unsupported window status: %s was provided, please report this as a bug', fromDict['status'])
            else:
                self.openState.enabled = False

            for key, value in {key: value for key, value in fromDict.items() if key not in ['name', 'status']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            return f'{self.id}: {self.openState.value.value}'

        class OpenState(Enum,):
            OPEN = 'open'
            CLOSED = 'closed'
            UNSUPPORTED = 'unsupported'
            INVALID = 'invalid'
            UNKNOWN = 'unknown open state'


class BatteryStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.currentSOC_pct = AddressableAttribute(
            localAddress='currentSOC_pct', parent=self, value=None, valueType=int)
        self.cruisingRangeElectric_km = AddressableAttribute(
            localAddress='cruisingRangeElectric_km', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update battery status from dict')

        if 'currentSOC_pct' in fromDict:
            self.currentSOC_pct.setValueWithCarTime(
                int(fromDict['currentSOC_pct']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.currentSOC_pct.enabled = False

        if 'cruisingRangeElectric_km' in fromDict:
            cruisingRangeElectric_km = int(fromDict['cruisingRangeElectric_km'])
            if self.fixAPI and cruisingRangeElectric_km == 0x3FFF:
                cruisingRangeElectric_km = None
                LOG.warning('%s: Attribute cruisingRangeElectric_km was error value 0x3FFF. Setting error state instead'
                            ' of 16383 km.', self.getGlobalAddress())
            self.cruisingRangeElectric_km.setValueWithCarTime(
                cruisingRangeElectric_km, lastUpdateFromCar=None, fromServer=True)
        else:
            self.cruisingRangeElectric_km.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['currentSOC_pct', 'cruisingRangeElectric_km']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.currentSOC_pct.enabled:
            string += f'\tCurrent SoC: {self.currentSOC_pct.value}%\n'
        if self.cruisingRangeElectric_km.enabled:
            if self.cruisingRangeElectric_km.value is not None:
                string += f'\tRange: {self.cruisingRangeElectric_km.value}km\n'
            else:
                string += '\tRange: currently unknown\n'
        return string


class ChargingStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.remainingChargingTimeToComplete_min = AddressableAttribute(
            localAddress='remainingChargingTimeToComplete_min', parent=self, value=None, valueType=int)
        self.chargingState = AddressableAttribute(
            localAddress='chargingState', value=None, parent=self, valueType=ChargingStatus.ChargingState)
        self.chargePower_kW = AddressableAttribute(
            localAddress='chargePower_kW', value=None, parent=self, valueType=int)
        self.chargeRate_kmph = AddressableAttribute(
            localAddress='chargeRate_kmph', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging status from dict')

        if 'remainingChargingTimeToComplete_min' in fromDict:
            self.remainingChargingTimeToComplete_min \
                .setValueWithCarTime(int(fromDict['remainingChargingTimeToComplete_min']), lastUpdateFromCar=None,
                                     fromServer=True)
        else:
            self.remainingChargingTimeToComplete_min.enabled = False

        if 'chargingState' in fromDict:
            try:
                self.chargingState.setValueWithCarTime(ChargingStatus.ChargingState(fromDict['chargingState']),
                                                       lastUpdateFromCar=None)
            except ValueError:
                self.chargingState.setValueWithCarTime(
                    ChargingStatus.ChargingState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported chargingState: %s was provided,'
                            ' please report this as a bug', fromDict['chargingState'])
        else:
            self.chargingState.enabled = False

        if 'chargePower_kW' in fromDict:
            self.chargePower_kW.setValueWithCarTime(
                int(fromDict['chargePower_kW']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.chargePower_kW.enabled = False

        if 'chargeRate_kmph' in fromDict:
            self.chargeRate_kmph.setValueWithCarTime(
                int(fromDict['chargeRate_kmph']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.chargeRate_kmph.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'remainingChargingTimeToComplete_min',
                                                                'chargingState',
                                                                'chargePower_kW',
                                                                'chargeRate_kmph'
                                                            ]))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.chargingState.enabled:
            string += f'\tState: {self.chargingState.value.value}\n'
        if self.remainingChargingTimeToComplete_min.enabled:
            string += f'\tRemaining Charging Time: {self.remainingChargingTimeToComplete_min.value} minutes\n'
        if self.chargePower_kW.enabled:
            string += f'\tCharge Power: {self.chargePower_kW.value} kW\n'
        if self.chargeRate_kmph.enabled:
            string += f'\tCharge Rate: {self.chargeRate_kmph.value} km/h\n'
        return string

    class ChargingState(Enum,):
        OFF = 'off'
        READY_FOR_CHARGING = 'readyForCharging'
        CHARGING = 'charging'
        ERROR = 'error'
        UNKNOWN = 'unknown charging state'


class ChargingSettings(GenericSettings):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.maxChargeCurrentAC = ChangeableAttribute(
            localAddress='maxChargeCurrentAC', parent=self, value=None, valueType=ChargingSettings.MaximumChargeCurrent)
        self.autoUnlockPlugWhenCharged = ChangeableAttribute(localAddress='autoUnlockPlugWhenCharged', value=None,
                                                             parent=self, valueType=ChargingSettings.UnlockPlugState)
        self.targetSOC_pct = ChangeableAttribute(localAddress='targetSOC_pct', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

        self.maxChargeCurrentAC.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.autoUnlockPlugWhenCharged.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                                   priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.targetSOC_pct.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                       priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging settings from dict')

        if 'maxChargeCurrentAC' in fromDict:
            try:
                self.maxChargeCurrentAC.setValueWithCarTime(ChargingSettings.MaximumChargeCurrent(
                    fromDict['maxChargeCurrentAC']), lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.maxChargeCurrentAC.setValueWithCarTime(ChargingSettings.MaximumChargeCurrent.UNKNOWN,
                                                            lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported maxChargeCurrentAC: %s was provided,'
                            ' please report this as a bug', fromDict['maxChargeCurrentAC'])
        else:
            self.maxChargeCurrentAC.enabled = False

        if 'autoUnlockPlugWhenCharged' in fromDict:
            try:
                self.autoUnlockPlugWhenCharged.setValueWithCarTime(ChargingSettings.UnlockPlugState(
                    fromDict['autoUnlockPlugWhenCharged']), lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.autoUnlockPlugWhenCharged.setValueWithCarTime(ChargingSettings.UnlockPlugState.UNKNOWN,
                                                                   lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported autoUnlockPlugWhenCharged: %s was provided,'
                            ' please report this as a bug', fromDict['autoUnlockPlugWhenCharged'])
        else:
            self.autoUnlockPlugWhenCharged.enabled = False

        if 'targetSOC_pct' in fromDict:
            self.targetSOC_pct.setValueWithCarTime(
                int(fromDict['targetSOC_pct']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.targetSOC_pct.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'maxChargeCurrentAC',
                                                                'autoUnlockPlugWhenCharged',
                                                                'targetSOC_pct'
                                                            ]))

    def __str__(self):
        string = super().__str__()
        if self.maxChargeCurrentAC.enabled:
            string += f'\n\tMaximum Charge Current AC: {self.maxChargeCurrentAC.value.value}'  # pylint: disable=no-member # this is a fales positive
        if self.autoUnlockPlugWhenCharged.enabled:
            string += f'\n\tAuto Unlock When Charged: {self.autoUnlockPlugWhenCharged.value.value}'  # pylint: disable=no-member # this is a fales positive
        if self.targetSOC_pct.enabled:
            string += f'\n\tTarget SoC: {self.targetSOC_pct.value} %'
        return string

    class UnlockPlugState(ControlInputEnum,):
        OFF = 'off'
        ON = 'on'
        UNKNOWN = 'unknown'

        @classmethod
        def allowedValues(cls):
            return [ChargingSettings.UnlockPlugState.OFF, ChargingSettings.UnlockPlugState.ON]

    class MaximumChargeCurrent(ControlInputEnum,):
        MAXIMUM = 'maximum'
        REDUCED = 'reduced'
        INVALID = 'invalid'
        UNKNOWN = 'unknown'

        @classmethod
        def allowedValues(cls):
            return [ChargingSettings.MaximumChargeCurrent.MAXIMUM, ChargingSettings.MaximumChargeCurrent.REDUCED]


class PlugStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.plugConnectionState = AddressableAttribute(
            localAddress='plugConnectionState', parent=self, value=None, valueType=PlugStatus.PlugConnectionState)
        self.plugLockState = AddressableAttribute(
            localAddress='plugLockState', value=None, parent=self, valueType=PlugStatus.PlugLockState)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Plug status from dict')

        if 'plugConnectionState' in fromDict:
            try:
                self.plugConnectionState.setValueWithCarTime(
                    PlugStatus.PlugConnectionState(fromDict['plugConnectionState']), lastUpdateFromCar=None,
                    fromServer=True)
            except ValueError:
                self.plugConnectionState.setValueWithCarTime(PlugStatus.PlugConnectionState.UNKNOWN,
                                                             lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported plugConnectionState: %s was provided,'
                            ' please report this as a bug', fromDict['plugConnectionState'])
        else:
            self.plugConnectionState.enabled = False

        if 'plugLockState' in fromDict:
            try:
                self.plugLockState.setValueWithCarTime(PlugStatus.PlugLockState(fromDict['plugLockState']),
                                                       lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.plugLockState.setValueWithCarTime(PlugStatus.PlugLockState.UNKNOWN,
                                                       lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported plugLockState: %s was provided,'
                            ' please report this as a bug', fromDict['plugLockState'])
        else:
            self.plugLockState.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['plugConnectionState', 'plugLockState']))

    def __str__(self):
        string = super().__str__() + '\n'
        string += '\tPlug:'
        if self.plugConnectionState.enabled:
            string += f' {self.plugConnectionState.value.value}, '
        if self.plugLockState.enabled:
            string += f'{self.plugLockState.value.value}'
        string = '\n'
        return string

    class PlugConnectionState(Enum,):
        CONNECTED = 'connected'
        DISCONNECTED = 'disconnected'
        UNKNOWN = 'unknown unlock plug state'

    class PlugLockState(Enum,):
        LOCKED = 'locked'
        UNLOCKED = 'unlocked'
        UNKNOWN = 'unknown unlock plug state'


class ClimatizationStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.remainingClimatisationTime_min = AddressableAttribute(
            localAddress='remainingClimatisationTime_min', parent=self, value=None, valueType=int)
        self.climatisationState = AddressableAttribute(localAddress='climatisationState', value=None, parent=self,
                                                       valueType=ClimatizationStatus.ClimatizationState)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Climatization status from dict')

        if 'remainingClimatisationTime_min' in fromDict:
            self.remainingClimatisationTime_min.setValueWithCarTime(int(fromDict['remainingClimatisationTime_min']),
                                                                    lastUpdateFromCar=None, fromServer=True)
        else:
            self.remainingClimatisationTime_min.enabled = False

        if 'climatisationState' in fromDict:
            try:
                self.climatisationState.setValueWithCarTime(
                    ClimatizationStatus.ClimatizationState(fromDict['climatisationState']), lastUpdateFromCar=None,
                    fromServer=True)
            except ValueError:
                self.climatisationState.setValueWithCarTime(ClimatizationStatus.ClimatizationState.UNKNOWN,
                                                            lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported climatisationState: %s was provided,'
                            ' please report this as a bug', fromDict['climatisationState'])
        else:
            self.climatisationState.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['remainingClimatisationTime_min', 'climatisationState']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.climatisationState.enabled:
            string += f'\tState: {self.climatisationState.value.value}\n'
        if self.remainingClimatisationTime_min.enabled:
            string += f'\tRemaining Climatization Time: {self.remainingClimatisationTime_min.value} min\n'
        return string

    class ClimatizationState(Enum,):
        OFF = 'off'
        HEATING = 'heating'
        COOLING = 'cooling'
        VENTILATION = 'ventilation'
        UNKNOWN = 'unknown climatization state'


class ClimatizationSettings(GenericSettings):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.targetTemperature_K = ChangeableAttribute(
            localAddress='targetTemperature_K', parent=self, value=None, valueType=float)
        self.targetTemperature_C = ChangeableAttribute(
            localAddress='targetTemperature_C', parent=self, value=None, valueType=float)
        self.climatisationWithoutExternalPower = ChangeableAttribute(
            localAddress='climatisationWithoutExternalPower', parent=self, value=None, valueType=bool)
        self.climatizationAtUnlock = ChangeableAttribute(
            localAddress='climatizationAtUnlock', parent=self, value=None, valueType=bool)
        self.windowHeatingEnabled = ChangeableAttribute(
            localAddress='windowHeatingEnabled', parent=self, value=None, valueType=bool)
        self.zoneFrontLeftEnabled = ChangeableAttribute(
            localAddress='zoneFrontLeftEnabled', parent=self, value=None, valueType=bool)
        self.zoneFrontRightEnabled = ChangeableAttribute(
            localAddress='zoneFrontRightEnabled', parent=self, value=None, valueType=bool)
        self.zoneRearLeftEnabled = ChangeableAttribute(
            localAddress='zoneRearLeftEnabled', parent=self, value=None, valueType=bool)
        self.zoneRearRightEnabled = ChangeableAttribute(
            localAddress='zoneRearRightEnabled', parent=self, value=None, valueType=bool)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

        self.targetTemperature_C.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.targetTemperature_K.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.climatisationWithoutExternalPower.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.climatizationAtUnlock.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.windowHeatingEnabled.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.zoneFrontLeftEnabled.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.zoneFrontRightEnabled.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.zoneRearLeftEnabled.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.zoneRearRightEnabled.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Climatization settings from dict')

        if 'targetTemperature_K' in fromDict:
            self.targetTemperature_K.setValueWithCarTime(
                float(fromDict['targetTemperature_K']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.targetTemperature_K.enabled = False

        if 'targetTemperature_C' in fromDict:
            self.targetTemperature_C.setValueWithCarTime(
                float(fromDict['targetTemperature_C']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.targetTemperature_C.enabled = False

        if 'climatisationWithoutExternalPower' in fromDict:
            self.climatisationWithoutExternalPower.setValueWithCarTime(
                toBool(fromDict['climatisationWithoutExternalPower']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.climatisationWithoutExternalPower.enabled = False

        if 'climatizationAtUnlock' in fromDict:
            self.climatizationAtUnlock.setValueWithCarTime(
                toBool(fromDict['climatizationAtUnlock']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.climatizationAtUnlock.enabled = False

        if 'windowHeatingEnabled' in fromDict:
            self.windowHeatingEnabled.setValueWithCarTime(
                toBool(fromDict['windowHeatingEnabled']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.windowHeatingEnabled.enabled = False

        if 'zoneFrontLeftEnabled' in fromDict:
            self.zoneFrontLeftEnabled.setValueWithCarTime(
                toBool(fromDict['zoneFrontLeftEnabled']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.zoneFrontLeftEnabled.enabled = False

        if 'zoneFrontRightEnabled' in fromDict:
            self.zoneFrontRightEnabled.setValueWithCarTime(
                toBool(fromDict['zoneFrontRightEnabled']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.zoneFrontRightEnabled.enabled = False

        if 'zoneRearLeftEnabled' in fromDict:
            self.zoneRearLeftEnabled.setValueWithCarTime(
                toBool(fromDict['zoneRearLeftEnabled']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.zoneRearLeftEnabled.enabled = False

        if 'zoneRearRightEnabled' in fromDict:
            self.zoneRearRightEnabled.setValueWithCarTime(
                toBool(fromDict['zoneRearRightEnabled']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.zoneRearRightEnabled.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + [
            'targetTemperature_K',
            'targetTemperature_C',
            'climatisationWithoutExternalPower',
            'climatizationAtUnlock',
            'windowHeatingEnabled',
            'zoneFrontLeftEnabled',
            'zoneFrontRightEnabled',
            'zoneRearLeftEnabled',
            'zoneRearRightEnabled']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.targetTemperature_C.enabled:
            string += f'\tTarget Temperature: {self.targetTemperature_C.value} °C ' \
                f'({self.targetTemperature_K.value}°K) \n'
        if self.climatisationWithoutExternalPower.enabled:
            string += f'\tClimatization without external Power: {self.climatisationWithoutExternalPower.value}\n'
        if self.climatizationAtUnlock.enabled:
            string += f'\tStart climatization after unlock: {self.climatizationAtUnlock.value}\n'
        if self.windowHeatingEnabled.enabled:
            string += f'\tWindow heating: {self.windowHeatingEnabled.value}\n'
        if self.zoneFrontLeftEnabled.enabled:
            string += f'\tHeating Front Left Seat: {self.zoneFrontLeftEnabled.value}\n'
        if self.zoneFrontRightEnabled.enabled:
            string += f'\tHeating Front Right Seat: {self.zoneFrontRightEnabled.value}\n'
        if self.zoneRearLeftEnabled.enabled:
            string += f'\tHeating Rear Left Seat: {self.zoneRearLeftEnabled.value}\n'
        if self.zoneRearRightEnabled.enabled:
            string += f'\tHeating Rear Right Seat: {self.zoneRearRightEnabled.value}\n'
        return string


class WindowHeatingStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.windows = AddressableDict(localAddress='windows', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update window heating status from dict')

        if 'windowHeatingStatus' in fromDict:
            for windowDict in fromDict['windowHeatingStatus']:
                if 'windowLocation' in windowDict:
                    if windowDict['windowLocation'] in self.windows:
                        self.windows[windowDict['windowLocation']].update(fromDict=windowDict)
                    else:
                        self.windows[windowDict['windowLocation']] = WindowHeatingStatus.Window(
                            fromDict=windowDict, parent=self.windows)
            for windowName in [windowName for windowName in self.windows.keys()
                               if windowName not in [window['windowLocation']
                               for window in fromDict['windowHeatingStatus'] if 'windowLocation' in window]]:
                del self.windows[windowName]
        else:
            self.windows.clear()
            self.windows.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['windowHeatingStatus']))

    def __str__(self):
        string = super().__str__() + '\n'
        string += f'\tWindows: {len(self.windows)} items\n'
        for window in self.windows.values():
            string += f'\t\t{window}\n'
        return string

    class Window(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.windowHeatingState = AddressableAttribute(
                localAddress='windowHeatingState', parent=self, value=None,
                valueType=WindowHeatingStatus.Window.WindowHeatingState)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update window from dict')

            if 'windowLocation' in fromDict:
                self.id = fromDict['windowLocation']
                self.address = self.id
            else:
                LOG.error('Window is missing windowLocation attribute')

            if 'windowHeatingState' in fromDict:
                try:
                    self.windowHeatingState.setValueWithCarTime(WindowHeatingStatus.Window.WindowHeatingState(
                        fromDict['windowHeatingState']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.windowHeatingState.setValueWithCarTime(WindowHeatingStatus.Window.WindowHeatingState.UNKNOWN,
                                                                lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported windowHeatingState: %s was provided,'
                                ' please report this as a bug', fromDict['windowHeatingState'])
            else:
                self.windowHeatingState.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['windowLocation', 'windowHeatingState']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            return f'{self.id}: {self.windowHeatingState.value.value}'

        class WindowHeatingState(Enum,):
            ON = 'on'
            OFF = 'off'
            UNKNOWN = 'unknown open state'


class LightsStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.lights = AddressableDict(localAddress='lights', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update light status from dict')

        if 'lights' in fromDict:
            for lightDict in fromDict['lights']:
                if 'name' in lightDict:
                    if lightDict['name'] in self.lights:
                        self.lights[lightDict['name']].update(fromDict=lightDict)
                    else:
                        self.lights[lightDict['name']] = LightsStatus.Light(fromDict=lightDict, parent=self.lights)
            for lightName in [lightName for lightName in self.lights.keys()
                              if lightName not in [light['name'] for light in fromDict['lights'] if 'name' in light]]:
                del self.lights[lightName]
        else:
            self.lights.clear()
            self.lights.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['lights']))

    def __str__(self):
        string = super().__str__() + '\n'
        string += f'\tLights: {len(self.lights)} items\n'
        for light in self.lights.values():
            string += f'\t\t{light}\n'
        return string

    class Light(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.status = AddressableAttribute(localAddress='status', parent=self,
                                               value=None, valueType=LightsStatus.Light.LightState)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update light from dict')

            if 'name' in fromDict:
                self.id = fromDict['name']
                self.address = self.id
            else:
                LOG.error('Light is missing name attribute')

            if 'status' in fromDict:
                try:
                    self.status.setValueWithCarTime(LightsStatus.Light.LightState(fromDict['status']),
                                                    lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.status.setValueWithCarTime(LightsStatus.Light.LightState.UNKNOWN,
                                                    lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported status: %s was provided,'
                                ' please report this as a bug', fromDict['status'])
            else:
                self.status.enabled = False

            for key, value in {key: value for key, value in fromDict.items() if key not in ['name', 'status']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            return f'{self.id}: {self.status.value.value}'

        class LightState(Enum,):
            ON = 'on'
            OFF = 'off'
            UNKNOWN = 'unknown open state'


class RangeStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.carType = AddressableAttribute(localAddress='carType', parent=self,
                                            value=None, valueType=RangeStatus.CarType)
        self.primaryEngine = RangeStatus.Engine(localAddress='primaryEngine', parent=self)
        self.secondaryEngine = RangeStatus.Engine(localAddress='secondaryEngine', parent=self)
        self.totalRange_km = AddressableAttribute(localAddress='totalRange_km', parent=self, value=None, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Climatization settings from dict')

        if 'carType' in fromDict:
            try:
                self.carType.setValueWithCarTime(RangeStatus.CarType(
                    fromDict['carType']), lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.carType.setValueWithCarTime(RangeStatus.CarType.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported carType: %s was provided,'
                            ' please report this as a bug', fromDict['carType'])
        else:
            self.carType.enabled = False

        if 'primaryEngine' in fromDict:
            self.primaryEngine.update(fromDict['primaryEngine'])
        else:
            self.primaryEngine.enabled = False

        if 'secondaryEngine' in fromDict:
            self.secondaryEngine.update(fromDict['secondaryEngine'])
        else:
            self.secondaryEngine.enabled = False

        if 'totalRange_km' in fromDict:
            self.totalRange_km.setValueWithCarTime(
                int(fromDict['totalRange_km']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.totalRange_km.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + ['carType',
                                                               'primaryEngine',
                                                               'secondaryEngine',
                                                               'totalRange_km']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.carType.enabled:
            string += f'\tCar Type: {self.carType.value.value}\n'
        if self.totalRange_km.enabled:
            string += f'\tTotal Range: {self.totalRange_km.value} km\n'
        if self.primaryEngine.enabled:
            string += f'\tPrimary Engine: {self.primaryEngine}\n'
        if self.secondaryEngine.enabled:
            string += f'\tSecondary Engine: {self.secondaryEngine}\n'
        return string

    class Engine(AddressableObject):
        def __init__(
            self,
            localAddress,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=localAddress, parent=parent)
            self.type = AddressableAttribute(localAddress='type', parent=self, value=None,
                                             valueType=RangeStatus.Engine.EngineType)
            self.currentSOC_pct = AddressableAttribute(
                localAddress='currentSOC_pct', parent=self, value=None, valueType=int)
            self.remainingRange_km = AddressableAttribute(
                localAddress='remainingRange_km', parent=self, value=None, valueType=int)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update Engine from dict')

            if 'type' in fromDict:
                try:
                    self.type.setValueWithCarTime(RangeStatus.Engine.EngineType(fromDict['type']),
                                                  lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.type.setValueWithCarTime(RangeStatus.Engine.EngineType.UNKNOWN,
                                                  lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported type: %s was provided,'
                                ' please report this as a bug', fromDict['type'])
            else:
                self.type.enabled = False

            if 'currentSOC_pct' in fromDict:
                self.currentSOC_pct.setValueWithCarTime(
                    int(fromDict['currentSOC_pct']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.currentSOC_pct.enabled = False

            if 'remainingRange_km' in fromDict:
                self.remainingRange_km.setValueWithCarTime(
                    int(fromDict['remainingRange_km']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.remainingRange_km.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['type', 'currentSOC_pct', 'remainingRange_km']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            return f'{self.type.value.value} SoC: {self.currentSOC_pct.value} % ({self.remainingRange_km.value} km)'

        class EngineType(Enum,):
            GASOLINE = 'gasoline'
            ELECTRIC = 'electric'
            UNKNOWN = 'unknown open state'

    class CarType(Enum,):
        ELECTRIC = 'electric'
        HYBRID = 'hybrid'
        UNKNOWN = 'unknown open state'


class CapabilityStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.capabilities = AddressableDict(localAddress='capabilities', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update capability status from dict')

        if 'capabilities' in fromDict:
            for capDict in fromDict['capabilities']:
                if 'id' in capDict:
                    if capDict['id'] in self.capabilities:
                        self.capabilities[capDict['id']].update(fromDict=capDict)
                    else:
                        self.capabilities[capDict['id']] = GenericCapability(
                            capabilityId=capDict['id'], fromDict=capDict, parent=self.capabilities)
            for capabilityId in [capabilityId for capabilityId in self.capabilities.keys()
                                 if capabilityId not in [capability['id']
                                 for capability in fromDict['capabilities'] if 'id' in capability]]:
                del self.capabilities[capabilityId]
        else:
            self.capabilities.clear()
            self.capabilities.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['capabilities']))

    def __str__(self):
        string = super().__str__() + '\n'
        string += f'\tCapabilities: {len(self.capabilities)} items\n'
        for capability in self.capabilities.values():
            string += f'\t\t{capability}\n'
        return string


class ClimatizationTimer(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.timers = AddressableDict(localAddress='timers', parent=self)
        self.timeInCar = AddressableAttribute(localAddress='timeInCar', parent=self, value=None, valueType=datetime)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update climatization timer from dict')

        if 'timers' in fromDict:
            for climatizationTimerDict in fromDict['timers']:
                if 'id' in climatizationTimerDict:
                    if climatizationTimerDict['id'] in self.timers:
                        self.timers[climatizationTimerDict['id']].update(fromDict=climatizationTimerDict)
                    else:
                        self.timers[climatizationTimerDict['id']] = ClimatizationTimer.Timer(
                            fromDict=climatizationTimerDict, parent=self.timers)
            for timerId in [timerId for timerId in self.timers.keys()
                            if timerId not in [timer['id']
                            for timer in fromDict['timers'] if 'id' in timer]]:
                del self.timers[timerId]
        else:
            self.timers.clear()
            self.timers.enabled = False

        if 'timeInCar' in fromDict:
            self.timeInCar.setValueWithCarTime(robustTimeParse(
                fromDict['timeInCar']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.timeInCar.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['timers', 'timeInCar']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.timeInCar.enabled:
            string += f'\tTime in Car: {self.timeInCar.value.isoformat()}' \
                f' (captured at {self.carCapturedTimestamp.value.isoformat()})\n'
        string += f'\tTimers: {len(self.timers)} items\n'
        for timer in self.timers.values():
            string += f'\t\t{timer}\n'
        return string

    class Timer(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.timerEnabled = AddressableAttribute(localAddress='enabled', parent=self, value=None, valueType=bool)
            self.recurringTimer = None
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update timer from dict')

            if 'id' in fromDict:
                self.id = fromDict['id']
                self.address = self.id
            else:
                LOG.error('Timer is missing id attribute')

            if 'enabled' in fromDict:
                self.timerEnabled.setValueWithCarTime(
                    toBool(fromDict['enabled']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.timerEnabled.enabled = False

            if 'recurringTimer' in fromDict:
                if self.recurringTimer is None:
                    self.recurringTimer = ClimatizationTimer.Timer.RecurringTimer(
                        localAddress='recurringTimer', parent=self, fromDict=fromDict['recurringTimer'])
                else:
                    self.recurringTimer.update(fromDict=fromDict['recurringTimer'])
            elif self.recurringTimer is not None:
                self.recurringTimer.enabled = False
                self.recurringTimer = None

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['id', 'enabled', 'recurringTimer']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            string = f'{self.id}: Enabled: {self.timerEnabled.value}'
            if self.recurringTimer is not None and self.recurringTimer.enabled:
                string += f' at {self.recurringTimer} '
            return string

        class RecurringTimer(AddressableObject):
            def __init__(
                self,
                localAddress,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress=localAddress, parent=parent)
                self.startTime = AddressableAttribute(
                    localAddress='startTime', parent=self, value=None, valueType=datetime)
                self.recurringOn = AddressableDict(localAddress='recurringOn', parent=self)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Update recurring timer from dict')

                if 'startTime' in fromDict:
                    self.startTime.setValueWithCarTime(datetime.strptime(f'{fromDict["startTime"]}+00:00', '%H:%M%z'),
                                                       lastUpdateFromCar=None, fromServer=True)
                else:
                    self.startTime.enabled = False

                if 'recurringOn' in fromDict:
                    for day, state in fromDict['recurringOn'].items():
                        if day in self.recurringOn:
                            self.recurringOn[day].setValueWithCarTime(state, lastUpdateFromCar=None, fromServer=True)
                        else:
                            self.recurringOn[day] = AddressableAttribute(
                                localAddress=day, parent=self.recurringOn, value=state, valueType=bool)
                    for day in [day for day in self.recurringOn.keys() if day not in fromDict['recurringOn'].keys()]:
                        del self.recurringOn[day]
                else:
                    self.recurringOn.clear()
                    self.recurringOn.enabled = False

                for key, value in {key: value for key, value in fromDict.items()
                                   if key not in ['startTime', 'recurringOn']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                string = f'{self.startTime.value.strftime("%H:%M")} on '
                for day, value in self.recurringOn.items():
                    if value:
                        string += day + ' '
                return string


class ParkingPosition(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.latitude = AddressableAttribute(localAddress='latitude', parent=self, value=None, valueType=float)
        self.longitude = AddressableAttribute(localAddress='longitude', parent=self, value=None, valueType=float)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update ParkingPosition from dict')

        if 'latitude' in fromDict:
            self.latitude.setValueWithCarTime(float(fromDict['latitude']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.latitude.enabled = False

        if 'longitude' in fromDict:
            self.longitude.setValueWithCarTime(float(fromDict['longitude']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.longitude.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['latitude', 'longitude']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.latitude.enabled:
            string += f'\tLatitude: {self.latitude.value}\n'
        if self.longitude.enabled:
            string += f'\tLongitude: {self.longitude.value}\n'
        return string


class ClimatisationRequestStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.status = AddressableAttribute(localAddress='status', parent=self,
                                           value=None, valueType=ClimatisationRequestStatus.Status)
        self.group = AddressableAttribute(localAddress='group', parent=self, value=None, valueType=int)
        self.info = AddressableAttribute(localAddress='info', parent=self, value=None, valueType=str)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Climatization Request status from dict')

        if 'status' in fromDict:
            try:
                self.status.setValueWithCarTime(ClimatisationRequestStatus.Status(fromDict['status']),
                                                lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.status.setValueWithCarTime(ClimatisationRequestStatus.Status.UNKNOWN,
                                                lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported status: %s was provided,'
                            ' please report this as a bug', fromDict['status'])
        else:
            self.status.enabled = False

        if 'group' in fromDict:
            self.group.setValueWithCarTime(int(fromDict['group']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.group.enabled = False

        if 'info' in fromDict:
            self.info.setValueWithCarTime(fromDict['info'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.info.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['status', 'group', 'info']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.status.enabled:
            string += f'\tStatus: {self.status.value.value}\n'
        if self.group.enabled:
            string += f'\tGroup: {self.group.value}\n'
        if self.info.enabled:
            string += f'\tInfo: {self.info.value}\n'
        return string

    class Status(Enum,):
        SUCCESSFULL = 'successful'
        POLLING_TIMEOUT = 'polling_timeout'
        IN_PROGRESS = 'in_progress'
        QUEUED = 'queued'
        UNKNOWN = 'unknown status'


class ChargingSettingsRequestStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.status = AddressableAttribute(localAddress='status', parent=self,
                                           value=None, valueType=ChargingSettingsRequestStatus.Status)
        self.group = AddressableAttribute(localAddress='group', parent=self, value=None, valueType=int)
        self.info = AddressableAttribute(localAddress='info', parent=self, value=None, valueType=str)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging settings Request status from dict')

        if 'status' in fromDict:
            try:
                self.status.setValueWithCarTime(ChargingSettingsRequestStatus.Status(fromDict['status']),
                                                lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.status.setValueWithCarTime(ChargingSettingsRequestStatus.Status.UNKNOWN,
                                                lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported status: %s was provided,'
                            ' please report this as a bug', fromDict['status'])
        else:
            self.status.enabled = False

        if 'group' in fromDict:
            self.group.setValueWithCarTime(int(fromDict['group']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.group.enabled = False

        if 'info' in fromDict:
            self.info.setValueWithCarTime(fromDict['info'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.info.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['status', 'group', 'info']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.status.enabled:
            string += f'\tStatus: {self.status.value.value}\n'
        if self.group.enabled:
            string += f'\tGroup: {self.group.value}\n'
        if self.info.enabled:
            string += f'\tInfo: {self.info.value}\n'
        return string

    class Status(Enum,):
        SUCCESSFULL = 'successful'
        POLLING_TIMEOUT = 'polling_timeout'
        IN_PROGRESS = 'in_progress'
        QUEUED = 'queued'
        UNKNOWN = 'unknown status'


class Controls(AddressableObject):
    def __init__(
        self,
        localAddress,
        vehicle,
        parent,
    ):
        self.vehicle = vehicle
        super().__init__(localAddress=localAddress, parent=parent)
        self.update()
        self.climatizationControl = None
        self.chargingControl = None

    def update(self):
        for status in self.vehicle.statuses.values():
            if isinstance(status, ClimatizationSettings):
                if self.climatizationControl is None:
                    self.climatizationControl = ChangeableAttribute(
                        localAddress='climatization', parent=self, value=Controls.Operation.NONE, valueType=Controls.Operation)
                    self.climatizationControl.addObserver(
                        self.__onClimatizationControlChange, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                        priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
            elif isinstance(status, ChargingSettings):
                if self.climatizationControl is None:
                    self.chargingControl = ChangeableAttribute(
                        localAddress='charging', parent=self, value=Controls.Operation.NONE, valueType=Controls.Operation)
                    self.chargingControl.addObserver(
                        self.__onChargingControlChange, AddressableLeaf.ObserverEvent.VALUE_CHANGED, priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def __onClimatizationControlChange(self, element, flags):
        if flags & AddressableLeaf.ObserverEvent.VALUE_CHANGED:
            if element.value in [Controls.Operation.START, Controls.Operation.STOP]:
                url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/climatisation/{element.value.value}'

                settingsDict = dict()
                if element.value == Controls.Operation.START:
                    if 'climatisationSettings' not in self.vehicle.statuses:
                        raise ControlError(
                            'Could not control climatization, there are no climatisationSettings for the vehicle available.')
                    climatizationSettings = self.vehicle.statuses['climatisationSettings']
                    for child in climatizationSettings.getLeafChildren():
                        if isinstance(child, ChangeableAttribute):
                            settingsDict[child.getLocalAddress()] = child.value

                data = json.dumps(settingsDict)
                controlResponse = self.vehicle.weConnect.session.post(url, data=data, allow_redirects=True)
                if controlResponse.status_code != requests.codes['ok']:
                    raise SetterError(f'Could not set value ({controlResponse.status_code})')
                # Trigger one update for the vehicle status to show result
                self.vehicle.updateStatus(force=True)

    def __onChargingControlChange(self, element, flags):
        if flags & AddressableLeaf.ObserverEvent.VALUE_CHANGED:
            if element.value in [Controls.Operation.START, Controls.Operation.STOP]:
                url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/charging/{element.value.value}'

                controlResponse = self.vehicle.weConnect.session.post(url, data='{}', allow_redirects=True)
                if controlResponse.status_code != requests.codes['ok']:
                    raise SetterError(f'Could not set value ({controlResponse.status_code})')
                # Trigger one update for the vehicle status to show result
                self.vehicle.updateStatus(force=True)

    class Operation(ControlInputEnum):
        START = 'start'
        STOP = 'stop'
        NONE = 'none'
        SETTINGS = 'settings'
        UNKNOWN = 'unknown'

        @classmethod
        def allowedValues(cls):
            return [Controls.Operation.START, Controls.Operation.STOP]
