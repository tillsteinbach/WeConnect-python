from enum import Enum
import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class ClimatizationStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.remainingClimatisationTime_min = AddressableAttribute(
            localAddress='remainingClimatisationTime_min', parent=self, value=None, valueType=int)
        self.climatisationState = AddressableAttribute(localAddress='climatisationState', value=None, parent=self,
                                                       valueType=ClimatizationStatus.ClimatizationState)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Climatization status from dict')

        if 'value' in fromDict:
            self.climatisationState.fromDict(fromDict['value'], 'climatisationState')
            if 'remainingClimatisationTime_min' in fromDict['value']:
                remainingTime = int(fromDict['value']['remainingClimatisationTime_min'])
                if self.fixAPI and remainingTime != 0 and self.climatisationState.value == ClimatizationStatus.ClimatizationState.OFF:
                    remainingTime = 0
                    LOG.debug('%s: Attribute remainingClimatisationTime_min is %s while climatisationState is %s. Setting 0 instead',
                              self.getGlobalAddress(), fromDict['value']['remainingClimatisationTime_min'], self.climatisationState.value)
                self.remainingClimatisationTime_min.setValueWithCarTime(remainingTime, lastUpdateFromCar=None, fromServer=True)
            else:
                self.remainingClimatisationTime_min.enabled = False
        else:
            self.remainingClimatisationTime_min.enabled = False
            self.climatisationState.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['remainingClimatisationTime_min', 'climatisationState']))

    def __str__(self):
        string = super().__str__()
        if self.climatisationState.enabled:
            string += f'\n\tState: {self.climatisationState.value.value}'  # pylint: disable=no-member
        if self.remainingClimatisationTime_min.enabled:
            string += f'\n\tRemaining Climatization Time: {self.remainingClimatisationTime_min.value} min'
        return string

    class ClimatizationState(Enum,):
        OFF = 'off'
        HEATING = 'heating'
        COOLING = 'cooling'
        VENTILATION = 'ventilation'
        INVALID = 'invalid'
        UNKNOWN = 'unknown climatization state'
