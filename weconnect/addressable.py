import logging
from datetime import datetime, timezone
from enum import Enum, Flag, auto
from typing import Dict

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

    def addObserver(self, observer, flag):
        self.__observers.add((observer, flag))
        LOG.debug('%s: Observer added with flags: %s', self.getGlobalAddress(), flag)

    def getObservers(self, flags):
        observers = set()
        for observer, observerflags in self.__observers:
            if flags & observerflags:
                observers.add(observer)
        if self.__parent is not None:
            observers.update(self.__parent.getObservers(flags))
        return observers

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
        if self.__parent is not None:
            return f'{self.__parent.getGlobalAddress()}/{self.__address}'
        return self.getLocalAddress()

    def getByAddressString(self, addressString):
        if addressString == self.getLocalAddress():
            return self
        return False

    class ObserverEvent(Flag):
        ENABLED = auto()
        DISABLED = auto()
        VALUE_CHANGED = auto()
        UPDATED_FROM_SERVER = auto()
        UPDATED_FROM_CAR = auto()
        ALL = ENABLED | DISABLED | VALUE_CHANGED | UPDATED_FROM_SERVER | UPDATED_FROM_CAR


class AddressableAttribute(AddressableLeaf):
    def __init__(
        self,
        localAddress,
        parent,
        value,
        lastUpdateFromCar=None
    ):
        super().__init__(localAddress, parent)
        self.__value = None
        if value is not None:
            self.setValueWithCarTime(value, lastUpdateFromCar)

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, newValue):
        raise NotImplementedError('You cannot set this attribute. Set is not implemented')

    def setValueWithCarTime(self, newValue, lastUpdateFromCar):
        valueChanged = newValue != self.__value
        self.__value = newValue
        flags = None
        if not self.enabled:
            self.enabled = True
        self.lastUpdateFromServer = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
        if valueChanged:
            self.lastChange = datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc)
            flags = AddressableLeaf.ObserverEvent.VALUE_CHANGED | AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER
        else:
            flags = AddressableLeaf.ObserverEvent.UPDATED_FROM_SERVER

        if lastUpdateFromCar is not None and lastUpdateFromCar != self.lastUpdateFromCar:
            self.lastUpdateFromCar = lastUpdateFromCar
            flags |= AddressableLeaf.ObserverEvent.UPDATED_FROM_CAR

        if flags is not None:
            self.notify(flags)

    def isLeaf(self):  # pylint: disable=R0201
        return True

    def getLeafChildren(self):
        return [self.getGlobalAddress()]

    def __str__(self):
        if isinstance(self.value, Enum):
            return str(self.value.value)
        if isinstance(self.value, datetime):
            return self.value.isoformat()
        return str(self.value)


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
        if self.isLeaf():
            return [self.getGlobalAddress()]

        children = [self.getGlobalAddress()]
        for child in self.__children.values():
            children += child.getLeafChildren()
        return children

    def getByAddressString(self, addressString):
        if '/' not in addressString:
            return super().getByAddressString(addressString)

        localAddress, _, childPath = addressString.partition('/')
        if not super().getByAddressString(localAddress):
            return False
        childAddress, _, _ = childPath.partition('/')
        if childAddress in self.__children:
            return self.__children[childAddress].getByAddressString(childPath)
        return False


class AddressableDict(AddressableObject, Dict):
    def __setitem__(self, key, item):
        self.addChild(item)
        super().setdefault(key, item)
        if not self.enabled:
            self.enabled = True
