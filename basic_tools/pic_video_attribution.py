# 获取图片和视频的属性
import os
import toml
from PIL import Image
import cv2
from moviepy.editor import VideoFileClip
import logging

library_path = os.path.dirname(os.path.abspath(__file__))
parent_directory = os.path.dirname(library_path)
SETTINGS = toml.load(os.path.join(parent_directory, "settings.toml"))


def get_size(abspath, settings=SETTINGS):
    """获取图片/视频尺寸"""
    if abspath[-4:] in settings["supportedFormat"]["picture"]:
        return Image.open(abspath).convert("RGB").size
    elif (abspath[-4:] == ".gif") or (abspath[-4:] == ".GIF"):
        clip = VideoFileClip(
            abspath,
            audio=False,
        )
        res = clip.size
        clip.close()
        return res
    elif abspath[-4:] in settings["supportedFormat"]["video"]:
        video = cv2.VideoCapture(abspath)
        return (
            int(video.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
    else:
        raise ("文件格式不在考虑范围内：%s" % (abspath[-4:]))


def get_duration(abspath, settings=SETTINGS):
    """
    获取`.gif`图片和视频文件的时长
    """
    if (abspath[-4:] == ".gif") or (abspath[-4:] == ".gif"):
        clip = VideoFileClip(
            abspath,
            audio=False,
        )
        res = clip.duration
        clip.close()
        return res
    elif abspath[-4:] in settings["supportedFormat"]["video"]:
        clip = VideoFileClip(
            abspath,
            audio=False,
        )
        res = clip.duration
        clip.close()
        return res
    else:
        print("获取视频长度的格式不受支持")
        exit()


def get_fps(abspath):
    video = cv2.VideoCapture(abspath)
    fps = video.get(cv2.CAP_PROP_FPS)
    return fps
