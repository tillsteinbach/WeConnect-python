import argparse

from PIL import Image

from weconnect import weconnect, addressable


def main():
    """ Simple example showing how to save pictures """
    parser = argparse.ArgumentParser(
        prog='allVehciles',
        description='Example retrieving all vehciles in the account')
    parser.add_argument('-u', '--username', help='Username of Volkswagen id', required=True)
    parser.add_argument('-p', '--password', help='Password of Volkswagen id', required=True)
    parser.add_argument('-o', '--outputDir', help='Output directory', required=True)

    args = parser.parse_args()

    def saveElement(element, flags):
        """Simple callback for saving the pictures

        Args:
            element (AddressableObject): Object for which an event occured
            flags (AddressableLeaf.ObserverEvent): Information about the type of the event
        """
        del flags
        if isinstance(element, addressable.AddressableAttribute) and element.valueType == Image.Image:
            element.saveToFile(f'{args.outputDir}/{element.localAddress}.png')

    print('#  Initialize WeConnect')
    weConnect = weconnect.WeConnect(username=args.username, password=args.password, updateAfterLogin=False, loginOnInit=False)
    print('#  Login')
    weConnect.login()
    print('#  Register for events')
    weConnect.addObserver(saveElement, addressable.AddressableLeaf.ObserverEvent.VALUE_CHANGED)
    print('#  update')
    weConnect.update()


if __name__ == '__main__':
    main()
