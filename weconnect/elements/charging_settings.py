import logging

from weconnect.addressable import AddressableLeaf, ChangeableAttribute
from weconnect.elements.generic_settings import GenericSettings
from weconnect.elements.control_operation import ControlInputEnum

LOG = logging.getLogger("weconnect")


class ChargingSettings(GenericSettings):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.maxChargeCurrentAC = ChangeableAttribute(
            localAddress='maxChargeCurrentAC', parent=self, value=None, valueType=ChargingSettings.MaximumChargeCurrent)
        self.autoUnlockPlugWhenCharged = ChangeableAttribute(localAddress='autoUnlockPlugWhenCharged', value=None,
                                                             parent=self, valueType=ChargingSettings.UnlockPlugState)
        self.targetSOC_pct = ChangeableAttribute(localAddress='targetSOC_pct', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

        self.maxChargeCurrentAC.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.autoUnlockPlugWhenCharged.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                                   priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.targetSOC_pct.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                       priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging settings from dict')

        if 'maxChargeCurrentAC' in fromDict and fromDict['maxChargeCurrentAC']:
            try:
                self.maxChargeCurrentAC.setValueWithCarTime(ChargingSettings.MaximumChargeCurrent(
                    fromDict['maxChargeCurrentAC']), lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.maxChargeCurrentAC.setValueWithCarTime(ChargingSettings.MaximumChargeCurrent.UNKNOWN,
                                                            lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported maxChargeCurrentAC: %s was provided,'
                            ' please report this as a bug', fromDict['maxChargeCurrentAC'])
        else:
            self.maxChargeCurrentAC.enabled = False

        if 'autoUnlockPlugWhenCharged' in fromDict and fromDict['autoUnlockPlugWhenCharged']:
            try:
                self.autoUnlockPlugWhenCharged.setValueWithCarTime(ChargingSettings.UnlockPlugState(
                    fromDict['autoUnlockPlugWhenCharged']), lastUpdateFromCar=None, fromServer=True)
            except ValueError:
                self.autoUnlockPlugWhenCharged.setValueWithCarTime(ChargingSettings.UnlockPlugState.UNKNOWN,
                                                                   lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported autoUnlockPlugWhenCharged: %s was provided,'
                            ' please report this as a bug', fromDict['autoUnlockPlugWhenCharged'])
        else:
            self.autoUnlockPlugWhenCharged.enabled = False

        if 'targetSOC_pct' in fromDict:
            self.targetSOC_pct.setValueWithCarTime(
                int(fromDict['targetSOC_pct']), lastUpdateFromCar=None, fromServer=True)
        else:
            self.targetSOC_pct.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'maxChargeCurrentAC',
                                                                'autoUnlockPlugWhenCharged',
                                                                'targetSOC_pct'
                                                            ]))

    def __str__(self):
        string = super().__str__()
        if self.maxChargeCurrentAC.enabled:
            string += f'\n\tMaximum Charge Current AC: {self.maxChargeCurrentAC.value.value}'  # pylint: disable=no-member # this is a fales positive
        if self.autoUnlockPlugWhenCharged.enabled:
            string += f'\n\tAuto Unlock When Charged: {self.autoUnlockPlugWhenCharged.value.value}'  # pylint: disable=no-member # this is a fales positive
        if self.targetSOC_pct.enabled:
            string += f'\n\tTarget SoC: {self.targetSOC_pct.value} %'
        return string

    class UnlockPlugState(ControlInputEnum,):
        OFF = 'off'
        ON = 'on'
        PERMANENT = 'permanent'
        UNKNOWN = 'unknown'

        @classmethod
        def allowedValues(cls):
            return [ChargingSettings.UnlockPlugState.OFF, ChargingSettings.UnlockPlugState.ON]

    class MaximumChargeCurrent(ControlInputEnum,):
        MAXIMUM = 'maximum'
        REDUCED = 'reduced'
        INVALID = 'invalid'
        UNKNOWN = 'unknown'

        @classmethod
        def allowedValues(cls):
            return [ChargingSettings.MaximumChargeCurrent.MAXIMUM, ChargingSettings.MaximumChargeCurrent.REDUCED]
