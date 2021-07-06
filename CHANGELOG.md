# Changelog
All notable changes to this project will be documented in this file.

## [Unreleased]
- No unreleased changes so far

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

[unreleased]: https://github.com/tillsteinbach/WeConnect-python/compare/v0.12.1...HEAD
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
