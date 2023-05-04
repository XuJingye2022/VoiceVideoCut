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
    command = 'ffmpeg -i "%s" -map 0:a:1 "%s"'%(path, audiopath)
    subprocess.call(command, shell=True)
    return audiopath

if __name__ == "__main__":
    get_second_track(r"E:\游戏视频\2023-04-29 剪辑速率测试\2023-04-29 16-41-13.mkv")