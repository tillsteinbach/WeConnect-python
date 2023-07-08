from enum import Enum
import re
import logging

import json
import requests

from weconnect.elements.error import Error
from weconnect.errors import SetterError
from weconnect.domain import Domain

from weconnect.addressable import AddressableLeaf, ChangeableAttribute, AddressableAttribute, AliasChangeableAttribute
from weconnect.elements.generic_settings import GenericSettings
from weconnect.util import celsiusToKelvin, farenheitToKelvin

LOG = logging.getLogger("weconnect")


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
        self.targetTemperature_C = AliasChangeableAttribute(localAddress='targetTemperature_C', parent=self, value=None,
                                                            targetAttribute=self.targetTemperature_K, conversion=celsiusToKelvin, valueType=float)
        self.targetTemperature_F = AliasChangeableAttribute(localAddress='targetTemperature_F', parent=self, value=None,
                                                            targetAttribute=self.targetTemperature_K, conversion=farenheitToKelvin, valueType=float)
        self.unitInCar = AddressableAttribute(
            localAddress='unitInCar', parent=self, value=None, valueType=ClimatizationSettings.UnitInCar)
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
        self.heaterSource = ChangeableAttribute(
            localAddress='heaterSource', parent=self, value=None, valueType=ClimatizationSettings.HeaterSource)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

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
        self.heaterSource.addObserver(
            self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def update(self, fromDict, ignoreAttributes=None):  # noqa: C901
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Climatization settings from dict')

        if 'value' in fromDict:
            self.targetTemperature_K.fromDict(fromDict['value'], 'targetTemperature_K')
            self.targetTemperature_C.fromDict(fromDict['value'], 'targetTemperature_C')
            self.targetTemperature_F.fromDict(fromDict['value'], 'targetTemperature_F')
            self.unitInCar.fromDict(fromDict['value'], 'unitInCar')
            self.climatisationWithoutExternalPower.fromDict(fromDict['value'], 'climatisationWithoutExternalPower')
            self.climatizationAtUnlock.fromDict(fromDict['value'], 'climatizationAtUnlock')
            self.windowHeatingEnabled.fromDict(fromDict['value'], 'windowHeatingEnabled')
            self.zoneFrontLeftEnabled.fromDict(fromDict['value'], 'zoneFrontLeftEnabled')
            self.zoneFrontRightEnabled.fromDict(fromDict['value'], 'zoneFrontRightEnabled')
            self.zoneRearLeftEnabled.fromDict(fromDict['value'], 'zoneRearLeftEnabled')
            self.zoneRearRightEnabled.fromDict(fromDict['value'], 'zoneRearRightEnabled')
            self.heaterSource.fromDict(fromDict['value'], 'heaterSource')
        else:
            self.targetTemperature_K.enabled = False
            self.targetTemperature_C.enabled = False
            self.targetTemperature_F.enabled = False
            self.unitInCar.enabled = False
            self.climatisationWithoutExternalPower.enabled = False
            self.climatizationAtUnlock.enabled = False
            self.windowHeatingEnabled.enabled = False
            self.zoneFrontLeftEnabled.enabled = False
            self.zoneFrontRightEnabled.enabled = False
            self.zoneRearLeftEnabled.enabled = False
            self.zoneRearRightEnabled.enabled = False
            self.heaterSource.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + [
            'targetTemperature_K',
            'targetTemperature_C',
            'targetTemperature_F',
            'unitInCar',
            'climatisationWithoutExternalPower',
            'climatizationAtUnlock',
            'windowHeatingEnabled',
            'zoneFrontLeftEnabled',
            'zoneFrontRightEnabled',
            'zoneRearLeftEnabled',
            'zoneRearRightEnabled',
            'heaterSource']))

    def __str__(self):  # noqa: C901
        string = super().__str__()
        if self.heaterSource.enabled:
            string += f'\n\tHeating Source: {self.heaterSource.value.value}'
        if self.targetTemperature_C.enabled:
            string += f'\n\tTarget Temperature in °C: {self.targetTemperature_C.value} °C '
        if self.targetTemperature_F.enabled:
            string += f'\n\tTarget Temperature in °F: {self.targetTemperature_F.value} °F '
        if self.targetTemperature_K.enabled:
            string += f'\n\tTarget Temperature in °K: {self.targetTemperature_K.value} °K '
        if self.unitInCar.enabled:
            string += f'\n\tTemperature unit in car: {self.unitInCar.value.value}'
        if self.climatisationWithoutExternalPower.enabled:
            string += f'\n\tClimatization without external Power: {self.climatisationWithoutExternalPower.value}'
        if self.climatizationAtUnlock.enabled:
            string += f'\n\tStart climatization after unlock: {self.climatizationAtUnlock.value}'
        if self.windowHeatingEnabled.enabled:
            string += f'\n\tWindow heating: {self.windowHeatingEnabled.value}'
        if self.zoneFrontLeftEnabled.enabled:
            string += f'\n\tHeating Front Left Seat: {self.zoneFrontLeftEnabled.value}'
        if self.zoneFrontRightEnabled.enabled:
            string += f'\n\tHeating Front Right Seat: {self.zoneFrontRightEnabled.value}'
        if self.zoneRearLeftEnabled.enabled:
            string += f'\n\tHeating Rear Left Seat: {self.zoneRearLeftEnabled.value}'
        if self.zoneRearRightEnabled.enabled:
            string += f'\n\tHeating Rear Right Seat: {self.zoneRearRightEnabled.value}'
        return string

    def valueChanged(self, element, flags):  # noqa: C901
        if flags & AddressableLeaf.ObserverEvent.VALUE_CHANGED \
                and not flags & AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER:
            url = f'https://emea.bff.cariad.digital/vehicle/v1/vehicles/{self.vehicle.vin.value}/climatisation/settings'
            settingsDict = dict()
            regex = re.compile('zone(Front|Rear)(Right|Left)Enabled')
            if self.targetTemperature_C.enabled:
                settingsDict['targetTemperature'] = self.targetTemperature_C.value
                settingsDict['targetTemperatureUnit'] = ClimatizationSettings.UnitInCar.CELSIUS.value
            elif self.targetTemperature_F.enabled:
                settingsDict['targetTemperature'] = self.targetTemperature_F.value
                settingsDict['targetTemperatureUnit'] = ClimatizationSettings.UnitInCar.FARENHEIT.value
            else:
                settingsDict['targetTemperature'] = 20.0
                settingsDict['targetTemperatureUnit'] = ClimatizationSettings.UnitInCar.CELSIUS.value

            if self.climatisationWithoutExternalPower.enabled:
                settingsDict['climatisationWithoutExternalPower'] = self.climatisationWithoutExternalPower.value
            if self.climatizationAtUnlock.enabled:
                settingsDict['climatizationAtUnlock'] = self.climatizationAtUnlock.value
            if self.windowHeatingEnabled.enabled:
                settingsDict['windowHeatingEnabled'] = self.windowHeatingEnabled.value
            if self.heaterSource.enabled:
                settingsDict['heaterSource'] = self.heaterSource.value.value
            for child in self.getLeafChildren():
                if re.match(regex, child.getLocalAddress()):
                    settingsDict[child.getLocalAddress()] = child.value
            data = json.dumps(settingsDict)
            putResponse = self.vehicle.weConnect.session.put(url, data=data, allow_redirects=True)
            if putResponse.status_code != requests.codes['ok']:
                errorDict = putResponse.json()
                if errorDict is not None and 'error' in errorDict:
                    error = Error(localAddress='error', parent=self, fromDict=errorDict['error'])
                    if error is not None:
                        message = ''
                        if error.message.enabled and error.message.value is not None:
                            message += error.message.value
                        if error.info.enabled and error.info.value is not None:
                            message += ' - ' + error.info.value
                        if error.retry.enabled and error.retry.value is not None:
                            if error.retry.value:
                                message += ' - Please retry in a moment'
                            else:
                                message += ' - No retry possible'
                        raise SetterError(f'Could not set value ({message})')
                    else:
                        raise SetterError(f'Could not set value ({putResponse.status_code})')
                raise SetterError(f'Could not not set value ({putResponse.status_code})')
            responseDict = putResponse.json()
            if 'data' in responseDict and 'requestID' in responseDict['data']:
                if self.vehicle.requestTracker is not None:
                    self.vehicle.requestTracker.trackRequest(responseDict['data']['requestID'], Domain.ALL, 20, 120)

    class UnitInCar(Enum,):
        CELSIUS = 'celsius'
        FARENHEIT = 'farenheit'
        UNKNOWN = 'unknown unit'

    class HeaterSource(Enum,):
        ELECTRIC = 'electric'
        UNKNOWN = 'unknown heater source'
