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
