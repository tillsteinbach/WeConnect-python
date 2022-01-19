from enum import Enum
import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class LVBatteryStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.batterySupport = AddressableAttribute(localAddress='batterySupport', value=None, parent=self,
                                                   valueType=LVBatteryStatus.BatterySupport)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update lv battery status from dict')

        if 'value' in fromDict:
            self.batterySupport.fromDict(fromDict['value'], 'batterySupport')
        else:
            self.batterySupport.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['batterySupport']))

    def __str__(self):
        string = super().__str__()
        if self.batterySupport.enabled:
            string += f'\n\tBattery Support: {self.batterySupport.value.value}'  # pylint: disable=no-member
        return string

    class BatterySupport(Enum,):
        NOT_ALLOWED = 'notAllowed'
        PENDING_DISABLED = 'pendingDisable'
        DISABLED = 'disabled'
        PENDING_ENABLED = 'pendingEnable'
        ENABLED = 'enabled'
        INVALID = 'invalid'
        UNKNOWN = 'unknown battery support'
