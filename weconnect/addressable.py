import logging
from datetime import datetime, timezone
from enum import Enum, IntEnum, Flag, auto
from typing import Dict, List

from PIL import Image
import ascii_magic

from weconnect.util import toBool, imgToASCIIArt

LOG = logging.getLogger("weconnect")


class AddressableLeaf():
    def __init__(
        self,
        localAddress,
        parent,
    ):
        self.__enabled = False
        self.__localAddress = localAddress
        self.__parent = parent
        self.__observers = set()
        self.lastChange = None
        self.lastUpdateFromServer = None
        self.lastUpdateFromCar = None
        self.onCompleteNotifyFlags = None

    def __del__(self):
        if self.enabled:
            self.enabled = False

    def addObserver(self, observer, flag, priority=None, onUpdateComplete=False):
        if priority is None:
            priority = AddressableLeaf.ObserverPriority.USER_MID
        self.__observers.add((observer, flag, priority, onUpdateComplete))
        LOG.debug('%s: Observer added with flags: %s', self.getGlobalAddress(), flag)

    def getObservers(self, flags, onUpdateComplete=False):
        return [observerEntry[0] for observerEntry in self.getObserverEntries(flags, onUpdateComplete)]

    def getObserverEntries(self, flags, onUpdateComplete=False):
        observers = set()
        for observerEntry in self.__observers:
            observer, observerflags, priority, observerOnUpdateComplete = observerEntry
            del observer
            del priority
            if (flags & observerflags) and observerOnUpdateComplete == onUpdateComplete:
                observers.add(observerEntry)
        if self.__parent is not None:
            observers.update(self.__parent.getObserverEntries(flags, onUpdateComplete))
        return sorted(observers, key=lambda entry: int(entry[2]))

    def notify(self, flags):
        observers = self.getObservers(flags, onUpdateComplete=False)
        for observer in observers:
            observer(element=self, flags=flags)
        if self.onCompleteNotifyFlags is not None:
            self.onCompleteNotifyFlags |= flags
        else:
            self.onCompleteNotifyFlags = flags
        LOG.debug('%s: Notify called with flags: %s for %d observers', self.getGlobalAddress(), flags, len(observers))

    def updateComplete(self):
        if self.onCompleteNotifyFlags is not None:
            observers = self.getObservers(self.onCompleteNotifyFlags, onUpdateComplete=True)
            for observer in observers:
                observer(element=self, flags=self.onCompleteNotifyFlags)
            self.onCompleteNotifyFlags = None
            LOG.debug('%s: Notify called on update complete with flags: %s for %d observers', self.getGlobalAddress(),
                      self.onCompleteNotifyFlags, len(observers))

    @property
    def enabled(self):
        return self.__enabled

    @enabled.setter
    def enabled(self, setEnabled):
        if setEnabled and not self.__enabled:
            if self.parent is not None:
                self.parent.addChild(self)
            self.notify(AddressableLeaf.ObserverEvent.ENABLED)
        self.__enabled = setEnabled

    @property
    def localAddress(self):
        return self.getLocalAddress()

    @localAddress.setter
    def localAddress(self, newAdress):
        self.__localAddress = newAdress

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, newParent):
        self.__parent = newParent

    def getLocalAddress(self):
        return self.__localAddress

    def getGlobalAddress(self):
        address = ''
        if self.__parent is not None:
            address = f'{self.__parent.getGlobalAddress()}/'
        address += f'{self.__localAddress}'
        return address

    def getByAddressString(self, addressString):
        if addressString == self.getLocalAddress():
            return self
        if addressString == '..':
            if self.parent is None:
                return self
            return self.parent
        if addressString == '/':
            return self.getRoot()
        return False

    def getRoot(self):
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


class AddressableAttribute(AddressableLeaf):
    def __init__(
        self,
        localAddress,
        parent,
        value,
        valueType=str,
        lastUpdateFromCar=None
    ):
        super().__init__(localAddress, parent)
        self.__value = None
        self.valueType = valueType
        if value is not None:
            self.setValueWithCarTime(value, lastUpdateFromCar, fromServer=True)

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, newValue):
        raise NotImplementedError('You cannot set this attribute. Set is not implemented')

    def setValueWithCarTime(self, newValue, lastUpdateFromCar=None, fromServer=False, noNotify=False):
        if newValue is not None and not isinstance(newValue, self.valueType):
            raise ValueError(f'{self.getGlobalAddress()}: new value {newValue} must be of type {self.valueType}'
                             f' but is of type {type(newValue)}')
        valueChanged = newValue != self.__value
        self.__value = newValue
        flags = None
        if not self.enabled:
            self.enabled = True
        self.lastUpdateFromServer = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
        if valueChanged:
            self.lastChange = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
            flags = AddressableLeaf.ObserverEvent.VALUE_CHANGED
            if fromServer:
                flags |= AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER
        elif fromServer:
            flags = AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER

        if lastUpdateFromCar is not None and lastUpdateFromCar != self.lastUpdateFromCar:
            self.lastUpdateFromCar = lastUpdateFromCar
            flags |= AddressableLeaf.ObserverEvent.UPDATED_FROM_CAR

        if not noNotify and flags is not None:
            self.notify(flags)

    def isLeaf(self):  # pylint: disable=R0201
        return True

    def getLeafChildren(self):
        return [self]

    def saveToFile(self, filename):
        if filename.endswith(('.txt', '.TXT', '.text')):
            with open(filename, mode='w') as file:
                if self.valueType == Image.Image:
                    file.write(imgToASCIIArt(self.value, columns=120, mode=ascii_magic.Modes.ASCII))
                else:
                    file.write(str(self))
        elif filename.endswith(('.htm', '.HTM', '.html', '.HTML')):
            with open(filename, mode='w') as file:
                if self.valueType == Image.Image:
                    html = """<!DOCTYPE html><head><title>ASCII art</title></head><body><pre style="display: inline-block; border-width: 4px 6px;
 border-color: black; border-style: solid; background-color:black; font-size: 8px;">"""
                    file.write(html)
                    file.write(imgToASCIIArt(self.value, columns=240, mode=ascii_magic.Modes.HTML))
                    file.write('<pre/></body></html>')
                else:
                    file.write(str(self))
        elif filename.endswith(('.png', '.PNG')):
            with open(filename, mode='wb') as file:
                if self.valueType == Image.Image:
                    self.value.save(fp=file, format='PNG')  # pylint: disable=no-member
                else:
                    raise ValueError('Attribute is no image and cannot be converted to one')
        elif filename.endswith(('.jpg', '.JPG', '.jpeg', '.JPEG')):
            with open(filename, mode='wb') as file:
                if self.valueType == Image.Image:
                    if self.value.mode in ("RGBA", "P"):  # pylint: disable=no-member
                        raise ValueError('Image contains transparency and thus cannot be saved as jpeg-file')
                    self.value.save(fp=file, format='JPEG')  # pylint: disable=no-member
                else:
                    raise ValueError('Attribute is no image and cannot be converted to one')
        else:
            raise ValueError('I cannot recognize the target file extension')

    def __str__(self):
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
        localAddress,
        parent,
        value,
        valueType=str,
        lastUpdateFromCar=None,
    ):
        super().__init__(localAddress=localAddress, parent=parent, value=value, valueType=valueType,
                         lastUpdateFromCar=lastUpdateFromCar)

    @AddressableAttribute.value.setter  # noqa: C901
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
        self.setValueWithCarTime(newValue=newValue, lastUpdateFromCar=None)


class AddressableObject(AddressableLeaf):
    def __init__(
        self,
        localAddress,
        parent,
    ):
        super().__init__(localAddress, parent)
        self.__children = dict()

    def isLeaf(self):
        return not self.__children

    def addChild(self, child):
        if not isinstance(child, AddressableLeaf):
            raise TypeError('Cannot add a child that is not addressable')
        self.__children[child.getLocalAddress()] = child
        self.enabled = True

    def getLeafChildren(self):
        if not self.enabled:
            return []
        if self.isLeaf():
            return [self]

        children = [self]
        for child in self.__children.values():
            if isinstance(child, AddressableObject):
                children.extend(child.getLeafChildren())
            elif isinstance(child, AddressableLeaf) and child.enabled:
                children.append(child)
        return children

    @property
    def children(self):
        return self.__children.values()

    def getByAddressString(self, addressString):
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

    def updateComplete(self):
        for child in self.__children.values():
            child.updateComplete()
        super().updateComplete()


class AddressableDict(AddressableObject, Dict):
    def __setitem__(self, key, item):
        self.addChild(item)
        retVal = super().setdefault(key, item)
        if not self.enabled:
            self.enabled = True
        return retVal

    def __str__(self):
        return '[' + ', '.join([str(item) for item in self.values()]) + ']'


class AddressableList(AddressableObject, List):
    def __add__(self, item):
        retVal = super().__add__(item)
        if not self.enabled:
            self.enabled = True
        return retVal

    def __str__(self):
        return '[' + ', '.join([str(item) for item in self]) + ']'
