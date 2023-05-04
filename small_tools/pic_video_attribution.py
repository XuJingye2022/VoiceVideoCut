# 获取图片和视频的属性

import toml
from PIL import Image
import cv2
from moviepy.editor import VideoFileClip


def get_size(abspath, settings):
    """获取图片/视频尺寸
    """
    if abspath[-4:] in settings["supportedFormat"]["picture"]:
        return Image.open(abspath).convert("RGB").size
    elif (abspath[-4:]==".gif") or (abspath[-4:]==".GIF"):
        clip = VideoFileClip(abspath, audio=False,)
        res = clip.size
        clip.close()
        return res
    elif abspath[-4:] in settings["supportedFormat"]["video"]:
        video = cv2.VideoCapture(abspath)
        return (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    else:
        raise("文件格式不在考虑范围内：%s" %(abspath[-4:]))

def get_duration(abspath, settings):
    """
    获取`.gif`图片和视频文件的时长
    """
    if (abspath[-4:]==".gif") or (abspath[-4:]==".gif"):
        clip = VideoFileClip(abspath, audio=False,)
        res = clip.duration
        clip.close()
        return res
    elif abspath[-4:] in settings["supportedFormat"]["video"]:
        clip = VideoFileClip(abspath, audio=False,)
        res = clip.duration
        clip.close()
        return res
    else:
        print("获取视频长度的格式不受支持")
        exit()


if __name__ == "__main__":
    settings = toml.load("./settings.toml")
    # vidpath = r"C:\Users\徐景晔\Pictures\Camera Roll\test.mp4"
    # gifpath = r"C:\Users\徐景晔\Pictures\搞笑图片\007kPYPngy1hb5jpfa8lfg304q06b4qp.gif"
    # print(get_size(gifpath, settings))
    # print(get_size(vidpath, settings))
    # print(get_duration(gifpath, settings))
    # print(get_duration(vidpath, settings))
    print(get_duration(r'E:\游戏视频\2023-04-17 饥饿派画家2：迷失\2023-04-17 22-30-04.mkv', settings))