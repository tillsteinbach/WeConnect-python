import logging
import json
import requests

from weconnect.addressable import AddressableObject, ChangeableAttribute, AddressableLeaf
from weconnect.elements.control_operation import ControlOperation
from weconnect.elements.charging_settings import ChargingSettings
from weconnect.elements.climatization_settings import ClimatizationSettings
from weconnect.errors import ControlError, SetterError

LOG = logging.getLogger("weconnect")


class Controls(AddressableObject):
    def __init__(
        self,
        localAddress,
        vehicle,
        parent,
    ):
        self.vehicle = vehicle
        super().__init__(localAddress=localAddress, parent=parent)
        self.update()
        self.climatizationControl = None
        self.chargingControl = None

    def update(self):
        for status in self.vehicle.statuses.values():
            if isinstance(status, ClimatizationSettings):
                if self.climatizationControl is None:
                    self.climatizationControl = ChangeableAttribute(
                        localAddress='climatization', parent=self, value=ControlOperation.NONE, valueType=ControlOperation)
                    self.climatizationControl.addObserver(
                        self.__onClimatizationControlChange, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                        priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
            elif isinstance(status, ChargingSettings):
                if self.chargingControl is None:
                    self.chargingControl = ChangeableAttribute(
                        localAddress='charging', parent=self, value=ControlOperation.NONE, valueType=ControlOperation)
                    self.chargingControl.addObserver(
                        self.__onChargingControlChange, AddressableLeaf.ObserverEvent.VALUE_CHANGED, priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def __onClimatizationControlChange(self, element, flags):
        if flags & AddressableLeaf.ObserverEvent.VALUE_CHANGED:
            if element.value in [ControlOperation.START, ControlOperation.STOP]:
                url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/climatisation/{element.value.value}'

                settingsDict = dict()
                if element.value == ControlOperation.START:
                    if 'climatisationSettings' not in self.vehicle.statuses:
                        raise ControlError(
                            'Could not control climatization, there are no climatisationSettings for the vehicle available.')
                    climatizationSettings = self.vehicle.statuses['climatisationSettings']
                    for child in climatizationSettings.getLeafChildren():
                        if isinstance(child, ChangeableAttribute):
                            settingsDict[child.getLocalAddress()] = child.value

                data = json.dumps(settingsDict)
                controlResponse = self.vehicle.weConnect.session.post(url, data=data, allow_redirects=True)
                if controlResponse.status_code != requests.codes['ok']:
                    raise SetterError(f'Could not set value ({controlResponse.status_code})')
                # Trigger one update for the vehicle status to show result
                self.vehicle.updateStatus(force=True)

    def __onChargingControlChange(self, element, flags):
        if flags & AddressableLeaf.ObserverEvent.VALUE_CHANGED:
            if element.value in [ControlOperation.START, ControlOperation.STOP]:
                url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/charging/{element.value.value}'

                controlResponse = self.vehicle.weConnect.session.post(url, data='{}', allow_redirects=True)
                if controlResponse.status_code != requests.codes['ok']:
                    raise SetterError(f'Could not set value ({controlResponse.status_code})')
                # Trigger one update for the vehicle status to show result
                self.vehicle.updateStatus(force=True)
