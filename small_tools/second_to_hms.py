def seconds_to_hms(seconds):
    # 计算小时数和余数
    hours, remainder = divmod(seconds, 3600)
    # 计算分钟数和秒数
    minutes, seconds = divmod(remainder, 60)
    # 返回结果
    return hours, minutes, seconds