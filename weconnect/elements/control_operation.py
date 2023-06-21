from enum import Enum


class ControlInputEnum(Enum):
    @classmethod
    def allowedValues(cls):
        return []


class ControlOperation(ControlInputEnum):
    START = 'start'
    STOP = 'stop'
    NONE = 'none'
    SETTINGS = 'settings'
    UNKNOWN = 'unknown'

    @classmethod
    def allowedValues(cls):
        return [ControlOperation.START, ControlOperation.STOP]


class AccessControlOperation(ControlInputEnum):
    LOCK = 'lock'
    UNLOCK = 'unlock'
    NONE = 'none'
    UNKNOWN = 'unknown'

    @classmethod
    def allowedValues(cls):
        return [AccessControlOperation.LOCK, AccessControlOperation.UNLOCK]


class HonkAndFlashControlOperation(ControlInputEnum):
    FLASH = 'flash'
    HONK_AND_FLASH = 'honkandflash'
    NONE = 'none'
    UNKNOWN = 'unknown'

    @classmethod
    def allowedValues(cls):
        return [HonkAndFlashControlOperation.FLASH, HonkAndFlashControlOperation.HONK_AND_FLASH]


class Operation(Enum):
    START = 'start'
    STOP = 'stop'
    SETTINGS = 'settings'
    LOCK = 'lock'
    UNLOCK = 'unlock'
    FLASH = 'flash'
    HONK_AND_FLASH = 'honkandflash'
    TIMERS = 'timers'
    MDOE = 'mode'
    PROFILES = 'profiles'
    UNKNOWN = 'unknown'
