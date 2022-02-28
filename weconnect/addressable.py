from __future__ import annotations
from typing import Callable, NoReturn, Optional, Dict, List, Set, Any, Tuple, Union, Type, TypeVar, Generic

import json
import logging
import time as timemodule
from datetime import datetime, timezone, time
from enum import Enum, IntEnum, Flag, auto

from weconnect.util import toBool, imgToASCIIArt, robustTimeParse, ExtendedWithNullEncoder

SUPPORT_IMAGES = False
try:
    from PIL import Image  # type: ignore
    SUPPORT_IMAGES = True
except ImportError:
    pass

SUPPORT_ASCII_IMAGES = False
try:
    import ascii_magic  # type: ignore
    SUPPORT_ASCII_IMAGES = True
except ImportError:
    pass

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
        lastUpdateFromCar: Optional[datetime] = None,
        valueGetter: Optional[Callable[[], Optional[T]]] = None,
        valueSetter: Optional[Callable[[Optional[T]], None]] = None
    ) -> None:
        super().__init__(localAddress, parent)
        self.__value: Optional[T] = None
        self.valueType: Type[T] = valueType
        self.valueGetter = valueGetter
        self.valueSetter = valueSetter
        if value is not None:
            self.setValueWithCarTime(value, lastUpdateFromCar, fromServer=True)

    @property
    def value(self) -> Optional[T]:
        if self.valueGetter is not None:
            return self.valueGetter()
        return self.__value

    @value.setter
    def value(self, newValue: Optional[T]) -> NoReturn:
        raise NotImplementedError('You cannot set this attribute. Set is not implemented')

    def asDict(self, filterCallable: Optional[Callable[[Any], None]] = None):
        if filterCallable is None or not filterCallable(self.value):
            return self.value
        return None

    def toJSON(self):
        if SUPPORT_IMAGES and isinstance(self.value, Image.Image):
            return None
        return json.dumps(self.value, cls=ExtendedWithNullEncoder, skipkeys=True, indent=4)

    def setValueWithCarTime(self, newValue, lastUpdateFromCar: Optional[datetime] = None, fromServer: bool = False, noNotify: bool = False) -> None:
        if newValue is not None and not isinstance(newValue, self.valueType):
            raise ValueError(f'{self.getGlobalAddress()}: new value {newValue} must be of type {self.valueType}'
                             f' but is of type {type(newValue)}')
        valueChanged: bool = newValue != self.__value
        self.__value = newValue
        flags: Optional[AddressableLeaf.ObserverEvent] = None
        if not self.enabled and valueChanged:
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

    def saveToFile(self, filename: str) -> None:  # noqa: C901
        if self.value is not None:
            if filename.endswith(('.txt', '.TXT', '.text')):
                with open(filename, mode='w', encoding='utf8') as textfile:
                    if SUPPORT_IMAGES and SUPPORT_ASCII_IMAGES and isinstance(self.value, Image.Image):
                        textfile.write(imgToASCIIArt(self.value, columns=120, mode=ascii_magic.Modes.ASCII))
                    else:
                        textfile.write(str(self))
            elif filename.endswith(('.htm', '.HTM', '.html', '.HTML')):
                with open(filename, mode='w', encoding='utf8') as htmlfile:
                    if SUPPORT_IMAGES and SUPPORT_ASCII_IMAGES and isinstance(self.value, Image.Image):
                        html = """<!DOCTYPE html><head><title>ASCII art</title></head><body><pre style="display: inline-block; border-width: 4px 6px;
    border-color: black; border-style: solid; background-color:black; font-size: 8px;">"""
                        htmlfile.write(html)
                        htmlfile.write(imgToASCIIArt(self.value, columns=240, mode=ascii_magic.Modes.HTML))
                        htmlfile.write('<pre/></body></html>')
                    else:
                        htmlfile.write(str(self))
            elif filename.endswith(('.json')):
                with open(filename, mode='w', encoding='utf8') as textfile:
                    if SUPPORT_IMAGES and SUPPORT_ASCII_IMAGES and isinstance(self.value, Image.Image):
                        raise ValueError('Attribute is an image and cannot be converted to json')
                    textfile.write(self.toJSON() + '\n')
            elif filename.endswith(('.png', '.PNG')):
                with open(filename, mode='wb') as pngfile:
                    if SUPPORT_IMAGES and isinstance(self.value, Image.Image):
                        self.value.save(fp=pngfile, format='PNG')  # pylint: disable=no-member
                    else:
                        raise ValueError('Attribute is no image and cannot be converted to one')
            elif filename.endswith(('.jpg', '.JPG', '.jpeg', '.JPEG')):
                with open(filename, mode='wb') as jpgfile:
                    if SUPPORT_IMAGES and isinstance(self.value, Image.Image):
                        if self.value.mode in ("RGBA", "P"):  # pylint: disable=no-member
                            raise ValueError('Image contains transparency and thus cannot be saved as jpeg-file')
                        self.value.save(fp=jpgfile, format='JPEG')  # pylint: disable=no-member
                    else:
                        raise ValueError('Attribute is no image and cannot be converted to one')
            else:
                raise ValueError('I cannot recognize the target file extension')
        else:
            raise ValueError('I cannot save None value')

    def fromDict(self, fromDict: dict, key: str):  # noqa: C901
        if fromDict is not None and key in fromDict and fromDict[key] is not None:
            if issubclass(self.valueType, bool):
                self.setValueWithCarTime(toBool(fromDict[key]), lastUpdateFromCar=None, fromServer=True)
            elif issubclass(self.valueType, int):
                self.setValueWithCarTime(int(fromDict[key]), lastUpdateFromCar=None, fromServer=True)
            elif issubclass(self.valueType, float):
                self.setValueWithCarTime(float(fromDict[key]), lastUpdateFromCar=None, fromServer=True)
            elif issubclass(self.valueType, Enum):
                if fromDict[key]:
                    try:
                        self.setValueWithCarTime(self.valueType(fromDict[key]), lastUpdateFromCar=None, fromServer=True)
                    except ValueError:
                        self.setValueWithCarTime(self.valueType.UNKNOWN, lastUpdateFromCar=None, fromServer=True)
                        LOG.warning('%s: An unsupported %s: %s was provided, known values are [%s]'
                                    ' please report this as a bug', self.getGlobalAddress(), key, fromDict[key],
                                    ', '.join([state.value for state in list(self.valueType)]))
                else:
                    self.enabled = False
            elif issubclass(self.valueType, datetime):
                self.setValueWithCarTime(robustTimeParse(fromDict[key]), lastUpdateFromCar=None, fromServer=True)
            elif issubclass(self.valueType, time):
                parsedtime = timemodule.strptime(fromDict[key], "%H:%M")
                self.setValueWithCarTime(time(hour=parsedtime.tm_hour, minute=parsedtime.tm_min), lastUpdateFromCar=None, fromServer=True)
            elif issubclass(self.valueType, str):
                self.setValueWithCarTime(str(fromDict[key]), lastUpdateFromCar=None, fromServer=True)
            else:
                raise ValueError(f'Unknown attribute type {self.valueType}')
        else:
            self.enabled = False

    def __str__(self) -> str:
        if isinstance(self.value, Enum):
            return str(self.value.value)  # pylint: disable=no-member
        if isinstance(self.value, datetime):
            return self.value.isoformat()  # pylint: disable=no-member
        if SUPPORT_IMAGES and isinstance(self.value, Image.Image):
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
        valueGetter: Optional[Callable[[], Optional[T]]] = None,
        valueSetter: Optional[Callable[[Optional[T]], None]] = None
    ) -> None:
        super().__init__(localAddress=localAddress, parent=parent, value=value, valueType=valueType,
                         lastUpdateFromCar=lastUpdateFromCar, valueGetter=valueGetter, valueSetter=valueSetter)

    @AddressableAttribute.value.setter  # type: ignore # noqa: C901
    def value(self, newValue):  # noqa: C901
        exceptions = []

        iterablevalueType = self.valueType
        if not isinstance(iterablevalueType, tuple):
            iterablevalueType = (iterablevalueType,)
        for valType in iterablevalueType:  # pylint: disable=too-many-nested-blocks
            if isinstance(newValue, str) and valType != str:
                try:
                    if valType in [int, float]:
                        newValue = valType(newValue)
                        exceptions = []
                    elif valType == bool:
                        newValue = toBool(newValue)
                        exceptions = []
                    elif issubclass(valType, Enum):
                        if not isinstance(newValue, Enum):
                            newValue = valType(newValue)
                            exceptions = []
                        try:
                            allowedValues = valType.allowedValues()
                            if newValue not in allowedValues:
                                raise ValueError('Value is not in allowed values')
                        except AttributeError:
                            pass
                        newValue = valType(newValue)
                        exceptions = []
                        break
                except ValueError:
                    valueFormat = ''
                    if valType == int:
                        valueFormat = 'N (Decimal number)'
                    elif valType == float:
                        valueFormat = 'F.F (Floating Point Number)'
                    elif valType == bool:
                        valueFormat = 'True/False (Boolean)'
                    elif issubclass(valType, Enum):
                        try:
                            valueFormat = 'select one of [' + ', '.join([enum.value for enum in valType.allowedValues()]) + ']'
                        except AttributeError:
                            valueFormat = 'select one of [' + ', '.join([enum.value for enum in valType])
                    exceptions.append(valueFormat)
            elif isinstance(newValue, int) and valType != int:
                if valType == float:
                    newValue = float(newValue)
                    exceptions = []
                    break
            else:
                exceptions = []

        if exceptions:
            raise ValueError(f'id {self.getGlobalAddress()} cannot be set to value {newValue}.'
                             f' You need to provide it in the correct format {" or ".join(exceptions)}')
        if self.valueSetter is not None:
            self.valueSetter(newValue)
        else:
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

    def asDict(self, filterCallable: Optional[Callable[[Any], None]] = None):
        asDict = {}
        for child in self.children:
            if child.enabled:
                childDict = child.asDict(filterCallable=filterCallable)
                if childDict is not None:
                    asDict[child.getLocalAddress()] = childDict
        return asDict

    def toJSON(self):
        def filterDict(element):
            if SUPPORT_IMAGES and isinstance(element, Image.Image):
                return True
            return False
        return json.dumps(self.asDict(filterCallable=filterDict), cls=ExtendedWithNullEncoder, skipkeys=True, indent=4)

    def isLeaf(self) -> bool:
        return not self.__children

    def addChild(self, child: AddressableLeaf):
        if not isinstance(child, AddressableLeaf):
            raise TypeError('Cannot add a child that is not addressable')
        self.__children[child.getLocalAddress()] = child
        self.enabled = True

    def getLeafChildren(self) -> List[AddressableLeaf]:
        return self.getRecursiveChildren(leaveOnly=True)

    def getRecursiveChildren(self, leaveOnly=False) -> List[AddressableLeaf]:
        if not self.enabled:
            return []
        if self.isLeaf():
            return [self]

        children: List[AddressableLeaf] = []
        if not leaveOnly:
            children.append(self)
        for child in self.__children.values():
            if child.enabled:
                if isinstance(child, AddressableObject):
                    children.extend(child.getRecursiveChildren(leaveOnly=leaveOnly))
                elif isinstance(child, AddressableLeaf):
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

    def saveToFile(self, filename: str) -> None:  # noqa: C901
        if filename.endswith(('.txt', '.TXT', '.text')):
            with open(filename, mode='w', encoding='utf8') as textfile:
                textfile.write(str(self))
        elif filename.endswith(('.htm', '.HTM', '.html', '.HTML')):
            with open(filename, mode='w', encoding='utf8'):
                raise ValueError('Object cannot be saved as HTML')
        elif filename.endswith(('.json')):
            with open(filename, mode='w', encoding='utf8') as textfile:
                textfile.write(self.toJSON() + '\n')
        elif filename.endswith(('.png', '.PNG')):
            with open(filename, mode='wb'):
                raise ValueError('Attribute is no image and cannot be converted to one')
        elif filename.endswith(('.jpg', '.JPG', '.jpeg', '.JPEG')):
            with open(filename, mode='wb'):
                raise ValueError('Attribute is no image and cannot be converted to one')
        else:
            raise ValueError('I cannot recognize the target file extension')


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
