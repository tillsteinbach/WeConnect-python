from datetime import datetime, time
import logging

from weconnect.addressable import AddressableAttribute, AddressableDict, AddressableObject
from weconnect.elements.enums import UnlockPlugState
from weconnect.elements.generic_settings import GenericSettings
from weconnect.elements.timer import Timer

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
        self.profiles = AddressableDict(localAddress='profiles', parent=self)
        self.timeInCar = AddressableAttribute(localAddress='timeInCar', parent=self, value=None, valueType=datetime)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update charging profiles from dict')

        if 'value' in fromDict:
            if 'profiles' in fromDict['value'] and fromDict['value']['profiles'] is not None:
                for profileDict in fromDict['value']['profiles']:
                    if 'id' in profileDict:
                        if profileDict['id'] in self.profiles:
                            self.profiles[profileDict['id']].update(fromDict=profileDict)
                        else:
                            self.profiles[profileDict['id']] = ChargingProfiles.ChargingProfile(fromDict=profileDict, parent=self.profiles)
                for profileId in [profileId for profileId in self.profiles.keys()
                                  if profileId not in [profile['id'] for profile in fromDict['value']['profiles'] if 'id' in profile]]:
                    del self.profiles[profileId]
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
        string += f'\n\t\tProfiles: {len(self.profiles)} items'
        for profile in self.profiles.values():
            string += '\n' + ''.join(['\t\t\t' + line for line in str(profile).splitlines(True)])
        return string

    class ChargingProfile(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None
        ):
            self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=int)
            self.name = AddressableAttribute(localAddress='name', parent=self, value=None, valueType=str)
            self.maxChargingCurrent = AddressableAttribute(localAddress='maxChargingCurrent', parent=self, value=None, valueType=str)
            self.minSOC_pct = AddressableAttribute(localAddress='minSOC_pct', parent=self, value=None, valueType=int)
            self.targetSOC_pct = AddressableAttribute(localAddress='targetSOC_pct', parent=self, value=None, valueType=int)
            self.timers = AddressableDict(localAddress='timers', parent=self)
            self.preferredChargingTimes = AddressableDict(localAddress='preferredChargingTimes', parent=self)
            self.options = None
            super().__init__(localAddress=None, parent=parent)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):  # noqa: C901
            LOG.debug('Update charging profile from dict')

            if 'id' in fromDict:
                self.id.fromDict(fromDict, 'id')
                self.localAddress = str(self.id.value)
            else:
                LOG.error('Charging Proile is missing id attribute')

            self.name.fromDict(fromDict, 'name')
            self.maxChargingCurrent.fromDict(fromDict, 'maxChargingCurrent')
            self.minSOC_pct.fromDict(fromDict, 'minSOC_pct')
            self.targetSOC_pct.fromDict(fromDict, 'targetSOC_pct')

            if 'options' in fromDict and fromDict['options'] is not None:
                if self.options is not None and self.options.enabled:
                    self.options.update(fromDict=fromDict['options'])
                else:
                    self.options = ChargingProfiles.ChargingProfile.Options(fromDict=fromDict['options'], parent=self)

            if 'timers' in fromDict and fromDict['timers'] is not None:
                for chargingProfileTimerDict in fromDict['timers']:
                    if 'id' in chargingProfileTimerDict:
                        if chargingProfileTimerDict['id'] in self.timers:
                            self.timers[chargingProfileTimerDict['id']].update(fromDict=chargingProfileTimerDict)
                        else:
                            self.timers[chargingProfileTimerDict['id']] = Timer(
                                fromDict=chargingProfileTimerDict, parent=self.timers)
                for timerId in [timerId for timerId in self.timers.keys()
                                if timerId not in [timer['id']
                                for timer in fromDict['timers'] if 'id' in timer]]:
                    del self.timers[timerId]
            else:
                self.timers.clear()
                self.timers.enabled = False

            if 'preferredChargingTimes' in fromDict and fromDict['preferredChargingTimes'] is not None:
                for preferredChargingTimesDict in fromDict['preferredChargingTimes']:
                    if 'id' in preferredChargingTimesDict:
                        if preferredChargingTimesDict['id'] in self.preferredChargingTimes:
                            self.preferredChargingTimes[preferredChargingTimesDict['id']].update(fromDict=preferredChargingTimesDict)
                        else:
                            self.preferredChargingTimes[preferredChargingTimesDict['id']] = ChargingProfiles.ChargingProfile.PreferredTime(
                                fromDict=preferredChargingTimesDict, parent=self.preferredChargingTimes)
                for timeId in [timeId for timeId in self.preferredChargingTimes.keys()
                               if timeId not in [timer['id']
                               for timer in fromDict['timers'] if 'id' in timer]]:
                    del self.preferredChargingTimes[timeId]
            else:
                self.preferredChargingTimes.clear()
                self.preferredChargingTimes.enabled = False

            for key, value in {key: value for key, value in fromDict.items() if key not in ['id', 'name', 'maxChargingCurrent', 'minSOC_pct', 'targetSOC_pct',
                                                                                            'timers', 'preferredChargingTimes', 'options']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            string = ''
            if self.id.enabled:
                string += f'Profile: {self.id.value}'
            if self.name.enabled:
                string += f' - {self.name.value}'
            if self.options is not None and self.options.enabled:
                string += f'\nOptions: {self.options}'
            if self.timers.enabled:
                string += f'\nTimers: {len(self.timers)} items'
                for timer in self.timers.values():
                    string += ''.join(['\n\t' + line for line in str(timer).splitlines(True)])
            if self.preferredChargingTimes.enabled:
                string += f'\nPreferred Times: {len(self.preferredChargingTimes)} items'
                for preferredTime in self.preferredChargingTimes.values():
                    string += ''.join(['\n\t' + line for line in str(preferredTime).splitlines(True)])
            return string

        class PreferredTime(AddressableObject):
            def __init__(
                self,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress=None, parent=parent)
                self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=int)
                self.preferredTimeEnabled = AddressableAttribute(localAddress='enabled', parent=self, value=None, valueType=bool)
                self.startTime = AddressableAttribute(localAddress='startTime', parent=self, value=None, valueType=time)
                self.endTime = AddressableAttribute(localAddress='endTime', parent=self, value=None, valueType=time)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Update preferred time from dict')

                if 'id' in fromDict:
                    self.id.fromDict(fromDict, 'id')
                    self.localAddress = str(self.id.value)
                else:
                    LOG.error('Preferred time is missing id attribute')

                self.preferredTimeEnabled.fromDict(fromDict, 'enabled')
                self.startTime.fromDict(fromDict, 'startTime')
                self.endTime.fromDict(fromDict, 'endTime')

                for key, value in {key: value for key, value in fromDict.items()
                                   if key not in ['id', 'enabled', 'startTime', 'endTime']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                string = ''
                if self.id.enabled:
                    string += f'{self.id.value}:'
                if self.preferredTimeEnabled.enabled:
                    string += f' Enabled: {self.preferredTimeEnabled.value}'
                if self.startTime.enabled:
                    string += f' Start: {self.startTime.value}'
                if self.endTime.enabled:
                    string += f' End: {self.endTime.value}'
                return string

        class Options(AddressableObject):
            def __init__(
                self,
                parent,
                fromDict=None,
            ):
                super().__init__(localAddress='options', parent=parent)
                self.id = AddressableAttribute(localAddress='id', parent=self, value=None, valueType=int)
                self.autoUnlockPlugWhenCharged = AddressableAttribute(localAddress='autoUnlockPlugWhenCharged', value=None, parent=self,
                                                                      valueType=UnlockPlugState)
                if fromDict is not None:
                    self.update(fromDict)

            def update(self, fromDict):
                LOG.debug('Update preferred time from dict')

                self.autoUnlockPlugWhenCharged.fromDict(fromDict, 'autoUnlockPlugWhenCharged')

                for key, value in {key: value for key, value in fromDict.items() if key not in ['autoUnlockPlugWhenCharged']}.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

            def __str__(self):
                string = ''
                if self.autoUnlockPlugWhenCharged.enabled:
                    string += f'\n\tAuto Unlock When Charged: {self.autoUnlockPlugWhenCharged.value.value}'
                return string
