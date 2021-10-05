from __future__ import annotations
from typing import Callable, NoReturn, Optional, Dict, List, Set, Any, Tuple, Union, Type, TypeVar, Generic

import logging
from datetime import datetime, timezone
from enum import Enum, IntEnum, Flag, auto

from PIL import Image  # type: ignore
import ascii_magic  # type: ignore

from weconnect.util import toBool, imgToASCIIArt


LOG: logging.Logger = logging.getLogger("weconnect")


class AddressableLeaf():
    def __init__(
        self,
        localAddress: str,
        parent: Optional[AddressableObject],
    ) -> None:
        self.__enabled: bool = False
        self.__localAddress: str = localAddress
        self.__parent: Optional[AddressableObject] = parent
        self.__observers: Set[Tuple[Callable[[Optional[Any], AddressableLeaf.ObserverEvent], None],
                                    AddressableLeaf.ObserverEvent, AddressableLeaf.ObserverPriority, bool]] = set()
        self.lastChange: Optional[datetime] = None
        self.lastUpdateFromServer: Optional[datetime] = None
        self.lastUpdateFromCar: Optional[datetime] = None
        self.onCompleteNotifyFlags: Optional[AddressableLeaf.ObserverEvent] = None

    def __del__(self) -> None:
        if self.enabled:
            self.enabled = False

    def addObserver(self, observer: Callable, flag: AddressableLeaf.ObserverEvent, priority: Optional[AddressableLeaf.ObserverPriority] = None,
                    onUpdateComplete: bool = False) -> None:
        if priority is None:
            priority = AddressableLeaf.ObserverPriority.USER_MID
        self.__observers.add((observer, flag, priority, onUpdateComplete))
        LOG.debug('%s: Observer added with flags: %s', self.getGlobalAddress(), flag)

    def removeObserver(self, observer: Callable, flag: Optional[AddressableLeaf.ObserverEvent] = None) -> None:
        self.__observers = filter(lambda observerEntry: observerEntry[0] == observer
                                  or (flag is not None and observerEntry[1] == flag), self.__observers)

    def getObservers(self, flags, onUpdateComplete: bool = False) -> List[Any]:
        return [observerEntry[0] for observerEntry in self.getObserverEntries(flags, onUpdateComplete)]

    def getObserverEntries(self, flags: AddressableLeaf.ObserverEvent, onUpdateComplete: bool = False) -> List[Any]:
        observers: Set[Tuple[Callable, AddressableLeaf.ObserverEvent, AddressableLeaf.ObserverPriority, bool]] = set()
        for observerEntry in self.__observers:
            observer, observerflags, priority, observerOnUpdateComplete = observerEntry
            del observer
            del priority
            if (flags & observerflags) and observerOnUpdateComplete == onUpdateComplete:
                observers.add(observerEntry)
        if self.__parent is not None:
            observers.update(self.__parent.getObserverEntries(flags, onUpdateComplete))
        return sorted(observers, key=lambda entry: int(entry[2]))

    def notify(self, flags: AddressableLeaf.ObserverEvent) -> None:
        observers: List[Callable] = self.getObservers(flags, onUpdateComplete=False)
        for observer in observers:
            observer(element=self, flags=flags)
        if self.onCompleteNotifyFlags is not None:
            # Remove disabled if was enabled and not yet notified
            if (flags & AddressableLeaf.ObserverEvent.ENABLED) and (self.onCompleteNotifyFlags & AddressableLeaf.ObserverEvent.DISABLED):
                self.onCompleteNotifyFlags &= ~AddressableLeaf.ObserverEvent.DISABLED  # pylint: disable=invalid-unary-operand-type
            # Remove enabled if was enabled and not yet notified
            elif (flags & AddressableLeaf.ObserverEvent.DISABLED) and (self.onCompleteNotifyFlags & AddressableLeaf.ObserverEvent.ENABLED):
                self.onCompleteNotifyFlags &= ~AddressableLeaf.ObserverEvent.ENABLED  # pylint: disable=invalid-unary-operand-type
            else:
                self.onCompleteNotifyFlags |= flags
        else:
            self.onCompleteNotifyFlags = flags
        LOG.debug('%s: Notify called with flags: %s for %d observers', self.getGlobalAddress(), flags, len(observers))

    def updateComplete(self) -> None:
        if self.onCompleteNotifyFlags is not None:
            observers = self.getObservers(self.onCompleteNotifyFlags, onUpdateComplete=True)
            for observer in observers:
                observer(element=self, flags=self.onCompleteNotifyFlags)
            if len(observers) > 0:
                LOG.debug('%s: Notify called on update complete with flags: %s for %d observers', self.getGlobalAddress(),
                          self.onCompleteNotifyFlags, len(observers))
            self.onCompleteNotifyFlags = None

    @property
    def enabled(self) -> bool:
        return self.__enabled

    @enabled.setter
    def enabled(self, setEnabled: bool) -> None:
        if setEnabled and not self.__enabled:
            if self.parent is not None:
                self.parent.addChild(self)
            self.notify(AddressableLeaf.ObserverEvent.ENABLED)
        elif not setEnabled and self.__enabled:
            self.notify(AddressableLeaf.ObserverEvent.DISABLED)
        self.__enabled = setEnabled

    @property
    def localAddress(self) -> str:
        return self.getLocalAddress()

    @localAddress.setter
    def localAddress(self, newAdress: str) -> None:
        self.__localAddress = newAdress

    @property
    def parent(self) -> Optional[AddressableObject]:
        return self.__parent

    @parent.setter
    def parent(self, newParent: AddressableObject):
        self.__parent = newParent

    def getLocalAddress(self) -> str:
        return self.__localAddress

    def getGlobalAddress(self) -> str:
        address = ''
        if self.__parent is not None:
            address = f'{self.__parent.getGlobalAddress()}/'
        address += f'{self.__localAddress}'
        return address

    def getByAddressString(self, addressString: str) -> Union[AddressableLeaf, bool]:
        if addressString == self.getLocalAddress():
            return self
        if addressString == '..':
            if self.parent is None:
                return self
            return self.parent
        if addressString == '/':
            return self.getRoot()
        return False

    def getRoot(self) -> AddressableLeaf:
        if self.parent is None:
            return self
        return self.parent.getRoot()

    class ObserverEvent(Flag):
        ENABLED = auto()
        DISABLED = auto()
        VALUE_CHANGED = auto()
        UPDATED_FROM_SERVER = auto()
        UPDATED_FROM_CAR = auto()
        ALL = ENABLED | DISABLED | VALUE_CHANGED | UPDATED_FROM_SERVER | UPDATED_FROM_CAR

    class ObserverPriority(IntEnum):
        INTERNAL_FIRST = 1
        INTERNAL_HIGH = 2
        USER_HIGH = 3
        INTERNAL_MID = 4
        USER_MID = 5
        INTERNAL_LOW = 6
        USER_LOW = 7
        INTERNAL_LAST = 8


T = TypeVar('T')


class AddressableAttribute(AddressableLeaf, Generic[T]):
    def __init__(
        self,
        localAddress: str,
        parent: AddressableObject,
        value: Optional[T],
        valueType: Type[T],
        lastUpdateFromCar: Optional[datetime] = None
    ) -> None:
        super().__init__(localAddress, parent)
        self.__value: Optional[T] = None
        self.valueType: Type[T] = valueType
        if value is not None:
            self.setValueWithCarTime(value, lastUpdateFromCar, fromServer=True)

    @property
    def value(self) -> Optional[T]:
        return self.__value

    @value.setter
    def value(self, newValue: Optional[T]) -> NoReturn:
        raise NotImplementedError('You cannot set this attribute. Set is not implemented')

    def setValueWithCarTime(self, newValue, lastUpdateFromCar: Optional[datetime] = None, fromServer: bool = False, noNotify: bool = False) -> None:
        if newValue is not None and not isinstance(newValue, self.valueType):
            raise ValueError(f'{self.getGlobalAddress()}: new value {newValue} must be of type {self.valueType}'
                             f' but is of type {type(newValue)}')
        valueChanged: bool = newValue != self.__value
        self.__value = newValue
        flags: Optional[AddressableLeaf.ObserverEvent] = None
        if not self.enabled:
            self.enabled = True
        self.lastUpdateFromServer = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
        if valueChanged:
            self.lastChange = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
            flags = AddressableLeaf.ObserverEvent.VALUE_CHANGED
            if fromServer:
                if flags is None:
                    flags = AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER
                else:
                    flags |= AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER
        elif fromServer:
            flags = AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER

        if lastUpdateFromCar is not None and lastUpdateFromCar != self.lastUpdateFromCar:
            self.lastUpdateFromCar = lastUpdateFromCar
            if flags is None:
                flags = AddressableLeaf.ObserverEvent.UPDATED_FROM_CAR
            else:
                flags |= AddressableLeaf.ObserverEvent.UPDATED_FROM_CAR

        if not noNotify and flags is not None:
            self.notify(flags)

    def isLeaf(self) -> bool:  # pylint: disable=R0201
        return True

    def getLeafChildren(self) -> List[AddressableLeaf]:
        return [self]

    def saveToFile(self, filename: str) -> None:  # noqa: C901
        if self.value is not None:
            if filename.endswith(('.txt', '.TXT', '.text')):
                with open(filename, mode='w', encoding='utf8') as textfile:
                    if isinstance(self.value, Image.Image):
                        textfile.write(imgToASCIIArt(self.value, columns=120, mode=ascii_magic.Modes.ASCII))
                    else:
                        textfile.write(str(self))
            elif filename.endswith(('.htm', '.HTM', '.html', '.HTML')):
                with open(filename, mode='w', encoding='utf8') as htmlfile:
                    if isinstance(self.value, Image.Image):
                        html = """<!DOCTYPE html><head><title>ASCII art</title></head><body><pre style="display: inline-block; border-width: 4px 6px;
    border-color: black; border-style: solid; background-color:black; font-size: 8px;">"""
                        htmlfile.write(html)
                        htmlfile.write(imgToASCIIArt(self.value, columns=240, mode=ascii_magic.Modes.HTML))
                        htmlfile.write('<pre/></body></html>')
                    else:
                        htmlfile.write(str(self))
            elif filename.endswith(('.png', '.PNG')):
                with open(filename, mode='wb') as pngfile:
                    if isinstance(self.value, Image.Image):
                        self.value.save(fp=pngfile, format='PNG')  # pylint: disable=no-member
                    else:
                        raise ValueError('Attribute is no image and cannot be converted to one')
            elif filename.endswith(('.jpg', '.JPG', '.jpeg', '.JPEG')):
                with open(filename, mode='wb') as jpgfile:
                    if isinstance(self.value, Image.Image):
                        if self.value.mode in ("RGBA", "P"):  # pylint: disable=no-member
                            raise ValueError('Image contains transparency and thus cannot be saved as jpeg-file')
                        self.value.save(fp=jpgfile, format='JPEG')  # pylint: disable=no-member
                    else:
                        raise ValueError('Attribute is no image and cannot be converted to one')
            else:
                raise ValueError('I cannot recognize the target file extension')
        else:
            raise ValueError('I cannot save None value')

    def __str__(self) -> str:
        if isinstance(self.value, Enum):
            return str(self.value.value)  # pylint: disable=no-member
        if isinstance(self.value, datetime):
            return self.value.isoformat()  # pylint: disable=no-member
        if isinstance(self.value, Image.Image):
            return imgToASCIIArt(self.value)  # pylint: disable=no-member
        return str(self.value)


class ChangeableAttribute(AddressableAttribute):
    def __init__(
        self,
        localAddress: str,
        parent: AddressableObject,
        value,
        valueType=str,
        lastUpdateFromCar: Optional[datetime] = None,
    ) -> None:
        super().__init__(localAddress=localAddress, parent=parent, value=value, valueType=valueType,
                         lastUpdateFromCar=lastUpdateFromCar)

    @AddressableAttribute.value.setter  # type: ignore # noqa: C901
    def value(self, newValue):  # noqa: C901
        if isinstance(newValue, str) and self.valueType != str:
            try:
                if self.valueType in [int, float]:
                    newValue = self.valueType(newValue)
                elif self.valueType == bool:
                    newValue = toBool(newValue)
                elif issubclass(self.valueType, Enum):
                    if not isinstance(newValue, Enum):
                        newValue = self.valueType(newValue)
                    try:
                        allowedValues = self.valueType.allowedValues()
                        if newValue not in allowedValues:
                            raise ValueError('Value is not in allowed values')
                    except AttributeError:
                        pass
                    newValue = self.valueType(newValue)
            except ValueError as vErr:
                valueFormat = ''
                if self.valueType == int:
                    valueFormat = 'N (Decimal number)'
                elif self.valueType == float:
                    valueFormat = 'F.F (Floating Point Number)'
                elif self.valueType == bool:
                    valueFormat = 'True/False (Boolean)'
                elif issubclass(self.valueType, Enum):
                    try:
                        valueFormat = 'select one of [' + ', '.join([enum.value for enum in self.valueType.allowedValues()]) + ']'
                    except AttributeError:
                        valueFormat = 'select one of [' + ', '.join([enum.value for enum in self.valueType])
                raise ValueError(f'id {self.getGlobalAddress()} cannot be set to value {newValue}.'
                                 f' You need to provide it in the correct format {valueFormat}') from vErr
        elif isinstance(newValue, int) and self.valueType != int:
            if self.valueType == float:
                newValue = float(newValue)

        self.setValueWithCarTime(newValue=newValue, lastUpdateFromCar=None)


class AliasChangeableAttribute(ChangeableAttribute):
    def __init__(
        self,
        localAddress: str,
        parent: AddressableObject,
        value,
        targetAttribute: ChangeableAttribute,
        conversion,
        valueType=str,
        lastUpdateFromCar: Optional[datetime] = None,
    ) -> None:
        super().__init__(localAddress=localAddress, parent=parent,
                         value=value, valueType=valueType,
                         lastUpdateFromCar=lastUpdateFromCar)
        self.targetAttribute = targetAttribute
        self.conversion = conversion

    @AddressableAttribute.value.setter
    def value(self, newValue):
        ChangeableAttribute.value.fset(self, newValue)  # pylint: disable=no-member
        convertedNewValue = self.conversion(self.value)
        self.targetAttribute.setValueWithCarTime(newValue=convertedNewValue,
                                                 lastUpdateFromCar=None)


class AddressableObject(AddressableLeaf):
    def __init__(
        self,
        localAddress: str,
        parent: Optional[AddressableObject],
    ) -> None:
        super().__init__(localAddress, parent)
        self.__children: dict[str, AddressableLeaf] = {}

    @AddressableLeaf.enabled.setter  # type: ignore
    def enabled(self, setEnabled: bool) -> None:
        if not setEnabled and self.enabled:
            for child in self.__children.values():
                child.enabled = False
        AddressableLeaf.enabled.fset(self, setEnabled)  # type: ignore

    def isLeaf(self) -> bool:
        return not self.__children

    def addChild(self, child: AddressableLeaf):
        if not isinstance(child, AddressableLeaf):
            raise TypeError('Cannot add a child that is not addressable')
        self.__children[child.getLocalAddress()] = child
        self.enabled = True

    def getLeafChildren(self) -> List[AddressableLeaf]:
        if not self.enabled:
            return []
        if self.isLeaf():
            return [self]

        children: List[AddressableLeaf] = [self]
        for child in self.__children.values():
            if isinstance(child, AddressableObject):
                children.extend(child.getLeafChildren())
            elif isinstance(child, AddressableLeaf) and child.enabled:
                children.append(child)
        return children

    @property
    def children(self) -> List[AddressableLeaf]:
        return list(self.__children.values())

    def getByAddressString(self, addressString: str) -> Union[AddressableLeaf, bool]:
        if '/' not in addressString or addressString == '/':
            return super().getByAddressString(addressString)

        localAddress, _, childPath = addressString.partition('/')
        if not super().getByAddressString(localAddress):
            return False
        childAddress, _, _ = childPath.partition('/')
        if childAddress == '..':
            if self.parent is not None:
                return self.parent.getByAddressString(childPath)
            return self
        if childAddress in self.__children:
            return self.__children[childAddress].getByAddressString(childPath)
        return False

    def updateComplete(self) -> None:
        for child in self.__children.values():
            child.updateComplete()
        super().updateComplete()


L = TypeVar('L', bound=AddressableLeaf)


class AddressableDict(AddressableObject, Dict[T, L]):
    def __setitem__(self, key: T, item: L):
        self.addChild(item)
        retVal = super().setdefault(key, item)
        if not self.enabled:
            self.enabled = True
        return retVal

    def __str__(self) -> str:
        return '[' + ', '.join([str(item) for item in self.values() if item.enabled]) + ']'


class AddressableList(AddressableObject, List[L]):
    def __add__(self, item):
        retVal = super().__add__(item)
        if not self.enabled:
            self.enabled = True
        return retVal

    def __str__(self) -> str:
        return '[' + ', '.join([str(item) for item in self if item.enabled]) + ']'
