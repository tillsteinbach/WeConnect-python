from enum import Enum
import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class GenericRequestStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.status = AddressableAttribute(localAddress='status', parent=self,
                                           value=None, valueType=GenericRequestStatus.Status)
        self.group = AddressableAttribute(localAddress='group', parent=self, value=None, valueType=int)
        self.info = AddressableAttribute(localAddress='info', parent=self, value=None, valueType=str)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Request status from dict')

        self.status.fromDict(fromDict, 'status')
        self.group.fromDict(fromDict, 'group')
        self.info.fromDict(fromDict, 'info')

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['status', 'group', 'info']))

    def __str__(self):
        string = super().__str__() + '\n'
        if self.status.enabled:
            string += f'\tStatus: {self.status.value.value}\n'  # pylint: disable=no-member
        if self.group.enabled:
            string += f'\tGroup: {self.group.value}\n'
        if self.info.enabled:
            string += f'\tInfo: {self.info.value}\n'
        return string

    class Status(Enum,):
        SUCCESSFULL = 'successful'
        FAIL = 'fail'
        POLLING_TIMEOUT = 'polling_timeout'
        IN_PROGRESS = 'in_progress'
        QUEUED = 'queued'
        DELAYED = 'delayed'
        TIMEOUT = 'timeout'
        FAIL_VEHICLE_IS_OFFLINE = 'fail_vehicle_is_offline'
        FAIL_IGNITION_ON = 'fail_ignition_on'
        FAIL_BATTERY_LOW = 'fail_battery_low'
        UNKNOWN = 'unknown status'
