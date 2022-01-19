import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class ParkingPosition(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.latitude = AddressableAttribute(localAddress='latitude', parent=self, value=None, valueType=float)
        self.longitude = AddressableAttribute(localAddress='longitude', parent=self, value=None, valueType=float)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update ParkingPosition from dict')

        # rename dict key to match new structure
        if 'data' in fromDict:
            fromDict['value'] = fromDict['data']
            del fromDict['data']

        if 'value' in fromDict:
            self.latitude.fromDict(fromDict['value'], 'lat')
            self.longitude.fromDict(fromDict['value'], 'lon')
        else:
            self.latitude.enabled = False
            self.longitude.enabled = False
            self.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['lat', 'lon']))

    def __str__(self):
        string = super().__str__()
        if self.latitude.enabled:
            string += f'\n\tLatitude: {self.latitude.value}'
        if self.longitude.enabled:
            string += f'\n\tLongitude: {self.longitude.value}'
        return string
