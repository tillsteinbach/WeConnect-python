import logging
from datetime import datetime
from enum import Enum


from .util import robustTimeParse

from .addressable import AddressableObject, AddressableAttribute, AddressableDict

LOG = logging.getLogger("weconnect")


class Vehicle(AddressableObject):
    def __init__(
        self,
        vin,
        session,
        parent,
        fromDict,
        cache=None,
    ):
        self.__session = session
        self.__cache = cache
        super().__init__(localAddress=vin, parent=parent)
        self.vin = AddressableAttribute(localAddress='vin', parent=self, value=None)
        self.role = AddressableAttribute(localAddress='role', parent=self, value=None)
        self.enrollmentStatus = AddressableAttribute(localAddress='enrollmentStatus', parent=self, value=None)
        self.model = AddressableAttribute(localAddress='model', parent=self, value=None)
        self.nickname = AddressableAttribute(localAddress='nickname', parent=self, value=None)
        self.capabilities = AddressableDict(localAddress='capabilities', parent=self)
        self.statuses = AddressableDict(localAddress='status', parent=self)
        self.images = AddressableAttribute(localAddress='images', parent=self, value=None)

        self.update(fromDict)

    def update(  # noqa: C901
        self,
        fromDict=None
    ):
        if fromDict is not None:
            LOG.debug('Create vehicle from dict')
            if 'vin' in fromDict:
                self.vin.value = fromDict['vin']
            else:
                self.vin.enabled = False

            if 'role' in fromDict:
                self.role.value = fromDict['role']
            else:
                self.role.enabled = False

            if 'enrollmentStatus' in fromDict:
                self.enrollmentStatus.value = fromDict['enrollmentStatus']
            else:
                self.enrollmentStatus.enabled = False

            if 'model' in fromDict:
                self.model.value = fromDict['model']
            else:
                self.model.enabled = False

            if 'nickname' in fromDict:
                self.nickname.value = fromDict['nickname']
            else:
                self.nickname.enabled = False

            if 'capabilities' in fromDict:
                for capDict in fromDict['capabilities']:
                    if 'id' in capDict:
                        if capDict['id'] in self.capabilities:
                            self.capabilities[capDict['id']].update(fromDict=capDict)
                        else:
                            self.capabilities[capDict['id']] = GenericCapability(
                                capabilityId=capDict['id'], parent=self.capabilities, fromDict=capDict)
                for capabilityId in [capabilityId for capabilityId in self.capabilities.keys()
                                     if capabilityId not in [capability['id']
                                     for capability in fromDict['capabilities'] if 'id' in capability]]:
                    del self.capabilities[capabilityId]
            else:
                self.capabilities.clear()
                self.capabilities.enabled = False

            if 'images' in fromDict:
                self.images.value = fromDict['images']
            else:
                self.images.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['vin',
                                              'role',
                                              'enrollmentStatus',
                                              'model',
                                              'nickname',
                                              'capabilities',
                                              'images']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        self.__updateStatus()
        # self.test()

    def __updateStatus(self):  # noqa: C901
        url = 'https://mobileapi.apps.emea.vwapps.io/vehicles/' + self.vin.value + '/status'
        if url in self.__cache:
            data = self.__cache[url]
        else:
            statusResponse = self.__session.get(url, allow_redirects=False)
            data = statusResponse.json()
            self.__cache[url] = data
        if 'data' in data and data['data']:
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
                           }
            for key, className in keyClassMap.items():
                if key in data['data']:
                    if key in self.statuses:
                        self.statuses[key].update(fromDict=data['data'][key])
                    else:
                        self.statuses[key] = className(
                            parent=self.statuses, statusId=key, fromDict=data['data'][key])

            for key, value in {key: value for key, value in data['data'].items()
                               if key not in keyClassMap.keys()}.items():
                # TODO GenericStatus(parent=self.statuses, statusId=statusId, fromDict=statusDict)
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        data = None
        url = 'https://mobileapi.apps.emea.vwapps.io/vehicles/' + self.vin.value + '/parkingposition'
        if url in self.__cache:
            data = self.__cache[url]
        else:
            statusResponse = self.__session.get(url, allow_redirects=False)
            if statusResponse.status_code == 200:
                data = statusResponse.json()
                self.__cache[url] = data
        if data is not None:
            if 'data' in data:
                if 'parkingPosition' in self.statuses:
                    self.statuses['parkingPosition'].update(fromDict=data['data'])
                else:
                    self.statuses['parkingPosition'] = ParkingPosition(
                        parent=self.statuses, statusId='parkingPosition', fromDict=data['data'])
            return
        if 'parkingPosition' in self.statuses:
            del self.statuses['parkingPosition']

    def __str__(self):
        string = \
            f'VIN:               {self.vin.value}\n' \
            f'Model:             {self.model.value}\n' \
            f'Nickname:          {self.nickname.value}\n' \
            f'Role:              {self.role.value}\n' \
            f'Enrollment Status: {self.enrollmentStatus.value}\n' \
            f'Capabilities:\n'
        for capability in self.capabilities.values():
            string += ''.join(['\t' + line for line in str(capability).splitlines(True)]) + '\n'
        string += 'Statuses:\n'
        for status in self.statuses.values():
            string += ''.join(['\t' + line for line in str(status).splitlines(True)]) + '\n'
        return string


class GenericCapability(AddressableObject):
    def __init__(
        self,
        capabilityId,
        parent,
        fromDict=None
    ):
        super().__init__(localAddress=capabilityId, parent=parent)
        self.id = AddressableAttribute(localAddress='id', parent=self, value=None)
        self.status = AddressableAttribute(localAddress='status', parent=self, value=None)
        self.expirationDate = AddressableAttribute(localAddress='expirationDate', parent=self, value=None)
        self.userDisablingAllowed = AddressableAttribute(localAddress='userDisablingAllowed', parent=self, value=None)
        if fromDict is not None:
            self.update(fromDict=fromDict)

    def update(self, fromDict):
        LOG.debug('Update capability from dict')

        if 'id' in fromDict:
            self.id.value = fromDict['id']
        else:
            self.id.enabled = False

        if 'status' in fromDict:
            self.status.value = fromDict['status']
        else:
            self.status.enabled = False

        if 'expirationDate' in fromDict:
            self.expirationDate.value = robustTimeParse(fromDict['expirationDate'])
        else:
            self.expirationDate.enabled = False

        if 'userDisablingAllowed' in fromDict:
            self.userDisablingAllowed.value = fromDict['userDisablingAllowed']
        else:
            self.userDisablingAllowed.enabled = False

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in ['id', 'status', 'expirationDate', 'userDisablingAllowed']}.items():
            LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    def __str__(self):
        return f'[{self.id.value}] Status: {self.status.value} disabling: {self.userDisablingAllowed.value} ' \
            f'(expires {self.expirationDate.value})'


class GenericStatus(AddressableObject):
    def __init__(
        self,
        parent,
        statusId,
        fromDict=None
    ):
        super().__init__(localAddress=None, parent=parent)
        self.id = statusId
        self.address = self.id
        self.carCapturedTimestamp = AddressableAttribute(localAddress='carCapturedTimestamp', parent=self, value=None)
        if fromDict is not None:
            self.update(fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create status from dict')

        if 'carCapturedTimestamp' in fromDict:
            self.carCapturedTimestamp.value = robustTimeParse(fromDict['carCapturedTimestamp'])
        else:
            self.carCapturedTimestamp.enabled = False

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in (['carCapturedTimestamp'] + ignoreAttributes)   # pylint: disable=C0325
                           }.items():
            LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    def __str__(self):
        return f'[{self.id}] (last captured {self.carCapturedTimestamp.value})'


class AccessStatus(GenericStatus):
    def __init__(
        self,
        parent,
        statusId,
        fromDict=None
    ):
        self.overallStatus = AddressableAttribute(localAddress='overallStatus', parent=self, value=None)
        self.doors = AddressableDict(localAddress='doors', parent=self)
        self.windows = AddressableDict(localAddress='windows', parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):  # noqa: C901
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create access status from dict')

        if 'overallStatus' in fromDict:
            self.overallStatus.value = fromDict['overallStatus']
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
            self.openState = AddressableAttribute(localAddress='openState', parent=self, value=None)
            self.lockState = AddressableAttribute(localAddress='lockState', parent=self, value=None)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Create door from dict')

            if 'name' in fromDict:
                self.id = fromDict['name']
                self.address = self.id
            else:
                LOG.error('Door is missing name attribute')

            if 'status' in fromDict:
                if 'locked' in fromDict['status']:
                    self.lockState.value = AccessStatus.Door.LockState.LOCKED
                elif 'unlocked' in fromDict['status']:
                    self.lockState.value = AccessStatus.Door.LockState.UNLOCKED
                else:
                    self.lockState.value = AccessStatus.Door.LockState.UNKNOWN

                if 'open' in fromDict['status']:
                    self.openState.value = AccessStatus.Door.OpenState.OPEN
                elif 'closed' in fromDict['status']:
                    self.openState.value = AccessStatus.Door.OpenState.CLOSED
                else:
                    self.openState.value = AccessStatus.Door.OpenState.UNKNOWN
            else:
                self.lockState.enabled = False
                self.openState.enabled = False

            for key, value in {key: value for key, value in fromDict.items() if key not in ['name', 'status']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            return f'{self.id}: {self.openState.value.value}, {self.lockState.value.value}'

        class OpenState(Enum):
            OPEN = 'open'
            CLOSED = 'closed'
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
            self.openState = AddressableAttribute(localAddress='openState', parent=self, value=None)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Create window from dict')

            if 'name' in fromDict:
                self.id = fromDict['name']
                self.address = self.id
            else:
                LOG.error('Window is missing name attribute')

            if 'status' in fromDict:
                if 'open' in fromDict['status']:
                    self.openState.value = AccessStatus.Window.OpenState.OPEN
                elif 'closed' in fromDict['status']:
                    self.openState.value = AccessStatus.Window.OpenState.CLOSED
                elif 'unsupported' in fromDict['status']:
                    self.openState.value = AccessStatus.Window.OpenState.UNSUPPORTED
                else:
                    self.openState.value = AccessStatus.Window.OpenState.UNKNOWN
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
            UNKNOWN = 'unknown open state'


class BatteryStatus(GenericStatus):
    def __init__(
        self,
        parent,
        statusId,
        fromDict=None
    ):
        self.currentSOC_pct = AddressableAttribute(localAddress='currentSOC_pct', parent=self, value=None)
        self.cruisingRangeElectric_km = AddressableAttribute(
            localAddress='cruisingRangeElectric_km', value=None, parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create battery status from dict')

        if 'currentSOC_pct' in fromDict:
            self.currentSOC_pct.value = int(fromDict['currentSOC_pct'])
        else:
            self.currentSOC_pct.enabled = False

        if 'cruisingRangeElectric_km' in fromDict:
            self.cruisingRangeElectric_km.value = int(fromDict['cruisingRangeElectric_km'])
        else:
            self.cruisingRangeElectric_km.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['currentSOC_pct', 'cruisingRangeElectric_km']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.currentSOC_pct.enabled:
            string += f'\tCurrent SoC: {self.currentSOC_pct.value}%\n'
        if self.cruisingRangeElectric_km.enabled:
            string += f'\tRange: {self.cruisingRangeElectric_km.value}km\n'
        return string


class ChargingStatus(GenericStatus):
    def __init__(
        self,
        parent,
        statusId,
        fromDict=None
    ):
        self.remainingChargingTimeToComplete_min = AddressableAttribute(
            localAddress='remainingChargingTimeToComplete_min', parent=self, value=None)
        self.chargingState = AddressableAttribute(localAddress='chargingState', value=None, parent=self)
        self.chargePower_kW = AddressableAttribute(localAddress='chargePower_kW', value=None, parent=self)
        self.chargeRate_kmph = AddressableAttribute(localAddress='chargeRate_kmph', value=None, parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create Charging status from dict')

        if 'remainingChargingTimeToComplete_min' in fromDict:
            self.remainingChargingTimeToComplete_min.value = int(fromDict['remainingChargingTimeToComplete_min'])
        else:
            self.remainingChargingTimeToComplete_min.enabled = False

        if 'chargingState' in fromDict:
            try:
                self.chargingState.value = ChargingStatus.ChargingState(fromDict['chargingState'])
            except ValueError:
                self.chargingState.value = ChargingStatus.ChargingState.UNKNOWN
                LOG.warning('An unsupported chargingState: %s was provided,'
                            ' please report this as a bug', fromDict['chargingState'])
        else:
            self.chargingState.enabled = False

        if 'chargePower_kW' in fromDict:
            self.chargePower_kW.value = int(fromDict['chargePower_kW'])
        else:
            self.chargePower_kW.enabled = False

        if 'chargeRate_kmph' in fromDict:
            self.chargeRate_kmph.value = int(fromDict['chargeRate_kmph'])
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


class ChargingSettings(GenericStatus):
    def __init__(
        self,
        parent,
        statusId,
        fromDict=None
    ):
        self.maxChargeCurrentAC = AddressableAttribute(localAddress='maxChargeCurrentAC', parent=self, value=None)
        self.autoUnlockPlugWhenCharged = AddressableAttribute(
            localAddress='autoUnlockPlugWhenCharged', value=None, parent=self)
        self.targetSOC_pct = AddressableAttribute(localAddress='targetSOC_pct', value=None, parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create Charging settings from dict')

        if 'maxChargeCurrentAC' in fromDict:
            self.maxChargeCurrentAC.value = fromDict['maxChargeCurrentAC']
        else:
            self.maxChargeCurrentAC.enabled = False

        if 'autoUnlockPlugWhenCharged' in fromDict:
            try:
                self.autoUnlockPlugWhenCharged.value = ChargingSettings.UnlockPlugState(
                    fromDict['autoUnlockPlugWhenCharged'])
            except ValueError:
                self.autoUnlockPlugWhenCharged.value = ChargingSettings.UnlockPlugState.UNKNOWN
                LOG.warning('An unsupported autoUnlockPlugWhenCharged: %s was provided,'
                            ' please report this as a bug', fromDict['autoUnlockPlugWhenCharged'])
        else:
            self.autoUnlockPlugWhenCharged.enabled = False

        if 'targetSOC_pct' in fromDict:
            self.targetSOC_pct.value = int(fromDict['targetSOC_pct'])
        else:
            self.targetSOC_pct.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'maxChargeCurrentAC',
                                                                'autoUnlockPlugWhenCharged',
                                                                'targetSOC_pct'
                                                            ]))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.maxChargeCurrentAC.enabled:
            string += f'\tMaximum Charge Current AC: {self.maxChargeCurrentAC.value}\n'
        if self.autoUnlockPlugWhenCharged.enabled:
            string += f'\tAuto Unlock When Charged: {self.autoUnlockPlugWhenCharged.value.value}\n'
        if self.targetSOC_pct.enabled:
            string += f'\tTarget SoC: {self.targetSOC_pct.value} %\n'
        return string

    class UnlockPlugState(Enum,):
        OFF = 'off'
        ON = 'on'
        UNKNOWN = 'unknown unlock plug state'


class PlugStatus(GenericStatus):
    def __init__(
        self,
        parent,
        statusId,
        fromDict=None
    ):
        self.plugConnectionState = AddressableAttribute(localAddress='plugConnectionState', parent=self, value=None)
        self.plugLockState = AddressableAttribute(localAddress='plugLockState', value=None, parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create Plug status from dict')

        if 'plugConnectionState' in fromDict:
            try:
                self.plugConnectionState.value = PlugStatus.PlugConnectionState(fromDict['plugConnectionState'])
            except ValueError:
                self.plugConnectionState.value = PlugStatus.PlugConnectionState.UNKNOWN
                LOG.warning('An unsupported plugConnectionState: %s was provided,'
                            ' please report this as a bug', fromDict['plugConnectionState'])
        else:
            self.plugConnectionState.enabled = False

        if 'plugLockState' in fromDict:
            try:
                self.plugLockState.value = PlugStatus.PlugLockState(fromDict['plugLockState'])
            except ValueError:
                self.plugLockState.value = PlugStatus.PlugLockState.UNKNOWN
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
        parent,
        statusId,
        fromDict=None
    ):
        self.remainingClimatisationTime_min = AddressableAttribute(
            localAddress='remainingClimatisationTime_min', parent=self, value=None)
        self.climatisationState = AddressableAttribute(localAddress='climatisationState', value=None, parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create Climatization status from dict')

        if 'remainingClimatisationTime_min' in fromDict:
            self.remainingClimatisationTime_min.value = int(fromDict['remainingClimatisationTime_min'])
        else:
            self.remainingClimatisationTime_min.enabled = False

        if 'climatisationState' in fromDict:
            try:
                self.climatisationState.value = ClimatizationStatus.ClimatizationState(fromDict['climatisationState'])
            except ValueError:
                self.climatisationState.value = ClimatizationStatus.ClimatizationState.UNKNOWN
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


class ClimatizationSettings(GenericStatus):
    def __init__(
        self,
        parent,
        statusId,
        fromDict=None
    ):
        self.targetTemperature_K = AddressableAttribute(localAddress='targetTemperature_K', parent=self, value=None)
        self.targetTemperature_C = AddressableAttribute(localAddress='targetTemperature_C', parent=self, value=None)
        self.climatisationWithoutExternalPower = AddressableAttribute(
            localAddress='climatisationWithoutExternalPower', parent=self, value=None)
        self.climatizationAtUnlock = AddressableAttribute(localAddress='climatizationAtUnlock', parent=self, value=None)
        self.windowHeatingEnabled = AddressableAttribute(localAddress='windowHeatingEnabled', parent=self, value=None)
        self.zoneFrontLeftEnabled = AddressableAttribute(localAddress='zoneFrontLeftEnabled', parent=self, value=None)
        self.zoneFrontRightEnabled = AddressableAttribute(localAddress='zoneFrontRightEnabled', parent=self, value=None)
        self.zoneRearLeftEnabled = AddressableAttribute(localAddress='zoneRearLeftEnabled', parent=self, value=None)
        self.zoneRearRightEnabled = AddressableAttribute(localAddress='zoneRearRightEnabled', parent=self, value=None)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create Climatization settings from dict')

        if 'targetTemperature_K' in fromDict:
            self.targetTemperature_K.value = float(fromDict['targetTemperature_K'])
        else:
            self.targetTemperature_K.enabled = False

        if 'targetTemperature_C' in fromDict:
            self.targetTemperature_C.value = float(fromDict['targetTemperature_C'])
        else:
            self.targetTemperature_C.enabled = False

        if 'climatisationWithoutExternalPower' in fromDict:
            self.climatisationWithoutExternalPower.value = fromDict['climatisationWithoutExternalPower']
        else:
            self.climatisationWithoutExternalPower.enabled = False

        if 'climatizationAtUnlock' in fromDict:
            self.climatizationAtUnlock.value = fromDict['climatizationAtUnlock']
        else:
            self.climatizationAtUnlock.enabled = False

        if 'windowHeatingEnabled' in fromDict:
            self.windowHeatingEnabled.value = fromDict['windowHeatingEnabled']
        else:
            self.windowHeatingEnabled.enabled = False

        if 'zoneFrontLeftEnabled' in fromDict:
            self.zoneFrontLeftEnabled.value = fromDict['zoneFrontLeftEnabled']
        else:
            self.zoneFrontLeftEnabled.enabled = False

        if 'zoneFrontRightEnabled' in fromDict:
            self.zoneFrontRightEnabled.value = fromDict['zoneFrontRightEnabled']
        else:
            self.zoneFrontRightEnabled.enabled = False

        if 'zoneRearLeftEnabled' in fromDict:
            self.zoneRearLeftEnabled.value = fromDict['zoneRearLeftEnabled']
        else:
            self.zoneRearLeftEnabled.enabled = False

        if 'zoneRearRightEnabled' in fromDict:
            self.zoneRearRightEnabled.value = fromDict['zoneRearRightEnabled']
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
        parent,
        statusId,
        fromDict=None
    ):
        self.windows = AddressableDict(localAddress='windows', parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create window heating status from dict')

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
            self.windowHeatingState = AddressableAttribute(localAddress='windowHeatingState', parent=self, value=None)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Create window from dict')

            if 'windowLocation' in fromDict:
                self.id = fromDict['windowLocation']
                self.address = self.id
            else:
                LOG.error('Window is missing windowLocation attribute')

            if 'windowHeatingState' in fromDict:
                try:
                    self.windowHeatingState.value = WindowHeatingStatus.Window.WindowHeatingState(
                        fromDict['windowHeatingState'])
                except ValueError:
                    self.windowHeatingState.value = WindowHeatingStatus.Window.WindowHeatingState.UNKNOWN
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
        parent,
        statusId,
        fromDict=None
    ):
        self.lights = AddressableDict(localAddress='lights', parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create light status from dict')

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
            self.status = AddressableAttribute(localAddress='status', parent=self, value=None)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Create light from dict')

            if 'name' in fromDict:
                self.id = fromDict['name']
                self.address = self.id
            else:
                LOG.error('Light is missing name attribute')

            if 'status' in fromDict:
                try:
                    self.status.value = LightsStatus.Light.LightState(fromDict['status'])
                except ValueError:
                    self.status.value = LightsStatus.Light.LightState.UNKNOWN
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
        parent,
        statusId,
        fromDict=None
    ):
        self.carType = AddressableAttribute(localAddress='carType', parent=self, value=None)
        self.primaryEngine = RangeStatus.Engine(localAddress='primaryEngine', parent=self)
        self.secondaryEngine = RangeStatus.Engine(localAddress='secondaryEngine', parent=self)
        self.totalRange_km = AddressableAttribute(localAddress='totalRange_km', parent=self, value=None)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create Climatization settings from dict')

        if 'carType' in fromDict:
            try:
                self.carType.value = RangeStatus.CarType(fromDict['carType'])
            except ValueError:
                self.carType.value = RangeStatus.CarType.UNKNOWN
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
            self.totalRange_km.value = int(fromDict['totalRange_km'])
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
            self.type = AddressableAttribute(localAddress='type', parent=self, value=None)
            self.currentSOC_pct = AddressableAttribute(localAddress='currentSOC_pct', parent=self, value=None)
            self.remainingRange_km = AddressableAttribute(localAddress='remainingRange_km', parent=self, value=None)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Create Engine from dict')

            if 'type' in fromDict:
                try:
                    self.type.value = RangeStatus.Engine.EngineType(fromDict['type'])
                except ValueError:
                    self.type.value = RangeStatus.Engine.EngineType.UNKNOWN
                    LOG.warning('An unsupported type: %s was provided,'
                                ' please report this as a bug', fromDict['type'])
            else:
                self.type.enabled = False

            if 'currentSOC_pct' in fromDict:
                self.currentSOC_pct.value = int(fromDict['currentSOC_pct'])
            else:
                self.currentSOC_pct.enabled = False

            if 'remainingRange_km' in fromDict:
                self.remainingRange_km.value = int(fromDict['remainingRange_km'])
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
        parent,
        statusId,
        fromDict=None
    ):
        self.capabilities = AddressableDict(localAddress='capabilities', parent=self)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create light status from dict')

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
        parent,
        statusId,
        fromDict=None
    ):
        self.timers = AddressableDict(localAddress='timers', parent=self)
        self.timeInCar = AddressableAttribute(localAddress='timeInCar', parent=self, value=None)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create climatization timer from dict')

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
            self.timeInCar.value = robustTimeParse(fromDict['timeInCar'])
        else:
            self.timeInCar.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['timers', 'timeInCar']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.timeInCar.enabled:
            string += f'\tTime in Car: {self.timeInCar.value} (captured at {self.carCapturedTimestamp.value})\n'
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
            self.timerEnabled = AddressableAttribute(localAddress='enabled', parent=self, value=None)
            self.recurringTimer = None
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Create timer from dict')

            if 'id' in fromDict:
                self.id = fromDict['id']
                self.address = self.id
            else:
                LOG.error('Timer is missing id attribute')

            if 'enabled' in fromDict:
                self.timerEnabled.value = bool(fromDict['enabled'])
            else:
                self.timerEnabled.enabled = False

            if 'recurringTimer' in fromDict:
                if self.recurringTimer is None:
                    self.recurringTimer = ClimatizationTimer.Timer.RecurringTimer(
                        localAddress='recurringTimer', parent=self, fromDict=fromDict['recurringTimer'])
                else:
                    self.recurringTimer.update(fromDict=fromDict['recurringTimer'])
            else:
                self.recurringTimer.enabled = False
                self.recurringTimer = None

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['id', 'enabled', 'recurringTimer']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            string = f'{self.id}: Enabled: {self.timerEnabled.value}'
            if self.recurringTimer.enabled:
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
                self.startTime = AddressableAttribute(localAddress='startTime', parent=self, value=None)
                self.recurringOn = AddressableDict(localAddress='recurringOn', parent=self)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Create recurring timer from dict')

                if 'startTime' in fromDict:
                    self.startTime.value = datetime.strptime(f'{fromDict["startTime"]}+00:00', '%H:%M%z')
                else:
                    self.startTime.enabled = False

                if 'recurringOn' in fromDict:
                    for day, state in fromDict['recurringOn'].items():
                        if day in self.recurringOn:
                            self.recurringOn[day].value = state
                        else:
                            self.recurringOn[day] = AddressableAttribute(
                                localAddress=day, parent=self.recurringOn, value=state)
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
        parent,
        statusId,
        fromDict=None
    ):
        self.latitude = AddressableAttribute(localAddress='latitude', parent=self, value=None)
        self.longitude = AddressableAttribute(localAddress='longitude', parent=self, value=None)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create Climatization status from dict')

        if 'latitude' in fromDict:
            self.latitude.value = float(fromDict['latitude'])
        else:
            self.latitude.enabled = False

        if 'longitude' in fromDict:
            self.longitude.value = float(fromDict['longitude'])
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
        parent,
        statusId,
        fromDict=None
    ):
        self.status = AddressableAttribute(localAddress='status', parent=self, value=None)
        self.group = AddressableAttribute(localAddress='group', parent=self, value=None)
        self.info = AddressableAttribute(localAddress='info', parent=self, value=None)
        super().__init__(parent, statusId, fromDict=fromDict)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Create Climatization Request status from dict')

        if 'status' in fromDict:
            try:
                self.status.value = RangeStatus.Engine.EngineType(fromDict['status'])
            except ValueError:
                self.status.value = RangeStatus.Engine.EngineType.UNKNOWN
                LOG.warning('An unsupported status: %s was provided,'
                            ' please report this as a bug', fromDict['status'])
        else:
            self.status.enabled = False

        if 'group' in fromDict:
            self.group.value = int(fromDict['group'])
        else:
            self.group.enabled = False

        if 'info' in fromDict:
            self.info.value = int(fromDict['info'])
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
        POLLING_TIMEOUT = 'polling_timeout'
        UNKNOWN = 'unknown open state'
