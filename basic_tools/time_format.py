from math import floor
import time

def time_stamp_to_time_string(timestamp, format):
    return time.strftime(format, time.localtime(timestamp))

def time_string_to_time_stamp(timestring, format):
    return time.mktime(time.strptime(timestring, format))


def seconds_to_hms(seconds):
    """Convert seconds to (hour, minutes, seconds, 'h:m:s')
    """
    h = int(seconds / 3600)
    m = int((seconds % 3600) / 60)
    s = int(seconds % 60)
    hms = f"{h:02d}:{m:02d}:{s:02d}"
    return h, m, s, hms

def hms_to_seconds(time_str: str):
    """Convert time `2:40:06.194953` to seconds
    """
    h, m, s = time_str.split(":")
    return 3600 * int(h) + 60 * int(m) + float(s)

def seconds_to_frame(seconds, framerate):
    """将秒数转化为时、分、秒、第几帧
    """
    h = int(seconds / 3600)
    m = int((seconds % 3600) / 60)
    s = int(floor(seconds % 60))
    f = int(seconds % 1 * framerate)
    progress = f"{h:02d}:{m:02d}:{s:02d}:{f}"
    return h, m, s, progress