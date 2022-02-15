import logging
import json
import requests

from weconnect.addressable import AddressableObject, ChangeableAttribute
from weconnect.elements.control_operation import ControlOperation
from weconnect.elements.charging_settings import ChargingSettings
from weconnect.elements.climatization_settings import ClimatizationSettings
from weconnect.elements.error import Error
from weconnect.errors import ControlError, SetterError
from weconnect.util import celsiusToKelvin, farenheitToKelvin
from weconnect.domain import Domain

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
                            localAddress='climatisation', parent=self, value=ControlOperation.NONE, valueType=(ControlOperation, float),
                            valueSetter=self.__setClimatizationControlChange)
                elif isinstance(status, ChargingSettings):
                    if self.chargingControl is None:
                        self.chargingControl = ChangeableAttribute(
                            localAddress='charging', parent=self, value=ControlOperation.NONE, valueType=ControlOperation,
                            valueSetter=self.__setChargingControlChange)

    def __setClimatizationControlChange(self, value):  # noqa: C901
        if isinstance(value, ControlOperation):
            if value not in [ControlOperation.START, ControlOperation.STOP]:
                raise ControlError('Could not control climatisation, control operation %s cannot be executed', value)
            control = value
            temperature = None
        elif isinstance(value, (int, float)):
            control = ControlOperation.START
            temperature = float(value)
        else:
            raise ControlError('Could not control climatisation, control argument %s cannot be understood', value)

        url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/climatisation/{control.value}'

        settingsDict = dict()
        if control == ControlOperation.START:
            if 'climatisation' not in self.vehicle.domains and 'climatisationSettings' not in self.vehicle.domains['climatisation']:
                raise ControlError('Could not control climatisation, there are no climatisationSettings for the vehicle available.')
            climatizationSettings = self.vehicle.domains['climatisation']['climatisationSettings']
            for child in climatizationSettings.getLeafChildren():
                if isinstance(child, ChangeableAttribute):
                    settingsDict[child.getLocalAddress()] = child.value
            if temperature is not None:
                if 'targetTemperature_C' in settingsDict:
                    settingsDict['targetTemperature_C'] = temperature
                settingsDict['targetTemperature_K'] = celsiusToKelvin(temperature)
            elif 'targetTemperature_K' not in settingsDict:
                if 'targetTemperature_C' in settingsDict:
                    settingsDict['targetTemperature_K'] = celsiusToKelvin(settingsDict['targetTemperature_C'])
                elif 'targetTemperature_F' in settingsDict:
                    settingsDict['targetTemperature_K'] = farenheitToKelvin(settingsDict['targetTemperature_F'])
                else:
                    settingsDict['targetTemperature_K'] = celsiusToKelvin(20.5)

        data = json.dumps(settingsDict)
        controlResponse = self.vehicle.weConnect.session.post(url, data=data, allow_redirects=True)
        if controlResponse.status_code != requests.codes['ok']:
            errorDict = controlResponse.json()
            if errorDict is not None and 'error' in errorDict:
                error = Error(localAddress='error', parent=self, fromDict=errorDict['error'])
                if error is not None:
                    message = ''
                    if error.message.enabled and error.message.value is not None:
                        message += error.message.value
                    if error.info.enabled and error.info.value is not None:
                        message += ' - ' + error.info.value
                    if error.retry.enabled and error.retry.value is not None:
                        if error.retry.value:
                            message += ' - Please retry in a moment'
                        else:
                            message += ' - No retry possible'
                    raise SetterError(f'Could not control climatisation ({message})')
                else:
                    raise SetterError(f'Could not control climatisation ({controlResponse.status_code})')
            raise SetterError(f'Could not control climatisation ({controlResponse.status_code})')
        responseDict = controlResponse.json()
        if 'data' in responseDict and 'requestID' in responseDict['data']:
            if self.vehicle.requestTracker is not None:
                self.vehicle.requestTracker.trackRequest(responseDict['data']['requestID'], Domain.CLIMATISATION, 20, 120)

    def __setChargingControlChange(self, value):  # noqa: C901
        if value in [ControlOperation.START, ControlOperation.STOP]:
            url = f'https://mobileapi.apps.emea.vwapps.io/vehicles/{self.vehicle.vin.value}/charging/{value.value}'

            controlResponse = self.vehicle.weConnect.session.post(url, data='{}', allow_redirects=True)
            if controlResponse.status_code != requests.codes['ok']:
                errorDict = controlResponse.json()
                if errorDict is not None and 'error' in errorDict:
                    error = Error(localAddress='error', parent=self, fromDict=errorDict['error'])
                    if error is not None:
                        message = ''
                        if error.message.enabled and error.message.value is not None:
                            message += error.message.value
                        if error.info.enabled and error.info.value is not None:
                            message += ' - ' + error.info.value
                        if error.retry.enabled and error.retry.value is not None:
                            if error.retry.value:
                                message += ' - Please retry in a moment'
                            else:
                                message += ' - No retry possible'
                        raise SetterError(f'Could not control charging ({message})')
                    else:
                        raise SetterError(f'Could not control charging ({controlResponse.status_code})')
                raise SetterError(f'Could not control charging ({controlResponse.status_code})')
            responseDict = controlResponse.json()
            if 'data' in responseDict and 'requestID' in responseDict['data']:
                if self.vehicle.requestTracker is not None:
                    self.vehicle.requestTracker.trackRequest(responseDict['data']['requestID'], Domain.CHARGING, 20, 120)
