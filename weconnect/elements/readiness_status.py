from enum import Enum
import logging

from weconnect.addressable import AddressableObject, AddressableAttribute
from weconnect.elements.generic_status import GenericStatus
from weconnect.util import toBool

LOG = logging.getLogger("weconnect")


class ReadinessStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.connectionState = None
        self.connectionWarning = None
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):  # noqa: C901
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update readiness status from dict')

        if 'connectionState' in fromDict:
            if self.connectionState is None:
                self.connectionState = ReadinessStatus.ConnectionState(parent=self, fromDict=fromDict['connectionState'])
            else:
                self.connectionState.update(fromDict=fromDict['connectionState'])
        elif self.connectionState is not None:
            self.connectionState.enabled = False
            self.connectionState = None

        if 'connectionWarning' in fromDict:
            if self.connectionWarning is None:
                self.connectionWarning = ReadinessStatus.ConnectionWarning(parent=self, fromDict=fromDict['connectionWarning'])
            else:
                self.connectionWarning.update(fromDict=fromDict['connectionWarning'])
        elif self.connectionWarning is not None:
            self.connectionWarning.enabled = False
            self.connectionWarning = None

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['connectionState', 'connectionWarning']))

    def __str__(self):
        string = super().__str__()
        if self.connectionState is not None and self.connectionState.enabled:
            string += f'\n\t{self.connectionState} '
        if self.connectionWarning is not None and self.connectionWarning.enabled:
            string += f'\n\t{self.connectionWarning} '
        return string

    class ConnectionState(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress='connectionState', parent=parent)
            self.isOnline = AddressableAttribute(localAddress='isOnline', parent=self, value=None, valueType=bool)
            self.isActive = AddressableAttribute(localAddress='isActive', parent=self, value=None, valueType=bool)
            self.batteryPowerLevel = AddressableAttribute(localAddress='batteryPowerLevel', parent=self, value=None,
                                                          valueType=ReadinessStatus.ConnectionState.BatteryPowerLevel)
            self.dailyPowerBudgetAvailable = AddressableAttribute(localAddress='dailyPowerBudgetAvailable', parent=self, value=None, valueType=bool)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update timer from dict')

            if 'isOnline' in fromDict:
                self.isOnline.setValueWithCarTime(toBool(fromDict['isOnline']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.isOnline.enabled = False

            if 'isActive' in fromDict:
                self.isActive.setValueWithCarTime(toBool(fromDict['isActive']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.isActive.enabled = False

            if 'batteryPowerLevel' in fromDict and fromDict['batteryPowerLevel']:
                try:
                    self.batteryPowerLevel.setValueWithCarTime(
                        ReadinessStatus.ConnectionState.BatteryPowerLevel(fromDict['batteryPowerLevel']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.batteryPowerLevel.setValueWithCarTime(ReadinessStatus.ConnectionState.BatteryPowerLevel.UNKNOWN, lastUpdateFromCar=None,
                                                               fromServer=True)
                    LOG.warning('An unsupported batteryPowerLevel: %s was provided, please report this as a bug', fromDict['batteryPowerLevel'])
            else:
                self.batteryPowerLevel.enabled = False

            if 'dailyPowerBudgetAvailable' in fromDict:
                self.dailyPowerBudgetAvailable.setValueWithCarTime(toBool(fromDict['dailyPowerBudgetAvailable']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.dailyPowerBudgetAvailable.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['isOnline', 'isActive', 'batteryPowerLevel', 'dailyPowerBudgetAvailable']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnString = 'Connection State: '
            if self.isOnline.enabled:
                returnString += f'\n\t\tIs online: {self.isOnline.value}'
            if self.isActive.enabled:
                returnString += f'\n\t\tIs active: {self.isActive.value}'
            if self.batteryPowerLevel.enabled:
                returnString += f'\n\t\tBattery power level: {self.batteryPowerLevel.value.value}'  # pylint: disable=no-member
            if self.dailyPowerBudgetAvailable.enabled:
                returnString += f'\n\t\tDaily Power Budget Available: {self.dailyPowerBudgetAvailable.value}'
            return returnString

        class BatteryPowerLevel(Enum):
            COMFORT = 'comfort'
            UNKNOWN = 'unknown battery power level'

    class ConnectionWarning(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress='connectionWarning', parent=parent)
            self.insufficientBatteryLevelWarning = AddressableAttribute(localAddress='insufficientBatteryLevelWarning', parent=self, value=None, valueType=bool)
            self.dailyPowerBudgetWarning = AddressableAttribute(localAddress='dailyPowerBudgetWarning', parent=self, value=None, valueType=bool)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update timer from dict')

            if 'insufficientBatteryLevelWarning' in fromDict:
                self.insufficientBatteryLevelWarning.setValueWithCarTime(toBool(fromDict['insufficientBatteryLevelWarning']), lastUpdateFromCar=None,
                                                                         fromServer=True)
            else:
                self.insufficientBatteryLevelWarning.enabled = False

            if 'dailyPowerBudgetWarning' in fromDict:
                self.dailyPowerBudgetWarning.setValueWithCarTime(toBool(fromDict['dailyPowerBudgetWarning']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.dailyPowerBudgetWarning.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['insufficientBatteryLevelWarning', 'dailyPowerBudgetWarning']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnString = 'Connection Warning: '
            if self.insufficientBatteryLevelWarning.enabled:
                returnString += f'\n\t\tInsufficient Battery Level Warning: {self.insufficientBatteryLevelWarning.value}'
            if self.dailyPowerBudgetWarning.enabled:
                returnString += f'\n\t\tDaily Power Budget Warning: {self.dailyPowerBudgetWarning.value}'
            return returnString
