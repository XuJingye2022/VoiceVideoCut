"""
工作流程：
1. 按此生成cut
2. 用剪映去除无意义的声音片段，但是保留空白
"""

import os
import subprocess
import numpy as np
import pandas as pd

from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, concatenate_audioclips, CompositeVideoClip
from moviepy.audio.fx import multiply_volume
from multipledispatch import dispatch, variadic
import toml

from small_tools.get_dB_from_mp3 import get_dB_from_video
from small_tools.time_convert import seconds_to_hms
from small_tools.file_manipulation import change_suffix, get_all_suffixs_files

SETTINGS = toml.load("./settings.toml")

def combine_ranges(t_ranges: list[tuple], t_error):
    """组合各个比较近的时间范围

    `t_error`: 时间范围之间的最大容许距离
    """
    pre_t1, pre_t2 = t_ranges[0]
    if pre_t1 > pre_t2:
        print(f"Cut range error: {pre_t1} and {pre_t2}")
        return None

    res_lst = []
    for t1, t2 in t_ranges:
        if t1 >= t2:
            print(f"Cut range error: {t1} and {t2}")
            return None

        if t1 > pre_t2 + t_error:
            res_lst.append((pre_t1, pre_t2))
            pre_t1, pre_t2 = t1, t2
        else:
            pre_t2 = t2
    res_lst.append((pre_t1, pre_t2))
    return res_lst


def get_clip(cut_range, all_videos, all_length, cumsum_length):
    """
    根据剪辑时间范围， 自动剪辑。

    只适合`cut_range`在一个视频内， 或者跨越两个视频。

    Parameters
    ---
    `all_videos`, `all_length`, `cumsum_length`是具有相同长度的列表。

    `all_videos`: 录屏视频的绝对路径.
    `all_length`: 录屏视频的各自长度.
    `cumsum_length`: 录屏视频的累计长度.
    """
    a, b = cut_range
    for i in range(len(all_length)):
        if cumsum_length[i] < a < b < cumsum_length[i + 1]:
            # 在单独第1个文件之内
            a -= cumsum_length[i]
            b -= cumsum_length[i]
            clip = VideoFileClip(all_videos[i])
            return clip.subclip(a, b)
        if cumsum_length[i] < a < cumsum_length[i + 1] < b:
            # 跨两个文件，实际上体验下来，4个多小时的视频还是不会分成两个文件
            a -= cumsum_length[i]
            b -= cumsum_length[i + 1]
            clip1 = VideoFileClip(all_videos[i])
            clip1 = clip1.subclip(a, all_length[i])
            clip2 = VideoFileClip(all_videos[i + 1])
            clip2 = clip2.subclip(0, b)
            return concatenate_videoclips([clip1, clip2], method="chain")


class Gam:
    def __init__(
        self,
        cutSetPath,
        settings
    ):
        self.noise_sig_length = settings["Gam"]["noise_sig_length"]
        self.growth_or_decay_time_of_voice = 0.5
        self.pre_t = settings["Gam"]["pre_time"]
        self.aft_t = settings["Gam"]["aft_time"]
        self.bet_t = settings["Gam"]["bet_time"] + 2 * self.growth_or_decay_time_of_voice
        self.speedx = settings["Gam"]["speedx"]
        self.cutSetPath = cutSetPath
        self.min_t = 0
        self.max_t = 0  # 加载后立马更改
        # self.settings = settings
        # self.mark_path = mark_path
        self.threads = settings["Gam"]["threads"]

    def from_tpoints_to_tranges(self, tlst: list) -> list[tuple]:
        return [
            (max(self.min_t, t - self.growth_or_decay_time_of_voice), min(self.max_t, t + self.growth_or_decay_time_of_voice))
            for t in tlst
        ]

    def remove_noise(self, time_lst: list) -> list:
        """
        前后一段时间内没有声音的，视为噪声
        """
        tmp_lst = [(max(self.min_t, t - 0.001), min(self.max_t, t + 0.001)) for t in time_lst]
        tmp_lst = combine_ranges(tmp_lst, 0)
        res_lst = []
        for t1, t2 in tmp_lst:
            if t2 - t1 >= self.noise_sig_length:
                res_lst.append((t1, t2))
        return res_lst

    def remove_dB_small(self, t_ranges, tlst, dBlst):
        df_dB = pd.DataFrame()
        df_dB["time"] = tlst
        df_dB["dB"] = dBlst
        for i in range(len(t_ranges)-1,-1, -1):
            t1, t2 = t_ranges[i]
            df = df_dB[(t1<=df_dB["time"]) & (df_dB["time"]<=t2)]
            if np.max(df["dB"]) < SETTINGS["Gam"]["cri_dB"]:
                del t_ranges[i]
        return t_ranges


    def get_time_set_to_cut(self, abs_video_path):
        """
        根据音量数据，得到需要剪辑的时间集合。

        `delta_t`: 需要将分贝数据加多少时间
        """
        # Get Volume Data
        abs_audio_volume_path = change_suffix(abs_video_path, "csv")
        if os.path.exists(abs_audio_volume_path):
            df = pd.read_csv(abs_audio_volume_path)
        else:
            timelst, dB_lst = get_dB_from_video(videopath=abs_video_path)
            df = pd.DataFrame()
            df["time"] = timelst
            df["dB"] = dB_lst
            df.to_csv(abs_audio_volume_path, index=False)
        # Select volumn data
        self.max_t = max(df["time"])
        df = df[(df["dB"] > SETTINGS["Gam"]["cri_dB"])]      # 这里多保留一些数据，因为存在低声嘀咕的情况
        df.reset_index(inplace=True, drop=True)
        # Load time and volumn data
        t_lst = list(df["time"])
        dB_lst = list(df["dB"])

        # ========== Deal with volumn data =========
        # 1. Remove spike noise
        t_ranges = self.remove_noise(t_lst)
        # 2. Extend time range: voice growth and decay
        t_ranges = [(max(self.min_t, a-self.growth_or_decay_time_of_voice), min(self.max_t, b+self.growth_or_decay_time_of_voice))
                    for a, b in t_ranges]
        t_ranges = combine_ranges(t_ranges, 2*self.growth_or_decay_time_of_voice + 0.01)
        # 4. Expand ranges and Combine
        t_ranges = [(max(self.min_t, a-self.pre_t), min(self.max_t, b+self.aft_t)) for a, b in t_ranges]
        t_ranges = combine_ranges(t_ranges, self.bet_t - self.aft_t - self.pre_t)
        # 6. 去除没有说话的部分——通过分贝数全程没有超过某个阈值判断
        t_ranges = self.remove_dB_small(t_ranges, t_lst, dB_lst)
        # 7. Remove short noise
        # 这一段不能前置，因为可能会去除一些语气词
        t_ranges = list(filter(lambda x: x[1]-x[0]-self.pre_t-self.aft_t-2*self.growth_or_decay_time_of_voice>self.noise_sig_length, t_ranges))
        print(pd.DataFrame(t_ranges))
        # ==========================================
        print("分段数量: ", len(t_ranges))
        # ============== 总时长 =============
        res = 0.0
        for i in range(len(t_ranges)):
            res += t_ranges[i][1] - t_ranges[i][0]
        hours, minutes, seconds, _ = seconds_to_hms(res)
        print("总时长：%s小时%s分钟%s秒"%(int(hours), int(minutes), seconds))

        # Save ranges of cut.
        df = pd.DataFrame(t_ranges)
        df.to_csv(self.cutSetPath, index=False, header=False)



def cut_game_record(record_root, nthreads):
    """
    `record_root`: 游戏录屏根目录， 里面可能存在多个录屏文件

    `nthreads`: 导出线程数.
    """
    output_folder = os.path.join(record_root, "Output")                 # 存放输出视频的文件夹
    video_output_path = os.path.join(output_folder, "output_cut.mp4")   # 相应输出视频的完整路径
    audio_output_path = os.path.join(output_folder, "output_cut.mp3")
    # 创建切割素材文件夹
    if not os.path.exists(output_folder): os.makedirs(output_folder)

    record_names, _ = get_all_suffixs_files(record_root, [".mp4"])
    video_clip_lst = []
    micro_clip_lst = []
    for i, record_name in enumerate(record_names):
        print(record_name)
        cut_range_name    = record_name.split(".")[0] + "_CutRange.csv"        # 剪辑时间范围的DataFrame. `index=False, headers=False`.
        cut_range_path    = os.path.join(record_root, cut_range_name)          # 剪辑时间范围的完整路径
        record_path       = os.path.join(record_root, record_name)             # 录屏的完整路径
        # Load video and microphone.
        all_video_clip = VideoFileClip(record_path)
        all_micro_clip = AudioFileClip(change_suffix(record_path, "mp3"))
        # Load cut time ranges.
        df = pd.read_csv(cut_range_path, names=["start", "end"])
        for i in range(0, len(df)):
            t1, t2 = df.loc[i, ["start","end"]]
            # 视频Clip
            video_clip = all_video_clip.subclip(t1, t2).crossfadein(0.3).crossfadeout(0.3)
            video_clip.audio = video_clip.audio.audio_normalize()
            video_clip_lst.append(video_clip)
            # 麦克风clip
            micro_clip_lst.append(all_micro_clip.subclip(t1, t2))
    # 组合并保存麦克风音频
    micro_audio = concatenate_audioclips(micro_clip_lst)
    micro_audio.write_audiofile(audio_output_path)
    all_micro_clip.close()
    for clip in micro_clip_lst: clip.close()
    # 组合并保存视频
    video = concatenate_videoclips(video_clip_lst, method="chain")
    video.write_videofile(video_output_path, threads=nthreads)
    all_video_clip.close()
    for clip in video_clip_lst: clip.close()
    
