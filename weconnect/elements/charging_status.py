from enum import Enum
import logging

from weconnect.addressable import AddressableAttribute
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class ChargingStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.remainingChargingTimeToComplete_min = AddressableAttribute(
            localAddress='remainingChargingTimeToComplete_min', parent=self, value=None, valueType=int)
        self.chargingState = AddressableAttribute(
            localAddress='chargingState', value=None, parent=self, valueType=ChargingStatus.ChargingState)
        self.chargeMode = AddressableAttribute(
            localAddress='chargeMode', value=None, parent=self, valueType=ChargingStatus.ChargeMode)
        self.chargePower_kW = AddressableAttribute(
            localAddress='chargePower_kW', value=None, parent=self, valueType=float)
        self.chargeRate_kmph = AddressableAttribute(
            localAddress='chargeRate_kmph', value=None, parent=self, valueType=float)
        self.chargeType = AddressableAttribute(localAddress='chargeType', value=None, parent=self, valueType=ChargingStatus.ChargeType)
        self.chargingSettings = AddressableAttribute(localAddress='chargingSettings', value=None, parent=self, valueType=str)
        self.chargingScenario = AddressableAttribute(localAddress='chargingScenario', value=None, parent=self, valueType=ChargingStatus.ChargingScenario)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):  # noqa: C901
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging status from dict')

        if 'value' in fromDict:
            self.remainingChargingTimeToComplete_min.fromDict(fromDict['value'], 'remainingChargingTimeToComplete_min')
            self.chargingState.fromDict(fromDict['value'], 'chargingState')
            self.chargeMode.fromDict(fromDict['value'], 'chargeMode')
            self.chargePower_kW.fromDict(fromDict['value'], 'chargePower_kW')
            if 'chargePower_kW' in fromDict['value']:
                chargePower_kW = float(fromDict['value']['chargePower_kW'])
                if self.fixAPI and chargePower_kW != 0 \
                        and self.chargingState.value in [ChargingStatus.ChargingState.OFF,
                                                         ChargingStatus.ChargingState.READY_FOR_CHARGING,
                                                         ChargingStatus.ChargingState.NOT_READY_FOR_CHARGING,
                                                         ChargingStatus.ChargingState.CHARGE_PURPOSE_REACHED_NOT_CONSERVATION_CHARGING,
                                                         ChargingStatus.ChargingState.ERROR]:
                    chargePower_kW = 0.0
                    LOG.debug('%s: Attribute chargePower_kW is %s while chargingState is %s. Setting 0 instead',
                              self.getGlobalAddress(), fromDict['value']['chargePower_kW'], self.chargingState.value)
                self.chargePower_kW.setValueWithCarTime(chargePower_kW, lastUpdateFromCar=None, fromServer=True)
            else:
                self.chargePower_kW.enabled = False
            if 'chargeRate_kmph' in fromDict['value']:
                chargeRate_kmph = float(fromDict['value']['chargeRate_kmph'])
                if self.fixAPI and chargeRate_kmph != 0 \
                        and self.chargingState.value in [ChargingStatus.ChargingState.OFF,
                                                         ChargingStatus.ChargingState.READY_FOR_CHARGING,
                                                         ChargingStatus.ChargingState.NOT_READY_FOR_CHARGING,
                                                         ChargingStatus.ChargingState.CHARGE_PURPOSE_REACHED_NOT_CONSERVATION_CHARGING,
                                                         ChargingStatus.ChargingState.ERROR]:
                    chargeRate_kmph = 0.0
                    LOG.debug('%s: Attribute chargeRate_kmph is %s while chargingState is %s. Setting 0 instead',
                              self.getGlobalAddress(), fromDict['value']['chargeRate_kmph'], self.chargingState.value)
                self.chargeRate_kmph.setValueWithCarTime(chargeRate_kmph, lastUpdateFromCar=None, fromServer=True)
            else:
                self.chargeRate_kmph.enabled = False
            self.chargeType.fromDict(fromDict['value'], 'chargeType')
            self.chargingSettings.fromDict(fromDict['value'], 'chargingSettings')
            self.chargingScenario.fromDict(fromDict['value'], 'chargingScenario')
        else:
            self.remainingChargingTimeToComplete_min.enabled = False
            self.chargingState.enabled = False
            self.chargeMode.enabled = False
            self.chargePower_kW.enabled = False
            self.chargeRate_kmph.enabled = False
            self.chargeType.enabled = False
            self.chargingSettings.enabled = False
            self.chargingScenario.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'remainingChargingTimeToComplete_min',
                                                                'chargingState',
                                                                'chargeMode',
                                                                'chargePower_kW',
                                                                'chargeRate_kmph',
                                                                'chargeType',
                                                                'chargingSettings',
                                                                'chargingScenario'
                                                            ]))

    def __str__(self):
        string = super().__str__()
        if self.chargingState.enabled:
            string += f'\n\tState: {self.chargingState.value.value}'  # pylint: disable=no-member
        if self.chargeMode.enabled:
            string += f'\n\tMode: {self.chargeMode.value.value}'  # pylint: disable=no-member
        if self.remainingChargingTimeToComplete_min.enabled:
            string += f'\n\tRemaining Charging Time: {self.remainingChargingTimeToComplete_min.value} minutes'
        if self.chargePower_kW.enabled:
            string += f'\n\tCharge Power: {self.chargePower_kW.value} kW'
        if self.chargeRate_kmph.enabled:
            string += f'\n\tCharge Rate: {self.chargeRate_kmph.value} km/h'
        if self.chargeType.enabled:
            string += f'\n\tCharge Type: {self.chargeType.value.value}'
        if self.chargingSettings.enabled:
            string += f'\n\tCharging Settings: {self.chargingSettings.value}'
        if self.chargingScenario.enabled:
            string += f'\n\tCharging Scenario: {self.chargingScenario.value}'
        return string

    class ChargingState(Enum,):
        OFF = 'off'
        READY_FOR_CHARGING = 'readyForCharging'
        NOT_READY_FOR_CHARGING = 'notReadyForCharging'
        CONSERVATION = 'conservation'
        CHARGE_PURPOSE_REACHED_NOT_CONSERVATION_CHARGING = 'chargePurposeReachedAndNotConservationCharging'
        CHARGE_PURPOSE_REACHED_CONSERVATION = 'chargePurposeReachedAndConservation'
        CHARGING = 'charging'
        ERROR = 'error'
        UNSUPPORTED = 'unsupported'
        DISCHARGING = 'discharging'
        UNKNOWN = 'unknown charging state'

    class ChargeMode(Enum,):
        MANUAL = 'manual'
        INVALID = 'invalid'
        OFF = 'off'
        TIMER = 'timer'
        ONLY_OWN_CURRENT = 'onlyOwnCurrent'
        PREFERRED_CHARGING_TIMES = 'preferredChargingTimes'
        TIMER_CHARGING_WITH_CLIMATISATION = 'timerChargingWithClimatisation'
        HOME_STORAGE_CHARGING = 'homeStorageCharging'
        IMMEDIATE_DISCHARGING = 'immediateDischarging'
        UNKNOWN = 'unknown charge mode'

    class ChargeType(Enum,):
        INVALID = 'invalid'
        OFF = 'off'
        AC = 'ac'
        DC = 'dc'
        UNSUPPORTED = 'unsupported'
        UNKNOWN = 'unknown charge type'

    class ChargingScenario(Enum,):
        OFF = 'off'
        IMMEDIATELY_CHARGING_ACTIVE = 'immediatelyChargingActive'
        IMMEDIATELY_CHARGING_FINISHED = 'immediatelyChargingFinished'
        CHARGING_TO_DEPARTURE_TIME_WAITING = 'chargingToDepartureTimeWaiting'
        CHARGING_TO_DEPARTURE_TIME_ACTIVE = 'chargingToDepartureTimeActive'
        OPTIMISED_CHARGING_FINISHED = 'optimisedChargingFinished'
        ERROR_CHARGING_SYSTEM = 'errorChargingSystem'
        UNKNOWN = 'unknown charging scenario'
