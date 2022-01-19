import logging
from enum import Enum

from weconnect.addressable import AddressableObject, AddressableAttribute, AddressableList

LOG = logging.getLogger("weconnect")


class ChargingStation(AddressableObject):  # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        weConnect,
        stationId,
        parent,
        fromDict,
        fixAPI=True,
    ):
        self.weConnect = weConnect
        super().__init__(localAddress=stationId, parent=parent)
        self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=str)
        self.name = AddressableAttribute(localAddress='name', parent=self, value=None, valueType=str)
        self.latitude = AddressableAttribute(localAddress='latitude', parent=self, value=None, valueType=float)
        self.longitude = AddressableAttribute(localAddress='longitude', parent=self, value=None, valueType=float)
        self.distance = AddressableAttribute(localAddress='distance', parent=self, value=None, valueType=float)
        self.address = None
        self.chargingPower = AddressableAttribute(localAddress='chargingPower', parent=self, value=None, valueType=float)
        self.chargingSpots = AddressableList(localAddress='chargingSpots', parent=self)
        self.authTypes = AddressableList(localAddress='authTypes', parent=self)
        self.filteredOut = AddressableAttribute(localAddress='filteredOut', parent=self, value=None, valueType=bool)
        self.isFavorite = AddressableAttribute(localAddress='isFavorite', parent=self, value=None, valueType=bool)
        self.operator = None
        self.isWeChargePartner = AddressableAttribute(localAddress='isWeChargePartner', parent=self, value=None, valueType=bool)

        self.fixAPI = fixAPI

        self.update(fromDict)

    def update(  # noqa: C901  # pylint: disable=too-many-branches
        self,
        fromDict=None,
    ):
        if fromDict is not None:
            LOG.debug('Create / update charging station')
            self.id.fromDict(fromDict, 'id')
            self.name.fromDict(fromDict, 'name')
            self.latitude.fromDict(fromDict, 'latitude')
            self.longitude.fromDict(fromDict, 'longitude')
            self.distance.fromDict(fromDict, 'distance')

            if 'address' in fromDict:
                if self.address is None:
                    self.address = ChargingStation.Address(localAddress='address', parent=self, fromDict=fromDict['address'])
                else:
                    self.address.update(fromDict=fromDict['address'])
            elif self.address is not None:
                self.address.enabled = False
                self.address = None

            self.chargingPower.fromDict(fromDict, 'chargingPower')

            if 'chargingSpots' in fromDict and fromDict['chargingSpots'] is not None:
                if len(fromDict['chargingSpots']) == len(self.chargingSpots):
                    for i, spot in enumerate(fromDict['chargingSpots']):
                        self.chargingSpots[i].update(fromDict=spot)
                else:
                    self.chargingSpots.clear()
                    for spot in fromDict['chargingSpots']:
                        self.chargingSpots.append(ChargingStation.ChargingSpot(localAddress=str(
                            len(self.chargingSpots)), parent=self.chargingSpots, fromDict=spot))
            else:
                self.chargingSpots.enabled = False
                self.chargingSpots.clear()

            if 'authTypes' in fromDict and fromDict['authTypes'] is not None:
                if len(fromDict['authTypes']) == len(self.authTypes):
                    for i, authType in enumerate(fromDict['authTypes']):
                        try:
                            authTypeEnum = ChargingStation.AUTHTYPE(authType)
                        except ValueError:
                            authTypeEnum = ChargingStation.AUTHTYPE.UNKNOWN
                            LOG.warning('An unsupported type: %s was provided, please report this as a bug', authTypeEnum)
                        self.authTypes[i].setValueWithCarTime(authTypeEnum, lastUpdateFromCar=None, fromServer=True)
                else:
                    self.authTypes.clear()
                    for authType in fromDict['authTypes']:
                        try:
                            authTypeEnum = ChargingStation.AUTHTYPE(authType)
                        except ValueError:
                            authTypeEnum = ChargingStation.AUTHTYPE.UNKNOWN
                            LOG.warning('An unsupported type: %s was provided, please report this as a bug', authTypeEnum)
                        self.authTypes.append(AddressableAttribute(localAddress=len(self.authTypes),
                                              parent=self.authTypes, value=authTypeEnum, valueType=ChargingStation.AUTHTYPE))
            else:
                self.authTypes.enabled = False
                self.authTypes.clear()

            self.filteredOut.fromDict(fromDict, 'filteredOut')
            self.isFavorite.fromDict(fromDict, 'isFavorite')
            self.isWeChargePartner.fromDict(fromDict, 'isWeChargePartner')

            if 'cpoiOperatorInfo' in fromDict:
                if self.operator is None:
                    self.operator = ChargingStation.Operator(localAddress='operator', parent=self, fromDict=fromDict['cpoiOperatorInfo'])
                else:
                    self.operator.update(fromDict=fromDict['cpoiOperatorInfo'])
            elif self.operator is not None:
                self.operator.enabled = False
                self.operator = None

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['id',
                                              'name',
                                              'latitude',
                                              'longitude',
                                              'distance',
                                              'address',
                                              'chargingPower',
                                              'chargingSpots',
                                              'authTypes',
                                              'filteredOut',
                                              'isFavorite',
                                              'isWeChargePartner',
                                              'cpoiOperatorInfo']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    class AUTHTYPE(Enum):
        RFID = 'RFID'
        APP = 'APP'
        QR = 'QR'
        NO_AUTH = 'NO_AUTH'
        UNKNOWN = 'UNKNOWN'

    class Address(AddressableObject):
        def __init__(
            self,
            localAddress,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=localAddress, parent=parent)
            self.city = AddressableAttribute(localAddress='city', parent=self, value=None, valueType=str)
            self.country = AddressableAttribute(localAddress='country', parent=self, value=None, valueType=str)
            self.postcode = AddressableAttribute(localAddress='postcode', parent=self, value=None, valueType=str)
            self.street = AddressableAttribute(localAddress='street', parent=self, value=None, valueType=str)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update address from dict')

            if 'city' in fromDict:
                self.city.setValueWithCarTime(fromDict['city'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.city.enabled = False

            if 'country' in fromDict:
                self.country.setValueWithCarTime(fromDict['country'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.country.enabled = False

            if 'postcode' in fromDict:
                self.postcode.setValueWithCarTime(fromDict['postcode'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.postcode.enabled = False

            if 'street' in fromDict:
                self.street.setValueWithCarTime(fromDict['street'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.street.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['city', 'country', 'postcode', 'street']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnString = ''
            if self.street.enabled:
                returnString += f'{self.street.value}, '
            if self.postcode.enabled:
                returnString += f'{self.postcode.value} '
            if self.city.enabled:
                returnString += f'{self.city.value}, '
            if self.country.enabled:
                returnString += f'{self.country.value}'
            return returnString

    class ChargingSpot(AddressableObject):
        def __init__(
            self,
            localAddress,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=localAddress, parent=parent)
            self.connectors = AddressableList(localAddress='connectors', parent=self)
            self.available = AddressableAttribute(localAddress='available', parent=self, value=None, valueType=ChargingStation.ChargingSpot.AVAILABILITY)
            self.chargingPower = AddressableAttribute(localAddress='chargingPower', parent=self, value=None, valueType=float)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update charging spot from dict')

            if 'connectors' in fromDict and fromDict['connectors'] is not None:
                if len(fromDict['connectors']) == len(self.connectors):
                    for i, connector in enumerate(fromDict['connectors']):
                        self.connectors[i].update(fromDict=connector)
                else:
                    self.connectors.clear()
                    for connector in fromDict['connectors']:
                        self.connectors.append(ChargingStation.ChargingSpot.Connector(
                            localAddress=str(len(self.connectors)), parent=self.connectors, fromDict=connector))
            else:
                self.connectors.enabled = False
                self.connectors.clear()

            if 'chargingPower' in fromDict:
                self.chargingPower.setValueWithCarTime(float(fromDict['chargingPower']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.chargingPower.enabled = False

            if 'available' in fromDict:
                try:
                    self.available.setValueWithCarTime(ChargingStation.ChargingSpot.AVAILABILITY(fromDict['available']),
                                                       lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.available.setValueWithCarTime(ChargingStation.ChargingSpot.AVAILABILITY.UNKNOWN,
                                                       lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported type: %s was provided,'
                                ' please report this as a bug', fromDict['available'])
            else:
                self.available.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['connectors', 'chargingPower', 'available', 'plugTypes']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnString = ''
            if self.available.enabled:
                returnString += f'Availability: {self.available.value.value}\n'  # pylint: disable=no-member
            if self.chargingPower.enabled:
                returnString += f'Max. Charging Power: {self.chargingPower.value}kW\n'
            returnString += f'Connectors: {len(self.connectors)} items\n'
            for connector in self.connectors:
                returnString += ''.join(['\t' + line for line in str(connector).splitlines(True)]) + '\n'
            return returnString

        class PlugType(Enum):
            TYPE1 = 'Type1'
            TYPE2 = 'Type2'
            CHADEMO = 'CHAdeMO'
            CCS = 'CCS'
            SCHUKO = 'Schuko'
            CEE3 = 'CEE3'
            UNKNOWN = 'unknown'

        class AVAILABILITY(Enum):
            AVAILABLE = 'AVAILABLE'
            OCCUPIED = 'OCCUPIED'
            UNKNOWN = 'UNKNOWN'

        class Connector(AddressableObject):
            def __init__(
                self,
                localAddress,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress=localAddress, parent=parent)
                self.plugType = AddressableAttribute(localAddress='plugType', parent=self, value=None, valueType=ChargingStation.ChargingSpot.PlugType)
                self.chargingPower = AddressableAttribute(localAddress='chargingPower', parent=self, value=None, valueType=float)

                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Update connector from dict')

                if 'plugType' in fromDict:
                    try:
                        self.plugType.setValueWithCarTime(ChargingStation.ChargingSpot.PlugType(fromDict['plugType']),
                                                          lastUpdateFromCar=None, fromServer=True)
                    except ValueError:
                        self.plugType.setValueWithCarTime(ChargingStation.ChargingSpot.PlugType.UNKNOWN,
                                                          lastUpdateFromCar=None, fromServer=True)
                        LOG.warning('An unsupported type: %s was provided,'
                                    ' please report this as a bug', fromDict['plugType'])
                else:
                    self.plugType.enabled = False

                if 'chargingPower' in fromDict:
                    self.chargingPower.setValueWithCarTime(float(fromDict['chargingPower']), lastUpdateFromCar=None, fromServer=True)
                else:
                    self.chargingPower.enabled = False

                for key, value in {key: value for key, value in fromDict.items()
                                   if key not in ['plugType', 'chargingPower']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                returnString = ''
                if self.plugType.enabled:
                    returnString += f'Plug Type: {self.plugType.value.value}\n'  # pylint: disable=no-member
                if self.chargingPower.enabled:
                    returnString += f'Max. Charging Power: {self.chargingPower.value}kW'
                return returnString

    class Operator(AddressableObject):
        def __init__(
            self,
            localAddress,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=localAddress, parent=parent)
            self.name = AddressableAttribute(localAddress='name', parent=self, value=None, valueType=str)
            self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=str)
            self.phoneNumber = AddressableAttribute(localAddress='phoneNumber', parent=self, value=None, valueType=str)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update charging spot from dict')

            if 'name' in fromDict:
                self.name.setValueWithCarTime(fromDict['name'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.name.enabled = False

            if 'id' in fromDict:
                self.id.setValueWithCarTime(fromDict['id'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.id.enabled = False

            if 'phoneNumber' in fromDict:
                self.phoneNumber.setValueWithCarTime(fromDict['phoneNumber'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.phoneNumber.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['name', 'id', 'phoneNumber']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnString = ''
            if self.name.enabled:
                returnString += self.name.value
            if self.id.enabled:
                returnString += f' (Id: {self.id.value})'
            if self.phoneNumber.enabled and self.phoneNumber.value:
                returnString += f' Phone: {self.phoneNumber.value}'
            return returnString

    def __str__(self):  # noqa: C901
        returnString = ''
        if self.id.enabled:
            returnString += f'ID:                  {self.id.value}\n'
        if self.name.enabled:
            returnString += f'Name:                {self.name.value}\n'
        if self.operator is not None and self.operator.enabled:
            returnString += f'Operator:            {self.operator}\n'
        if self.latitude.enabled:
            returnString += f'Latitude:            {self.latitude.value}\n'
        if self.longitude.enabled:
            returnString += f'Longitude:           {self.longitude.value}\n'
        if self.distance.enabled:
            returnString += f'Distance:            {round(self.distance.value)}m\n'
        if self.address is not None and self.address.enabled:
            returnString += f'Address:             {self.address}\n'
        if self.chargingPower.enabled:
            returnString += f'Max. Charging Power: {self.chargingPower.value}kW\n'
        returnString += f'Charging Spots: {len(self.chargingSpots)} items\n'
        for spot in self.chargingSpots:
            returnString += ''.join(['\t' + line for line in str(spot).splitlines(True)]) + '\n'
        returnString += f'Authentification:    {", ".join([authtype.value.value for authtype in self.authTypes])}\n'
        returnString += 'Options:             '
        if self.filteredOut.enabled and self.filteredOut.value:
            returnString += 'filtered out; '
        if self.isFavorite.enabled and self.isFavorite.value:
            returnString += 'favourite; '
        if self.isWeChargePartner.enabled and self.isWeChargePartner.value:
            returnString += 'weCharge partner; '
        returnString += '\n'
        return returnString
