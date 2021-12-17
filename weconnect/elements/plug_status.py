from enum import Enum
import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class PlugStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.plugConnectionState = AddressableAttribute(
            localAddress='plugConnectionState', parent=self, value=None, valueType=PlugStatus.PlugConnectionState)
        self.plugLockState = AddressableAttribute(
            localAddress='plugLockState', value=None, parent=self, valueType=PlugStatus.PlugLockState)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Plug status from dict')

        if 'plugConnectionState' in fromDict and fromDict['plugConnectionState']:
            try:
                self.plugConnectionState.setValueWithCarTime(
                    PlugStatus.PlugConnectionState(fromDict['plugConnectionState']), lastUpdateFromCar=None,
                    fromServer=True)
            except ValueError:
                self.plugConnectionState.setValueWithCarTime(PlugStatus.PlugConnectionState.UNKNOWN,
                                                             lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported plugConnectionState: %s was provided,'
                            ' please report this as a bug', fromDict['plugConnectionState'])
        else:
            self.plugConnectionState.enabled = False

        if 'plugLockState' in fromDict and fromDict['plugLockState']:
            try:
                self.plugLockState.setValueWithCarTime(PlugStatus.PlugLockState(fromDict['plugLockState']),
                                                       lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.plugLockState.setValueWithCarTime(PlugStatus.PlugLockState.UNKNOWN,
                                                       lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported plugLockState: %s was provided,'
                            ' please report this as a bug', fromDict['plugLockState'])
        else:
            self.plugLockState.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['plugConnectionState', 'plugLockState']))

    def __str__(self):
        string = super().__str__()
        string += '\n\tPlug:'
        if self.plugConnectionState.enabled:
            string += f' {self.plugConnectionState.value.value}, '  # pylint: disable=no-member
        if self.plugLockState.enabled:
            string += f'{self.plugLockState.value.value}'  # pylint: disable=no-member
        return string

    class PlugConnectionState(Enum,):
        CONNECTED = 'connected'
        DISCONNECTED = 'disconnected'
        INVALID = 'invalid'
        UNSUPPORTED = 'unsupported'
        UNKNOWN = 'unknown unlock plug state'

    class PlugLockState(Enum,):
        LOCKED = 'locked'
        UNLOCKED = 'unlocked'
        INVALID = 'invalid'
        UNSUPPORTED = 'unsupported'
        UNKNOWN = 'unknown unlock plug state'
