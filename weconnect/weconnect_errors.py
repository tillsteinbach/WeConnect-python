from enum import Flag, auto


class ErrorEventType(Flag):
    HTTP = auto()
    TIMEOUT = auto()
    CONNECTION = auto()
    ALL = HTTP | TIMEOUT | CONNECTION
