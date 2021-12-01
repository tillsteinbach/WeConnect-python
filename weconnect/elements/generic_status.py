from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from enum import Enum
import logging
from datetime import datetime, timedelta, timezone

if TYPE_CHECKING:
    from weconnect.elements.vehicle import Vehicle

from weconnect.util import robustTimeParse, toBool
from weconnect.addressable import AddressableObject, AddressableAttribute, AddressableList, AddressableDict
from weconnect.elements.control_operation import ControlOperation

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
        self.error: GenericStatus.StatusError = GenericStatus.StatusError(localAddress='error', parent=self)
        self.target: AddressableList[GenericStatus.Target] = AddressableList(localAddress='target', parent=self)

        if fromDict is not None:
            self.update(fromDict=fromDict)

    def update(self, fromDict: Dict[str, Any], ignoreAttributes: Optional[List[str]] = None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update status from dict')

        if 'carCapturedTimestamp' in fromDict:
            carCapturedTimestamp: Optional[datetime] = robustTimeParse(fromDict['carCapturedTimestamp'])
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
            self.carCapturedTimestamp.enabled = False

        for key, value in {key: value for key, value in fromDict.items()
                           if key not in (['carCapturedTimestamp'] + ignoreAttributes)
                           }.items():
            LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

    def updateError(self, fromDict: Dict[str, Any]) -> None:
        if fromDict is None:
            self.error.reset()
        else:
            self.error.update(fromDict)

    def updateTarget(self, fromDict: Optional[List[Any]]) -> None:
        if fromDict is None:
            self.target.clear()
            self.target.enabled = False
        else:
            for target in fromDict:
                self.target.append(GenericStatus.Target(localAddress=str(
                    len(self.target)), parent=self.target, fromDict=target))

    def __str__(self) -> str:
        returnString: str = f'[{self.id}]'
        if self.carCapturedTimestamp.enabled and self.carCapturedTimestamp.value is not None:
            returnString += f' (last captured {self.carCapturedTimestamp.value.isoformat()})'
        if self.error.enabled:
            returnString += f'\n\tError: {self.error}'
        for target in self.target:
            returnString += f'\n\tTarget: {target}'
        return returnString

    class Target(AddressableObject):
        def __init__(
            self,
            localAddress: str,
            parent: AddressableList[GenericStatus.Target],
            fromDict: Dict[str, Any] = None,
        ) -> None:
            super().__init__(localAddress=localAddress, parent=parent)
            self.status: AddressableAttribute[GenericStatus.Target.Status] = AddressableAttribute(localAddress='status', parent=self,
                                                                                                  value=None, valueType=GenericStatus.Target.Status)
            self.operation: AddressableAttribute[ControlOperation] = AddressableAttribute(
                localAddress='operation', parent=self, value=None, valueType=ControlOperation)
            self.body: AddressableAttribute[str] = AddressableAttribute(localAddress='body', parent=self, value=None, valueType=str)
            self.group: AddressableAttribute[int] = AddressableAttribute(localAddress='group', parent=self, value=None, valueType=int)
            self.info: AddressableAttribute[str] = AddressableAttribute(localAddress='info', parent=self, value=None, valueType=str)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict: Dict[str, Any]) -> None:
            LOG.debug('Update Status Target from dict')

            if 'status' in fromDict and fromDict['status']:
                try:
                    self.status.setValueWithCarTime(GenericStatus.Target.Status(
                        fromDict['status']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.status.setValueWithCarTime(GenericStatus.Target.Status.UNKNOWN,
                                                    lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported target status: %s was provided,'
                                ' please report this as a bug', fromDict['status'])
            else:
                self.status.enabled = False

            if 'operation' in fromDict and fromDict['operation']:
                try:
                    self.operation.setValueWithCarTime(ControlOperation(
                        fromDict['operation']), lastUpdateFromCar=None, fromServer=True)
                except ValueError:
                    self.operation.setValueWithCarTime(ControlOperation.UNKNOWN,
                                                       lastUpdateFromCar=None, fromServer=True)
                    LOG.warning('An unsupported target operation: %s was provided,'
                                ' please report this as a bug', fromDict['operation'])
            else:
                self.operation.enabled = False

            if 'body' in fromDict:
                self.body.setValueWithCarTime(str(fromDict['body']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.body.enabled = False

            if 'group' in fromDict:
                self.group.setValueWithCarTime(int(fromDict['group']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.group.enabled = False

            if 'info' in fromDict:
                self.info.setValueWithCarTime(fromDict['info'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.info.enabled = False

        def __str__(self) -> str:
            returnValue: str = ''
            if self.operation.enabled and self.operation.value is not None:
                returnValue += f'{self.operation.value.value} operation,'
            if self.status.enabled and self.status.value is not None:
                returnValue += f' status {self.status.value.value} '
            if self.info.enabled and self.info.value is not None:
                returnValue += f' information: {self.info.value}'
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
            UNKNOWN = 'unknown status'

    class StatusError(AddressableObject):
        def __init__(
            self,
            localAddress: str,
            parent: GenericStatus,
            fromDict: Dict[str, Any] = None,
        ) -> None:
            super().__init__(localAddress=localAddress, parent=parent)
            self.code: AddressableAttribute[int] = AddressableAttribute(localAddress='code', parent=self, value=None, valueType=int)
            self.message: AddressableAttribute[str] = AddressableAttribute(localAddress='message', parent=self, value=None, valueType=str)
            self.group: AddressableAttribute[int] = AddressableAttribute(localAddress='group', parent=self, value=None, valueType=int)
            self.info: AddressableAttribute[str] = AddressableAttribute(localAddress='info', parent=self, value=None, valueType=str)
            self.retry: AddressableAttribute[bool] = AddressableAttribute(localAddress='retry', parent=self, value=None, valueType=bool)

            if fromDict is not None:
                self.update(fromDict)

        def reset(self) -> None:
            self.code.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.code.enabled = False
            self.message.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.message.enabled = False
            self.group.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.group.enabled = False
            self.info.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.info.enabled = False
            self.retry.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
            self.retry.enabled = False
            self.enabled = False

        def update(self, fromDict: Dict[str, Any]) -> None:
            LOG.debug('Update Status Error from dict')

            if 'code' in fromDict:
                self.code.setValueWithCarTime(int(fromDict['code']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.code.enabled = False

            if 'message' in fromDict:
                self.message.setValueWithCarTime(fromDict['message'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.message.enabled = False

            if 'group' in fromDict:
                self.group.setValueWithCarTime(int(fromDict['group']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.code.enabled = False

            if 'info' in fromDict:
                self.info.setValueWithCarTime(fromDict['info'], lastUpdateFromCar=None, fromServer=True)
            else:
                self.info.enabled = False

            if 'retry' in fromDict:
                self.retry.setValueWithCarTime(toBool(fromDict['retry']), lastUpdateFromCar=None, fromServer=True)
            else:
                self.retry.enabled = False

            if not self.code.enabled and not self.message.enabled and not self.code.enabled and not self.info.enabled \
                    and not self.retry.enabled:
                self.enabled = False
            else:
                self.enabled = True

            for key, value in {key: value for key, value in fromDict.items()
                               if key not in ['code', 'message', 'group', 'info', 'retry']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self) -> str:
            return f'Error {self.code.value}: {self.message.value} info: {self.info.value}'
