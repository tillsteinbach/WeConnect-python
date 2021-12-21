import logging
import json
import requests

from weconnect.addressable import AddressableObject, ChangeableAttribute, AddressableLeaf
from weconnect.elements.control_operation import ControlOperation
from weconnect.elements.charging_settings import ChargingSettings
from weconnect.elements.climatization_settings import ClimatizationSettings
from weconnect.errors import ControlError, SetterError
from weconnect.util import celsiusToKelvin, farenheitToKelvin

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
        for domain in self.vehicle.domains.values():
            for status in domain.values():
                if isinstance(status, ClimatizationSettings):
                    if self.climatizationControl is None:
                        self.climatizationControl = ChangeableAttribute(
                            localAddress='climatisation', parent=self, value=ControlOperation.NONE, valueType=ControlOperation)
                        self.climatizationControl.addObserver(
                            self.__onClimatizationControlChange, AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                            priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)
                elif isinstance(status, ChargingSettings):
                    if self.chargingControl is None:
                        self.chargingControl = ChangeableAttribute(
                            localAddress='charging', parent=self, value=ControlOperation.NONE, valueType=ControlOperation)
                        self.chargingControl.addObserver(
                            self.__onChargingControlChange, AddressableLeaf.ObserverEvent.VALUE_CHANGED, priority=AddressableLeaf.ObserverPriority.INTERNAL_MID)

    def __onClimatizationControlChange(self, element, flags):  # noqa: C901
        if flags & AddressableLeaf.ObserverEvent.VALUE_CHANGED:
            if element.value in [ControlOperation.START, ControlOperation.STOP]:
                url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/climatisation/{element.value.value}'

                settingsDict = dict()
                if element.value == ControlOperation.START:
                    if 'climatisation' not in self.vehicle.domains and 'climatisationSettings' not in self.vehicle.domains['climatisation']:
                        raise ControlError(
                            'Could not control climatisation, there are no climatisationSettings for the vehicle available.')
                    climatizationSettings = self.vehicle.domains['climatisation']['climatisationSettings']
                    for child in climatizationSettings.getLeafChildren():
                        if isinstance(child, ChangeableAttribute):
                            settingsDict[child.getLocalAddress()] = child.value
                        if 'targetTemperature_K' not in settingsDict:
                            if 'targetTemperature_C' in settingsDict:
                                settingsDict['targetTemperature_K'] = celsiusToKelvin(settingsDict['targetTemperature_C'])
                            elif 'targetTemperature_F' in settingsDict:
                                settingsDict['targetTemperature_K'] = farenheitToKelvin(settingsDict['targetTemperature_F'])
                            else:
                                settingsDict['targetTemperature_K'] = celsiusToKelvin(20.5)

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
