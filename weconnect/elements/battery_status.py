import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class BatteryStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.currentSOC_pct = AddressableAttribute(
            localAddress='currentSOC_pct', parent=self, value=None, valueType=int)
        self.navigationTargetSOC_pct = AddressableAttribute(
            localAddress='navigationTargetSOC_pct', parent=self, value=None, valueType=int)
        self.cruisingRangeElectric_km = AddressableAttribute(
            localAddress='cruisingRangeElectric_km', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update battery status from dict')

        if 'value' in fromDict:
            if 'cruisingRangeElectric_km' in fromDict['value']:
                cruisingRangeElectric_km = int(fromDict['value']['cruisingRangeElectric_km'])
                if self.fixAPI and cruisingRangeElectric_km == 0x3FFF:
                    cruisingRangeElectric_km = None
                    LOG.info('%s: Attribute cruisingRangeElectric_km was error value 0x3FFF. Setting error state instead'
                             ' of 16383 km.', self.getGlobalAddress())

                if (self.fixAPI
                    and round((self.cruisingRangeElectric_km.value or 0) * 0.621371) == cruisingRangeElectric_km and cruisingRangeElectric_km != 0
                        and self.currentSOC_pct.value == int(fromDict['value']['currentSOC_pct'])):
                    LOG.info('%s: Attribute cruisingRangeElectric_km was miscalculated (miles/km) this is a bug in the API and the new value will not be used',
                             self.getGlobalAddress())
                else:
                    self.cruisingRangeElectric_km.setValueWithCarTime(
                        cruisingRangeElectric_km, lastUpdateFromCar=None, fromServer=True)
            else:
                self.cruisingRangeElectric_km.enabled = False

            self.currentSOC_pct.fromDict(fromDict['value'], 'currentSOC_pct')
            self.navigationTargetSOC_pct.fromDict(fromDict['value'], 'navigationTargetSOC_pct')
        else:
            self.currentSOC_pct.enabled = False
            self.cruisingRangeElectric_km.enabled = False
            self.navigationTargetSOC_pct.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['currentSOC_pct', 'navigationTargetSOC_pct', 'cruisingRangeElectric_km']))

    def __str__(self):
        string = super().__str__()
        if self.currentSOC_pct.enabled:
            string += f'\n\tCurrent SoC: {self.currentSOC_pct.value}%'
        if self.navigationTargetSOC_pct.enabled:
            string += f'\n\tNavigation Target SoC: {self.navigationTargetSOC_pct.value}%'
        if self.cruisingRangeElectric_km.enabled:
            if self.cruisingRangeElectric_km.value is not None:
                string += f'\n\tRange: {self.cruisingRangeElectric_km.value}km'
            else:
                string += '\n\tRange: currently unknown'
        return string
