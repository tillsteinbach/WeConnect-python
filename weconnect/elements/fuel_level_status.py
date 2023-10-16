import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus
from weconnect.elements.enums import EngineType, CarType

LOG = logging.getLogger("weconnect")


class FuelLevelStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.currentFuelLevel_pct = AddressableAttribute(localAddress='currentFuelLevel_pct', parent=self, value=None, valueType=int)
        self.currentSOC_pct = AddressableAttribute(localAddress='currentSOC_pct', parent=self, value=None, valueType=int)
        self.primaryEngineType = AddressableAttribute(localAddress='primaryEngineType', parent=self, value=None, valueType=EngineType)
        self.secondaryEngineType = AddressableAttribute(localAddress='secondaryEngineType', parent=self, value=None, valueType=EngineType)
        self.carType = AddressableAttribute(localAddress='carType', parent=self, value=None, valueType=CarType)

        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update fuel level status from dict')

        if 'value' in fromDict:
            self.currentFuelLevel_pct.fromDict(fromDict['value'], 'currentFuelLevel_pct')
            self.currentSOC_pct.fromDict(fromDict['value'], 'currentSOC_pct')
            self.primaryEngineType.fromDict(fromDict['value'], 'primaryEngineType')
            self.secondaryEngineType.fromDict(fromDict['value'], 'secondaryEngineType')
            self.carType.fromDict(fromDict['value'], 'carType')
        else:
            self.currentFuelLevel_pct.enabled = False
            self.currentSOC_pct.enabled = False
            self.primaryEngineType.enabled = False
            self.secondaryEngineType.enabled = False
            self.carType.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + ['currentFuelLevel_pct',
                                                               'currentSOC_pct',
                                                               'primaryEngineType',
                                                               'secondaryEngineType',
                                                               'carType']))

    def __str__(self):
        string = super().__str__()
        if self.carType.enabled:
            string += f'\n\tCar Type: {self.carType.value.value}'  # pylint: disable=no-member
        if self.primaryEngineType.enabled:
            string += f'\n\tPrimary Engine: {self.primaryEngineType.value.value}'
        if self.secondaryEngineType.enabled:
            string += f'\n\tSecondary Engine: {self.secondaryEngineType.value.value}'
        if self.currentFuelLevel_pct.enabled:
            string += f'\n\tCurrent Fuel Level: {self.currentFuelLevel_pct.value}%'
        if self.currentSOC_pct.enabled:
            string += f'\n\tCurrent Charge Level: {self.currentSOC_pct.value}%'
        return string
