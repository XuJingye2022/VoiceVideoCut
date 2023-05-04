# VoiceVideoCut
这个程序是用来剪辑双音轨的语音视频的. 适合录制无特效的**视频教程**、**游戏录屏**、**反应视频**.

*This progam is used to cut speech in a dual track video, suitable for **video tutorials**, **game screen recording** and **reaction video**.*

# What does this program do?
通过人声音轨, 找到连续的人声范围——即初始的剪辑范围. 

*By voice track, the program can calculate speech range, which is initial clipping range.*

然后每个范围都可以在编辑界面中预览. 如果觉得这个范围需要扩展, 你可以通过`+1s`和`-1s`按钮来调整. 当然过于接近的范围最后会合并.

*Every clipping range can be previewed in the program, and you can adjust these ranges by `+1s` and `-1s` button. Two ranges too close will be combined at last.*

最后, 你有两个导出方式:

*At last, you have two methods to export this video:*

1. 删除其它范围, 

    *Export without parts outside these clipping ranges;*

2. 加速其它范围.
   
    *Export with those parts but at multiple speeds.*


# How to use it?
1. 下载整个程序.
   
   *Download all this program.*
2. 安装[K-Lite Codec Pack](http://www.codecguide.com/download_k-lite_codec_pack_standard.htm).
   
   Install [K-Lite Codec Pack](http://www.codecguide.com/download_k-lite_codec_pack_standard.htm).
3. 安装[OBS](https://obsproject.com/download).
   
   Install [OBS](https://obsproject.com/download).
   
4. 使用OBS录制之前, 点击`混音器 - 设置`, 并给单独给麦克风音轨2.

    Before recording, you should clik `Audio Mixer - Advanced Audio Properties`, and set microphone to track 2.

    ![](pics/2023-05-04%20075434.png)

    在OBS设置中, 设置视频类型为`mp4`(`mkv`格式的`self.media_player.position()`计时方法会有错误), 且视频音轨选中`1`和`2`(其中音轨`2`就是麦克风音轨).

    In `Setting - Output - Recording`, you need to set `Recording Format`: `mp4` and `Audio Track`: `1+2`.(Track `2` is microphone track)

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
  
  Every function is single thread. Don't move the window especially when export videos.

- 代码可读性差了点.
  
- 用的时候小心点.

我自己打算增加如下功能:
- [ ] 光标移动到剪辑时间范围的中间时， 会出现`+`按钮， 你可以点击它增加新的行. 新的行不默认为Chat, 而是Trans, 意味着Transition scenes, 过渡场景. 用来交代从前一个场景到后一个场景的过渡. 用来交代游戏角色动作的连续. QRadioButton三个分别为: Trans, Chat(enable=False), noise.
- [ ] 