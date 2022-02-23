from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from enum import Enum
import logging
from datetime import datetime, timedelta, timezone

if TYPE_CHECKING:
    from weconnect.elements.vehicle import Vehicle

from weconnect.util import robustTimeParse
from weconnect.addressable import AddressableObject, AddressableAttribute, AddressableList, AddressableDict
from weconnect.elements.control_operation import ControlOperation
from weconnect.elements.error import Error

LOG: logging.Logger = logging.getLogger("weconnect")


class GenericStatus(AddressableObject):
    def __init__(
        self,
        vehicle: Vehicle,
        parent: AddressableDict[str, GenericStatus],
        statusId: str,
        fromDict: Optional[Dict[str, Any]] = None,
        fixAPI: bool = True,
    ) -> None:
        self.vehicle: Vehicle = vehicle
        self.fixAPI: bool = fixAPI
        super().__init__(localAddress=statusId, parent=parent)
        self.id: str = statusId
        self.carCapturedTimestamp: AddressableAttribute[datetime] = AddressableAttribute(
            localAddress='carCapturedTimestamp', parent=self, value=None, valueType=datetime)
        self.error: Error = Error(localAddress='error', parent=self)
        self.requests: AddressableDict[GenericStatus.Request] = AddressableDict(localAddress='request', parent=self)

        if fromDict is not None:
            self.update(fromDict=fromDict)

    def hasError(self) -> bool:
        return self.error.enabled

    def hasRequests(self) -> bool:
        return len(self.requests) > 0

    def update(self, fromDict: Dict[str, Any], ignoreAttributes: Optional[List[str]] = None):  # noqa: C901
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update status from dict')

        if 'value' in fromDict:
            if 'carCapturedTimestamp' in fromDict['value']:
                carCapturedTimestamp: Optional[datetime] = robustTimeParse(fromDict['value']['carCapturedTimestamp'])
                if self.fixAPI and carCapturedTimestamp is not None:
                    # Looks like for some cars the calculation of the carCapturedTimestamp does not account for the timezone
                    # Unfortunatly it is unknown what the timezone of the car is. So the best we can do is substract 30
                    # minutes as long as the timestamp is in the future. This will create false results when the query
                    # interval is large
                    fixed: timedelta = timedelta(hours=0, minutes=0)
                    while carCapturedTimestamp > datetime.utcnow().replace(tzinfo=timezone.utc):
                        carCapturedTimestamp -= timedelta(hours=0, minutes=30)
                        fixed -= timedelta(hours=0, minutes=30)
                    if fixed > timedelta(hours=0, minutes=0):
                        LOG.warning('%s: Attribute carCapturedTimestamp was in the future. Substracted %s to fix this.'
                                    ' This is a problem of the weconnect API and might be fixed in the future',
                                    self.getGlobalAddress(), fixed)
                    if carCapturedTimestamp == datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0,
                                                        tzinfo=timezone.utc):
                        carCapturedTimestamp = None

                self.carCapturedTimestamp.setValueWithCarTime(carCapturedTimestamp, lastUpdateFromCar=None, fromServer=True)
                if self.carCapturedTimestamp.value is None:
                    self.carCapturedTimestamp.enabled = False
            else:
                self.carCapturedTimestamp.setValueWithCarTime(None, fromServer=True)
                self.carCapturedTimestamp.enabled = False

            if isinstance(fromDict['value'], Dict):
                for key, value in {key: value for key, value in fromDict['value'].items()
                                   if key not in (['carCapturedTimestamp'] + ignoreAttributes)
                                   }.items():
                    LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)
        else:
            self.carCapturedTimestamp.setValueWithCarTime(None, fromServer=True)
            self.carCapturedTimestamp.enabled = False

        if 'error' in fromDict:
            self.error.update(fromDict['error'])
        else:
            self.error.reset()

        if 'requests' in fromDict:
            requestsToRemove = list(self.requests.keys())
            for request in fromDict['requests']:
                key = None
                if 'requestId' in request:
                    key = request['requestId']
                elif 'operation' in request:
                    key = request['operation']
                else:
                    key = "none"
                if key in self.requests:
                    self.requests[key].update(fromDict=request)
                    if key in requestsToRemove:
                        requestsToRemove.remove(key)
                else:
                    newRequest = GenericStatus.Request(localAddress=key, parent=self.requests, fromDict=request)
                    self.requests[key] = newRequest

            for requestKey in requestsToRemove:
                self.requests[requestKey].enabled = False
                del self.requests[requestKey]

        else:
            self.requests.clear()
            self.requests.enabled = False

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in (['value', 'error', 'requests'] + ['carCapturedTimestamp'] + ignoreAttributes)}.items():
            LOG.warning('%s: Unknown element %s with value %s', self.getGlobalAddress(), key, value)

    def __str__(self) -> str:
        returnString: str = f'[{self.id}]'
        if self.carCapturedTimestamp.enabled and self.carCapturedTimestamp.value is not None:
            returnString += f' (last captured {self.carCapturedTimestamp.value.isoformat()})'
        if self.error.enabled:
            returnString += '\n\tError: ' + ''.join(['\t' + line for line in str(self.error).splitlines(True)])
        for request in self.requests.values():
            returnString += f'\n\tRequest: {request}'
        return returnString

    class Request(AddressableObject):
        def __init__(
            self,
            localAddress: str,
            parent: AddressableList[GenericStatus.Request],
            fromDict: Dict[str, Any] = None,
        ) -> None:
            super().__init__(localAddress=localAddress, parent=parent)
            self.status: AddressableAttribute[GenericStatus.Request.Status] = AddressableAttribute(localAddress='status', parent=self,
                                                                                                   value=None, valueType=GenericStatus.Request.Status)
            self.operation: AddressableAttribute[ControlOperation] = AddressableAttribute(
                localAddress='operation', parent=self, value=None, valueType=ControlOperation)
            self.body: AddressableAttribute[str] = AddressableAttribute(localAddress='body', parent=self, value=None, valueType=str)
            self.group: AddressableAttribute[int] = AddressableAttribute(localAddress='group', parent=self, value=None, valueType=int)
            self.info: AddressableAttribute[str] = AddressableAttribute(localAddress='info', parent=self, value=None, valueType=str)
            self.requestId: AddressableAttribute[str] = AddressableAttribute(localAddress='requestId', parent=self, value=None, valueType=str)
            self.vcfRequestId: AddressableAttribute[str] = AddressableAttribute(localAddress='vcfRequestId', parent=self, value=None, valueType=str)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict: Dict[str, Any]) -> None:  # noqa: C901
            LOG.debug('Update Request from dict')
            self.status.fromDict(fromDict, 'status')
            self.operation.fromDict(fromDict, 'operation')
            self.body.fromDict(fromDict, 'body')
            self.group.fromDict(fromDict, 'group')
            self.info.fromDict(fromDict, 'info')
            self.requestId.fromDict(fromDict, 'requestId')
            self.vcfRequestId.fromDict(fromDict, 'vcfRequestId')

        def __str__(self) -> str:
            returnValue: str = ''
            if self.operation.enabled and self.operation.value is not None:
                returnValue += f'{self.operation.value.value} operation,'
            if self.status.enabled and self.status.value is not None:
                returnValue += f' status {self.status.value.value} '
            if self.info.enabled and self.info.value is not None:
                returnValue += f' information: {self.info.value}'
            if self.requestId.enabled and self.requestId.value is not None:
                returnValue += f' Request Id: {self.requestId.value}'
            return returnValue

        class Status(Enum,):
            SUCCESSFULL = 'successful'
            FAIL = 'fail'
            POLLING_TIMEOUT = 'polling_timeout'
            IN_PROGRESS = 'in_progress'
            QUEUED = 'queued'
            DELAYED = 'delayed'
            TIMEOUT = 'timeout'
            FAIL_VEHICLE_IS_OFFLINE = 'fail_vehicle_is_offline'
            FAIL_IGNITION_ON = 'fail_ignition_on'
            FAIL_BATTERY_LOW = 'fail_battery_low'
            FAIL_PLUG_ERROR = 'fail_plug_error'
            FAIL_CHARGE_PLUG_NOT_CONNECTED = 'fail_charge_plug_not_connected'
            FAIL_NO_EXTERNAL_POWER = 'fail_no_external_power'
            UNKNOWN = 'unknown status'
