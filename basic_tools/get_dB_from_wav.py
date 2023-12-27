import numpy as np
from pydub import AudioSegment
from .export_audio_track import get_audio_track


def get_dB_from_wav(audiopath):
    sound = AudioSegment.from_file(audiopath, format="wav")
    time = [i / 1000 for i in range(len(sound))]
    dbfs_list = [sound[i].rms for i in range(len(sound))]
    dbfs_array = np.array(dbfs_list)
    dbfs_array = 20 * np.log10(dbfs_array)
    dbfs_array[dbfs_array == -np.inf] = 0
    return time, list(dbfs_array)


def get_dB_from_video(videopath, track_num):
    audiopath = get_audio_track(videopath, track_num)
    tlst, dBlst = get_dB_from_wav(audiopath)
    return tlst, dBlst
