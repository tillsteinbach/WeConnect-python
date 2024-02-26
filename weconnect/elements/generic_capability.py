from enum import IntEnum
import logging
from datetime import datetime

from weconnect.addressable import AddressableObject, AddressableAttribute

LOG = logging.getLogger("weconnect")


class GenericCapability(AddressableObject):
    def __init__(
        self,
        capabilityId,
        parent,
        fromDict=None,
        fixAPI=True,
    ):
        self.fixAPI = fixAPI
        super().__init__(localAddress=capabilityId, parent=parent)
        self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=str)
        self.status = AddressableAttribute(localAddress='status', parent=self, value=None, valueType=list)
        self.expirationDate = AddressableAttribute(
            localAddress='expirationDate', parent=self, value=None, valueType=datetime)
        self.userDisablingAllowed = AddressableAttribute(
            localAddress='userDisablingAllowed', parent=self, value=None, valueType=bool)
        LOG.debug('Create capability from dict')
        if fromDict is not None:
            self.update(fromDict=fromDict)

    def update(self, fromDict):
        LOG.debug('Update capability from dict')

        self.id.fromDict(fromDict, 'id')

        if 'status' in fromDict:
            statuses = []
            for status in fromDict['status']:
                try:
                    statuses.append(GenericCapability.Status(status))
                except ValueError:
                    statuses.append(GenericCapability.Status(GenericCapability.Status.UNKNOWN))
                    LOG.debug('An unsupported status: %s was provided, please report this as a bug', status)
            self.status.setValueWithCarTime(statuses, lastUpdateFromCar=None, fromServer=True)
        else:
            self.status.enabled = False

        self.expirationDate.fromDict(fromDict, 'expirationDate')
        self.userDisablingAllowed.fromDict(fromDict, 'userDisablingAllowed')

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in ['id', 'status', 'expirationDate', 'userDisablingAllowed']}.items():
            LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    def __str__(self):
        returnString = f'[{self.id.value}]'
        if self.status.enabled and self.status.value is not None:
            returnString += f' Status: {", ".join([status.name for status in self.status.value])}'
        returnString += f' disabling: {self.userDisablingAllowed.value}'
        if self.expirationDate.enabled:
            returnString += f' (expires {self.expirationDate.value.isoformat()})'  # pylint: disable=no-member
        return returnString

    class Status(IntEnum):
        UNKNOWN = 0
        DEACTIVATED = 1001
        INITIALLY_DISABLED = 1003
        DISABLED_BY_USER = 1004
        OFFLINE_MODE = 1005
        WORKSHOP_MODE = 1006
        MISSING_OPERATION = 1007
        MISSING_SERVICE = 1008
        PLAY_PROTECTION = 1009
        POWER_BUDGET_REACHED = 1010
        DEEP_SLEEP = 1011
        LOCATION_DATA_DISABLED = 1013
        LICENSE_INACTIVE = 2001
        LICENSE_EXPIRED = 2002
        MISSING_LICENSE = 2003
        USER_NOT_VERIFIED = 3001
        TERMS_AND_CONDITIONS_NOT_ACCEPTED = 3002
        INSUFFICIENT_RIGHTS = 3003
        CONSENT_MISSING = 3004
        LIMITED_FEATURE = 3005
        AUTH_APP_CERT_ERROR = 3006
        STATUS_UNSUPPORTED = 4001
