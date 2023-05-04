from pydub import AudioSegment
import numpy as np
import os
from .export_voice_track import get_second_track
# import matplotlib.pyplot as plt

def get_dB_from_mp3(path):
    sound = AudioSegment.from_file(path, format="mp3")

    time = [i/1000 for i in range(len(sound))]
    dbfs_list = [sound[i].rms for i in range(len(sound))]
    dbfs_array = np.array(dbfs_list)
    dbfs_min = min(dbfs_array[dbfs_array != -np.inf])
    dbfs_array[dbfs_array == -np.inf] = dbfs_min
    dbfs_array = dbfs_array - dbfs_min
    dbfs_array = dbfs_array/max(dbfs_array)
    return time, list(dbfs_array)

def get_dB_from_video(videopath):
    audio_path = get_second_track(videopath)
    tlst, dBlst = get_dB_from_mp3(audio_path)
    os.remove(audio_path)
    return tlst, dBlst


if __name__ == "__main__":
    get_dB_from_mp3(r"E:\游戏视频\2023-04-29 剪辑速率测试\microphone_audio.mp3")

    # import pandas as pd
    # df = pd.read_csv(r"E:\游戏视频\2023-04-29 剪辑速率测试\分贝数据.csv")

    # path = r"E:\游戏视频\2023-04-29 剪辑速率测试\microphone_audio.mp3"
    # sound = AudioSegment.from_file(path, format="mp3")

    # time = [i/1000 for i in range(len(sound))]
    # dbfs_list = [sound[i].rms for i in range(len(sound))]
    # dbfs_array = np.array(dbfs_list)
    # dbfs_min = min(dbfs_array[dbfs_array != -np.inf])
    # dbfs_array[dbfs_array == -np.inf] = dbfs_min
    # dbfs_array = dbfs_array - dbfs_min
    # dbfs_array = dbfs_array/max(dbfs_array)
    

    # plt.plot(time, dbfs_array)
    # plt.plot(df["time"], df["dB"]/max(df["dB"]), c="r")
    # plt.ylabel('dBFS')
    # plt.xlabel('Time (s)')
    # plt.show()