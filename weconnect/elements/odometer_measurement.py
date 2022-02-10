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

        if 'value' in fromDict:
            if 'odometer' in fromDict['value']:
                odometer = int(fromDict['value']['odometer'])
                if self.fixAPI and odometer == 0x7FFFFFFF:
                    odometer = None
                    LOG.info('%s: Attribute odometer was error value 0x7FFFFFFF. Setting error state instead'
                             ' of 2147483647 km.', self.getGlobalAddress())
                self.odometer.setValueWithCarTime(odometer, lastUpdateFromCar=None, fromServer=True)
            else:
                self.odometer.enabled = False
        else:
            self.odometer.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['odometer']))

    def __str__(self):
        string = super().__str__()
        if self.odometer.enabled:
            string += f'\n\tOdometer: {self.odometer.value}km'
        return string
