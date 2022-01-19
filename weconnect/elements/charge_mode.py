from enum import Enum
from typing import List
import logging

from weconnect.addressable import AddressableAttribute, AddressableObject
from weconnect.elements.generic_status import GenericStatus

LOG = logging.getLogger("weconnect")


class ChargeMode(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.preferredChargeMode = AddressableAttribute(localAddress='preferredChargeMode', value=None, parent=self,
                                                        valueType=ChargeMode.ChargeModeEnum)
        self.availableChargeModes = ChargeMode.ChargeModeList(localAddress='availableChargeModes', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update ChargeMode status from dict')

        if 'value' in fromDict:
            self.preferredChargeMode.fromDict(fromDict['value'], 'preferredChargeMode')

            if 'availableChargeModes' in fromDict['value']:
                if self.availableChargeModes is None:
                    self.availableChargeModes = ChargeMode.ChargeModeList(localAddress='availableChargeModes', parent=self,
                                                                          fromDict=fromDict['value']['availableChargeModes'])
                else:
                    self.availableChargeModes.update(fromDict=fromDict['value']['availableChargeModes'])
            elif self.availableChargeModes is not None:
                self.availableChargeModes.clear()
                self.availableChargeModes.enabled = False
        else:
            self.preferredChargeMode.enabled = False
            self.availableChargeModes.clear()
            self.availableChargeModes.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['preferredChargeMode', 'availableChargeModes']))

    def __str__(self):
        string = super().__str__()
        if self.preferredChargeMode is not None and self.preferredChargeMode.enabled:
            string += f'\n\tPreferred charge mode: {self.preferredChargeMode.value.value}'  # pylint: disable=no-member
        if self.availableChargeModes is not None and self.availableChargeModes.enabled:
            string += f'\n\tAvailable charge modes: {self.availableChargeModes}'
        return string

    class ChargeModeEnum(Enum,):
        MANUAL = 'manual'
        TIMER = 'timer'
        ONLY_OWN_CURRENT = 'onlyOwnCurrent'
        PREFERRED_CHARGING_TIMES = 'preferredChargingTimes'
        TIMER_CHARGING_WITH_CLIMATISATION = 'timerChargingWithClimatisation'
        INVALID = 'invalid'
        UNKNOWN = 'unknown charge mode'

    class ChargeModeList(AddressableObject, List):
        def update(self, fromDict):
            LOG.debug('Update timer from dict')

            self.clear()
            if fromDict is not None and len(fromDict) > 0:
                for mode in fromDict:
                    try:
                        self.append(ChargeMode.ChargeModeEnum(mode))
                    except ValueError:
                        self.append(ChargeMode.ChargeModeEnum.UNKNOWN)
                        LOG.warning('An unsupported mode: %s was provided, please report this as a bug', mode)
                if not self.enabled:
                    self.enabled = True
            elif self.enabled:
                self.enabled = False

        def __str__(self):
            return '[' + ', '.join([item.value for item in self]) + ']'
