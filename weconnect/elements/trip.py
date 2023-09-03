import logging
from enum import Enum

from datetime import datetime

from weconnect.addressable import AddressableObject, AddressableAttribute
from weconnect.elements.enums import CarType

LOG = logging.getLogger("weconnect")


class Trip(AddressableObject):  # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        vehicle,
        tripType,
        parent,
        fromDict,
        fixAPI=True,
    ):
        super().__init__(localAddress=tripType, parent=parent)
        self.vehicle = vehicle
        self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=int)
        self.tripEndTimestamp = AddressableAttribute(localAddress='tripEndTimestamp', parent=self, value=None, valueType=datetime)
        self.tripType = AddressableAttribute(localAddress='tripType', parent=self, value=None, valueType=Trip.TripType)
        self.vehicleType = AddressableAttribute(localAddress='vehicleType', parent=self, value=None, valueType=CarType)
        self.mileage_km = AddressableAttribute(localAddress='mileage_km', parent=self, value=None, valueType=int)
        self.startMileage_km = AddressableAttribute(localAddress='startMileage_km', parent=self, value=None, valueType=int)
        self.overallMileage_km = AddressableAttribute(localAddress='overallMileage_km', parent=self, value=None, valueType=int)
        self.travelTime = AddressableAttribute(localAddress='travelTime', parent=self, value=None, valueType=int)
        self.averageFuelConsumption = AddressableAttribute(localAddress='averageFuelConsumption', parent=self, value=None, valueType=float)
        self.averageElectricConsumption = AddressableAttribute(localAddress='averageElectricConsumption', parent=self, value=None, valueType=float)
        self.averageSpeed_kmph = AddressableAttribute(localAddress='averageSpeed_kmph', parent=self, value=None, valueType=int)
        self.averageAuxConsumption = AddressableAttribute(localAddress='averageAuxConsumption', parent=self, value=None, valueType=float)
        self.averageRecuperation = AddressableAttribute(localAddress='averageRecuperation', parent=self, value=None, valueType=float)

        self.fixAPI = fixAPI

        self.update(fromDict)

    def update(  # noqa: C901  # pylint: disable=too-many-branches
        self,
        fromDict=None,
    ):
        if fromDict is not None:
            LOG.debug('Create / update trip station')
            self.id.fromDict(fromDict, 'id')
            self.tripEndTimestamp.fromDict(fromDict, 'tripEndTimestamp')
            self.tripType.fromDict(fromDict, 'tripType')
            self.vehicleType.fromDict(fromDict, 'vehicleType')
            self.mileage_km.fromDict(fromDict, 'mileage_km')
            self.startMileage_km.fromDict(fromDict, 'startMileage_km')
            self.overallMileage_km.fromDict(fromDict, 'overallMileage_km')
            self.travelTime.fromDict(fromDict, 'travelTime')
            self.averageFuelConsumption.fromDict(fromDict, 'averageFuelConsumption')
            self.averageElectricConsumption.fromDict(fromDict, 'averageElectricConsumption')
            self.averageSpeed_kmph.fromDict(fromDict, 'averageSpeed_kmph')
            self.averageAuxConsumption.fromDict(fromDict, 'averageAuxConsumption')
            self.averageRecuperation.fromDict(fromDict, 'averageRecuperation')

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['id',
                                              'tripEndTimestamp',
                                              'tripType',
                                              'vehicleType',
                                              'mileage_km',
                                              'startMileage_km',
                                              'overallMileage_km',
                                              'travelTime',
                                              'averageFuelConsumption',
                                              'averageElectricConsumption',
                                              'averageSpeed_kmph',
                                              'averageAuxConsumption',
                                              'averageRecuperation']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    class TripType(Enum):
        SHORTTERM = 'shortTerm'
        LONGTERM = 'longTerm'
        CYCLIC = 'cyclic'
        UNKNOWN = 'unkown trip type'

    def __str__(self):  # noqa: C901
        returnString = ''
        if self.id.enabled:
            returnString += f'ID:                   {self.id.value}\n'
        if self.tripEndTimestamp.enabled:
            returnString += f'End:                  {self.tripEndTimestamp.value}\n'
        if self.tripType.enabled:
            returnString += f'Type:                 {self.tripType.value.value}\n'
        if self.vehicleType.enabled:
            returnString += f'Vehicle Type:         {self.vehicleType.value.value}\n'
        if self.mileage_km.enabled:
            returnString += f'Mileage:              {self.mileage_km.value}km\n'
        if self.startMileage_km.enabled:
            returnString += f'Start Mileage:        {self.startMileage_km.value}km\n'
        if self.overallMileage_km.enabled:
            returnString += f'Overall Mileage:      {self.overallMileage_km.value}km\n'
        if self.travelTime.enabled:
            returnString += f'Travel Time:          {self.travelTime.value}\n'
        if self.averageFuelConsumption.enabled:
            returnString += f'Fuel Consumption:     {self.averageFuelConsumption.value}l/100km\n'
        if self.averageElectricConsumption.enabled:
            returnString += f'Electric Consumption: {self.averageElectricConsumption.value}kWh/100km\n'
        if self.averageSpeed_kmph.enabled:
            returnString += f'Average Speed:        {self.averageSpeed_kmph.value}kmh\n'
        if self.averageAuxConsumption.enabled:
            returnString += f'Average Aux Consumption: {self.averageAuxConsumption.value}\n'
        if self.averageRecuperation.enabled:
            returnString += f'Average Recuperation: {self.averageRecuperation.value}\n'
        returnString += '\n'
        return returnString
