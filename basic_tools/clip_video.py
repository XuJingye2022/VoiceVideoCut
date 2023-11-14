import os


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


def combine_videos(input_video_list, output_video):
    cmd1 = 'ffmpeg -i "concat:'
    cmd2 = "|".join(input_video_list)
    cmd3 = f'" {output_video}'
    print(cmd1 + cmd2 + cmd3)
    os.system(cmd1 + cmd2 + cmd3)