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
        LOG.debug('Update Climatization settings from dict')

        if 'carType' in fromDict and fromDict['carType']:
            try:
                self.carType.setValueWithCarTime(RangeStatus.CarType(
                    fromDict['carType']), lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.carType.setValueWithCarTime(RangeStatus.CarType.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported carType: %s was provided,'
                            ' please report this as a bug', fromDict['carType'])
        else:
            self.carType.enabled = False

        if 'primaryEngine' in fromDict:
            self.primaryEngine.update(fromDict['primaryEngine'])
        else:
            self.primaryEngine.enabled = False

        if 'secondaryEngine' in fromDict:
            self.secondaryEngine.update(fromDict['secondaryEngine'])
        else:
            self.secondaryEngine.enabled = False

        if 'totalRange_km' in fromDict:
            self.totalRange_km.setValueWithCarTime(
                int(fromDict['totalRange_km']), lastUpdateFromCar=None, fromServer=True)
        else:
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
            self.remainingRange_km = AddressableAttribute(
                localAddress='remainingRange_km', parent=self, value=None, valueType=int)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update Engine from dict')

            if 'type' in fromDict and fromDict['type']:
                try:
                    self.type.setValueWithCarTime(RangeStatus.Engine.EngineType(fromDict['type']),
                                                  lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.type.setValueWithCarTime(RangeStatus.Engine.EngineType.UNKNOWN,
                                                  lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported type: %s was provided,'
                                ' please report this as a bug', fromDict['type'])
            else:
                self.type.enabled = False

            if 'currentSOC_pct' in fromDict:
                self.currentSOC_pct.setValueWithCarTime(
                    int(fromDict['currentSOC_pct']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.currentSOC_pct.enabled = False

            if 'remainingRange_km' in fromDict:
                self.remainingRange_km.setValueWithCarTime(
                    int(fromDict['remainingRange_km']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.remainingRange_km.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['type', 'currentSOC_pct', 'remainingRange_km']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            string = ""
            if self.type.enabled:
                string += f"{self.type.value.value} "
            if self.currentSOC_pct.enabled:
                string += f" SoC: {self.currentSOC_pct.value}%"
            if self.remainingRange_km.enabled:
                string += f" ({self.remainingRange_km.value} km)"
            return string

        class EngineType(Enum,):
            GASOLINE = 'gasoline'
            ELECTRIC = 'electric'
            PETROL = 'petrol'
            CNG = 'cng'
            LPG = 'lpg'
            INVALID = 'invalid'
            UNKNOWN = 'unknown engine type'

    class CarType(Enum,):
        ELECTRIC = 'electric'
        HYBRID = 'hybrid'
        GASOLINE = 'gasoline'
        PETROL = 'petrol'
        CNG = 'cng'
        LPG = 'lpg'
        INVALID = 'invalid'
        UNKNOWN = 'unknown car type'
