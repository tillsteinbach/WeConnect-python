import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class WarningLightsStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.mileage_km = AddressableAttribute(localAddress='mileage_km', value=None, parent=self, valueType=int)
        self.warningLights = AddressableAttribute(localAddress='warningLights', value=None, parent=self, valueType=str)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update maintenance status from dict')

        if 'value' in fromDict:
            if 'mileage_km' in fromDict['value']:
                mileage_km = int(fromDict['value']['mileage_km'])
                if self.fixAPI and mileage_km == 0x7FFFFFFF:
                    mileage_km = None
                    LOG.info('%s: Attribute mileage_km was error value 0x7FFFFFFF. Setting error state instead'
                             ' of 2147483647 km.', self.getGlobalAddress())
                self.mileage_km.setValueWithCarTime(mileage_km, lastUpdateFromCar=None, fromServer=True)
            else:
                self.mileage_km.enabled = False

            self.warningLights.fromDict(fromDict['value'], 'warningLights')
        else:
            self.mileage_km.enabled = False
            self.warningLights.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'mileage_km',
                                                                'warningLights',
                                                            ]))

    def __str__(self):
        string = super().__str__()
        if self.mileage_km.enabled:
            string += f'\n\tCurrent milage: {self.mileage_km.value} km'
        if self.warningLights.enabled:
            string += f'\n\tWarning Lights: {self.warningLights.value}'
        return string
