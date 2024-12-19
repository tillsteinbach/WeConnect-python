# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- No unreleased changes so far

## [0.60.7] - 2024-12-19
### Fixed
- Fix for reoccuring consent requests

### Added
- Warning light color white

## [0.60.6] - 2024-12-06
### Fixed
- Fixed error message when new terms and conditions need to be accepted

## [0.60.5] - 2024-09-13
### Added
- AUTHTYPE PROPRIETARY added
- ChargingScenarios IMMEDIATELY_CHARGING_ACTIVE, IMMEDIATELY_CHARGING_FINISHED, CHARGING_TO_DEPARTURE_TIME_WAITING, CHARGING_TO_DEPARTURE_TIME_ACTIVE, OPTIMISED_CHARGING_FINISHED, ERROR_CHARGING_SYSTEM added
- climatisationTemperatureOutside added (for now only error shown due to missing support in cars firmware)

## [0.60.4] - 2024-08-02
### Added
- usePrivateCurrentEnabled added
- maxChargeCurrentAC_A added
- self.chargingScenario added
- self.targetDateTimeLocal added
- ICON_NOT_FOUND added

### Changed
- Updated pillow dependency to 10.4.0

## [0.60.3] - 2024-06-13
### Added
- ChargeType UNSUPPORTED added
- TargetSOCReachable reachable, notReachable added
- Warning light category OTHER added
- navigationTargetSOC_pct added (Thanks to User @Lake292 for the contribution)
- TemperatureOutsideStatus added (Thanks to User @Lake292 for the contribution)

### Changed
- Updated pillow dependency to 10.3.0
- Updated requests dependency to 2.32.3

## [0.60.2] - 2024-02-28
### Fixed
- Fixes a bug introduced by the new timers attributes

## [0.60.1] - 2024-02-27
### Added
- Added new departure timer attributes

## [0.60.0] - 2024-02-26
### Fixed
- Fixes a bug in activeVentilation and auxiliaryHeating controls
- Problem showing error related to miles/km conversion fixed
- Problem with RGBA conversion fixed

### Added
- AuxiliaryHeatingStatus added
- Several new Attributes added

### Changed
- Updated pillow dependency to 10.2.0, fixing potential security issue
- Updated several dependencies

## [0.59.5] - 2023-11-15
### Fixed
- Fixes a bug in activeVentilation and auxiliaryHeating controls

### Changed
- Do not immediatlyretry on 429 errors

## [0.59.4] - 2023-10-29
### Changed
- Improves error propagation on 429 errors

## [0.59.3] - 2023-10-27
### Fixed
- Fixes a bug introduced by the range correction

## [0.59.2] - 2023-10-27
### Fixed
- Fixes a bug in the API that causes incorrect range values for cars using miles instead of km (thanks to user @bendavidson for the contribution)

### Added
- Added attributes for Hv battery temperature

## [0.59.1] - 2023-10-16
### Added
- Added PCS_REMOTE authentification to charging stations enum

### Changed
- Updated pillow dependencies

## [0.59.0] - 2023-10-16
### Added
- Added several new statuses and attributes

## [0.58.3] - 2023-09-23
### Fixed
- Fixed bug with new handling of 429 errors

## [0.58.2] - 2023-09-22
### Added
- New error class to deal with 429 errors from server (too many requests)

## [0.58.1] - 2023-09-22
### Added
- Added some new auth types for charging stations

### Changed
- Updated build dependencies

## [0.58.0] - 2023-09-03
### Added
- honking and flashing on cars supporting honkAndFlash capability
- carType FUEL added
- BatteryPowerLevel EMERGENCY added
- trip averageAuxConsumption and averageRecuperation added for selected cars
- updating of trips fixed (thanks to user gilder0 for contributing)

### Fixed
- Fixed some linter errors

### Changed
- Updated build dependencies
- Improved logging of charging station errors

## [0.57.0] - 2023-07-20
### Added
- honking and flashing on cars supporting honkAndFlash capability

## [0.56.2] - 2023-07-12
### Fixed
- Another small bugfix for fetching trips

## [0.56.1] - 2023-07-12
### Fixed
- Don't throw error when fetching trips and car is not supporting certain categories

## [0.56.0] - 2023-07-10
### Added
- BETA: functionality to read status for active ventilation and auxiliary heating (non electric cars)
- BETA: functionality to control active ventilation and auxiliary heating (non electric cars)
- Added heaterSource attribute in climatization settings
- Possibility to read trip statistics (if supported by the car)

### Changed
- Updated pillow dependency to 10.0.0

## [0.55.1] - 2023-06-09
### Added
- added INVALID ExternalPower state

### Changed
- Updated requests dependency to 2.31.0

## [0.55.0] - 2023-04-28
### Fixed
- Library will retry login (but give an error) if refresh token got invalidated

### Added
- Add suport for battery care settings
- Add timers operation to fix warnings
- Add invalid light status

### Changed
- Updated dependencies

## [0.54.2] - 2023-03-02
### Fixed
- Fixes unknown operation error

## [0.54.1] - 2023-02-28 (PLEASE NOTICE! All depending applications need to imediatly update to work again!)
### Fixed
- Changed URLs to the new URLs necessary to contact the backend

## [0.54.0] - 2023-02-20
### Changed
- Update acii_magic to 2.2.1

## [0.53.0] - 2023-02-20
### Added
- Add very basic thread safety by protecting update
- Add ENGINE category for warning lights

### Fixed
- Problem with missing token

## [0.52.0] - 2023-02-15
### Added
- Add new error state (Thanks to user madd0)
- Add new timer attribute targetSOC_pct

### Fixed
- Bug that could make attributes disappear on certain values

## [0.51.1] - 2023-02-03
### Changed
- Updated dependencies

### Fixed
- Logging output for missing enums

## [0.51.0] - 2023-01-13
### Added
- BrandCode 'N' added for ID Buzz (Nutzfahrzeuge) support

### Changed
- Updated dependencies for pillow and pylint

## [0.50.1] - 2022-11-30
### Fixed
- Fixed bug where an attribute was not correctly enabled again when it reappears without changed value (Big thanks to user @ColinRobbins for this finding)

## [0.50.0] - 2022-11-21
### Added
- Support for proxy servers (thanks to user towe96)
- New option for log handle filter

## [0.49.0] - 2022-11-15
### Added
- Add new currentFuelLevel_pct attribute

### Changed
- Updated dependencies for pillow, oauthlib and pylint
- Relogin if the refresh token expired

## [0.48.3] - 2022-10-13
### Changed
- Don't store cookies in between requests
- No cache header added

## [0.48.2] - 2022-10-04
### Added
- Add invalid door lock state

## [0.48.1] - 2022-09-23
### Added
- Tire warning light category

### Fixed
- Bug with honk and flash endpoint

## [0.48.0] - 2022-09-19
### Added
- Preparations for Honk and Flash Endpoint
- doorLockStatus attribute added

### Changed
- Show controls only if capability is available
- Updated oauth requirements

### Fixed
- fix parsing of empty strings

## [0.47.1] - 2022-08-24
### Fixed
- Allow climatization without external power when the real setting from the car was not received

## [0.47.0] - 2022-08-09
### Added
- Support for S-PIN
- Support for locking/unlocking

## [0.46.0] - 2022-08-02
### Added
- Attributes for diesel cars
- New status departureTimersStatus & chargingProfilesStatus
- Support for python 3.10

### Fixed
- Build without image support now works without asking for requirements

## [0.45.1] - 2022-07-25
### Fixed
- ReadinessStatus fixed after changes in backend

## [0.45.0] - 2022-07-14
### Added
- Allow to force relogin after a period of time

## [0.44.2] - 2022-06-28
### Fixed
- Fixed error with warning light icon

## [0.44.1] - 2022-06-28
### Fixed
- Fixed setting climatisation settings (all but climatisationWithoutExternalPower)

## [0.44.0] - 2022-06-28
### Added
- Allow to control window heating
- Login procedure for MyCupra (this is login functionality only, no data retrieval yet!)
- ChargingState: DISCHARGING
- ChargeMode: HOME_STORAGE_CHARGING, IMMEDIATE_DISCHARGING
- window heating control: only for MEB cars
- wake-up control: not for MEB cars
- DevicePlatform: MBB_OFFLINE
- Role: CDIS_UNKNOWN_USER
- UserRoleStatus: DISABLED_HMI, DISABLED_SPIN, DISABLED_PU_SPIN_RESET, CDIS_UNKNOWN_USER

## [0.43.2] - 2022-06-23
### Added
- Added new values for attribute externalPower: unsupported
- Added new values for attribute chragingStatus: unsupported

## [0.43.1] - 2022-06-23
### Added
- Added new values for attribute externalPower: active
- Added new values for attribute ledColor: green, red

## [0.43.0] - 2022-06-22 (Happy birthday Peer!)
### Added
- Added new attribute: externalPower

## [0.42.0] - 2022-06-17
### Added
- Added new attributes: brandCode, autoUnlockPlugWhenChargedAC, ledColor (warning, it is not yet clear what values are allowed, so use these with caution)

## [0.41.0] - 2022-05-25
 ### Added
 - selective allCapable added to only fetch data that is provided by the car

 ### Fixed
 - Errors in domains are catched and do not produce warnings anymore

## [0.40.0] - 2022-05-12
### Added
- weconnect-trace-id header added

### Fixed
- Publish remaining climatization time only once

### Changed
- user-agent header updated
- selective feature changed

## [0.39.0] - 2022-04-12
### Added
- Support for warning lights including png icons

### Changed
- Update pillow requirement from 9.0.1 to 9.1.0

## [0.38.1] - 2022-03-22
### Changed
- Improved error messages on login errors

## [0.38.0] - 2022-03-19
### Added
- Added BatteryPowerLevel 'off' in readiness status.
- Added ClimatizationStatus 'invalid'
- Added occurringOn and startTime in singe timer

## [0.37.2] - 2022-03-04
### Fixed
- Catch error when server is not responding correctly during login

## [0.37.1] - 2022-02-28
### Fixed
- Bug in charging control

## [0.37.0] - 2022-02-25
### Fixed
- Requests tracking behaviour
- Catch error when token could not be fetched

### Changed
- Requests changed from list to dict

### Added
- Possibility to use temperature when startng climatisation
- Added fail_no_external_power to generic request status
- Added chargeType attribute to chargingStatus
- Added chargingSettings attribute to chargingStatus

## [0.36.4] - 2022-02-12
### Fixed
- Fixes bug in charging state API fixing procedure

## [0.36.3] - 2022-02-11
### Fixed
- Fixes login again after changes in the login form

## [0.36.2] - 2022-02-10
### Fixed
- Fixes json output for values that are zero

## [0.36.1] - 2022-02-10
### Fixed
- Fixes for chargePower, chargeRate and remaining climatisationTime when fixAPI=True

## [0.36.0] - 2022-02-03
### Changed
- Refactors the OAuth procedure

### Added
- Add authentification for WeCharge
- Attributes for automation/chargingProfiles
- Possibility to output and save json format for the whole or parts of the tree
- Added status fail_charge_plug_not_connected

## [0.35.1] - 2022-01-28
### Fixed
- Quick fix for login problem due to changes of the login page

## [0.35.0] - 2022-01-24
### Changed
- Better tracking of several parallel requests

### Fixed
- Reduced number of unnecesary events for none values

## [0.34.0] - 2022-01-23
### Changed
- Code refactoring

### Fixed
- duplicated entries in getChildren
- Domains are now in domains topic
- Fixed Request Tracker
- Parking Position also selectivevly usable

## [0.33.0] - 2022-01-18
### Added
- Add new tags attribute

## [0.32.1] - 2022-01-17
### Fixed
- Fixed a problem where the temperature of the climatization is always set to 20.5 C

## [0.32.0] - 2022-01-14
### Fixed
- Change datatype for chargePower_kW and chargeRate_kmph from Integer to Float

## [0.31.0] - 2022-01-14
### Added
- Image support is now optional and can be installed with pip install weconnect\[Images\], remove \[Images\] if you do not need image support in your project
- New disconnect method that cancles all timers and thus terminates all additional threads
- New timeout parameter to limit the time waiting in requests for the VW servers

## [0.30.4] - 2022-01-12
### Fixed
- Fix problem with stored tokens
- Hide 504 gateway_timeout error on missing parking position

## [0.30.3] - 2022-01-11
### Fixed
- Make login more robust against server errors
- Hide 204 no_content error on missing parking position

## [0.30.2] - 2022-01-10
### Fixed
- timezone problem

## [0.30.1] - 2022-01-10
### Fixed
- missing init file

## [0.30.0] - 2022-01-10
### Added
- Request Tracker to track progress of control requests

## [0.29.0] - 2022-01-05
### Added
- Added MBB Platform (used in e.g. e-up)
- Duplicate log entry filter
- Added vehicle warning lights

### Changed
- Changed to new selective update endpoint. ***Warning this is a breaking change in the API!***

### Fixed
- conflicts when simplejson is installed and preferred from requests

## [0.28.0] - 2021-12-20
### Added
- decoding of capability status
- new charge modes
- new plug states
- new engine and car types
- new status capabilitiesStatus

### Changed
- Only fetch parking position if the capability is enabled

## [0.27.2] - 2021-12-16
- No changes, just a new version number for pypi

## [0.27.1] - 2021-12-16
### Fixed
- Fixed exception when WeConnect Server unnecessarily asks for a new login

## [0.27.0] - 2021-12-09
### Added
- added UnlockPlugState permanent

## [0.26.0] - 2021-12-08
### Added
- Add new gasoline car type

## [0.25.1] - 2021-12-01
### Fixed
- Fixed missing readiness_status module

## [0.25.0] - 2021-12-01
### Added
- Add new status fail_battery_low
- Add new attributes readinessStatus, readinessBatterySupportStatus and devicePlatform

## [0.24.0] - 2021-11-25
### Added
- Add new Charging State CHARGE_PURPOSE_REACHED_CONSERVATION (thanks to [gordoncrossley](https://github.com/gordoncrossley) for reporting)

## [0.23.1] - 2021-11-19
### Fixed
- Fixed addressing of timers

## [0.23.0] - 2021-11-19
### Added
- Add new Charging State CHARGE_PURPOSE_REACHED_NOT_CONSERVATION_CHARGING (thanks to [gordoncrossley](https://github.com/gordoncrossley) for reporting)

## [0.22.1] - 2021-11-04
### Fixed
- Fixed ChunkedEncodingError when server is terminating the connection

## [0.22.0] - 2021-11-01
### Added
- Added new userRoleStatus attribute

### Fixed
- Fix when refreshing of tokens fail, start retry procedure

## [0.21.5] - 2021-10-21
### Fixed
- Fix badge for unlocked vehicle

## [0.21.4] - 2021-10-19
### Fixed
- Fixes return None for elapsed statistics if no statistics are available

## [0.21.3] - 2021-10-14
### Fixed
- Fixes picture caching

## [0.21.2] - 2021-10-11
### Fixed
- Fixes error recording again

## [0.21.1] - 2021-10-10
### Fixed
- Fixes error recording
- Will delete cache if file is corrupted

## [0.21.0] - 2021-10-06
### Added
- Possibility to register for error callbacks
- Records time necessary to retrieve data

### Fixed
- Climate settings

## [0.20.15] - 2021-09-28
### Fixed
- Fixed badges

## [0.20.14] - 2021-09-27
### Fixed
- Fixed resetting of parkingposition while driving

## [0.20.13] - 2021-09-23
### Added
- New attributes: electricRange, gasolineRange

## [0.20.12] - 2021-09-23
### Fixed
- Fixed problems coming from changes in the API

### Added
- New images with badges
- New attributes: odometerMeasurement, rangeMeasurements, unitInCar, targetTemperature_F

## [0.20.11] - 2021-09-16
### Fixed
- Handling new exceptions coming from retries

## [0.20.10] - 2021-09-15
### Added
- Will retry a request 3 times to try to make instable server connection more stable

## [0.20.9] - 2021-09-14
### Fixed
- Problem when token could not be refreshed

## [0.20.8] - 2021-09-10
### Fixed
- Fix if range is corrupted

## [0.20.7] - 2021-09-09
### Added
- Catching aborted connections and throwing RetrievelErrors instead

## [0.20.6] - 2021-09-02
### Fixed
- Allow forbidden (403) return code for parking position
- Continue fetching data even if retrieval for one car fails

## [0.20.5] - 2021-09-02
### Fixed
- Fixed UnboundLocalError in condition GDC_MISSING

## [0.20.4] - 2021-09-01
### Fixed
- Removed python typing Final as it is not available in python 3.7

## [0.20.3] - 2021-08-30
### Fixed
- Display of consent url fixed

### Added
- Added new error state delayed

## [0.20.2] - 2021-08-26
### Added
- New error messages for parking position
- Started to add typing information

## [0.20.1] - 2021-08-26
### Added
- New error state: fail_ignition_on

## [0.20.0] - 2021-08-25
### Changed
- AccessStatus OverallStatus from String value to Enumeration

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

[unreleased]: https://github.com/tillsteinbach/WeConnect-python/compare/v0.60.7...HEAD
[0.60.7]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.60.7
[0.60.6]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.60.6
[0.60.5]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.60.5
[0.60.4]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.60.4
[0.60.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.60.3
[0.60.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.60.2
[0.60.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.60.1
[0.60.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.60.0
[0.59.5]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.59.5
[0.59.4]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.59.4
[0.59.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.59.3
[0.59.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.59.2
[0.59.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.59.1
[0.59.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.59.0
[0.58.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.58.3
[0.58.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.58.2
[0.58.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.58.1
[0.58.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.58.0
[0.57.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.57.0
[0.56.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.56.2
[0.56.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.56.1
[0.56.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.56.0
[0.55.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.55.1
[0.55.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.55.0
[0.54.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.54.2
[0.54.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.54.1
[0.54.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.54.0
[0.53.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.53.0
[0.52.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.52.0
[0.51.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.51.1
[0.51.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.51.0
[0.50.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.50.1
[0.50.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.50.0
[0.49.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.49.0
[0.48.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.48.3
[0.48.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.48.2
[0.48.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.48.1
[0.48.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.48.0
[0.47.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.47.1
[0.47.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.47.0
[0.46.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.46.0
[0.45.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.45.1
[0.45.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.45.0
[0.44.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.44.2
[0.44.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.44.1
[0.44.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.44.0
[0.43.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.43.2
[0.43.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.43.1
[0.43.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.43.0
[0.42.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.42.0
[0.41.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.41.0
[0.40.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.40.0
[0.39.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.39.0
[0.38.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.38.1
[0.38.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.38.0
[0.37.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.37.2
[0.37.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.37.1
[0.37.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.37.0
[0.36.4]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.36.4
[0.36.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.36.3
[0.36.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.36.2
[0.36.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.36.1
[0.36.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.36.0
[0.35.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.35.1
[0.35.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.35.0
[0.34.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.34.0
[0.33.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.33.0
[0.32.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.32.1
[0.32.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.32.0
[0.31.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.31.0
[0.30.4]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.30.4
[0.30.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.30.3
[0.30.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.30.2
[0.30.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.30.1
[0.30.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.30.0
[0.29.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.29.0
[0.28.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.28.0
[0.27.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.27.2
[0.27.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.27.1
[0.27.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.27.0
[0.26.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.26.0
[0.25.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.25.1
[0.25.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.25.0
[0.24.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.24.0
[0.23.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.23.1
[0.23.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.23.0
[0.22.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.22.1
[0.22.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.22.0
[0.21.5]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.21.5
[0.21.4]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.21.4
[0.21.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.21.3
[0.21.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.21.2
[0.21.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.21.1
[0.21.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.21.0
[0.20.15]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.15
[0.20.14]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.14
[0.20.13]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.13
[0.20.12]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.12
[0.20.11]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.11
[0.20.10]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.10
[0.20.9]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.9
[0.20.8]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.8
[0.20.7]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.7
[0.20.6]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.6
[0.20.5]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.5
[0.20.4]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.4
[0.20.3]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.3
[0.20.2]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.2
[0.20.1]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.1
[0.20.0]: https://github.com/tillsteinbach/WeConnect-python/releases/tag/v0.20.0
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
