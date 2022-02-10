import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class MaintenanceStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.inspectionDue_days = AddressableAttribute(localAddress='inspectionDue_days', parent=self, value=None, valueType=int)
        self.inspectionDue_km = AddressableAttribute(localAddress='inspectionDue_km', value=None, parent=self, valueType=int)
        self.mileage_km = AddressableAttribute(localAddress='mileage_km', value=None, parent=self, valueType=int)
        self.oilServiceDue_days = AddressableAttribute(localAddress='oilServiceDue_days', value=None, parent=self, valueType=int)
        self.oilServiceDue_km = AddressableAttribute(localAddress='oilServiceDue_km', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update maintenance status from dict')

        if 'value' in fromDict:
            self.inspectionDue_days.fromDict(fromDict['value'], 'inspectionDue_days')
            self.inspectionDue_km.fromDict(fromDict['value'], 'inspectionDue_km')

            if 'mileage_km' in fromDict['value']:
                mileage_km = int(fromDict['value']['mileage_km'])
                if self.fixAPI and mileage_km == 0x7FFFFFFF:
                    mileage_km = None
                    LOG.info('%s: Attribute mileage_km was error value 0x7FFFFFFF. Setting error state instead'
                             ' of 2147483647 km.', self.getGlobalAddress())
                self.mileage_km.setValueWithCarTime(mileage_km, lastUpdateFromCar=None, fromServer=True)
            else:
                self.mileage_km.enabled = False
            self.oilServiceDue_days.fromDict(fromDict['value'], 'oilServiceDue_days')
            self.oilServiceDue_km.fromDict(fromDict['value'], 'oilServiceDue_km')
        else:
            self.inspectionDue_days.enabled = False
            self.inspectionDue_km.enabled = False
            self.mileage_km.enabled = False
            self.oilServiceDue_days.enabled = False
            self.oilServiceDue_km.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'inspectionDue_days',
                                                                'inspectionDue_km',
                                                                'mileage_km',
                                                                'oilServiceDue_days',
                                                                'oilServiceDue_km'
                                                            ]))

    def __str__(self):
        string = super().__str__()
        if self.mileage_km.enabled:
            string += f'\n\tCurrent milage: {self.mileage_km.value} km'
        if self.inspectionDue_days.enabled:
            string += f'\n\tInspection due in: {self.inspectionDue_days.value} days'
        if self.inspectionDue_km.enabled:
            string += f'\n\tInspection due in: {self.inspectionDue_km.value} km'
        if self.oilServiceDue_km.enabled:
            string += f'\n\tOil service in: {self.oilServiceDue_km.value} km'
        if self.oilServiceDue_days.enabled:
            string += f'\n\tOil service in: {self.oilServiceDue_days.value} days'
        return string
