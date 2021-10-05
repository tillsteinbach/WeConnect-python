from enum import Enum
import logging

import json
import requests

from weconnect.addressable import AddressableLeaf, ChangeableAttribute, AliasChangeableAttribute
from weconnect.elements.generic_status import GenericStatus
from weconnect.errors import SetterError

LOG = logging.getLogger("weconnect")


class GenericSettings(GenericStatus):
    def valueChanged(self, element, flags):
        del element
        if flags & AddressableLeaf.ObserverEvent.VALUE_CHANGED \
                and not flags & AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER:
            setting = self.id.partition('Settings')[0]
            url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/{setting}/settings'
            settingsDict = dict()
            for child in self.getLeafChildren():
                if isinstance(child, ChangeableAttribute) and not isinstance(child, AliasChangeableAttribute):
                    if isinstance(child.value, Enum):  # pylint: disable=no-member # this is a fales positive
                        settingsDict[child.getLocalAddress()] = child.value.value  # pylint: disable=no-member # this is a fales positive
                    else:
                        settingsDict[child.getLocalAddress()] = child.value  # pylint: disable=no-member # this is a fales positive
            data = json.dumps(settingsDict)
            putResponse = self.vehicle.weConnect.session.put(url, data=data, allow_redirects=True)
            if putResponse.status_code != requests.codes['ok']:
                raise SetterError(f'Could not set value ({putResponse.status_code})')
