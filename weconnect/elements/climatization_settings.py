from enum import Enum
import logging

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
            'zoneRearRightEnabled']))

    def __str__(self):  # noqa: C901
        string = super().__str__()
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

    class UnitInCar(Enum,):
        CELSIUS = 'celsius'
        FARENHEIT = 'farenheit'
        UNKNOWN = 'unknown unit'
