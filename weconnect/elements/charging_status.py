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
            localAddress='chargePower_kW', value=None, parent=self, valueType=int)
        self.chargeRate_kmph = AddressableAttribute(
            localAddress='chargeRate_kmph', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging status from dict')

        if 'remainingChargingTimeToComplete_min' in fromDict:
            self.remainingChargingTimeToComplete_min \
                .setValueWithCarTime(int(fromDict['remainingChargingTimeToComplete_min']), lastUpdateFromCar=None,
                                     fromServer=True)
        else:
            self.remainingChargingTimeToComplete_min.enabled = False

        if 'chargingState' in fromDict and fromDict['chargingState']:
            try:
                self.chargingState.setValueWithCarTime(ChargingStatus.ChargingState(fromDict['chargingState']),
                                                       lastUpdateFromCar=None)
            except ValueError:
                self.chargingState.setValueWithCarTime(
                    ChargingStatus.ChargingState.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported chargingState: %s was provided,'
                            ' please report this as a bug', fromDict['chargingState'])
        else:
            self.chargingState.enabled = False

        if 'chargeMode' in fromDict and fromDict['chargeMode']:
            try:
                self.chargeMode.setValueWithCarTime(ChargingStatus.ChargeMode(fromDict['chargeMode']), lastUpdateFromCar=None)
            except ValueError:
                self.chargeMode.setValueWithCarTime(
                    ChargingStatus.ChargeMode.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported chargeMode: %s was provided,'
                            ' please report this as a bug', fromDict['chargeMode'])
        else:
            self.chargeMode.enabled = False

        if 'chargePower_kW' in fromDict:
            self.chargePower_kW.setValueWithCarTime(
                int(fromDict['chargePower_kW']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.chargePower_kW.enabled = False

        if 'chargeRate_kmph' in fromDict:
            self.chargeRate_kmph.setValueWithCarTime(
                int(fromDict['chargeRate_kmph']), lastUpdateFromCar=None, fromServer=True)
        else:
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
