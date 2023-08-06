"""
导出麦克风音轨成mp3文件
"""
from moviepy.editor import *
from .file_manipulation import change_suffix
import os
import subprocess

def get_second_track(videopath):
    """导出视频的第二个音轨，默认只有麦克风音轨
    """
    audiopath = change_suffix(videopath, "mp3")
    if not os.path.exists(audiopath):
        command = 'ffmpeg -i "%s" -map 0:a:1? "%s"'%(videopath, audiopath)
        subprocess.call(command, shell=True)
    else:
        print("音频文件已存在")
    return audiopath

if __name__ == "__main__":
    get_second_track("E:/游戏视频/2023-05-30 【密特罗德 究极】/2023-05-29 22-43-32.mp4")