from enum import Flag, auto


class ErrorEventType(Flag):
    HTTP = auto()
    TIMEOUT = auto()
    CONNECTION = auto()
    JSON = auto()
    ALL = HTTP | TIMEOUT | CONNECTION | JSON
