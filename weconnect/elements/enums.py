from enum import Enum

from weconnect.elements.control_operation import ControlInputEnum


class MaximumChargeCurrent(ControlInputEnum,):
    MAXIMUM = 'maximum'
    REDUCED = 'reduced'
    INVALID = 'invalid'
    UNKNOWN = 'unknown'

    @classmethod
    def allowedValues(cls):
        return [MaximumChargeCurrent.MAXIMUM, MaximumChargeCurrent.REDUCED]


class UnlockPlugState(ControlInputEnum,):
    OFF = 'off'
    ON = 'on'
    PERMANENT = 'permanent'
    UNKNOWN = 'unknown'

    @classmethod
    def allowedValues(cls):
        return [UnlockPlugState.OFF, UnlockPlugState.ON]


class BatteryCareMode(ControlInputEnum,):
    ACTIVATED = 'activated'
    DEACTIVATED = 'deactivated'
    UNKNOWN = 'unknown'

    @classmethod
    def allowedValues(cls):
        return [BatteryCareMode.ACTIVATED, BatteryCareMode.DEACTIVATED]


class CarType(Enum,):
    ELECTRIC = 'electric'
    FUEL = 'fuel'
    HYBRID = 'hybrid'
    GASOLINE = 'gasoline'
    PETROL = 'petrol'
    DIESEL = 'diesel'
    CNG = 'cng'
    LPG = 'lpg'
    INVALID = 'invalid'
    UNKNOWN = 'unknown car type'


class EngineType(Enum,):
    GASOLINE = 'gasoline'
    ELECTRIC = 'electric'
    PETROL = 'petrol'
    DIESEL = 'diesel'
    CNG = 'cng'
    LPG = 'lpg'
    INVALID = 'invalid'
    UNKNOWN = 'unknown engine type'


class SpinState(Enum,):
    DEFINED = 'DEFINED'
    UNKNOWN = 'unknown spin state'


class TargetSOCReachable(Enum,):
    INVALID = 'invalid'
    CALCULATING = 'calculating'
    NOT_REACHABLE = 'notReachable'
    REACHABLE = 'reachable'
    UNKNOWN = 'unknown'
