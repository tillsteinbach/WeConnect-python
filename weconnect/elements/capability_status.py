import logging

from weconnect.addressable import AddressableDict
from weconnect.elements.generic_status import GenericStatus
from weconnect.elements.generic_capability import GenericCapability

LOG = logging.getLogger("weconnect")


class CapabilityStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.capabilities = AddressableDict(localAddress='capabilities', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update capability status from dict')

        if 'value' in fromDict:
            for capDict in fromDict['value']:
                if 'id' in capDict:
                    if capDict['id'] in self.capabilities:
                        self.capabilities[capDict['id']].update(fromDict=capDict)
                    else:
                        self.capabilities[capDict['id']] = GenericCapability(
                            capabilityId=capDict['id'], fromDict=capDict, parent=self.capabilities)
            for capabilityId in [capabilityId for capabilityId in self.capabilities.keys()
                                 if capabilityId not in [capability['id']
                                 for capability in fromDict['value'] if 'id' in capability]]:
                del self.capabilities[capabilityId]
        else:
            self.capabilities.clear()
            self.capabilities.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes))

    def __str__(self):
        string = super().__str__()
        string += f'\n\tCapabilities: {len(self.capabilities)} items'
        for capability in self.capabilities.values():
            string += f'\n\t\t{capability}'
        return string
