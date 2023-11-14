import os

from tqdm import tqdm
import pandas as pd

from .file_mani import change_file_extension
from .get_dB_from_mp3 import get_dB_from_video
from .segments_mani import combine_time_segments, remove_noise


def divide_speech_in_mp3(video_path, audio_cache_folder, data_path, SETTINGS):
    """
    根据音量数据，得到需要剪辑的时间集合。

    `delta_t`: 需要将分贝数据加多少时间
    """

    NOISE_LENGTH = SETTINGS["Gam"]["noise_sig_length"]
    CRI_DB_RATIO = SETTINGS["Gam"]["cri_dB_ratio"]
    GROWTH_DECAY_TIME_OF_SPEECH = SETTINGS["Gam"]["growth_or_decay_time_of_voice"]
    SPEECH_CHANNEL = SETTINGS["Gam"]["speech_channel"]
    # Get Volume Data
    abs_audio_volume_path = change_file_extension(video_path, "csv")
    if os.path.exists(abs_audio_volume_path):
        df = pd.read_csv(abs_audio_volume_path)
    else:
        timelst, dB_lst = get_dB_from_video(video_path, SPEECH_CHANNEL)
        df = pd.DataFrame()
        df["time"] = timelst
        df["dB"] = dB_lst
        df.to_csv(abs_audio_volume_path, index=False)
    # Select volumn data
    max_t = max(df["time"])
    max_video_dB = max(df["dB"])
    df = df[(df["dB"] > max_video_dB * CRI_DB_RATIO)]  # 这里多保留一些数据，因为存在低声嘀咕的情况
    df.reset_index(inplace=True, drop=True)
    # Load time and volumn data
    t_lst = list(df["time"])
    dB_lst = list(df["dB"])

    # ========== Deal with volumn data =========
    # 1. Remove spike noise
    t_ranges = remove_noise(t_lst, max_t, NOISE_LENGTH)
    # 2. Extend time range: voice growth and decay
    t_ranges = [
        (
            max(0, a - GROWTH_DECAY_TIME_OF_SPEECH),
            min(max_t, b + GROWTH_DECAY_TIME_OF_SPEECH),
        )
        for a, b in t_ranges
    ]
    t_ranges = combine_time_segments(t_ranges, 0)
    # 7. Remove short noise
    # 这一段不能前置，因为可能会去除一些语气词
    t_ranges = list(
        filter(
            lambda x: x[1] - x[0] - 2 * GROWTH_DECAY_TIME_OF_SPEECH > NOISE_LENGTH,
            t_ranges,
        )
    )
    if not os.path.exists(audio_cache_folder):
        os.makedirs(audio_cache_folder)

    df = pd.DataFrame()
    for i, (tL, tR) in tqdm(
        enumerate(t_ranges), desc="Dividing speech", total=len(t_ranges)
    ):
        name = str(i).rjust(5, "0")
        os.system(
            f'ffmpeg -loglevel quiet -y -i "{video_path}" -map 0:a:{SPEECH_CHANNEL} -ss {tL} -to {tR} -vn "{audio_cache_folder}/{name}.mp3"'
        )
        df.loc[name + ".mp3", "start"] = tL
        df.loc[name + ".mp3", "end"] = tR

    df.to_csv(data_path)
    print(data_path)
    return df
