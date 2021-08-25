# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- No unreleased changes so far

## [0.19.3] - 2021-08-25
### Fixed
- Fix setting float values from int input
- Fix controls for charging

### Added
- New error state: fail_vehicle_is_offline
- New status: climatisationSettingsRequestStatus

## [0.19.2] - 2021-08-20
### Fixed
- Fixed bad gateway error with parking position when car is driving

## [0.19.1] - 2021-08-19
### Fixed
- Catching timeout error
- Fixed parking position with renaming attributes for position after change in the API

## [0.19.0] - 2021-08-15
### Added
- Possibility to set caching time for picture downloads seperately

## [0.18.3] - 2021-08-14
### Fixed
- Bug with failing picture download

## [0.18.2] - 2021-08-11
### Fixed
- Bug with observers when disabling attributes

## [0.18.1] - 2021-08-10
### Fixed
- Fix parking position disabling when parking position is gone
- Fix force parameter for updates

## [0.18.0] - 2021-08-09
### Added
- Possibility to fetch chargers without updating chargersList
- Possibility to remove registered observers

## [0.17.0] - 2021-08-07
### Added
- New API elements for GUEST_USER, UNKNOWN enrollment status and delayed and timeout of operations

### Changed
- Parking position is removed when not available anymore (e.g. because car is driving) can be used to detect that the car is not stationary

## [0.16.0] - 2021-08-05
### Added
- Possibility to fill cache from strings instead of files

### Fixed
- Observers that are triggered after the update finished were failing in certain cases

## [0.15.1] - 2021-07-30
### Fixed
- Fixes charging and climatization controls

## [0.15.0] - 2021-07-29
### Added
- Possibility to add Observers that are triggered after the update finished

## [0.14.0] - 2021-07-28
### Fixed
- Fix for sorting observers (fixes crash)

### Added
- Added WindowHeatingState.INVALID
- Added ChargeMode.INVALID
- New statuses lvBatteryStatus (seen for ID vehicles), maintenanceStatus for legacy cars (contains milage and km/days until service) 

## [0.13.2] - 2021-07-26
### Changed
- Improved error message when user consent is missing
- More robust against server side errors when refreshing the tokens

## [0.13.1] - 2021-07-26
### Fixed
- Packaging of subpackages

### Changed
- removed relative imports

## [0.13.0] - 2021-07-26
### Added
- Dummy for maintenance status (currently no data provided, only error messages)
- Added attribute for chargeMode

### Changed
- Divide Code in several modules for better maintenance
- More compact string formating

## [0.12.3] - 2021-07-25
### Fixed
- Allow status code 404 for parking position

## [0.12.2] - 2021-07-18
### Fixed
- Exception due to changes in the API fixed
- Allow status code 204 for parking position

## [0.12.1] - 2021-07-06
### Added
- Possibility to disable capabilities and pictures in constructor

## [0.12.0] - 2021-07-05
### Added
- Possibility to retrieve images and save attributes to files on disk

## [0.11.1] - 2021-07-03
### Fixed
- Addressing of statuses

## [0.11.0] - 2021-07-02
### Added
- Possibility to retrieve data for public charging stations

### Fixed
- Make robust against null data in response

## [0.10.0] - 2021-06-28
### Changed
- Use access token instead of id token
- More robust on connection problems with WeConnect servers

### Fixed
- Fixed TypeError when maxAge is not set (fixes #5)
- Fixed that Enums can be set by Enum and not only by value

## [0.9.1] - 2021-06-21
### Fixed
- Added chargeMode off (fixes #4)

## [0.9.0] - 2021-06-21
### Added
- Fail status for all target operations

## [0.8.2] - 2021-06-21
### Fixed
- Fixed getLeafChildren Method

## [0.8.1] - 2021-06-21
### Fixed
- Wrong error message containing unused attribute

## [0.8.0] - 2021-06-21
### Added
- Support for chargeMode attribute

## [0.7.0] - 2021-06-21
### Added
- Support for singleTimer attribute

## [0.6.2] - 2021-06-18
### Fixed
- Small bugfixes

### Added
- First set of tests 

## [0.6.1] - 2021-06-13
### Fixed
- Bug in observers that did not allow correct sorting of the Enum

## [0.6.0] - 2021-06-11
### Added
- New attribute coUsers for users in secondary role

### Changed
- Enum used for role and enrollmentStatus attributes

## [0.5.2] - 2021-06-10
### Fixed
- Charging settings setting and request status response

## [0.5.1] - 2021-06-09
### Fixed
- Bug with missing recurring timer

## [0.5.0] - 2021-06-09
### Added
- Attribute Change from String

### Fixed
- Fix ChargingSettings to String method to use Enum value instead of raw enum 
format"

## [0.4.1] - 2021-06-06
### Changed
- Check allowed values for maximum charge current

### Fixed
- Problem with event observers

###
- Added events for deleted objects

## [0.4.0] - 2021-06-04
### Added:
- Allow setting parameters through the API

### Fixed:
- Various small fixes

## [0.3.2] - 2021-06-02
### Fixed:
- Various small API problems
- Prepared for setters

## [0.3.1] - 2021-05-31
### Added
- Handling of API error for electric range

### Fixed
- Problems with caching feature

## [0.3.0] - 2021-05-28
### Added
- Improved error handling for login

## [0.2.1] - 2021-05-28
### Fixed
- Make weconnect object printable by __str__ method

## [0.2.0] - 2021-05-27
### Added
- Possibility to persist tokens through the API
- Possibility to cache data through the API

## [0.1.1] - 2021-05-26
Minor fix in observer interface

## [0.1.0] - 2021-05-26
Initial release

[unreleased]: https://github.com/tillsteinbach/WeConnect-python/compare/v0.19.3...HEAD
[0.19.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.19.3
[0.19.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.19.2
[0.19.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.19.1
[0.19.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.19.0
[0.18.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.18.3
[0.18.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.18.2
[0.18.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.18.1
[0.18.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.18.0
[0.17.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.17.0
[0.16.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.16.0
[0.15.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.15.1
[0.15.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.15.0
[0.14.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.14.0
[0.13.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.13.2
[0.13.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.13.1
[0.13.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.13.0
[0.12.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.12.3
[0.12.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.12.2
[0.12.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.12.1
[0.12.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.12.0
[0.11.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.11.1
[0.11.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.11.0
[0.10.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.10.0
[0.9.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.9.1
[0.9.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.9.0
[0.8.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.8.2
[0.8.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.8.1
[0.8.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.8.0
[0.7.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.7.0
[0.6.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.6.2
[0.6.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.6.1
[0.6.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.6.0
[0.5.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.5.2
[0.5.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.5.1
[0.5.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.5.0
[0.4.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.4.1
[0.4.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.4.0
[0.3.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.3.2
[0.3.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.3.1
[0.3.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.3.0
[0.2.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.2.1
[0.2.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.2.0
[0.1.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.1.1
[0.1.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.1.0
