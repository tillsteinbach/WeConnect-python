import logging
from datetime import datetime

from weconnect.util import robustTimeParse
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

        if 'id' in fromDict:
            self.id.setValueWithCarTime(fromDict['id'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.id.enabled = False

        if 'status' in fromDict:
            self.status.setValueWithCarTime(fromDict['status'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.status.enabled = False

        if 'expirationDate' in fromDict:
            self.expirationDate.setValueWithCarTime(robustTimeParse(
                fromDict['expirationDate']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.expirationDate.enabled = False

        if 'userDisablingAllowed' in fromDict:
            self.userDisablingAllowed.setValueWithCarTime(
                fromDict['userDisablingAllowed'], lastUpdateFromCar=None, fromServer=True)
        else:
            self.userDisablingAllowed.enabled = False

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in ['id', 'status', 'expirationDate', 'userDisablingAllowed']}.items():
            LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    def __str__(self):
        returnString = f'[{self.id.value}] Status: {self.status.value} disabling: {self.userDisablingAllowed.value}'
        if self.expirationDate.enabled:
            returnString += f' (expires {self.expirationDate.value.isoformat()})'  # pylint: disable=no-member
        return returnString
