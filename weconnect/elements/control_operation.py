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
