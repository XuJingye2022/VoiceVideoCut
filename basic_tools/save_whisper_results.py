import srt
import datetime
import pandas as pd
import opencc

cc = opencc.OpenCC("t2s")

def save_dataframe(speech_range_path, transcribe_results, sample_rate, lang="zh"):
    df = pd.DataFrame(columns=["start", "end", "text", "use"])

    def _add_sub(df, start, end, text):
        df.loc[len(df)] = {
            "start": start,
            "end": end,
            "text": cc.convert(text) if lang == "zh" else text,
            "use": True,
        }
        return df

    for r in transcribe_results:
        origin = r["origin_timestamp"]

        for s in r["segments"]:
            start = s["start"] + origin[0] / sample_rate
            end = min(
                s["end"] + origin[0] / sample_rate,
                origin[1] / sample_rate,
            )
            if start > end:
                continue
            # mark any empty segment that is not very short
            df = _add_sub(df, start, end, s["text"])
    df.to_csv(speech_range_path, index=False)


def gen_srt(all_text_list, sub_segs_in_output_video):
    if len(all_text_list) != len(sub_segs_in_output_video):
        print(len(all_text_list), "!=", len(sub_segs_in_output_video))
        raise "不等长？"

    subs = []

    def _add_sub(start, end, text):
        subs.append(
            srt.Subtitle(
                index=0,
                start=datetime.timedelta(seconds=start),
                end=datetime.timedelta(seconds=end),
                content=text.strip(),
            )
        )

    for i in range(len(all_text_list)):
        start = sub_segs_in_output_video[i][0]
        end = sub_segs_in_output_video[i][1]
        text = all_text_list[i]
        _add_sub(start, end, text)

    return subs


def save_srt(
    output_path,
    all_text_list,
    sub_segs_in_output_video,
    encoding="utf8",
):
    subs = gen_srt(all_text_list, sub_segs_in_output_video)  # 生成.srt文件的字幕
    with open(output_path, "wb") as f:
        f.write(srt.compose(subs).encode(encoding, "replace"))  # 将字幕写入.srt文件


def subtitle_segments_in_output_video(
    subtitle_segments_list: list[list],
    cut_segments_list: list[list],
    all_text_list: list[list]
):
    """通过字幕在原视频中的位置，以及原视频的剪切位置，获得字幕在新视频中的位置"""
    subtitle_segments_in_output_video = []
    temp_text_list = []

    total_time_pre = 0
    for subtitle_segments, cut_segments, text_list in zip(
        subtitle_segments_list, cut_segments_list, all_text_list
    ):
        for tL, tR in cut_segments:
            for (sub_tL, sub_tR), text in zip(subtitle_segments, text_list):
                if sub_tR < tL:
                    continue
                if sub_tL > tR:
                    break
                subtitle_segments_in_output_video.append(
                    (
                        total_time_pre + max(sub_tL, tL) - tL,
                        total_time_pre + min(sub_tR, tR) - tL,
                    )
                )
                temp_text_list.append(text)
            total_time_pre += tR - tL

    return subtitle_segments_in_output_video, temp_text_list
