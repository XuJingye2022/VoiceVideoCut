import subprocess
from .filemani import change_suffix
import os

def mkv2mp4(video_path: str):
    output_path = change_suffix(video_path, "mp4")
    if not os.path.exists(output_path):
        cmd = f'ffmpeg -i "{video_path}" -codec copy "{output_path}"'
        subprocess.call(cmd)
    os.remove(video_path)
    return output_path