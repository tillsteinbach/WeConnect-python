from datetime import datetime
import logging

from weconnect.addressable import AddressableObject, AddressableAttribute, AddressableDict
from weconnect.elements.generic_status import GenericStatus
from weconnect.util import robustTimeParse, toBool

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

        if 'timers' in fromDict and fromDict['timers'] is not None:
            for climatizationTimerDict in fromDict['timers']:
                if 'id' in climatizationTimerDict:
                    if climatizationTimerDict['id'] in self.timers:
                        self.timers[climatizationTimerDict['id']].update(fromDict=climatizationTimerDict)
                    else:
                        self.timers[climatizationTimerDict['id']] = ClimatizationTimer.Timer(
                            fromDict=climatizationTimerDict, parent=self.timers)
            for timerId in [timerId for timerId in self.timers.keys()
                            if timerId not in [timer['id']
                            for timer in fromDict['timers'] if 'id' in timer]]:
                del self.timers[timerId]
        else:
            self.timers.clear()
            self.timers.enabled = False

        if 'timeInCar' in fromDict:
            self.timeInCar.setValueWithCarTime(robustTimeParse(
                fromDict['timeInCar']), lastUpdateFromCar=None, fromServer=True)
        else:
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

    class Timer(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.timerEnabled = AddressableAttribute(localAddress='enabled', parent=self, value=None, valueType=bool)
            self.recurringTimer = None
            self.singleTimer = None
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update timer from dict')

            if 'id' in fromDict:
                self.id = fromDict['id']
                self.localAddress = str(self.id)
            else:
                LOG.error('Timer is missing id attribute')

            if 'enabled' in fromDict:
                self.timerEnabled.setValueWithCarTime(
                    toBool(fromDict['enabled']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.timerEnabled.enabled = False

            if 'recurringTimer' in fromDict:
                if self.recurringTimer is None:
                    self.recurringTimer = ClimatizationTimer.Timer.RecurringTimer(
                        localAddress='recurringTimer', parent=self, fromDict=fromDict['recurringTimer'])
                else:
                    self.recurringTimer.update(fromDict=fromDict['recurringTimer'])
            elif self.recurringTimer is not None:
                self.recurringTimer.enabled = False
                self.recurringTimer = None

            if 'singleTimer' in fromDict:
                if self.singleTimer is None:
                    self.singleTimer = ClimatizationTimer.Timer.SingleTimer(
                        localAddress='singleTimer', parent=self, fromDict=fromDict['singleTimer'])
                else:
                    self.singleTimer.update(fromDict=fromDict['singleTimer'])
            elif self.singleTimer is not None:
                self.singleTimer.enabled = False
                self.singleTimer = None

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['id', 'enabled', 'recurringTimer', 'singleTimer']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            string = f'{self.id}: Enabled: {self.timerEnabled.value}'
            if self.recurringTimer is not None and self.recurringTimer.enabled:
                string += f' at {self.recurringTimer} '
            if self.singleTimer is not None and self.singleTimer.enabled:
                string += f' at {self.singleTimer} '
            return string

        class RecurringTimer(AddressableObject):
            def __init__(
                self,
                localAddress,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress=localAddress, parent=parent)
                self.startTime = AddressableAttribute(
                    localAddress='startTime', parent=self, value=None, valueType=datetime)
                self.recurringOn = AddressableDict(localAddress='recurringOn', parent=self)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Update recurring timer from dict')

                if 'startTime' in fromDict:
                    self.startTime.setValueWithCarTime(datetime.strptime(f'{fromDict["startTime"]}+00:00', '%H:%M%z'),
                                                       lastUpdateFromCar=None, fromServer=True)
                else:
                    self.startTime.enabled = False

                if 'recurringOn' in fromDict and fromDict['recurringOn'] is not None:
                    for day, state in fromDict['recurringOn'].items():
                        if day in self.recurringOn:
                            self.recurringOn[day].setValueWithCarTime(state, lastUpdateFromCar=None, fromServer=True)
                        else:
                            self.recurringOn[day] = AddressableAttribute(
                                localAddress=day, parent=self.recurringOn, value=state, valueType=bool)
                    for day in [day for day in self.recurringOn.keys() if day not in fromDict['recurringOn'].keys()]:
                        del self.recurringOn[day]
                else:
                    self.recurringOn.clear()
                    self.recurringOn.enabled = False

                for key, value in {key: value for key, value in fromDict.items()
                                   if key not in ['startTime', 'recurringOn']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                string = f'{self.startTime.value.strftime("%H:%M")} on '  # pylint: disable=no-member
                for day, value in self.recurringOn.items():
                    if value:
                        string += day + ' '
                return string

        class SingleTimer(AddressableObject):
            def __init__(
                self,
                localAddress,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress=localAddress, parent=parent)
                self.startDateTime = AddressableAttribute(
                    localAddress='startDateTime', parent=self, value=None, valueType=datetime)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Update recurring timer from dict')

                if 'startDateTime' in fromDict:
                    self.startDateTime.setValueWithCarTime(robustTimeParse(fromDict["startDateTime"]), lastUpdateFromCar=None, fromServer=True)
                else:
                    self.startDateTime.enabled = False

                for key, value in {key: value for key, value in fromDict.items()
                                   if key not in ['startDateTime']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                return self.startDateTime.value.isoformat()  # pylint: disable=no-member
