import re
from datetime import datetime

import shutil

from PIL import Image
import ascii_magic


def robustTimeParse(timeString):
    timestring = timeString.replace('Z', '+00:00')
    match = re.search(
        r'^(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.)(?P<fractions>\d+)(?P<end>\+\d{2}:\d{2})$', timestring)
    if match:
        timestring = match.group('start') + match.group('fractions').ljust(6, "0") + match.group('end')
    return datetime.fromisoformat(timestring).replace(microsecond=0)


def toBool(value):
    if value in [True, 'True', 'true', 'yes']:
        return True
    if value in [False, 'False', 'false', 'no']:
        return False
    raise ValueError('Not a valid boolean value (True/False)')


def imgToASCIIArt(img, columns=0, mode=ascii_magic.Modes.TERMINAL):
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

    return ascii_magic.from_image(cropped_image, columns=columns, mode=mode)
