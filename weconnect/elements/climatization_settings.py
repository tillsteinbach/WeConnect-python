import logging

from weconnect.addressable import AddressableLeaf, ChangeableAttribute
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
        string = super().__str__()
        if self.targetTemperature_C.enabled:
            string += f'\n\tTarget Temperature: {self.targetTemperature_C.value} °C ' \
                f'({self.targetTemperature_K.value}°K)'
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
