import os, shutil
from multipledispatch import dispatch

def clip_video(input_video: str, tL: float, tR: float, output_video: str, audio: bool = False):
    """剪切视频
    """
    if audio is False:
        print(f"ffmpeg -loglevel quiet -y -i {input_video} -an -ss {tL} -to {tR} {output_video}")
        os.system(f"ffmpeg -loglevel quiet -y -i {input_video} -an -ss {tL} -to {tR} {output_video}")
    else:
        print(f"ffmpeg -loglevel quiet -y -i {input_video} -ss {tL} -to {tR} {output_video}")
        os.system(f"ffmpeg -loglevel quiet -y -i {input_video} -ss {tL} -to {tR} {output_video}")


def clip_audio(input_audio: str, tL: float, tR: float, output_audio: str):
    """剪切音频
    """
    print(f"ffmpeg -loglevel quiet -y -i {input_audio} -ss {tL} -to {tR} -vn {output_audio}")
    os.system(f"ffmpeg -loglevel quiet -y -i {input_audio} -ss {tL} -to {tR} -vn {output_audio}")


def combine_video_and_audio(input_video, input_audio, ouput_video):
    os.system(f"ffmpeg -loglevel quiet -y -i {input_video} -i {input_audio} {ouput_video}")

@dispatch(str, str, str)
def combine_videos(input_video1, input_video2, output_video):
    cmd1 = 'ffmpeg -i "concat:'
    cmd2 = "|".join([input_video1, input_video2])
    cmd3 = f'" "{output_video}"'
    print(cmd1 + cmd2 + cmd3)
    os.system(cmd1 + cmd2 + cmd3)


@dispatch(list, str)
def combine_videos(input_video_lst, output_video):
    # 创建一个包含所有视频文件名的文本文件
    with open("input_list.txt", "w", encoding="utf8") as file:
        for video in input_video_lst:
            file.write(f"file '{video}'\n")

    # 使用ffmpeg执行合并操作
    os.system(f'ffmpeg -loglevel quiet -y -f concat -safe 0 -i input_list.txt -c copy {output_video}')

    # 删除临时文件
    os.remove("input_list.txt")

def append_clip_to_video(input_video: str, tL: float, tR: float, output_video: str, audio: bool = False):
    if not os.path.exists(output_video):
        clip_video(input_video, tL, tR, output_video, audio)
    else:
        tmp_name = os.path.join(os.path.split(output_video)[0], "tmp.mp4")
        clip_video(input_video, tL, tR, tmp_name, audio)
        print("导出单视频临时文件成功")
        tmp_all = os.path.join(os.path.split(output_video)[0], "tmp_output.mp4")
        combine_videos(output_video, tmp_name, tmp_all)
        print("导出总视频临时文件成功")
        os.remove(tmp_name)
        os.remove(output_video)
        os.rename(tmp_all, output_video)
