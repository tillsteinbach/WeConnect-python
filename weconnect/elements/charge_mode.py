from enum import Enum
import logging

from weconnect.addressable import AddressableAttribute
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
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update ChargeMode status from dict')

        if 'preferredChargeMode' in fromDict:
            try:
                self.preferredChargeMode.setValueWithCarTime(
                    ChargeMode.ChargeModeEnum(fromDict['preferredChargeMode']), lastUpdateFromCar=None,
                    fromServer=True)
            except ValueError:
                self.preferredChargeMode.setValueWithCarTime(ChargeMode.ChargeModeEnum.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                LOG.warning('An unsupported preferredChargeMode: %s was provided, please report this as a bug', fromDict['preferredChargeMode'])
        else:
            self.preferredChargeMode.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(
            ignoreAttributes + ['preferredChargeMode']))

    def __str__(self):
        string = super().__str__()
        if self.preferredChargeMode.enabled:
            string += f'\n\tPreferred charge mode: {self.preferredChargeMode.value.value}'  # pylint: disable=no-member
        return string

    class ChargeModeEnum(Enum,):
        MANUAL = 'manual'
        UNKNOWN = 'unknown charge mode'
