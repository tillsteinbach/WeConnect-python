import re
from datetime import datetime


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
