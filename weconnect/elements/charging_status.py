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
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):  # noqa: C901
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging status from dict')

        if 'value' in fromDict:
            if 'remainingChargingTimeToComplete_min' in fromDict['value']:
                self.remainingChargingTimeToComplete_min \
                    .setValueWithCarTime(int(fromDict['value']['remainingChargingTimeToComplete_min']), lastUpdateFromCar=None,
                                         fromServer=True)
            else:
                self.remainingChargingTimeToComplete_min.enabled = False

            if 'chargingState' in fromDict['value'] and fromDict['value']['chargingState']:
                try:
                    self.chargingState.setValueWithCarTime(ChargingStatus.ChargingState(fromDict['value']['chargingState']),
                                                           lastUpdateFromCar=None)
                except ValueError:
                    self.chargingState.setValueWithCarTime(
                        ChargingStatus.ChargingState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported chargingState: %s was provided,'
                                ' please report this as a bug', fromDict['value']['chargingState'])
            else:
                self.chargingState.enabled = False

            if 'chargeMode' in fromDict['value'] and fromDict['value']['chargeMode']:
                try:
                    self.chargeMode.setValueWithCarTime(ChargingStatus.ChargeMode(fromDict['value']['chargeMode']), lastUpdateFromCar=None)
                except ValueError:
                    self.chargeMode.setValueWithCarTime(
                        ChargingStatus.ChargeMode.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported chargeMode: %s was provided,'
                                ' please report this as a bug', fromDict['value']['chargeMode'])
            else:
                self.chargeMode.enabled = False

            if 'chargePower_kW' in fromDict['value']:
                self.chargePower_kW.setValueWithCarTime(
                    float(fromDict['value']['chargePower_kW']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.chargePower_kW.enabled = False

            if 'chargeRate_kmph' in fromDict['value']:
                self.chargeRate_kmph.setValueWithCarTime(
                    float(fromDict['value']['chargeRate_kmph']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.chargeRate_kmph.enabled = False
        else:
            self.remainingChargingTimeToComplete_min.enabled = False
            self.chargingState.enabled = False
            self.chargeMode.enabled = False
            self.chargePower_kW.enabled = False
            self.chargeRate_kmph.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'remainingChargingTimeToComplete_min',
                                                                'chargingState',
                                                                'chargeMode',
                                                                'chargePower_kW',
                                                                'chargeRate_kmph'
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
        UNKNOWN = 'unknown charging state'

    class ChargeMode(Enum,):
        MANUAL = 'manual'
        INVALID = 'invalid'
        OFF = 'off'
        TIMER = 'timer'
        ONLY_OWN_CURRENT = 'onlyOwnCurrent'
        PREFERRED_CHARGING_TIMES = 'preferredChargingTimes'
        TIMER_CHARGING_WITH_CLIMATISATION = 'timerChargingWithClimatisation'
        UNKNOWN = 'unknown charge mode'
