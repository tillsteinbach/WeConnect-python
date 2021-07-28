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

        if 'inspectionDue_days' in fromDict:
            self.inspectionDue_days.setValueWithCarTime(int(fromDict['inspectionDue_days']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.inspectionDue_days.enabled = False

        if 'inspectionDue_km' in fromDict:
            self.inspectionDue_km.setValueWithCarTime(int(fromDict['inspectionDue_km']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.inspectionDue_km.enabled = False

        if 'mileage_km' in fromDict:
            self.mileage_km.setValueWithCarTime(int(fromDict['mileage_km']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.mileage_km.enabled = False

        if 'oilServiceDue_days' in fromDict:
            self.oilServiceDue_days.setValueWithCarTime(int(fromDict['oilServiceDue_days']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.oilServiceDue_days.enabled = False

        if 'oilServiceDue_km' in fromDict:
            self.oilServiceDue_km.setValueWithCarTime(int(fromDict['oilServiceDue_km']), lastUpdateFromCar=None, fromServer=True)
        else:
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
