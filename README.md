# VoiceVideoCut
这个程序是用来剪辑双音轨的语音视频的. 适合录制无特效的**视频教程**、**游戏录屏**、**反应视频**.
This progam is used to cut speech in a dual track video, suitable for **video tutorials**, **game screen recording** and **reaction video**.

# How to use it?
1. 下载整个程序. Download all this program.
2. 安装K-Lite Codec Pack给装了. Install [K-Lite Codec Pack](http://www.codecguide.com/download_k-lite_codec_pack_standard.htm).
3. 安装OBS. Install [OBS](https://obsproject.com/download).
4. 使用OBS录制之前, 点击混音器的设置, 并给麦克风一个单独的音轨.
![](pics/2023-05-04%20075434.png)
在OBS设置中, 设置视频类型为`mp4`(`mkv`格式的`self.media_player.position()`计时方法会有错误), 且视频音轨选中`1`和`2`(其中音轨`2`就是麦克风音轨).
![](pics/2023-05-04%20075857.png)
5. 录制视频.
6. 运行`Main.py`.
7. 通过`Open Video File`选择视频文件.
8. 点击`Analyze`分析人声的范围.
   * 当持续时间小于0.5s会被认为是噪声并删除掉.
   * 如果视频目录存在`SpeechRange.csv`, 将会直接读取. 想删除的话可以点击`Clear Cache`删除所有缓存文件.
9. 通过点击4个`-/+`符号, 调整剪辑片段的左右边界.
    如果你觉得这个片段不需要, 可以选择`Noise`单选框.
    你可以通过点击文本框(有时单机有时双击), 预览视频.
10. 点击`Save New Range`保存剪辑范围到`CutRange.csv`. 再次点击`Analyze`, 就会加载`CutRange.csv`到编辑列表. 如果你不满意, 或者程序崩溃了, 只要`CutRange.csv`存在, 就可以继续编辑.
11. 通过点击`Cut`或者`Acc Cut`剪辑视频:
    * `Cut`意味着删除剪辑范围之外的片段;
    * `Acc Cut`意味着加速剪辑范围之外的片段.
12. 点击`Clear Cache`清楚所有缓存文件.


# Some Problem
- 所有过程都是单线程, 尤其是导出视频时, 千万不能动主窗口.
- 代码可读性差了点.