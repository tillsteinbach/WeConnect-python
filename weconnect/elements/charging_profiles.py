from datetime import datetime
import logging

from weconnect.addressable import AddressableAttribute, AddressableList
from weconnect.elements.generic_settings import GenericSettings

LOG = logging.getLogger("weconnect")


class ChargingProfiles(GenericSettings):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.profiles = AddressableList(localAddress='profiles', parent=self)
        self.timeInCar = AddressableAttribute(localAddress='timeInCar', parent=self, value=None, valueType=datetime)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update charging profiles from dict')

        if 'value' in fromDict:
            if 'profiles' in fromDict['value'] and fromDict['value']['profiles'] is not None:
                for profile in fromDict['value']['profiles']:
                    LOG.warning('Charging profiles are not yet implemented %s', profile)
            else:
                self.profiles.clear()
                self.profiles.enabled = False

            self.timeInCar.fromDict(fromDict['value'], 'timeInCar')
        else:
            self.profiles.clear()
            self.profiles.enabled = False
            self.timeInCar.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['profiles', 'timeInCar']))

    def __str__(self):
        string = super().__str__()
        if self.timeInCar.enabled:
            string += f'\n\tTime in Car: {self.timeInCar.value.isoformat()}'  # pylint: disable=no-member
            string += f' (captured at {self.carCapturedTimestamp.value.isoformat()})'  # pylint: disable=no-member
        string += f'\n\tProfiles: {len(self.profiles)} items'
        for profile in self.profiles:
            string += f'\n\t\t{profile}'
        return string
