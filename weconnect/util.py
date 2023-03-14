from __future__ import annotations
from enum import Enum
from typing import Any

import re
from datetime import datetime

import json

import logging

import shutil

SUPPORT_IMAGES = False
try:
    from PIL import Image  # type: ignore
    SUPPORT_IMAGES = True
except ImportError:
    pass

SUPPORT_ASCII_IMAGES = False
try:
    import ascii_magic  # type: ignore
    SUPPORT_ASCII_IMAGES = True
except ImportError:
    pass


def robustTimeParse(timeString: str) -> datetime:
    timeString = timeString.replace('Z', '+00:00')
    match = re.search(
        r'^(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.)(?P<fractions>\d+)(?P<end>\+\d{2}:\d{2})$', timeString)
    if match:
        timeString = match.group('start') + match.group('fractions').ljust(6, "0") + match.group('end')
    return datetime.fromisoformat(timeString).replace(microsecond=0)


def toBool(value: Any) -> bool:
    if value in [True, 'True', 'true', 'yes']:
        return True
    if value in [False, 'False', 'false', 'no']:
        return False
    raise ValueError('Not a valid boolean value (True/False)')


if SUPPORT_ASCII_IMAGES:
    class ASCIIModes(Enum):
        TERMINAL = 'TERMINAL'
        ASCII = 'ASCII'
        HTML = 'HTML'

    def imgToASCIIArt(img: Image, columns: int = 0, mode=ASCIIModes.TERMINAL) -> str:
        bbox = img.getbbox()

        # Crop the image to the contents of the bounding box
        image = img.crop(bbox)

        # Determine the width and height of the cropped image
        (width, height) = image.size

        # Create a new image object for the output image
        cropped_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        # Paste the cropped image onto the new image
        cropped_image.paste(image, (0, 0))

        if columns == 0:
            columns = shutil.get_terminal_size()[0]

        if mode == ASCIIModes.ASCII:
            return ascii_magic.from_pillow_image(cropped_image).to_ascii(columns=columns, monochrome=True)
        if mode == ASCIIModes.HTML:
            return ascii_magic.from_pillow_image(cropped_image).to_html(columns=columns)
        return ascii_magic.from_pillow_image(cropped_image).to_ascii(columns=columns)


def celsiusToKelvin(value):
    return value + 273.15


def kelvinToCelsius(value):
    return value - 273.15


def farenheitToKelvin(value):
    return 273.5 + ((value - 32.0) * (5.0 / 9.0))


class DuplicateFilter(logging.Filter):

    def __init__(self, doNotFilterAbove=logging.ERROR, filterResetSeconds: int = 0, name: str = '') -> None:
        super().__init__(name=name)
        self.lastLog = {}
        self.firstTime = True
        self.doNotFilterAbove = doNotFilterAbove
        self.filterResetSeconds = filterResetSeconds

    def filter(self, record) -> bool:
        # don't filter critical or error messages:
        if record.levelno >= self.doNotFilterAbove:
            return True

        if record.module in self.lastLog:
            if record.levelno in self.lastLog[record.module]:
                if self.lastLog[record.module][record.levelno][0] == (record.msg, record.args):
                    if (datetime.now() - self.lastLog[record.module][record.levelno][1]).total_seconds() < self.filterResetSeconds:
                        if self.firstTime:
                            self.firstTime = False
                            logging.info('Repeated log messages from the same module are hidden (does not apply to errors or critical problems)')
                        return False
            self.lastLog[record.module][record.levelno] = ((record.msg, record.args), datetime.now())
        else:
            self.lastLog[record.module] = {record.levelno: ((record.msg, record.args), datetime.now())}
        return True


class ExtendedEncoder(json.JSONEncoder):
    """Datetime object encode used for json serialization"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def default(self, o: Any) -> str:
        """Serialize datetime object to isodate string

        Args:
            o (datetime): datetime object

        Returns:
            str: object represented as isoformat string
        """
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


class ExtendedWithNullEncoder(ExtendedEncoder):
    """Datetime object encode used for json serialization"""

    def default(self, o: Any) -> str:
        try:
            return super().default(o)
        except TypeError:
            return None
