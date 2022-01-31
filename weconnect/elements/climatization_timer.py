from datetime import datetime
import logging

from weconnect.addressable import AddressableAttribute, AddressableDict
from weconnect.elements.generic_status import GenericStatus
from weconnect.elements.timer import Timer

LOG = logging.getLogger("weconnect")


class ClimatizationTimer(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.timers = AddressableDict(localAddress='timers', parent=self)
        self.timeInCar = AddressableAttribute(localAddress='timeInCar', parent=self, value=None, valueType=datetime)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update climatization timer from dict')

        if 'value' in fromDict:
            if 'timers' in fromDict['value'] and fromDict['value']['timers'] is not None:
                for climatizationTimerDict in fromDict['value']['timers']:
                    if 'id' in climatizationTimerDict:
                        if climatizationTimerDict['id'] in self.timers:
                            self.timers[climatizationTimerDict['id']].update(fromDict=climatizationTimerDict)
                        else:
                            self.timers[climatizationTimerDict['id']] = Timer(
                                fromDict=climatizationTimerDict, parent=self.timers)
                for timerId in [timerId for timerId in self.timers.keys()
                                if timerId not in [timer['id']
                                for timer in fromDict['value']['timers'] if 'id' in timer]]:
                    del self.timers[timerId]
            else:
                self.timers.clear()
                self.timers.enabled = False

            self.timeInCar.fromDict(fromDict['value'], 'timeInCar')
        else:
            self.timers.clear()
            self.timers.enabled = False
            self.timeInCar.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['timers', 'timeInCar']))

    def __str__(self):
        string = super().__str__()
        if self.timeInCar.enabled:
            string += f'\n\tTime in Car: {self.timeInCar.value.isoformat()}'  # pylint: disable=no-member
            string += f' (captured at {self.carCapturedTimestamp.value.isoformat()})'  # pylint: disable=no-member
        string += f'\n\tTimers: {len(self.timers)} items'
        for timer in self.timers.values():
            string += f'\n\t\t{timer}'
        return string
