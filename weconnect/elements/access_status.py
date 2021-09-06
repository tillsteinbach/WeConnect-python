from enum import Enum
import logging

from weconnect.addressable import AddressableObject, AddressableAttribute, AddressableDict
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class AccessStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.overallStatus = AddressableAttribute(localAddress='overallStatus', parent=self, value=None, valueType=AccessStatus.OverallState)
        self.doors = AddressableDict(localAddress='doors', parent=self)
        self.windows = AddressableDict(localAddress='windows', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):  # noqa: C901
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update access status from dict')

        if 'overallStatus' in fromDict and fromDict['overallStatus']:
            try:
                self.overallStatus.setValueWithCarTime(
                    AccessStatus.OverallState(fromDict['overallStatus']), lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.overallStatus.setValueWithCarTime(AccessStatus.OverallState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported overallStatus: %s was provided, please report this as a bug', fromDict['overallStatus'])
        else:
            self.overallStatus.enabled = False

        if 'doors' in fromDict and fromDict['doors'] is not None:
            for doorDict in fromDict['doors']:
                if 'name' in doorDict:
                    if doorDict['name'] in self.doors:
                        self.doors[doorDict['name']].update(fromDict=doorDict)
                    else:
                        self.doors[doorDict['name']] = AccessStatus.Door(fromDict=doorDict, parent=self.doors)
            for doorName in [doorName for doorName in self.doors.keys()
                             if doorName not in [door['name'] for door in fromDict['doors'] if 'name' in door]]:
                del self.doors[doorName]
        else:
            self.doors.clear()
            self.doors.enabled = False

        if 'windows' in fromDict and fromDict['windows'] is not None:
            for windowDict in fromDict['windows']:
                if 'name' in windowDict:
                    if windowDict['name'] in self.windows:
                        self.windows[windowDict['name']].update(fromDict=windowDict)
                    else:
                        self.windows[windowDict['name']] = AccessStatus.Window(fromDict=windowDict, parent=self.windows)
            for windowName in [windowName for windowName in self.windows.keys()
                               if windowName not in [window['name']
                               for window in fromDict['windows'] if 'name' in window]]:
                del self.doors[windowName]
        else:
            self.windows.clear()
            self.windows.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['overallStatus', 'doors', 'windows']))

    def __str__(self):
        string = super().__str__()
        string += f'\n\tOverall Status: {self.overallStatus.value.value}'
        string += f'\n\tDoors: {len(self.doors)} items'
        for door in self.doors.values():
            string += f'\n\t\t{door}'
        string += f'\n\tWindows: {len(self.windows)} items'
        for window in self.windows.values():
            string += f'\n\t\t{window}'
        return string

    class OverallState(Enum):
        SAFE = 'safe'
        UNSAFE = 'unsafe'
        INVALID = 'invalid'
        UNKNOWN = 'unknown overall state'

    class Door(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.openState = AddressableAttribute(
                localAddress='openState', parent=self, value=None, valueType=AccessStatus.Door.OpenState)
            self.lockState = AddressableAttribute(
                localAddress='lockState', parent=self, value=None, valueType=AccessStatus.Door.LockState)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update door from dict')

            if 'name' in fromDict:
                self.id = fromDict['name']
                self.localAddress = self.id
            else:
                LOG.error('Door is missing name attribute')

            if 'status' in fromDict and fromDict['status']:
                if 'locked' in fromDict['status']:
                    self.lockState.setValueWithCarTime(
                        AccessStatus.Door.LockState.LOCKED, lastUpdateFromCar=None, fromServer=True)
                elif 'unlocked' in fromDict['status']:
                    self.lockState.setValueWithCarTime(
                        AccessStatus.Door.LockState.UNLOCKED, lastUpdateFromCar=None, fromServer=True)
                else:
                    self.lockState.setValueWithCarTime(
                        AccessStatus.Door.LockState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)

                if 'open' in fromDict['status']:
                    self.openState.setValueWithCarTime(AccessStatus.Door.OpenState.OPEN,
                                                       lastUpdateFromCar=None, fromServer=True)
                elif 'closed' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Door.OpenState.CLOSED, lastUpdateFromCar=None, fromServer=True)
                elif 'unsupported' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Door.OpenState.UNSUPPORTED, lastUpdateFromCar=None, fromServer=True)
                elif 'invalid' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Door.OpenState.INVALID, lastUpdateFromCar=None, fromServer=True)
                else:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Door.OpenState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
            else:
                self.lockState.enabled = False
                self.openState.enabled = False

            for key, value in {key: value for key, value in fromDict.items() if key not in ['name', 'status']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnString = f'{self.id}: '
            if self.openState.enabled:
                returnString += f'{self.openState.value.value}'  # pylint: disable=no-member
            elif self.lockState.enabled:
                returnString += f', {self.lockState.value.value}'  # pylint: disable=no-member
            return returnString

        class OpenState(Enum):
            OPEN = 'open'
            CLOSED = 'closed'
            UNSUPPORTED = 'unsupported'
            INVALID = 'invalid'
            UNKNOWN = 'unknown open state'

        class LockState(Enum):
            LOCKED = 'locked'
            UNLOCKED = 'unlocked'
            UNKNOWN = 'unknown lock state'

    class Window(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.openState = AddressableAttribute(
                localAddress='openState', parent=self, value=None, valueType=AccessStatus.Window.OpenState)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update window from dict')

            if 'name' in fromDict:
                self.id = fromDict['name']
                self.localAddress = self.id
            else:
                LOG.error('Window is missing name attribute')

            if 'status' in fromDict and fromDict['status']:
                if 'open' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Window.OpenState.OPEN, lastUpdateFromCar=None, fromServer=True)
                elif 'closed' in fromDict['status']:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Window.OpenState.CLOSED, lastUpdateFromCar=None, fromServer=True)
                elif 'unsupported' in fromDict['status']:
                    self.openState.setValueWithCarTime(AccessStatus.Window.OpenState.UNSUPPORTED, lastUpdateFromCar=None)
                elif 'invalid' in fromDict['status']:
                    self.openState.setValueWithCarTime(AccessStatus.Window.OpenState.INVALID, lastUpdateFromCar=None)
                else:
                    self.openState.setValueWithCarTime(
                        AccessStatus.Window.OpenState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('No unsupported window status: %s was provided, please report this as a bug', fromDict['status'])
            else:
                self.openState.enabled = False

            for key, value in {key: value for key, value in fromDict.items() if key not in ['name', 'status']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            return f'{self.id}: {self.openState.value.value}'  # pylint: disable=no-member

        class OpenState(Enum,):
            OPEN = 'open'
            CLOSED = 'closed'
            UNSUPPORTED = 'unsupported'
            INVALID = 'invalid'
            UNKNOWN = 'unknown open state'
