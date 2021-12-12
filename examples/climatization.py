import argparse

from weconnect import weconnect

from weconnect.elements.control_operation import ControlOperation


def main():
    """ Simple example showing how to start climatization in a vehicle by providing the VIN as a parameter """
    parser = argparse.ArgumentParser(
        prog='climatization',
        description='Example starting climatizaton')
    parser.add_argument('-u', '--username', help='Username of Volkswagen id', required=True)
    parser.add_argument('-p', '--password', help='Password of Volkswagen id', required=True)
    parser.add_argument('--vin', help='VIN of the vehicle to start climatization', required=True)

    args = parser.parse_args()

    print('#  Initialize WeConnect')
    weConnect = weconnect.WeConnect(username=args.username, password=args.password, updateAfterLogin=False, loginOnInit=False)
    print('#  Login')
    weConnect.login()
    print('#  update')
    weConnect.update()

    for vin, vehicle in weConnect.vehicles.items():
        if vin == args.vin:
            if "climatisationStatus" in vehicle.statuses and vehicle.statuses["climatisationStatus"].enabled:
                if vehicle.statuses["climatisationStatus"].climatisationState.enabled:
                    print('#  climatization status')
                    print(vehicle.statuses["climatisationStatus"].climatisationState.value)

            if vehicle.controls.climatizationControl is not None and vehicle.controls.climatizationControl.enabled:
                print('#  start climatization')
                vehicle.controls.climatizationControl.value = ControlOperation.START
    print('#  done')


if __name__ == '__main__':
    main()
