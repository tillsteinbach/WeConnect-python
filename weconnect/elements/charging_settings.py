import logging

from weconnect.addressable import AddressableLeaf, ChangeableAttribute
from weconnect.elements.generic_settings import GenericSettings
from weconnect.elements.enums import UnlockPlugState, MaximumChargeCurrent

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
            localAddress='maxChargeCurrentAC', parent=self, value=None, valueType=MaximumChargeCurrent)
        self.maxChargeCurrentAC_A = ChangeableAttribute(
            localAddress='maxChargeCurrentAC_A', parent=self, value=None, valueType=int)
        self.autoUnlockPlugWhenCharged = ChangeableAttribute(localAddress='autoUnlockPlugWhenCharged', value=None,
                                                             parent=self, valueType=UnlockPlugState)
        self.autoUnlockPlugWhenChargedAC = ChangeableAttribute(localAddress='autoUnlockPlugWhenChargedAC', value=None,
                                                               parent=self, valueType=UnlockPlugState)
        self.targetSOC_pct = ChangeableAttribute(localAddress='targetSOC_pct', value=None, parent=self, valueType=int)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

        self.maxChargeCurrentAC.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.maxChargeCurrentAC_A.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                              priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.autoUnlockPlugWhenCharged.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                                   priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.autoUnlockPlugWhenChargedAC.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                                     priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
        self.targetSOC_pct.addObserver(self.valueChanged, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                       priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update Charging settings from dict')

        if 'value' in fromDict:
            self.maxChargeCurrentAC.fromDict(fromDict['value'], 'maxChargeCurrentAC')
            self.maxChargeCurrentAC_A.fromDict(fromDict['value'], 'maxChargeCurrentAC_A')
            self.autoUnlockPlugWhenCharged.fromDict(fromDict['value'], 'autoUnlockPlugWhenCharged')
            self.autoUnlockPlugWhenChargedAC.fromDict(fromDict['value'], 'autoUnlockPlugWhenChargedAC')
            self.targetSOC_pct.fromDict(fromDict['value'], 'targetSOC_pct')
        else:
            self.maxChargeCurrentAC.enabled = False
            self.maxChargeCurrentAC_A.enabled = False
            self.autoUnlockPlugWhenCharged.enabled = False
            self.autoUnlockPlugWhenChargedAC.enabled = False
            self.targetSOC_pct.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'maxChargeCurrentAC',
                                                                'maxChargeCurrentAC_A',
                                                                'autoUnlockPlugWhenCharged',
                                                                'autoUnlockPlugWhenChargedAC',
                                                                'targetSOC_pct'
                                                            ]))

    def __str__(self):
        string = super().__str__()
        if self.maxChargeCurrentAC.enabled:
            string += f'\n\tMaximum Charge Current AC: {self.maxChargeCurrentAC.value.value}'  # pylint: disable=no-member # this is a fales positive
        if self.maxChargeCurrentAC_A.enabled:
            string += f'\n\tMaximum Charge Current AC: {self.maxChargeCurrentAC_A.value}'
        if self.autoUnlockPlugWhenCharged.enabled:
            string += f'\n\tAuto Unlock When Charged: {self.autoUnlockPlugWhenCharged.value.value}'  # pylint: disable=no-member # this is a fales positive
        if self.autoUnlockPlugWhenChargedAC.enabled:
            string += f'\n\tAuto Unlock When Charged AC: {self.autoUnlockPlugWhenChargedAC.value.value}'  # pylint: disable=no-member # this is a fales positive
        if self.targetSOC_pct.enabled:
            string += f'\n\tTarget SoC: {self.targetSOC_pct.value} %'
        return string
