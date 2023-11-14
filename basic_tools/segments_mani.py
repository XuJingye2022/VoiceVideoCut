import logging
from portion import closed, empty
from multipledispatch import dispatch


@dispatch(list, float, float)
def remove_noise(time_lst: list, max_t: float, noise_sig_length: float):
    """
    前后一段时间内没有声音的，视为噪声
    """
    tmp_lst = [(max(0, t - 0.0011), min(max_t, t + 0.0011)) for t in time_lst]
    tmp_lst = combine_time_segments(tmp_lst, 0)
    res_lst = []
    for t1, t2 in tmp_lst:
        if t2 - t1 >= noise_sig_length:
            res_lst.append((t1, t2))
    return res_lst


@dispatch(list, float)
def remove_noise(segments: list, noise_sig_length: float):
    """
    片段过短的，视为噪声
    
    `segments`可能有两种类型。
    
    1. 来自于VAD分析的`list[dict]`类型。
    
    2. 来自音量分析的`list[tuple]`类型。
    """
    if isinstance(segments[0], dict):
        return [s for s in segments if s["end"] - s["start"] > noise_sig_length]
    else:
        return [s for s in segments if s[1] - s[0] > noise_sig_length]


def combine_time_segments(segments: list[tuple], t_error):
    """组合各个比较近的时间范围

    `t_error`: 时间范围之间的最大容许距离
    """
    if isinstance(segments[0], dict):
        results = []
        i = 0
        while i < len(segments):
            s = segments[i]
            for j in range(i + 1, len(segments)):
                if segments[j]["start"] < s["end"] + t_error:
                    s["end"] = segments[j]["end"]
                    i = j
                else:
                    break
            i += 1
            results.append(s)
        return results
    else:
        pre_t1, pre_t2 = segments[0]
        if pre_t1 > pre_t2:
            logging.error(f"Cut range error: {pre_t1} and {pre_t2}")
            return None

        res_lst = []
        for t1, t2 in segments:
            if t1 >= t2:
                logging.error(f"Cut range error: {t1} and {t2}")
                return None

            if t1 > pre_t2 + t_error:
                res_lst.append((pre_t1, pre_t2))
                pre_t1, pre_t2 = t1, t2
            else:
                pre_t2 = t2
        res_lst.append((pre_t1, pre_t2))
        return res_lst


def union_of_time_segments(time_segments_1: list, time_segments_2: list):
    """将时间范围的并集"""
    intervals1 = _time_segments_to_intervals(time_segments_1)
    intervals2 = _time_segments_to_intervals(time_segments_2)
    return _intervals_to_time_segments(intervals1 | intervals2)


def intersection_of_time_segments(time_segments_1: list, time_segments_2: list):
    """将时间范围的交集"""
    intervals1 = _time_segments_to_intervals(time_segments_1)
    intervals2 = _time_segments_to_intervals(time_segments_2)
    return _intervals_to_time_segments(intervals1 & intervals2)


def difference_of_time_segments(time_segments_1: list, time_segments_2: list):
    """将时间范围的差集"""
    intervals1 = _time_segments_to_intervals(time_segments_1)
    intervals2 = _time_segments_to_intervals(time_segments_2)
    return _intervals_to_time_segments(intervals1 - intervals2)


def expand_time_segments(
    segments: list,
    expand_head,
    expand_tail,
    min_t,
    max_t,
):
    """将时间范围向前扩展`expand_head`，向后扩展`expand_tail`."""
    if isinstance(segments[0], dict):
        results = []
        for i in range(len(segments)):
            t = segments[i]
            start = max(t["start"] - expand_head, segments[i - 1]["end"] if i > 0 else 0)
            end = min(
                t["end"] + expand_tail,
                segments[i + 1]["start"] if i < len(segments) - 1 else max_t,
            )
            results.append({"start": start, "end": end})
        return results
    else:
        intervals = empty()
        for tL, tR in segments:
            new_tL = tL - expand_head
            new_tR = tR + expand_tail
            intervals = intervals | closed(new_tL, new_tR)
        intervals = intervals & closed(min_t, max_t)
        return _intervals_to_time_segments(intervals)


def _time_segments_to_intervals(time_segments: list[tuple]):
    intervals = empty()
    for tL, tR in time_segments:
        intervals = intervals | closed(tL, tR)


def _intervals_to_time_segments(intervals):
    time_segments = []
    for interval in intervals:
        time_segments.append((interval.lower, interval.upper))
    return time_segments
