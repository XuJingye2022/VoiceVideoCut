import os
import logging

import pandas as pd
import toml

from .file_mani import change_file_extension, get_all_files_with_extensions
from .save_whisper_results import save_srt, subtitle_segments_in_output_video
from .clip_video import clip_video, combine_videos

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
    # 临时视频文件夹和临时视频文件名
    tmp_videos_folder = os.path.join(output_folder, "tmp_videos")
    if not os.path.exists(tmp_videos_folder):
        os.mkdir(tmp_videos_folder)
    tmp_video_path_lst = []
    # 字幕文件相关
    all_subtitle_segments_list = []
    all_cut_segments_list = []
    all_text_list = []
    for abs_record_file in abs_record_files:
        input_video_name_with_extension = os.path.basename(abs_record_file)
        input_video_name = os.path.splitext(input_video_name_with_extension)[0]
        cut_range_path = os.path.splitext(abs_record_file)[0] + "_CutRange.csv"
        speech_range_path = os.path.splitext(abs_record_file)[0] + "_SpeechRange.csv"

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

        i = 0
        for index, row in df_cut.iterrows():
            t1, t2 = row["start"], row["end"]
            tmp_cut_segments.append((t1, t2))
            # 视频Clip
            tmp_video_path = os.path.join(
                tmp_videos_folder,
                "%s_%s.mp4" % (input_video_name, i)
            )
            tmp_video_path_lst.append(tmp_video_path)
            clip_video(abs_record_file, t1, t2, tmp_video_path, audio=True)
            i += 1
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
    print(tmp_video_path_lst)
    combine_videos(tmp_video_path_lst, video_output_path)
    logging.info("视频导出完成")
    exit()
