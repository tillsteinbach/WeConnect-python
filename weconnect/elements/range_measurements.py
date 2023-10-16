import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class RangeMeasurements(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.totalRange_km = AddressableAttribute(
            localAddress='totalRange_km', value=None, parent=self, valueType=int)
        self.electricRange = AddressableAttribute(
            localAddress='electricRange', parent=self, value=None, valueType=int)
        self.gasolineRange = AddressableAttribute(
            localAddress='gasolineRange', value=None, parent=self, valueType=int)
        self.adBlueRange = AddressableAttribute(
            localAddress='adBlueRange', value=None, parent=self, valueType=int)
        self.dieselRange = AddressableAttribute(
            localAddress='dieselRange', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update battery status from dict')

        if 'value' in fromDict:
            self.totalRange_km.fromDict(fromDict['value'], 'totalRange_km')
            self.electricRange.fromDict(fromDict['value'], 'electricRange')
            self.gasolineRange.fromDict(fromDict['value'], 'gasolineRange')
            self.adBlueRange.fromDict(fromDict['value'], 'adBlueRange')
            self.dieselRange.fromDict(fromDict['value'], 'dieselRange')
        else:
            self.totalRange_km.enabled = False
            self.electricRange.enabled = False
            self.gasolineRange.enabled = False
            self.adBlueRange.enabled = False
            self.dieselRange.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['totalRange_km', 'electricRange', 'gasolineRange', 'adBlueRange', 'dieselRange']))

    def __str__(self):
        string = super().__str__()
        if self.totalRange_km.enabled:
            string += f'\n\tTotal Range: {self.totalRange_km.value}km'
        if self.electricRange.enabled:
            string += f'\n\tElectric Range: {self.electricRange.value}km'
        if self.gasolineRange.enabled:
            string += f'\n\tGasoline Range: {self.gasolineRange.value}km'
        if self.adBlueRange.enabled:
            string += f'\n\tAdBlue Range: {self.adBlueRange.value}km'
        if self.dieselRange.enabled:
            string += f'\n\tDiesel Range: {self.dieselRange.value}km'
        return string
