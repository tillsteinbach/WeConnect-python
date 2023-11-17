from enum import Enum
import logging

from weconnect.addressable import AddressableAttribute, AddressableObject
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class RangeStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.carType = AddressableAttribute(localAddress='carType', parent=self,
                                            value=None, valueType=RangeStatus.CarType)
        self.primaryEngine = RangeStatus.Engine(localAddress='primaryEngine', parent=self)
        self.secondaryEngine = RangeStatus.Engine(localAddress='secondaryEngine', parent=self)
        self.totalRange_km = AddressableAttribute(localAddress='totalRange_km', parent=self, value=None, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update range status from dict')

        if 'value' in fromDict:
            self.carType.fromDict(fromDict['value'], 'carType')

            if 'primaryEngine' in fromDict['value']:
                self.primaryEngine.update(fromDict['value']['primaryEngine'])
            else:
                self.primaryEngine.enabled = False

            if 'secondaryEngine' in fromDict['value']:
                self.secondaryEngine.update(fromDict['value']['secondaryEngine'])
            else:
                self.secondaryEngine.enabled = False

            if 'totalRange_km' in fromDict['value'] and self.fixAPI \
                    and round((self.totalRange_km.value or 0) * 0.621371) == int(fromDict['value']['totalRange_km']) and self.totalRange_km.value != 0:
                LOG.info('%s: Attribute totalRange_km was miscalculated (miles/km) this is a bug in the API and the new value will not be used',
                         self.getGlobalAddress())
            else:
                self.totalRange_km.fromDict(fromDict['value'], 'totalRange_km')

        else:
            self.carType.enabled = False
            self.primaryEngine.enabled = False
            self.secondaryEngine.enabled = False
            self.totalRange_km.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + ['carType',
                                                               'primaryEngine',
                                                               'secondaryEngine',
                                                               'totalRange_km']))

    def __str__(self):
        string = super().__str__()
        if self.carType.enabled:
            string += f'\n\tCar Type: {self.carType.value.value}'  # pylint: disable=no-member
        if self.totalRange_km.enabled:
            string += f'\n\tTotal Range: {self.totalRange_km.value} km'
        if self.primaryEngine.enabled:
            string += f'\n\tPrimary Engine: {self.primaryEngine}'
        if self.secondaryEngine.enabled:
            string += f'\n\tSecondary Engine: {self.secondaryEngine}'
        return string

    class Engine(AddressableObject):
        def __init__(
            self,
            localAddress,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=localAddress, parent=parent)
            self.type = AddressableAttribute(localAddress='type', parent=self, value=None,
                                             valueType=RangeStatus.Engine.EngineType)
            self.currentSOC_pct = AddressableAttribute(
                localAddress='currentSOC_pct', parent=self, value=None, valueType=int)
            self.currentFuelLevel_pct = AddressableAttribute(
                localAddress='currentFuelLevel_pct', parent=self, value=None, valueType=int)
            self.remainingRange_km = AddressableAttribute(
                localAddress='remainingRange_km', parent=self, value=None, valueType=int)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update Engine from dict')

            self.type.fromDict(fromDict, 'type')
            self.currentFuelLevel_pct.fromDict(fromDict, 'currentFuelLevel_pct')

            if ('remainingRange_km' in fromDict and self.parent.fixAPI
                and round((self.remainingRange_km.value or 0) * 0.621371) == int(fromDict['remainingRange_km']) and self.remainingRange_km.value != 0
                    and self.currentSOC_pct.value == int(fromDict['currentSOC_pct'])):
                LOG.info('%s: Attribute remainingRange_km was miscalculated (miles/km) this is a bug in the API and the new value will not be used',
                         self.getGlobalAddress())
            else:
                self.remainingRange_km.fromDict(fromDict, 'remainingRange_km')

            self.currentSOC_pct.fromDict(fromDict, 'currentSOC_pct')

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['type', 'currentSOC_pct', 'currentFuelLevel_pct', 'remainingRange_km']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            string = ""
            if self.type.enabled:
                string += f"{self.type.value.value} "
            if self.currentFuelLevel_pct.enabled:
                string += f" Fuel Level: {self.currentFuelLevel_pct.value}%"
            elif self.currentSOC_pct.enabled:
                string += f" SoC: {self.currentSOC_pct.value}%"
            if self.remainingRange_km.enabled:
                string += f" ({self.remainingRange_km.value} km)"
            return string

        class EngineType(Enum,):
            GASOLINE = 'gasoline'
            ELECTRIC = 'electric'
            PETROL = 'petrol'
            DIESEL = 'diesel'
            CNG = 'cng'
            LPG = 'lpg'
            INVALID = 'invalid'
            UNKNOWN = 'unknown engine type'

    class CarType(Enum,):
        ELECTRIC = 'electric'
        HYBRID = 'hybrid'
        GASOLINE = 'gasoline'
        PETROL = 'petrol'
        DIESEL = 'diesel'
        CNG = 'cng'
        LPG = 'lpg'
        INVALID = 'invalid'
        UNKNOWN = 'unknown car type'
