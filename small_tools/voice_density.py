# 这个包用来根据剪辑时间范围CutRange.csv
# 评估声音文件中人声的密度
# 并绘制图像

# ====================================== 导入Python加速器库 ==================================================
import socket, sys
host_name = socket.gethostname()
if (host_name == 'localhost.localdomain'): sys.path.insert(0, '/home/xujingye/MyFunction') # 导师工作站
if (host_name[0:6] == 'acc-ap'): sys.path.insert(0, '/sharefs/heps/user/xujingye/MyFunction') # acc-apXX.ihep.ac.cn 服务器
if (host_name == 'DESKTOP-FDIN0I7'): sys.path.insert(0, 'D:/Documents/PythonFiles/001.科研/000.Accelerator/MyFunctionForAccelerator') # 办公室电脑
if (host_name == '宿舍电脑'): sys.path.insert(0, r'F:/Documents/PythonProgramme/001.科研/000.Accelerator/MyFunctionForAccelerator') # 宿舍电脑
if (host_name == 'Tina'): sys.path.insert(0, r'D:/PythonFile/001.科研/000.Accelerator/MyFunctionForAccelerator') # Surface
if (host_name == '家里电脑'): sys.path.insert(0, r'E:/Documents/PythonProgramme/001.科研/000.Accelerator/MyFunctionForAccelerator') # 家里电脑
# ===========================================================================================================

from plot_fun import density_distribution
import numpy as np
from file_manipulation import change_suffix
import os
import pandas as pd

def get_voice_density(cut_range_list, abs_video_path):
    abs_audio_volume_path = change_suffix(abs_video_path, "csv")
    df = pd.read_csv(abs_audio_volume_path)
    res_time_list = []
    res_density_list = []
    for t1, t2 in cut_range_list:
        bin_num = (t2 - t1)/0.1
        # Select volumn data
        tmpdf = df[t1<=df["time"]<=t2]
        tmpdf.reset_index(inplace=True, drop=True)
        # Load time and volumn data
        time_arr = np.array(tmpdf["time"])
        dB_arr = np.array(tmpdf["dB"])
    
