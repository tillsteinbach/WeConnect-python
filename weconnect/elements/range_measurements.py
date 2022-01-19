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
        self.electricRange = AddressableAttribute(
            localAddress='electricRange', parent=self, value=None, valueType=int)
        self.gasolineRange = AddressableAttribute(
            localAddress='gasolineRange', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update battery status from dict')

        if 'value' in fromDict:
            self.electricRange.fromDict(fromDict['value'], 'electricRange')
            self.gasolineRange.fromDict(fromDict['value'], 'gasolineRange')
        else:
            self.electricRange.enabled = False
            self.gasolineRange.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['electricRange', 'gasolineRange']))

    def __str__(self):
        string = super().__str__()
        if self.electricRange.enabled:
            string += f'\n\tElectric Range: {self.electricRange.value}km'
        if self.gasolineRange.enabled:
            string += f'\n\tGasoline Range: {self.gasolineRange.value}km'
        return string
