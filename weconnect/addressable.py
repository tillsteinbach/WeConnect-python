import logging
from datetime import datetime, timezone
from enum import Enum, IntEnum, Flag, auto
from typing import Dict, List

LOG = logging.getLogger("weconnect")


class AddressableLeaf():
    def __init__(
        self,
        localAddress,
        parent,
    ):
        self.__enabled = False
        self.__address = localAddress
        self.__parent = parent
        self.__observers = set()
        self.lastChange = None
        self.lastUpdateFromServer = None
        self.lastUpdateFromCar = None

    def __del__(self):
        if self.enabled:
            self.enabled = False

    def addObserver(self, observer, flag, priority=None):
        if priority is None:
            priority = AddressableLeaf.ObserverPriority.USER_MID
        self.__observers.add((observer, flag, priority))
        LOG.debug('%s: Observer added with flags: %s', self.getGlobalAddress(), flag)

    def getObservers(self, flags):
        return [observerEntry[0] for observerEntry in self.getObserverEntries(flags)]

    def getObserverEntries(self, flags):
        observers = set()
        for observerEntry in self.__observers:
            observer, observerflags, priority = observerEntry
            del observer
            del priority
            if flags & observerflags:
                observers.add(observerEntry)
        if self.__parent is not None:
            observers.update(self.__parent.getObserverEntries(flags))
        return sorted(observers, key=lambda entry: entry[2])

    def notify(self, flags):
        observers = self.getObservers(flags)
        for observer in observers:
            observer(element=self, flags=flags)
        LOG.debug('%s: Notify called with flags: %s for %d observers', str(self), flags, len(observers))
        LOG.debug('%s: Notify called with flags: %s for %d observers', self.getGlobalAddress(), flags, len(observers))

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
    def address(self):
        return self.getLocalAddress()

    @address.setter
    def address(self, newAdress):
        self.__address = newAdress

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, newParent):
        self.__parent = newParent

    def getLocalAddress(self):
        return self.__address

    def getGlobalAddress(self):
        address = ''
        if self.__parent is not None:
            address = f'{self.__parent.getGlobalAddress()}/'
        address += f'{self.__address}'
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
            raise ValueError(f'{self.getGlobalAddress()}: new value must be of type {self.valueType}'
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

    def __str__(self):
        if isinstance(self.value, Enum):
            return str(self.value.value)
        if isinstance(self.value, datetime):
            return self.value.isoformat()
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
                elif issubclass(self.valueType, Enum):
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
                raise ValueError(f'id {self.getGlobalAddress()} cannot be set. You need to provide it in the correct format {valueFormat}') from vErr
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
            children += child.getLeafChildren()
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
