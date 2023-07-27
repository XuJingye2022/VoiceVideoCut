def seconds_to_hms(seconds):
    h = int(seconds / 3600)
    m = int((seconds % 3600) / 60)
    s = int(seconds % 60)
    progress = f"{h:02d}:{m:02d}:{s:02d}"
    return h, m, s, progress

def seconds_to_frame(seconds, framerate):
    h = int(seconds / 3600)
    m = int((seconds % 3600) / 60)
    s = int(seconds % 60)
    f = int(seconds * framerate)
    progress = f"{h:02d}:{m:02d}:{s:02d}:{f}"
    return h, m, s, progress
