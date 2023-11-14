import os
import logging

import pandas as pd
import toml

from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
)
from moviepy.audio.fx.volumex import volumex

from .file_mani import change_file_extension, get_all_files_with_extensions
from .save_whisper_results import save_srt, subtitle_segments_in_output_video


SETTINGS = toml.load("./settings.toml")
MAX_DB = SETTINGS["Gam"]["max_dB"]
CRI_DB_RATIO = SETTINGS["Gam"]["cri_dB_ratio"]


def get_volumex_of_video(max_dB_now):
    return 10 ** (MAX_DB / 20) / (10 ** (max_dB_now / 20))


def cut_game_record(record_root, nthreads, preview=False):
    """
    `record_root`: 游戏录屏根目录， 里面可能存在多个录屏文件

    `nthreads`: 导出线程数.
    """
    # Folder and filenames
    output_folder = os.path.join(record_root, "Output")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    if preview is False:
        resolution_w = SETTINGS["outputsettings"]["resolution_w"]
        resolution_h = SETTINGS["outputsettings"]["resolution_h"]
        video_output_path = os.path.join(output_folder, "output_cut.mp4")
    else:
        resolution_w = SETTINGS["outputsettings"]["resolution_w_preview"]
        resolution_h = SETTINGS["outputsettings"]["resolution_h_preview"]
        video_output_path = os.path.join(output_folder, "preview_cut.mp4")

    # 视频和音频文件
    _, abs_record_files = get_all_files_with_extensions(record_root, [".mp4"])
    video_clip_lst = []
    micro_clip_lst = []
    all_subtitle_segments_list = []
    all_cut_segments_list = []
    all_text_list = []
    for abs_record_file in abs_record_files:
        cut_range_path = os.path.splitext(abs_record_file)[0] + "_CutRange.csv"
        speech_range_path = os.path.splitext(abs_record_file)[0] + "_SpeechRange.csv"
        # speech_track_path = change_file_extension(abs_record_file, "mp3")  # 麦克风音轨路径
        nvolumex = 1.30  # get_volumex_of_video(max(get_dB_from_mp3(speech_track_path)[1]))
        print("音量增加倍数：", nvolumex)

        all_video_clip = VideoFileClip(
            abs_record_file, target_resolution=(resolution_h, resolution_w)
        ).fx(volumex, nvolumex)
        all_micro_clip = AudioFileClip(change_file_extension(abs_record_file, "mp3"))
        # Load cut time ranges.
        df_cut = pd.read_csv(cut_range_path)
        df_sub = pd.read_csv(speech_range_path)
        df_sub = df_sub[(df_sub["use"] == True)]
        df_sub.reset_index(drop=True)
        tmp_cut_segments = []
        tmp_sub_segments = []
        tmp_txt_list = []
        for index, row in df_sub.iterrows():
            if row["text"].replace(" ", "") == "":
                continue
            tmp_sub_segments.append((row["start"], row["end"]))
            tmp_txt_list.append(row["text"])
        for index, row in df_cut.iterrows():
            t1, t2 = row["start"], row["end"]
            tmp_cut_segments.append((t1, t2))
            # 视频Clip
            video_clip = (
                all_video_clip.subclip(t1, t2).crossfadein(0.3).crossfadeout(0.3)
            )
            video_clip_lst.append(video_clip)
            # 麦克风clip
            micro_clip_lst.append(all_micro_clip.subclip(t1, t2))
        all_cut_segments_list.append(tmp_cut_segments)
        all_subtitle_segments_list.append(tmp_sub_segments)
        all_text_list.append(tmp_txt_list)
    # 保存字幕文件
    print(all_text_list)
    sub_segs_in_output_video, all_text_list = subtitle_segments_in_output_video(
        all_subtitle_segments_list, all_cut_segments_list, all_text_list
    )
    print(all_text_list)
    save_srt(
        change_file_extension(video_output_path, "srt"),
        all_text_list,
        sub_segs_in_output_video,
    )
    # exit()
    # 组合并保存视频
    video = concatenate_videoclips(video_clip_lst, method="chain")
    video.write_videofile(video_output_path, threads=nthreads)
    all_video_clip.close()
    for clip in video_clip_lst:
        clip.close()
    logging.info("视频导出完成")
    exit()
