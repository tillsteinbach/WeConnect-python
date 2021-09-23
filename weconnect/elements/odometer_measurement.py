import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class OdometerMeasurement(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.odometer = AddressableAttribute(
            localAddress='odometer', parent=self, value=None, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Odometer measurement from dict')

        if 'odometer' in fromDict:
            self.odometer.setValueWithCarTime(int(fromDict['odometer']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.odometer.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['odometer']))

    def __str__(self):
        string = super().__str__()
        if self.odometer.enabled:
            string += f'\n\tOdometer: {self.odometer.value}km'
        return string
