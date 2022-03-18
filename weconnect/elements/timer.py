from datetime import datetime
import logging

from weconnect.addressable import AddressableObject, AddressableAttribute, AddressableDict

from weconnect.util import robustTimeParse, toBool

LOG = logging.getLogger("weconnect")


class Timer(AddressableObject):
    def __init__(
        self,
        parent,
        fromDict=None,
    ):
        super().__init__(localAddress=None, parent=parent)
        self.timerEnabled = AddressableAttribute(localAddress='enabled', parent=self, value=None, valueType=bool)
        self.climatisation = AddressableAttribute(localAddress='climatisation', parent=self, value=None, valueType=bool)
        self.recurringTimer = None
        self.singleTimer = None
        if fromDict is not None:
            self.update(fromDict)

    def update(self, fromDict):  # noqa: C901
        LOG.debug('Update timer from dict')

        if 'id' in fromDict:
            self.id = fromDict['id']
            self.localAddress = str(self.id)
        else:
            LOG.error('Timer is missing id attribute')

        if 'enabled' in fromDict:
            self.timerEnabled.setValueWithCarTime(toBool(fromDict['enabled']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.timerEnabled.enabled = False

        if 'climatisation' in fromDict:
            self.climatisation.setValueWithCarTime(toBool(fromDict['climatisation']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.timerEnabled.enabled = False

        if 'recurringTimer' in fromDict:
            if self.recurringTimer is None:
                self.recurringTimer = Timer.RecurringTimer(
                    localAddress='recurringTimer', parent=self, fromDict=fromDict['recurringTimer'])
            else:
                self.recurringTimer.update(fromDict=fromDict['recurringTimer'])
        elif self.recurringTimer is not None:
            self.recurringTimer.enabled = False
            self.recurringTimer = None

        if 'singleTimer' in fromDict:
            if self.singleTimer is None:
                self.singleTimer = Timer.SingleTimer(
                    localAddress='singleTimer', parent=self, fromDict=fromDict['singleTimer'])
            else:
                self.singleTimer.update(fromDict=fromDict['singleTimer'])
        elif self.singleTimer is not None:
            self.singleTimer.enabled = False
            self.singleTimer = None

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in ['id', 'enabled', 'climatisation', 'recurringTimer', 'singleTimer']}.items():
            LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    def __str__(self):
        string = f'{self.id}: Enabled: {self.timerEnabled.value}'
        if self.climatisation.enabled:
            string += f' (Climatisation: {self.climatisation.value})'
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
            self.occurringOn = AddressableAttribute(
                localAddress='occurringOn', parent=self, value=None, valueType=str)
            self.startTime = AddressableAttribute(
                localAddress='startTime', parent=self, value=None, valueType=datetime)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update recurring timer from dict')

            if 'startDateTime' in fromDict:
                self.startDateTime.setValueWithCarTime(robustTimeParse(fromDict["startDateTime"]), lastUpdateFromCar=None, fromServer=True)
            else:
                self.startDateTime.enabled = False

            self.occurringOn.fromDict(fromDict, 'occurringOn')

            if 'startTime' in fromDict:
                self.startTime.setValueWithCarTime(datetime.strptime(f'{fromDict["startTime"]}+00:00', '%H:%M%z'),
                                                   lastUpdateFromCar=None, fromServer=True)
            else:
                self.startTime.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['startDateTime', 'occurringOn', 'startTime']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnString = ""
            if self.startDateTime.enabled:
                returnString += self.startDateTime.value.isoformat()  # pylint: disable=no-member
            if self.occurringOn.enabled:
                returnString += self.occurringOn.value
            if self.startTime.enabled:
                returnString += f' {self.startTime.value.strftime("%H:%M")}'
            return returnString
