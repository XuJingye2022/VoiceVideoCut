# VoiceVideoCut
这个程序是用来剪辑双音轨的语音视频的. 适合录制无特效的**视频教程**、**游戏录屏**、**反应视频**.

# 这个程序可以做什么
通过人声音轨, 找到连续的人声范围——即初始的剪辑范围. 

然后每个范围都可以在编辑界面中预览. 如果觉得这个范围需要扩展, 你可以通过`+1s`和`-1s`按钮来调整. 当然过于接近的范围最后会合并.

最后, 你有两个导出方式:

1. 删除其它范围, 

2. 加速其它范围(感觉没用，暂时没做).

# 使用方法
1. 下载整个程序.
   
2. 安装[K-Lite Codec Pack](http://www.codecguide.com/download_k-lite_codec_pack_standard.htm).
   
3. 安装[OBS](https://obsproject.com/download).
   
4. 使用OBS录制之前, 点击`混音器 - 设置`, 并给单独给麦克风音轨2.

    ![](pics/2023-05-04%20075434.png)

    在OBS设置中, 设置视频类型为`mkv` or `mp4`(Update 2023.05.24), 且视频音轨选中`1`和`2`(其中音轨`2`就是麦克风音轨).

    ![](pics/2023-05-04%20075857.png)

5. 录制视频.
   
6. 运行`Main.py`.
   
7. 通过`Open Video File`选择视频文件.
   
8. 点击`Analyze`分析人声的范围.
   * 当持续时间小于0.5s会被认为是噪声并删除掉——你可以在`GamMicroTrack.py`的120行更改设置.
   * 如果视频目录存在`SpeechRange.csv`, 将会直接读取. 想删除的话可以点击`Clear Cache`删除所有缓存文件.
   
9. 通过点击4个`-/+`符号, 调整剪辑片段的左右边界.
    如果你觉得这个片段不需要, 可以选择`Noise`单选框.
    你可以通过点击文本框(有时单机有时双击), 预览视频.
10. 点击`Save New Range`保存剪辑范围到`CutRange.csv`. 再次点击`Analyze`, 就会加载`CutRange.csv`到编辑列表. 如果你不满意, 或者程序崩溃了, 只要`CutRange.csv`存在, 就可以继续编辑.
11. 通过点击`Cut`剪辑视频。`Cut`意味着删除剪辑范围之外的片段;
12. 点击`Clear Cache`清楚所有缓存文件.


# 一些问题
- 所有过程都是单线程, 尤其是导出视频时, 千万不能动主窗口.
  
- 代码可读性差了点.
  
- 用的时候小心点.

# TODO
- [ ] 配合[Whisper](https://github.com/openai/whisper) or [autocut](https://github.com/dorgonman/autocut) or [CTranslate2](https://github.com/OpenNMT/CTranslate2/)，展示字幕文件