import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus
from weconnect.util import kelvinToCelsius

LOG = logging.getLogger("weconnect")


class TemperatureOutsideStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.temperatureOutside_K = AddressableAttribute(localAddress='temperatureOutside_K', parent=self, value=None, valueType=float)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update outside temperature status from dict')

        if 'value' in fromDict:
            self.temperatureOutside_K.fromDict(fromDict['value'], 'temperatureOutside_K')

        else:
            self.temperatureOutside_K.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + ['temperatureOutside_K']))

    def __str__(self):
        string = super().__str__()
        if self.temperatureOutside_K.enabled:
            string += f'\n\tOutside temperature {kelvinToCelsius(self.temperatureOutside_K.value)}°C'
        return string
