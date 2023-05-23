"""
导出麦克风音轨成mp3文件
"""
from moviepy.editor import *
import os
import subprocess

def get_second_track(path):
    """导出视频的第二个音轨，默认只有麦克风音轨
    """
    root, _ = os.path.split(path)
    audiopath = os.path.join(root,"microphone_audio.mp3")
    command = 'ffmpeg -i "%s" -map 0:a:1? "%s"'%(path, audiopath)
    subprocess.call(command, shell=True)
    return audiopath

if __name__ == "__main__":
    get_second_track("E:/游戏视频/2023-05-11 【王国之泪】P01 到达海拉鲁大地/Output/output_cut.mp4")