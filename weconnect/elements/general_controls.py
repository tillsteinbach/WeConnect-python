import re
import logging
import requests

from weconnect.addressable import AddressableObject, ChangeableAttribute
from weconnect.errors import ControlError, SetterError

LOG = logging.getLogger("weconnect")


class GeneralControls(AddressableObject):
    def __init__(
        self,
        localAddress,
        parent,
    ):
        super().__init__(localAddress=localAddress, parent=parent)
        if self.parent.spin is not None:
            self.spinControl = ChangeableAttribute(localAddress='spin', parent=self, value='', valueType=str, valueSetter=self.__setSPINControlChange,
                                                   valueGetter=self.__getSPINControlChange)
        else:
            self.spinControl = None

    def __setSPINControlChange(self, value):  # noqa: C901
        if value is None:
            self.parent.spin = value
            return
        elif value == 'None' or value == '':
            self.parent.spin = None
            return
        elif not re.match(r"^\d{4}$", value):
            raise ControlError(f'S-PIN {value} cannot be set/verified, needs to be 4 digits')

        url = 'https://emea.bff.cariad.digital/vehicle/v1/spin/verify'

        data = {}
        data['spin'] = value
        controlResponse = self.parent.session.post(url, json=data, allow_redirects=True)
        if controlResponse.status_code != requests.codes['no_content']:
            dataDict = controlResponse.json()
            if dataDict is not None and 'data' in dataDict:
                errorDict = dataDict['data']
                print(errorDict)
                if errorDict is not None and 'error' in errorDict:
                    errormessage = f'Error: {errorDict["error"]["errorType"]}, S-PIN State: {errorDict["error"]["spinState"]}'
                    if errorDict["error"]["remainingTries"] > 0:
                        errormessage += f', Remaining tries: {errorDict["error"]["remainingTries"]}'
                    if errorDict["error"]["spinLockedWaitingTime"] > 0:
                        errormessage += f', Locked waiting time: {errorDict["error"]["spinLockedWaitingTime"]}'
                    raise SetterError(errormessage)
        self.parent.spin = value

    def __getSPINControlChange(self):
        return 'For security reasons the S-PIN cannot be read out'
