from enum import Enum
from datetime import datetime
import logging

from weconnect.addressable import AddressableAttribute, AddressableDict, AddressableObject
from weconnect.elements.generic_status import GenericStatus

from weconnect.util import robustTimeParse, toBool

LOG = logging.getLogger("weconnect")


class DepartureTimersStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.heaterSource = AddressableAttribute(localAddress='heaterSource', parent=self, value=None, valueType=DepartureTimersStatus.HeaterSource)
        self.minSOC_pct = AddressableAttribute(localAddress='minSOC_pct', parent=self, value=None, valueType=int)
        self.timers = AddressableDict(localAddress='timers', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update climatization timer from dict')

        if 'value' in fromDict:
            self.heaterSource.fromDict(fromDict['value'], 'heaterSource')
            self.minSOC_pct.fromDict(fromDict['value'], 'minSOC_pct')

            if 'timers' in fromDict['value'] and fromDict['value']['timers'] is not None:
                for climatizationTimerDict in fromDict['value']['timers']:
                    if 'id' in climatizationTimerDict:
                        if climatizationTimerDict['id'] in self.timers:
                            self.timers[climatizationTimerDict['id']].update(fromDict=climatizationTimerDict)
                        else:
                            self.timers[climatizationTimerDict['id']] = DepartureTimersStatus.Timer(
                                fromDict=climatizationTimerDict, parent=self.timers)
                for timerId in [timerId for timerId in self.timers.keys()
                                if timerId not in [timer['id']
                                for timer in fromDict['value']['timers'] if 'id' in timer]]:
                    del self.timers[timerId]
            else:
                self.timers.clear()
                self.timers.enabled = False

        else:
            self.heaterSource.enabled = False
            self.minSOC_pct.enabled = False
            self.timers.clear()
            self.timers.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes + ['timers', 'heaterSource', 'minSOC_pct']))

    def __str__(self):
        string = super().__str__()
        if self.heaterSource.enabled:
            string += f'\n\tHeater Source: {self.heaterSource.value.value}'
        if self.minSOC_pct.enabled:
            string += f'\n\tMin SoC: {self.minSOC_pct.value}%'
        string += f'\n\tTimers: {len(self.timers)} items\n'
        for timer in self.timers.values():
            string += ''.join(['\t\t' + line for line in str(timer).splitlines(True)]) + '\n'
        return string

    class HeaterSource(Enum,):
        AUTOMATIC = 'automatic'
        ELECTRIC = 'electric'
        UNKNOWN = 'unknown'

    class Timer(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.timerEnabled = AddressableAttribute(localAddress='enabled', parent=self, value=None, valueType=bool)
            self.climatisation = AddressableAttribute(localAddress='climatisation', parent=self, value=None, valueType=bool)
            self.charging = AddressableAttribute(localAddress='charging', parent=self, value=None, valueType=bool)
            self.targetSOC_pct = AddressableAttribute(localAddress='targetSOC_pct', value=None, parent=self, valueType=int)
            self.recurringTimer = None
            self.singleTimer = None
            self.preferredChargingTimes = AddressableDict(localAddress='preferredChargingTimes', parent=self)
            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):  # noqa: C901
            LOG.debug('Update timer from dict')

            if 'id' in fromDict:
                self.id = fromDict['id']
                self.localAddress = str(self.id)
            else:
                LOG.error('Timer is missing id attribute')

            self.timerEnabled.fromDict(fromDict, 'enabled')
            self.climatisation.fromDict(fromDict, 'climatisation')
            self.charging.fromDict(fromDict, 'charging')
            self.targetSOC_pct.fromDict(fromDict, 'targetSOC_pct')

            if 'recurringTimer' in fromDict:
                if self.recurringTimer is None:
                    self.recurringTimer = DepartureTimersStatus.Timer.RecurringTimer(
                        localAddress='recurringTimer', parent=self, fromDict=fromDict['recurringTimer'])
                else:
                    self.recurringTimer.update(fromDict=fromDict['recurringTimer'])
            elif self.recurringTimer is not None:
                self.recurringTimer.enabled = False
                self.recurringTimer = None

            if 'singleTimer' in fromDict:
                if self.singleTimer is None:
                    self.singleTimer = DepartureTimersStatus.Timer.SingleTimer(
                        localAddress='singleTimer', parent=self, fromDict=fromDict['singleTimer'])
                else:
                    self.singleTimer.update(fromDict=fromDict['singleTimer'])
            elif self.singleTimer is not None:
                self.singleTimer.enabled = False
                self.singleTimer = None

            if 'preferredChargingTimes' in fromDict and fromDict['preferredChargingTimes'] is not None:
                for preferredChargingTimeDict in fromDict['preferredChargingTimes']:
                    if 'id' in preferredChargingTimeDict:
                        if preferredChargingTimeDict['id'] in self.preferredChargingTimes:
                            self.preferredChargingTimes[preferredChargingTimeDict['id']].update(fromDict=preferredChargingTimeDict)
                        else:
                            self.preferredChargingTimes[preferredChargingTimeDict['id']] = DepartureTimersStatus.Timer.PreferredChargingTimes(
                                localAddress=preferredChargingTimeDict['id'], fromDict=preferredChargingTimeDict, parent=self.preferredChargingTimes)
                for timerId in [timerId for timerId in self.preferredChargingTimes.keys()
                                if timerId not in [timer['id']
                                for timer in fromDict['preferredChargingTimes'] if 'id' in timer]]:
                    del self.PreferredChargingTimes[timerId]
            else:
                self.preferredChargingTimes.clear()
                self.preferredChargingTimes.enabled = False

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['id', 'enabled', 'climatisation', 'charging', 'targetSOC_pct', 'recurringTimer', 'singleTimer',
                                              'preferredChargingTimes']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            string = f'{self.id}: Enabled: {self.timerEnabled.value}'
            if self.climatisation.enabled:
                string += f', Climatisation: {self.climatisation.value}'
            if self.charging.enabled:
                string += f', Charging: {self.charging.value}'
            if self.targetSOC_pct.enabled:
                string += f' to {self.targetSOC_pct.value}% SoC'
            if self.recurringTimer is not None and self.recurringTimer.enabled:
                string += f' at {self.recurringTimer} '
            if self.singleTimer is not None and self.singleTimer.enabled:
                string += f' at {self.singleTimer} '
            if self.preferredChargingTimes.enabled and len(self.preferredChargingTimes) > 0:
                string += f'\n\tPreferred charging times: {len(self.preferredChargingTimes)} items'
                for preferredChargingTime in self.preferredChargingTimes.values():
                    string += f'\n\t\t{preferredChargingTime}'
            return string

        class RecurringTimer(AddressableObject):
            def __init__(
                self,
                localAddress,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress=localAddress, parent=parent)
                self.departureTimeLocal = AddressableAttribute(
                    localAddress='departureTimeLocal', parent=self, value=None, valueType=datetime)
                self.targetTimeLocal = AddressableAttribute(
                    localAddress='targetTimeLocal', parent=self, value=None, valueType=datetime)
                self.repetitionDays = AddressableDict(localAddress='repetitionDays', parent=self)
                self.recurringOn = AddressableDict(localAddress='recurringOn', parent=self)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):  # noqa: C901
                LOG.debug('Update recurring timer from dict')

                if 'departureTimeLocal' in fromDict:
                    self.departureTimeLocal.setValueWithCarTime(datetime.strptime(f'{fromDict["departureTimeLocal"]}+00:00', '%H:%M%z'),
                                                                lastUpdateFromCar=None, fromServer=True)
                else:
                    self.departureTimeLocal.enabled = False

                if 'targetTimeLocal' in fromDict:
                    self.targetTimeLocal.setValueWithCarTime(datetime.strptime(f'{fromDict["targetTimeLocal"]}+00:00', '%H:%M%z'),
                                                             lastUpdateFromCar=None, fromServer=True)
                else:
                    self.targetTimeLocal.enabled = False

                if 'repetitionDays' in fromDict and fromDict['repetitionDays'] is not None:
                    for day in fromDict['repetitionDays']:
                        if day in self.repetitionDays:
                            self.repetitionDays[day].setValueWithCarTime(True, lastUpdateFromCar=None, fromServer=True)
                        else:
                            self.repetitionDays[day] = AddressableAttribute(
                                localAddress=day, parent=self.repetitionDays, value=True, valueType=bool)
                    for day in [day for day in self.repetitionDays if day not in fromDict['repetitionDays']]:
                        del self.repetitionDays[day]
                else:
                    self.repetitionDays.clear()
                    self.repetitionDays.enabled = False

                if 'recurringOn' in fromDict and fromDict['recurringOn'] is not None:
                    for day, enabled in fromDict['recurringOn'].items():
                        if day in self.recurringOn:
                            self.recurringOn[day].setValueWithCarTime(enabled, lastUpdateFromCar=None, fromServer=True)
                        else:
                            self.recurringOn[day] = AddressableAttribute(
                                localAddress=day, parent=self.recurringOn, value=enabled, valueType=bool)
                    for day in [day for day in self.recurringOn if day not in fromDict['recurringOn']]:
                        del self.recurringOn[day]
                else:
                    self.recurringOn.clear()
                    self.recurringOn.enabled = False

                for key, value in {key: value for key, value in fromDict.items()
                                   if key not in ['departureTimeLocal', 'targetTimeLocal', 'repetitionDays', 'recurringOn']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                string = f'{self.departureTimeLocal.value.strftime("%H:%M")} on '  # pylint: disable=no-member
                for day, value in self.recurringOn.items():
                    if value.value:
                        string += day + ' '
                return string

        class PreferredChargingTimes(AddressableObject):
            def __init__(
                self,
                localAddress,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress=localAddress, parent=parent)
                self.timerEnabled = AddressableAttribute(localAddress='enabled', parent=self, value=None, valueType=bool)
                self.startTimeLocal = AddressableAttribute(
                    localAddress='startTimeLocal', parent=self, value=None, valueType=datetime)
                self.endTimeLocal = AddressableAttribute(
                    localAddress='endTimeLocal', parent=self, value=None, valueType=datetime)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Update preferred charging times from dict')

                if 'id' in fromDict:
                    self.id = fromDict['id']
                    self.localAddress = str(self.id)
                else:
                    LOG.error('Charging time is missing id attribute')

                if 'enabled' in fromDict:
                    self.timerEnabled.setValueWithCarTime(toBool(fromDict['enabled']), lastUpdateFromCar=None, fromServer=True)
                else:
                    self.timerEnabled.enabled = False

                if 'startTimeLocal' in fromDict:
                    self.startTimeLocal.setValueWithCarTime(datetime.strptime(f'{fromDict["startTimeLocal"]}+00:00', '%H:%M%z'),
                                                            lastUpdateFromCar=None, fromServer=True)
                else:
                    self.startTimeLocal.enabled = False

                if 'endTimeLocal' in fromDict:
                    self.endTimeLocal.setValueWithCarTime(datetime.strptime(f'{fromDict["endTimeLocal"]}+00:00', '%H:%M%z'),
                                                          lastUpdateFromCar=None, fromServer=True)
                else:
                    self.endTimeLocal.enabled = False

                for key, value in {key: value for key, value in fromDict.items()
                                   if key not in ['id', 'enabled', 'startTimeLocal', 'endTimeLocal']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                string = f'{self.id}: Enabled: {self.timerEnabled.value}'
                if self.startTimeLocal.enabled:
                    string += f', Start: {self.startTimeLocal.value.strftime("%H:%M")}'
                if self.endTimeLocal.enabled:
                    string += f', End: {self.endTimeLocal.value.strftime("%H:%M")}'
                return string

        class SingleTimer(AddressableObject):
            def __init__(
                self,
                localAddress,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress=localAddress, parent=parent)
                self.departureDateTimeLocal = AddressableAttribute(
                    localAddress='departureDateTimeLocal', parent=self, value=None, valueType=datetime)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Update recurring timer from dict')

                if 'departureDateTimeLocal' in fromDict:
                    self.departureDateTimeLocal.setValueWithCarTime(robustTimeParse(fromDict["departureDateTimeLocal"]), lastUpdateFromCar=None,
                                                                    fromServer=True)
                else:
                    self.departureDateTimeLocal.enabled = False

                for key, value in {key: value for key, value in fromDict.items()
                                   if key not in ['departureDateTimeLocal']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                returnString = ""
                if self.departureDateTimeLocal.enabled:
                    returnString += self.departureDateTimeLocal.value.isoformat()  # pylint: disable=no-member
                return returnString
