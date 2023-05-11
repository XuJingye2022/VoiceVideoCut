"""
工作流程：
1. 按此生成cut
2. 用剪映去除无意义的声音片段，但是保留空白
"""

import os
import subprocess
import numpy as np
import pandas as pd

from moviepy.editor import VideoFileClip, concatenate_videoclips
from small_tools.get_dB_from_mp3 import get_dB_from_video
from multipledispatch import dispatch, variadic

def change_suffix(s: str, new_post_fix: str):
    """更改字符串的后缀
    
    Param
    ---
    s: 包含后缀的路径或者文件名.

    new_post_fix: 不包含`.`的新文件后缀.
    """
    lst = s.split(".")
    lst[-1] = new_post_fix
    return ".".join(lst)

def seconds_to_hms(seconds):
    # 计算小时数和余数
    hours, remainder = divmod(seconds, 3600)
    # 计算分钟数和秒数
    minutes, seconds = divmod(remainder, 60)
    # 返回结果
    return hours, minutes, seconds

def combine_sets(set1, set2):
    """利用set2连续地扩充set1.

    如果无法连续,原样返回
    """
    x_l, x_r = set1
    a2, b2 = set2
    if (b2 <= x_l) or (a2 >= x_r):
        return (x_l, x_r)
    if a2 <= x_l <= b2 <= x_r:
        return (a2, x_r)
    if x_l <= a2 <= x_r <= b2:
        return (x_l, b2)
    if (a2 <= x_l) and (b2 >= x_r):
        return (a2, b2)
    if (x_l <= a2) and (b2 <= x_r):
        return (x_l, x_r)


def combine_ranges(t_ranges: list[tuple], t_error):
    """结合各个比较近的时间范围

    `t_error`: 时间范围之间的最大容许距离
    """
    pre_t1, pre_t2 = t_ranges[0]
    res_lst = []
    for t1, t2 in t_ranges:
        if t1 > pre_t2 + t_error:
            res_lst.append((pre_t1, pre_t2))
            pre_t1, pre_t2 = t1, t2
        else:
            pre_t2 = t2
    res_lst.append((pre_t1, pre_t2))
    return res_lst


def select_lists_according_list1(lst1: list, lst2: list, cri_fun):
    res_lst1, res_lst2 = [], []
    for x, y in zip(lst1, lst2):
        if cri_fun(x):
            res_lst1.append(x)
            res_lst2.append(y)
    return res_lst1, res_lst2


def get_zero_point(xlist: list, ylist: list):
    x1, x2, x3 = xlist
    y1, y2, y3 = ylist
    k = (y3 - y2) / (x3 - x2)
    return 0.5 * (x1 - y1 / k + x2 - y2 / k)


def get_all_suffixs_files(root: str, suffixs: list) -> tuple[list]:
    """获取目录下指定后缀文件名

    Parameters
    ---
    `root`: Absolute path of folder.

    `suffixs`: Suffixs to select.

    Return
    ---
    `namelist`: List of file name.

    `abspathlist`: List of absolute path of files.
    """
    name_lst, path_lst = [], []
    for tmproot, _, tmppaths in os.walk(root):
        if tmproot == root:
            for tmppath in tmppaths:
                for _ in filter(tmppath.endswith, suffixs):
                    name_lst.append(tmppath)
                    path_lst.append("%s/%s" % (root, tmppath))
    return name_lst, path_lst


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
            return concatenate_videoclips([clip1, clip2])


class Gam:
    def __init__(
        self,
        cutSetPath,
        threads,
        settings,
    ):
        self.noise_sig_length = 0.1
        self.pre_t = 3.1
        self.aft_t = 0.1
        self.bet_t = 3.21
        self.speedx = settings["Gam"]["speed"]["speedx"]
        self.cutSetPath = cutSetPath
        self.min_t = 0
        self.max_t = 0  # 加载后立马更改
        # self.settings = settings
        # self.mark_path = mark_path
        self.threads = threads

    def from_tpoints_to_tranges(self, tlst: list) -> list[tuple]:
        return [
            (max(self.min_t, t - self.pre_t), min(self.max_t, t + self.aft_t))
            for t in tlst
        ]

    def remove_noise(self, time_lst: list) -> list:
        """
        前后0.5s内没有声音的，视为噪声
        """
        res_lst = []
        if abs(time_lst[1] - time_lst[0]) < self.noise_sig_length:
            res_lst.append(time_lst[0])
        for i in range(1, len(time_lst) - 1):
            cond1 = abs(time_lst[i] - time_lst[i - 1]) < self.noise_sig_length
            cond2 = abs(time_lst[i + 1] - time_lst[i]) < self.noise_sig_length
            if cond1 and cond2:
                res_lst.append(time_lst[i])
        if abs(time_lst[-1] - time_lst[-2]) < self.noise_sig_length:
            res_lst.append(time_lst[-1])
        return res_lst

    def remove_dB_small(self, t_ranges, tlst, dBlst):
        df_dB = pd.DataFrame()
        df_dB["time"] = tlst
        df_dB["dB"] = dBlst
        for i in range(len(t_ranges)-1,-1, -1):
            t1, t2 = t_ranges[i]
            df = df_dB[(t1<=df_dB["time"]) & (df_dB["time"]<=t2)]
            if np.max(df["dB"]) < 0.01:
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
        df = df[(df["dB"] > 0.05)]
        df.reset_index(inplace=True, drop=True)
        print(df)
        # Load time and volumn data
        t_lst = list(df["time"])
        dB_lst = list(df["dB"])

        # ========== Deal with volumn data =========
        # 1. Remove spike noise
        t_lst_remove_noise = self.remove_noise(t_lst)
        # 2. Transform time point to time range
        t_ranges = self.from_tpoints_to_tranges(t_lst_remove_noise)
        # 3. Combine time range, with speech gap:
        t_ranges = combine_ranges(t_ranges, self.bet_t - self.aft_t - self.pre_t)
        # 4. 去除没有说话的部分——通过分贝数全程没有超过某个阈值判断
        t_ranges = self.remove_dB_small(t_ranges, t_lst, dB_lst)
        # 5. Remove short noise
        t_ranges = list(filter(lambda x: x[1]-x[0]-self.pre_t-self.aft_t>self.noise_sig_length, t_ranges))
        # ==========================================
        print("分段数量: ", len(t_ranges))
        # ============== 总时长 =============
        res = 0.0
        for i in range(len(t_ranges)):
            res += t_ranges[i][1] - t_ranges[i][0]
        hours, minutes, seconds = seconds_to_hms(res)
        print("总时长：%s小时%s分钟%s秒"%(int(hours), int(minutes), seconds))

        # Save ranges of cut.
        df = pd.DataFrame(t_ranges)
        df.to_csv(self.cutSetPath, index=False, header=False)


def cut_game_video_single_file(record_name, output_name, record_root, nthreads):
    """
    `record_name`: 游戏录屏文件, `.mp4`格式.

    `output_name`: 输出视频文件.

    `record_root`: 游戏录屏根目录， 里面可能存在多个录屏文件

    `nthreads`: 导出线程数.
    """
    cut_range_name = record_name.split(".")[0] + "_CutRange.csv"        # 剪辑时间范围的DataFrame. `index=False, headers=False`.
    cut_range_path = os.path.join(record_root, cut_range_name)          # 剪辑时间范围的完整路径
    record_path = os.path.join(record_root, record_name)                # 录屏的完整路径
    output_folder = os.path.join(record_root, "Output")                 # 存放输出视频的文件夹
    output_path = os.path.join(output_folder, output_name)              # 相应输出视频的完整路径
    # 创建切割素材文件夹
    if not os.path.exists(output_folder): os.makedirs(output_folder)

    # Load video clip.
    all_clip = VideoFileClip(record_path)
    # Load cut time ranges.
    df = pd.read_csv(cut_range_path, names=["start", "end"])
    clip_lst = []
    for i in range(0, len(df)):
        t1, t2 = df.loc[i, ["start","end"]]
        clip_lst.append(all_clip.subclip(t1, t2).crossfadein(0.3).crossfadeout(0.3))
    # 组合
    video = concatenate_videoclips(clip_lst)
    video.write_videofile(output_path, threads=nthreads)
    # 关闭各个锁定的clip
    all_clip.close()
    for clip in clip_lst: clip.close()

def cut_game_video_multifile_individual(record_root, nthreads):
    """
    `record_root`: 游戏录屏根目录， 里面可能存在多个录屏文件

    `nthreads`: 导出线程数.
    """
    record_names, _ = get_all_suffixs_files(record_root, [".mkv"])
    if len(record_names) == 1:
        cut_game_video_single_file(record_names[0], "output_cut.mkv", record_root, nthreads)
    else:
        for i, record_name in enumerate(record_names):
            cut_game_video_single_file(record_name, "%s.mkv"%i, record_root, nthreads)
        str1 = " ".join(['-i "%s"'%os.path.join(record_root, "Output", str(j)+".mp4") for j in range(len(record_names))])
        str2 = os.path.join(record_root, "Output", "output_cut.mp4")
        command = 'ffmpeg %s -codec copy "%s"'%(str1, str2)
        print(command)
        subprocess.call(command, shell=True)

def cut_game_video_multifile_together(record_root, nthreads):
    """
    `record_root`: 游戏录屏根目录， 里面可能存在多个录屏文件

    `nthreads`: 导出线程数.
    """
    output_folder = os.path.join(record_root, "Output")                 # 存放输出视频的文件夹
    output_path = os.path.join(output_folder, "output_cut.mp4")              # 相应输出视频的完整路径
    # 创建切割素材文件夹
    if not os.path.exists(output_folder): os.makedirs(output_folder)

    record_names, _ = get_all_suffixs_files(record_root, [".mkv"])
    print(record_names)
    clip_lst = []
    for i, record_name in enumerate(record_names):
        print(record_name)
        cut_range_name = record_name.split(".")[0] + "_CutRange.csv"        # 剪辑时间范围的DataFrame. `index=False, headers=False`.
        cut_range_path = os.path.join(record_root, cut_range_name)          # 剪辑时间范围的完整路径
        record_path = os.path.join(record_root, record_name)                # 录屏的完整路径
        
        # Load video clip.
        print(record_path)
        all_clip = VideoFileClip(record_path)
        # Load cut time ranges.
        df = pd.read_csv(cut_range_path, names=["start", "end"])
        for i in range(0, len(df)):
            t1, t2 = df.loc[i, ["start","end"]]
            clip_lst.append(all_clip.subclip(t1, t2).crossfadein(0.3).crossfadeout(0.3))
    # 组合
    video = concatenate_videoclips(clip_lst)
    video.write_videofile(output_path, threads=nthreads)
    # 关闭各个锁定的clip
    all_clip.close()
    for clip in clip_lst: clip.close()

def cut_game_record(root, nthreads, individual=False):
    if individual==False:
        cut_game_video_multifile_together(root, nthreads)
    else:
        cut_game_video_multifile_individual(root, nthreads)

if __name__ == "__main__":
    # test_microphone(1, 400)

    THREADS = 7                                                                # 导出视频时的线程数

    root = r"E:\游戏视频\2023-05-10 【旷野之息】通关准备工作、救出水神兽、抵达主殿"
    if not os.path.exists(root):
        print("Error! 不存在指定目录文件夹! 请检查文件设置！"); exit()

    cut_game_record(root, THREADS)