from weconnect import addressable


def test_AddressableLeafGetObservers():
    addressableLeaf = addressable.AddressableLeaf(localAddress='none', parent=None)

    def observe1():
        pass

    def observe2():
        pass

    def observe3():
        pass

    addressableLeaf.addObserver(observe1, flag=addressable.AddressableLeaf.ObserverEvent.VALUE_CHANGED,
                                priority=addressable.AddressableLeaf.ObserverPriority.INTERNAL_LOW)
    addressableLeaf.addObserver(observe2, flag=addressable.AddressableLeaf.ObserverEvent.ENABLED,
                                priority=addressable.AddressableLeaf.ObserverPriority.INTERNAL_HIGH)
    addressableLeaf.addObserver(observe3, flag=addressable.AddressableLeaf.ObserverEvent.ALL,
                                priority=addressable.AddressableLeaf.ObserverPriority.USER_MID)

    observerEntries = addressableLeaf.getObserverEntries(addressable.AddressableLeaf.ObserverEvent.ALL)

    assert len(observerEntries) == 3

    assert observerEntries[0][0] == observe2
    assert observerEntries[0][1] == addressable.AddressableLeaf.ObserverEvent.ENABLED
    assert observerEntries[0][2] == addressable.AddressableLeaf.ObserverPriority.INTERNAL_HIGH

    assert observerEntries[1][0] == observe3
    assert observerEntries[1][1] == addressable.AddressableLeaf.ObserverEvent.ALL
    assert observerEntries[1][2] == addressable.AddressableLeaf.ObserverPriority.USER_MID

    assert observerEntries[2][0] == observe1
    assert observerEntries[2][1] == addressable.AddressableLeaf.ObserverEvent.VALUE_CHANGED
    assert observerEntries[2][2] == addressable.AddressableLeaf.ObserverPriority.INTERNAL_LOW
