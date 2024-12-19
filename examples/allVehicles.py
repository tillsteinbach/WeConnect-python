import argparse

from weconnect import weconnect


def main():
    """ Simple example showing how to retrieve all vehicles from the account """
    parser = argparse.ArgumentParser(
        prog='allVehicles',
        description='Example retrieving all vehicles in the account')
    parser.add_argument('-u', '--username', help='Username of Volkswagen id', required=True)
    parser.add_argument('-p', '--password', help='Password of Volkswagen id', required=True)

    args = parser.parse_args()

    print('#  Initialize WeConnect')
    weConnect = weconnect.WeConnect(username=args.username, password=args.password, updateAfterLogin=False, loginOnInit=False)
    print('#  Login')
    weConnect.login()
    print('#  update')
    weConnect.update()
    print('#  print results')
    for vin, vehicle in weConnect.vehicles.items():
        del vin
        print(vehicle)
    print('#  done')


if __name__ == '__main__':
    main()
