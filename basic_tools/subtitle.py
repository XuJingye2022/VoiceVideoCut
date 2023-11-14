# encoding:utf-8
import time
import datetime
import os
import socket
import re

import json
import getpass
import whisper
import opencc
import pandas as pd
from tqdm import tqdm
from multipledispatch import dispatch
from pydub import AudioSegment
import torch

from .time_format import hms_to_seconds
from .file_mani import get_all_files_with_extensions


user_name = getpass.getuser()  # 获取当前用户名
hostname = socket.gethostname()  # 获取当前主机名

cc = opencc.OpenCC("t2s")


def get_mp3_content_in_folder(audio_folder, data_path):
    names, abs_paths = get_all_files_with_extensions(audio_folder, "mp3")
    abs_paths.sort()
    df = pd.read_csv(data_path, index_col=0)
    for name, abs_path in tqdm(
        zip(names, abs_paths), desc="Speech recognizing", total=len(names)
    ):
        df.loc[name, "text"] = get_mp3_content(abs_path)
    df.to_csv(data_path)
    return df


@dispatch(str, list)
def get_mp3_content(audio_path: str, t_ranges: list):
    text_list = []
    model = whisper.load_model("large", in_memory=True)
    # 加载整个mp3文件
    audio = AudioSegment.from_file(audio_path)
    for t_start, t_end in t_ranges:
        # 提取范围
        segment = audio[int(round(t_start * 1000)) : int(round(t_end * 1000))]
        print(segment)
        # 转化为字节流
        # segment_bytes = np.array(segment.get_array_of_samples())
        segment_bytes = segment.export(format="mp3").read()
        # segment_bytes = segment_bytes.decode('latin-1', errors='ignore').encode('utf-8')
        audio_segment = whisper.load_audio(segment_bytes)
        mel = whisper.log_mel_spectrogram(audio_segment).to(model.device)
        # decode the audio
        options = whisper.DecodingOptions(fp16=False, language="Chinese")
        result = whisper.decode(model, mel, options)
        # print the recognized text
        text = cc.convert(result.text, "zh-cn")
        text_list.append(text)
    return text_list


@dispatch(str)
def get_mp3_content(audio_path: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = whisper.load_model("base", in_memory=True).to(device)
    audio = whisper.load_audio(audio_path)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(device)
    # decode the audio
    options = whisper.DecodingOptions(fp16=False, language="Chinese")
    result = whisper.decode(model, mel, options)
    # print the recognized text
    text = cc.convert(result.text, "zh-cn")
    return text


def get_srt_second_range(srt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        texts = f.readlines()
    text = "".join(texts)
    text = text.replace(",", ".")
    time_ranges_str = re.findall(
        r"[\d]{2}:[\d]{2}:[\d]{2}.[\d]{3} --> [\d]{2}:[\d]{2}:[\d]{2}.[\d]{3}", text
    )
    time_ranges_lst = []
    for time_range_str in time_ranges_str:
        hms1, hms2 = time_range_str.split(" --> ")
        time_ranges_lst.append((hms_to_seconds(hms1), hms_to_seconds(hms2)))
    return time_ranges_lst


def get_srt_text(srt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        texts = f.readlines()
    text = "".join(texts)
    text = text.replace("\n\n\n", "\n")
    text = text.replace("\n\n", "\n")
    texts = text.split("\n")
    return texts[2 : len(texts) : 3]


def save_jianying_subtitle_as_srt(savepath):
    """
    获取剪映的字幕文件，保存为srt文件。
    """
    content = merger_content()
    n = 0
    text = ""
    for ct in content:
        n += 1
        content_text = ct[0]
        start_duration = timeFormat(str(ct[1]).replace(".", ","))
        end_duration = timeFormat(str(ct[-1]).replace(".", ","))
        text_duration = f"{start_duration} --> {end_duration}"
        text += str(n) + "\n" + text_duration + "\n" + content_text + "\n\n"
    # 写入
    with open(savepath, "w", encoding="utf-8") as f:
        f.write(str(text))


def merger_content():
    """
    把时间与字幕内容合并
    :return:
    """
    content = get_content()
    duration_time = get_tracks()

    subtitle = []

    for k, v in content.items():
        durationinfo = duration_time[k]
        duration = int(durationinfo["duration"])  # 字幕片段时长时间
        start = int(durationinfo["start"]) / 1000000  # 字幕片段开始时间
        statrTime = datetime.timedelta(seconds=start)  # 转换成时间格式
        endduration = (
            int(int(durationinfo["duration"])) + int(durationinfo["start"])
        ) / 1000000
        endTime = datetime.timedelta(seconds=endduration)
        duration_list = [str(statrTime), str(endTime)]
        t = [v] + duration_list
        subtitle.append(t)
    return subtitle


def get_content():
    """
    获取字幕内容
    :return:
    """
    materials = readjson()["materials"]
    texts = materials["texts"]
    content = {}
    for tt in texts:
        textId = tt["id"]
        text_content = re.findall(r"\[(.*?)\]", tt["content"])[0]
        text_dict = {textId: text_content}
        content.update(text_dict)
    return content


def get_tracks():
    """
    获取时间
    :return:
    """
    tracks = readjson()["tracks"]
    durations_dict = {}
    for tk in tracks:
        flag = tk["flag"]
        if str(flag) == "1":
            segments = tk["segments"]
            for s in segments:
                material_id = s["material_id"]
                target_timerange = s["target_timerange"]
                duration = {material_id: target_timerange}
                durations_dict.update(duration)
    return durations_dict


def readjson():
    """
    读取字幕文本
    :return:
    """
    with open(readfiles(), "r", encoding="utf-8") as load_f:
        load_dict = json.load(load_f)
        return load_dict


def readfiles():
    path = rf"C:\Users\{user_name}\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"

    path = new_report(path)
    file = os.listdir(path)
    draft_content = [x for x in file if "draft_content.json" == x][0]
    subtitle_path = os.path.join(path, draft_content)
    print("读取到 剪映字幕文件")
    return subtitle_path


def new_report(test_report):
    """
    读取文件，并返回最新的目录（文件夹）路径
    :param test_report:
    :return:
    """
    file = os.listdir(test_report)  # 列出目录的下所有文件和文件夹保存到lists

    folderlist = []
    tdict = {}

    for f in file:
        filepath = os.path.join(test_report, f)
        if os.path.isdir(filepath) == True:
            folderlist.append(str(f))
            ctime = time.ctime(os.path.getctime(filepath))
            s = int(time.mktime(time.strptime(ctime, "%a %b %d %H:%M:%S %Y")))
            t = {s: f}
            tdict.update(t)

    max_time = max(list(tdict.keys()))
    new_filepath = os.path.join(test_report, tdict[max_time])
    return new_filepath


def timeFormat(t):
    h = t.split(":")[0]
    m = t.split(":")[1]
    s = t.split(":")[-1][0:6]
    if len(re.findall(",", s)) == 0:
        s += ",000"

    if len(h) == 1:
        timeT = ["0" + str(h)] + [m] + [s]
        timeT = ":".join(timeT)
        return timeT
    if len(h) == 2:
        timeT = [h] + [m] + [s]
        timeT = ":".join(timeT)
        return timeT


if __name__ == "__main__":
    text_list = get_mp3_content(
        r"E:\游戏视频\2023-09-22【Realistic Colonies】P06 能装岩浆的背包、惨死于下界\Output\output_cut.wav",
        [(4, 7)],
    )
    print(text_list)
