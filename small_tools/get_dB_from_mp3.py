from pydub import AudioSegment
import numpy as np
import os
from .export_voice_track import get_second_track
# import matplotlib.pyplot as plt

def get_dB_from_mp3(audiopath):
    sound = AudioSegment.from_file(audiopath, format="mp3")
    time = [i/1000 for i in range(len(sound))]
    dbfs_list = [sound[i].rms for i in range(len(sound))]
    dbfs_array = np.array(dbfs_list)
    dbfs_array = 20*np.log10(dbfs_array)
    dbfs_array[dbfs_array==-np.inf]=0
    return time, list(dbfs_array)


def get_dB_from_video(videopath):
    audiopath = get_second_track(videopath)
    tlst, dBlst = get_dB_from_mp3(audiopath)
    return tlst, dBlst


if __name__ == "__main__":
    pass
    # time, dB_lst = get_dB_from_video(r"E:\游戏视频\2023-05-13 【王国之泪】P06 访问水神殿\2023-05-13 21-58-28.mp4")
    # plt.plot(time, dB_lst, label="pre")
    # time, dB_lst = get_dB_from_video(r"E:\游戏视频\2023-08-01【王国之泪】P23\2023-08-01 18-35-43.mp4")
    # plt.plot(time, dB_lst, label="aft")
    # plt.legend()
    # plt.show()