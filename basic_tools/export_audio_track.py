"""
导出麦克风音轨成wav文件
"""
from .file_mani import change_file_extension
import os
import subprocess
import logging


def get_audio_track(videopath, track_num):
    """导出视频的第`track_num`个音轨，默认只有麦克风音轨

    `track_num`: 从`0`开始计数的数值
    """
    logging.info("正在导出麦克风音轨...")
    # 我发现导出mp3格式和wav格式的音频长短不一样
    # .mp3格式比视频更长, 后者则和视频相同
    audiopath = change_file_extension(videopath, "wav")
    if os.path.exists(audiopath):
        logging.info("音频文件已存在")
    else:
        command = 'ffmpeg -loglevel quiet -y -i "%s" -map 0:a:%s "%s"' % (
            videopath,
            track_num,
            audiopath,
        )
        print(command)
        subprocess.call(command, shell=True)
    return audiopath
