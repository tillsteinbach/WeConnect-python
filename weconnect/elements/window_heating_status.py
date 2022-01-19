from enum import Enum
import logging

from weconnect.addressable import AddressableAttribute, AddressableDict, AddressableObject
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class WindowHeatingStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.windows = AddressableDict(localAddress='windows', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update window heating status from dict')

        if 'value' in fromDict:
            if 'windowHeatingStatus' in fromDict['value'] and fromDict['value']['windowHeatingStatus'] is not None:
                for windowDict in fromDict['value']['windowHeatingStatus']:
                    if 'windowLocation' in windowDict:
                        if windowDict['windowLocation'] in self.windows:
                            self.windows[windowDict['windowLocation']].update(fromDict=windowDict)
                        else:
                            self.windows[windowDict['windowLocation']] = WindowHeatingStatus.Window(
                                fromDict=windowDict, parent=self.windows)
                for windowName in [windowName for windowName in self.windows.keys()
                                   if windowName not in [window['windowLocation']
                                   for window in fromDict['value']['windowHeatingStatus'] if 'windowLocation' in window]]:
                    del self.windows[windowName]
            else:
                self.windows.clear()
                self.windows.enabled = False
        else:
            self.windows.clear()
            self.windows.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['windowHeatingStatus']))

    def __str__(self):
        string = super().__str__()
        string += f'\n\tWindows: {len(self.windows)} items'
        for window in self.windows.values():
            string += f'\n\t\t{window}'
        return string

    class Window(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.windowHeatingState = AddressableAttribute(
                localAddress='windowHeatingState', parent=self, value=None,
                valueType=WindowHeatingStatus.Window.WindowHeatingState)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update window from dict')

            if 'windowLocation' in fromDict:
                self.id = fromDict['windowLocation']
                self.localAddress = self.id
            else:
                LOG.error('Window is missing windowLocation attribute')

            self.windowHeatingState.fromDict(fromDict, 'windowHeatingState')

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['windowLocation', 'windowHeatingState']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            return f'{self.id}: {self.windowHeatingState.value.value}'  # pylint: disable=no-member

        class WindowHeatingState(Enum,):
            ON = 'on'
            OFF = 'off'
            INVALID = 'invalid'
            UNKNOWN = 'unknown open state'
