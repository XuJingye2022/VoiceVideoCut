import os


def is_video(filepath):
    _, ext = os.path.splitext(filepath)
    return ext in [".mp4", ".mov", ".mkv", ".avi", ".flv"]


def is_audio(filepath):
    _, ext = os.path.splitext(filepath)
    return ext in [".wav", ".mp3", ".flac"]
