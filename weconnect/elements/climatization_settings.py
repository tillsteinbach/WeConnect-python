from enum import Enum
import logging

from weconnect.addressable import AddressableLeaf, ChangeableAttribute, AddressableAttribute, AliasChangeableAttribute
from weconnect.elements.generic_settings import GenericSettings
from weconnect.util import toBool

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
        def celsiusToKelvin(value):
            return value + 273.15

        def farenheitToKelvin(value):
            return 273.5 + ((value - 32.0) * (5.0 / 9.0))

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

        if 'targetTemperature_K' in fromDict and fromDict['targetTemperature_K'] is not None:
            self.targetTemperature_K.setValueWithCarTime(
                float(fromDict['targetTemperature_K']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.targetTemperature_K.enabled = False

        if 'targetTemperature_C' in fromDict and fromDict['targetTemperature_C'] is not None:
            self.targetTemperature_C.setValueWithCarTime(
                float(fromDict['targetTemperature_C']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.targetTemperature_C.enabled = False

        if 'targetTemperature_F' in fromDict and fromDict['targetTemperature_F'] is not None:
            self.targetTemperature_F.setValueWithCarTime(
                float(fromDict['targetTemperature_F']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.targetTemperature_F.enabled = False

        if 'unitInCar' in fromDict and fromDict['unitInCar']:
            try:
                self.unitInCar.setValueWithCarTime(
                    ClimatizationSettings.UnitInCar(fromDict['unitInCar']), lastUpdateFromCar=None,
                    fromServer=True)
            except ValueError:
                self.unitInCar.setValueWithCarTime(ClimatizationSettings.UnitInCar.UNKNOWN,
                                                   lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported unitInCar: %s was provided,'
                            ' please report this as a bug', fromDict['unitInCar'])
        else:
            self.unitInCar.enabled = False

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
