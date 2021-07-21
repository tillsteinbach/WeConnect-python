

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
- [WeConnect-cli](https://github.com/tillsteinbach/WeConnect-cli): A commandline interface to interact with WeConnect
- [WeConnect-MQTT](https://github.com/tillsteinbach/WeConnect-mqtt): A MQTT Client that provides WeConnect data to the MQTT Broker of your choice (e.g. your home automation solution such as [ioBroker](https://www.iobroker.net), [FHEM](https://fhem.de) or [Home Assistant](https://www.home-assistant.io))

## Tested with
- Volkswagen ID.3 Modelyear 2021
- Volkswagen Passat GTE Modelyear 2021

## Login & Consent
WeConnect-python is based on the new WeConnect ID API that was introduced with the new series of ID cars. If you use another car or hybrid you probably need to agree to the terms and conditions of the WeConnect ID interface. Easiest to do so is by installing the WeConnect ID app on your smartphone and login there. If necessary you will be asked to agree to the terms and conditions.

## Reporting Issues
Please feel free to open an issue at [GitHub Issue page](https://github.com/tillsteinbach/WeConnect-python/issues) to report problems you found.

### Known Issues
- The API is in alpha state and may change unexpectedly at any time! Please conscider this and pin to a specific version if you depend on it.
- Examples and API documentation is missing

## Credits
Inspired by [TA2k/ioBroker.vw-connect](https://github.com/TA2k/ioBroker.vw-connect/) that gave me a point to start working with the API
