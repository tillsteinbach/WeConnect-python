import logging

from weconnect.addressable import AddressableLeaf, ChangeableAttribute
from weconnect.elements.generic_settings import GenericSettings
from weconnect.elements.enums import BatteryCareMode

LOG = logging.getLogger("weconnect")


class ChargingCareSettings(GenericSettings):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.batteryCareMode = ChangeableAttribute(
            localAddress='batteryCareMode', parent=self, value=None, valueType=BatteryCareMode)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

        self.batteryCareMode.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                         priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging Care settings from dict')

        if 'value' in fromDict:
            self.batteryCareMode.fromDict(fromDict['value'], 'batteryCareMode')
        else:
            self.batteryCareMode.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'batteryCareMode',
                                                            ]))

    def __str__(self):
        string = super().__str__()
        if self.batteryCareMode.enabled:
            string += f'\n\tBattery Care Mode: {self.batteryCareMode.value.value}'  # pylint: disable=no-member # this is a fales positive
        return string
