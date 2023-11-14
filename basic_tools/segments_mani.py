from portion import closed, empty


def remove_noise(time_lst: list, max_t, noise_sig_length) -> list:
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


def combine_time_segments(t_ranges: list[tuple], t_error):
    """组合各个比较近的时间范围

    `t_error`: 时间范围之间的最大容许距离
    """
    pre_t1, pre_t2 = t_ranges[0]
    if pre_t1 > pre_t2:
        print(f"Cut range error: {pre_t1} and {pre_t2}")
        return None

    res_lst = []
    for t1, t2 in t_ranges:
        if t1 >= t2:
            print(f"Cut range error: {t1} and {t2}")
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
    time_segments: list,
    prepend_delta_t,
    append_delta_t,
    min_t,
    max_t,
):
    """将时间范围向前扩展`prepend_delta_t`，向后扩展`append_delta_t`."""
    intervals = empty()
    for tL, tR in time_segments:
        new_tL = tL - prepend_delta_t
        new_tR = tR + append_delta_t
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
