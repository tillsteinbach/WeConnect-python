import pytest

from weconnect import addressable


def test_AddressableLeafGetObservers():
    parentAddressableLeaf = addressable.AddressableObject(localAddress='none', parent=None)
    addressableLeaf = addressable.AddressableLeaf(localAddress='none', parent=parentAddressableLeaf)

    def observe1():
        pass

    def observe2():
        pass

    def observe3():
        pass

    def observe4():
        pass

    observerEntries = addressableLeaf.getObserverEntries(addressable.AddressableLeaf.ObserverEvent.ALL)
    assert len(observerEntries) == 0

    addressableLeaf.addObserver(observe1, flag=addressable.AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                priority=addressable.AddressableLeaf.ObserverPriority.INTERNAL_LOW)

    observerEntries = addressableLeaf.getObserverEntries(addressable.AddressableLeaf.ObserverEvent.ALL)
    assert len(observerEntries) == 1

    addressableLeaf.addObserver(observe2, flag=addressable.AddressableLeaf.ObserverEvent.ENABLED,
                                priority=addressable.AddressableLeaf.ObserverPriority.INTERNAL_HIGH)

    observerEntries = addressableLeaf.getObserverEntries(addressable.AddressableLeaf.ObserverEvent.ALL)
    assert len(observerEntries) == 2

    # Add without priority assuming it will have USER_MID as default
    addressableLeaf.addObserver(observe3, flag=addressable.AddressableLeaf.ObserverEvent.ALL)

    observerEntries = addressableLeaf.getObserverEntries(flags=addressable.AddressableLeaf.ObserverEvent.ALL)
    assert len(observerEntries) == 3

    assert observerEntries[0][0] == observe2  # pylint: disable=comparison-with-callable
    assert observerEntries[0][1] == addressable.AddressableLeaf.ObserverEvent.ENABLED
    assert observerEntries[0][2] == addressable.AddressableLeaf.ObserverPriority.INTERNAL_HIGH

    assert observerEntries[1][0] == observe3  # pylint: disable=comparison-with-callable
    assert observerEntries[1][1] == addressable.AddressableLeaf.ObserverEvent.ALL
    assert observerEntries[1][2] == addressable.AddressableLeaf.ObserverPriority.USER_MID

    assert observerEntries[2][0] == observe1  # pylint: disable=comparison-with-callable
    assert observerEntries[2][1] == addressable.AddressableLeaf.ObserverEvent.VALUE_CHANGED
    assert observerEntries[2][2] == addressable.AddressableLeaf.ObserverPriority.INTERNAL_LOW

    observers = addressableLeaf.getObservers(flags=addressable.AddressableLeaf.ObserverEvent.ALL)

    assert len(observers) == 3

    for observerEntry, observer in zip(observerEntries, observers):
        assert observerEntry[0] == observer

    # Now request only a subset of registred observers
    observerEntries = addressableLeaf.getObserverEntries(flags=addressable.AddressableLeaf.ObserverEvent.VALUE_CHANGED)
    assert len(observerEntries) == 2

    # Observer for post update only
    observerEntries = addressableLeaf.getObserverEntries(addressable.AddressableLeaf.ObserverEvent.ALL, onUpdateComplete=True)
    assert len(observerEntries) == 0

    addressableLeaf.addObserver(observe4, flag=addressable.AddressableLeaf.ObserverEvent.ENABLED,
                                priority=addressable.AddressableLeaf.ObserverPriority.INTERNAL_HIGH, onUpdateComplete=True)

    observerEntries = addressableLeaf.getObserverEntries(addressable.AddressableLeaf.ObserverEvent.ALL)
    assert len(observerEntries) == 3
    observerEntries = addressableLeaf.getObserverEntries(addressable.AddressableLeaf.ObserverEvent.ALL, onUpdateComplete=True)
    assert len(observerEntries) == 1


def test_AddressableLeafParents():
    parentAddressableLeaf = addressable.AddressableObject(localAddress='none', parent=None)
    addressableLeaf = addressable.AddressableLeaf(localAddress='none', parent=parentAddressableLeaf)

    assert parentAddressableLeaf.enabled is False
    assert addressableLeaf.enabled is False

    leafChildren = parentAddressableLeaf.getLeafChildren()
    assert len(leafChildren) == 0

    addressableLeaf.enabled = True

    assert parentAddressableLeaf.enabled is True
    assert addressableLeaf.enabled is True

    addressableLeaf.enabled = True
    assert addressableLeaf.enabled is True

    leafChildren = parentAddressableLeaf.getLeafChildren()
    assert len(leafChildren) == 2  # This is two as it is the oarent as well as the child

    addressableLeaf.enabled = False
    assert addressableLeaf.enabled is False

    del addressableLeaf
    del parentAddressableLeaf


def test_AddressableLeafAdresses():
    parentAddressableLeaf = addressable.AddressableObject(localAddress='parent', parent=None)
    addressableLeaf = addressable.AddressableLeaf(localAddress='child', parent=parentAddressableLeaf)

    getterAddress = addressableLeaf.localAddress
    localAdress = addressableLeaf.getLocalAddress()
    globalAdress = addressableLeaf.getGlobalAddress()

    assert getterAddress == localAdress
    assert localAdress == 'child'
    assert globalAdress == 'parent/child'

    addressableLeaf.localAddress = 'newChild'

    localAdress = addressableLeaf.getLocalAddress()
    globalAdress = addressableLeaf.getGlobalAddress()
    assert localAdress == 'newChild'
    assert globalAdress == 'parent/newChild'


def test_AddressableLeafParent():
    parentAddressableLeaf = addressable.AddressableObject(localAddress='parent', parent=None)
    addressableLeaf = addressable.AddressableLeaf(localAddress='child', parent=parentAddressableLeaf)

    assert addressableLeaf.parent == parentAddressableLeaf

    assert addressableLeaf.getRoot() == parentAddressableLeaf
    assert parentAddressableLeaf.getRoot() == parentAddressableLeaf

    newParentAddressableLeaf = addressable.AddressableObject(localAddress='newparent', parent=None)
    addressableLeaf.parent = newParentAddressableLeaf

    assert addressableLeaf.parent == newParentAddressableLeaf


#  TODO: By string not complete implementation yet
def test_AddressableByAddressString():
    root = addressable.AddressableObject(localAddress='root', parent=None)
    parent = addressable.AddressableObject(localAddress='parent', parent=root)
    leaf = addressable.AddressableLeaf(localAddress='leaf', parent=parent)

    assert leaf.getByAddressString('anything') is False
    assert leaf.getByAddressString('leaf') == leaf
    assert leaf.getByAddressString('..') == parent
    assert leaf.getByAddressString('/') == root

    assert parent.getByAddressString('anything') is False
    assert parent.getByAddressString('parent') == parent
    assert parent.getByAddressString('..') == root
    assert parent.getByAddressString('/') == root

    assert root.getByAddressString('anything') is False
    assert root.getByAddressString('root') == root
    assert root.getByAddressString('..') == root
    assert root.getByAddressString('/') == root


def test_AdressableAttribute():
    attribute = addressable.AddressableAttribute(localAddress='test', parent=None, value=None, valueType=str, lastUpdateFromCar=None)
    assert attribute.value is None

    attribute = addressable.AddressableAttribute(localAddress='test', parent=None, value='value', valueType=str, lastUpdateFromCar=None)
    assert attribute.value == 'value'

    with pytest.raises(NotImplementedError):
        attribute.value = 'newValue'


def test_AdressableObjectLeafChildren():
    addressableObject = addressable.AddressableObject(localAddress='parent', parent=None)
    childAddressableLeaf1 = addressable.AddressableAttribute(localAddress='child1', parent=addressableObject, value=None, valueType=str, lastUpdateFromCar=None)
    childAddressableLeaf2 = addressable.AddressableAttribute(localAddress='child2', parent=addressableObject, value=None, valueType=str, lastUpdateFromCar=None)

    children = addressableObject.getLeafChildren()
    assert len(children) == 0

    addressableObject.enabled = True
    children = addressableObject.getLeafChildren()
    assert len(children) == 1
    assert children[0] == addressableObject

    childAddressableLeaf1.setValueWithCarTime(newValue='test1')

    children = addressableObject.getLeafChildren()
    assert len(children) == 2
    assert children[0] == addressableObject
    assert children[1] == childAddressableLeaf1

    childAddressableLeaf2.setValueWithCarTime(newValue='test2')

    children = addressableObject.getLeafChildren()
    assert len(children) == 3
    assert children[0] == addressableObject
    assert children[1] == childAddressableLeaf1
    assert children[2] == childAddressableLeaf2
