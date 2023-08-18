

# WeConnect-python
[![GitHub sourcecode](https://img.shields.io/badge/Source-GitHub-green)](https://github.com/tillsteinbach/WeConnect-python/)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/tillsteinbach/WeConnect-python)](https://github.com/tillsteinbach/WeConnect-python/releases/latest)
[![GitHub](https://img.shields.io/github/license/tillsteinbach/WeConnect-python)](https://github.com/tillsteinbach/WeConnect-python/blob/master/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/tillsteinbach/WeConnect-python)](https://github.com/tillsteinbach/WeConnect-python/issues)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/weconnect?label=PyPI%20Downloads)](https://pypi.org/project/weconnect/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/weconnect)](https://pypi.org/project/weconnect/)
[![Donate at PayPal](https://img.shields.io/badge/Donate-PayPal-2997d8)](https://www.paypal.com/donate?hosted_button_id=2BVFF5GJ9SXAJ)
[![Sponsor at Github](https://img.shields.io/badge/Sponsor-GitHub-28a745)](https://github.com/sponsors/tillsteinbach)

Python API for the Volkswagen WeConnect Services. If you are not a developer and ended up here you probably want to check out a project using this library (see below).

## Projects in which the library is used
- [VWsFriend](https://github.com/tillsteinbach/VWsFriend): VWsFriend records statistics about your car (charging sessions, battery, trips, fueling, etc.) and displays them nicely. It also allows you to forward data from the car to other applications such as [A better routeplanner](https://abetterrouteplanner.com/) and allows you to integrate your car into [Apple HomeKit](https://www.apple.com/ios/home/)
- [WeConnect-cli](https://github.com/tillsteinbach/WeConnect-cli): A commandline interface to interact with WeConnect
- [WeConnect-MQTT](https://github.com/tillsteinbach/WeConnect-mqtt): A MQTT Client that provides WeConnect data to the MQTT Broker of your choice (e.g. your home automation solution such as [ioBroker](https://www.iobroker.net), [FHEM](https://fhem.de) or [Home Assistant](https://www.home-assistant.io))

## WARNING
Use this API with care. If you use it wrong (e.g. too many logins, repeated login attempts with wrong password, ...) your account may get blocked.

## Install
```
pip3 install weconnect[Images]
```
The minimum required python version is 3.8

## Getting started
- To get started have a look in the [examples folder](https://github.com/tillsteinbach/WeConnect-python/tree/main/examples)

## Tested with
- Volkswagen ID.3 Modelyear 2021
- Volkswagen Passat GTE Modelyear 2021

## Login & Consent
WeConnect-python is based on the new WeConnect API that was introduced with the new series of ID cars. If you use another car or hybrid you probably need to agree to the terms and conditions of the new WeConnect interface. Easiest to do so is by installing the Volkswagen app on your smartphone and login there. If necessary you will be asked to agree to the terms and conditions.

## Reporting Issues
Please feel free to open an issue at [GitHub Issue page](https://github.com/tillsteinbach/WeConnect-python/issues) to report problems you found.

### Known Issues
- The API is in alpha state and may change unexpectedly at any time! Please conscider this and pin to a specific version if you depend on it.
- Examples and API documentation is missing

## Credits
Inspired by [TA2k/ioBroker.vw-connect](https://github.com/TA2k/ioBroker.vw-connect/) that gave me a point to start working with the API

## Seat, Cupra, Skoda IV, ...
In an effort to try to make WeConnect-python also to work with latest generation of vehicles from other volkswagen brands I'm looking for users to temporarily share access to their accounts. If you are willing to support please send me a message.
- Already tried: Cupra Born (The API looks a bit different, maybe it is older, I will check again in some weeks), thanks to the user initdebugs
