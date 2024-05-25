import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus
from weconnect.util import kelvinToCelsius

LOG = logging.getLogger("weconnect")


class TemperatureBatteryStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.temperatureHvBatteryMin_K = AddressableAttribute(localAddress='temperatureHvBatteryMin_K', parent=self, value=None, valueType=float)
        self.temperatureHvBatteryMax_K = AddressableAttribute(localAddress='temperatureHvBatteryMax_K', parent=self, value=None, valueType=float)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update battery temperature status from dict')

        if 'value' in fromDict:
            self.temperatureHvBatteryMin_K.fromDict(fromDict['value'], 'temperatureHvBatteryMin_K')
            self.temperatureHvBatteryMax_K.fromDict(fromDict['value'], 'temperatureHvBatteryMax_K')

        else:
            self.temperatureHvBatteryMin_K.enabled = False
            self.temperatureHvBatteryMax_K.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + ['temperatureHvBatteryMin_K',
                                                               'temperatureHvBatteryMax_K']))

    def __str__(self):
        string = super().__str__()
        if self.temperatureHvBatteryMin_K.enabled and self.temperatureHvBatteryMax_K.enabled:
            string += f'\n\tBattery temperature between {kelvinToCelsius(self.temperatureHvBatteryMin_K.value)} and' \
                + f' {kelvinToCelsius(self.temperatureHvBatteryMax_K.value)}°C'
        return string
