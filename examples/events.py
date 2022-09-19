import argparse
from time import sleep

from weconnect import weconnect, addressable


def main():
    """ Simple example showing how to work with events """
    parser = argparse.ArgumentParser(
        prog='allVehciles',
        description='Example retrieving all vehciles in the account')
    parser.add_argument('-u', '--username', help='Username of Volkswagen id', required=True)
    parser.add_argument('-p', '--password', help='Password of Volkswagen id', required=True)

    args = parser.parse_args()

    print('#  Initialize WeConnect')
    weConnect = weconnect.WeConnect(username=args.username, password=args.password, updateAfterLogin=False, loginOnInit=False)
    print('#  Login')
    weConnect.login()
    print('#  Register for events')
    weConnect.addObserver(onWeConnectEvent, addressable.AddressableLeaf.ObserverEvent.VALUE_CHANGED  # pylint: disable=unsupported-binary-operation
                          | addressable.AddressableLeaf.ObserverEvent.ENABLED  # pylint: disable=unsupported-binary-operation
                          | addressable.AddressableLeaf.ObserverEvent.DISABLED)  # pylint: disable=unsupported-binary-operation
    print('#  update')
    while True:
        weConnect.update()
        sleep(300)


def onWeConnectEvent(element, flags):
    """Simple callback example

    Args:
        element (AddressableObject): Object for which an event occured
        flags (AddressableLeaf.ObserverEvent): Information about the type of the event
    """
    if isinstance(element, addressable.AddressableAttribute):
        if flags & addressable.AddressableLeaf.ObserverEvent.ENABLED:
            print(f'New attribute is available: {element.getGlobalAddress()}: {element.value}')
        elif flags & addressable.AddressableLeaf.ObserverEvent.VALUE_CHANGED:
            print(f'Value changed: {element.getGlobalAddress()}: {element.value}')
        elif flags & addressable.AddressableLeaf.ObserverEvent.DISABLED:
            print(f'Attribute is not available anymore: {element.getGlobalAddress()}')


if __name__ == '__main__':
    main()
