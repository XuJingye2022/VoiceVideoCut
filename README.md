# VoiceVideoCut
这个程序是用来裁切语音视频的。
适合录制无特效的**视频教程**、**游戏录屏**、**反应视频**。

初始是因为大量游戏录屏充斥着无意义的片段，因此希望精简一些。

## 这个程序可以做什么
通过纯人声音轨（目前也支持的混合音轨，但是效果很差）, 找到连续的人声范围——即初始的剪辑范围. 

然后每个范围都可以在编辑界面中预览. 如果觉得这个范围需要扩展, 你可以通过`+1s`和`-1s`按钮来调整. 当然过于接近的范围最后会合并.


## 使用方法
1. 下载整个程序.
2. 有GPU的，自己根据自己CUDA版本，自行安装PyTorch。没有GPU的也没关系，只是无法使用语音识别功能，根据音量来划分片段还是可以的。先执行这一步，可以避免第三步安装`whisper`时，安装CPU版本的PyTorch。
3. 在`requirements.txt`同一级目录下, 用`pip3 install -r requirements.txt`安装依赖。
4. 安装[K-Lite Codec Pack](http://www.codecguide.com/download_k-lite_codec_pack_standard.htm).
5. 安装[OBS](https://obsproject.com/download).
6. 安装ffmpeg，并在环境变量中添加`ffmpeg`的路径.
7. 使用OBS录制之前, 点击`混音器 - 设置`, 并给单独给麦克风音轨2.
    ![](pics/2023-05-04%20075434.png)
    在OBS设置中, 设置视频类型为`mp4`, 且视频音轨选中`1`和`2`(其中音轨`2`就是麦克风音轨).
    ![](pics/2023-05-04%20075857.png)
8. 录制视频.
9. 运行`Main.py`.
10. 通过`Open Video File`选择视频文件.
11. 点击`Analyze`分析人声的范围.
   * 当持续时间小于0.5s会被认为是噪声并删除掉——你可以在`GamMicroTrack.py`的120行更改设置.
   * 如果视频目录存在`SpeechRange.csv`, 将会直接读取. 想删除的话可以点击`Clear Cache`删除所有缓存文件.
12. 通过点击4个`-/+`符号, 调整剪辑片段的左右边界.
    如果你觉得这个片段不需要, 可以选择`Noise`单选框.
    你可以通过点击文本框(有时单机有时双击), 预览视频.
13. 点击`Save New Range`保存剪辑范围到`CutRange.csv`. 再次点击`Analyze`, 就会加载`CutRange.csv`到编辑列表. 如果你不满意, 或者程序崩溃了, 只要`CutRange.csv`存在, 就可以继续编辑.
14. 通过点击`Cut`剪辑视频。`Cut`意味着删除剪辑范围之外的片段;
15. 点击`Clear Cache`清楚所有缓存文件.


## 一些问题
- 所有过程都是单线程, 尤其是导出视频时, 千万不能动主窗口.
- 代码可读性差了点.
- 没有防呆设计，用的时候只能按操作顺序来.

## TODO
- [ ] 秒数尝试更改为时间码`xx:xx:xx:xx`，`Hours:Minutes:Seconds:Frames`
- [x] 尝试QLineEdit通过方向键上下键调整时间。
- [ ] 尝试在编辑字幕同时，完成剪辑的操作。


## 文件结构说明
```
VOICEVIDEOCUT
| README.md                     # 简单说明文档
| settings.toml                 # 剪辑设置文件，可在里面直接更改
└ QSS-master                    # 窗口设置文件
└ pics                          # Markdown中会用到的图片
└ basic_tools                   # 自定义的一些代码
    | __init__.py               # 包初始化文件
    | clip_video.py             # 实行基本的剪辑操作
    | cut.py                    # 剪辑视频
    | divide_speech.py          # 划分讲话的时间段
    | export_audio_track.py     # 导出音轨
    | file_mani.py              # 获取文件名、更改文件名后缀
    | get_dB_from_mp3.py        # 获取音轨文件中的分贝值
    | is_video_audio.py         # 判断是否是音视频文件
    | pic_video_attribution.py  # 获取图片、视频的属性尺寸时长特性
    | save_whisper_results.py   # 保存whisper语音分析的结果
    | segments_mani.py          # 对识别出的语音片段范围进行扩展、合并等操作
    | speech.py                 # 语音识别
    | subtitle_line_edit.py     # 自定义的QLineEdit，用于编辑字幕的合并、分段操作
    └ time_format.py            # 各种时间格式的转换
```

## 为什么优先采用双音轨
纯人声音轨，可以：
1. 避免与游戏中的人声混合。便于之后的whisper语音识别。

2. 能让程序根据音量大小来提取讲话片段。根据我的体验，VAD效果没有根据音量的提取效果好。下面就是一个VAD+whisper方案划分失败的案例。

```
[
    {
        'text': '你到底抽不出来',
        'segments': [
            {
                'id': 0,
                'seek': 0,
                'start': 0.0,
                'end': 2.0,
                'text': '你到底抽不出来',
                'tokens': [50364, 2166, 33883, 46022, 1960, 44561, 50464],
                'temperature': 0.0,
                'avg_logprob': -0.8920868039131165,
                'compression_ratio': 0.65625,
                'no_speech_prob': 0.11517102271318436
            }
        ], 
        'language': 'zh',
        'origin_timestamp': (29088, 384480)  # (1.818 sec, 24.03 sec)
    }, 
    {
        'text': '啊,對,要建房子', 
        'segments': [
            {
                'id': 0,
                'seek': 0,
                'start': 0.0,
                'end': 1.8,
                'text': '啊,對,要建房子', 
                'tokens': [50364, 4905, 11, 2855, 11, 4275, 34157, 38242, 7626, 50454],
                'temperature': 0.0, 
                'avg_logprob': -0.43075110695578833, 
                'compression_ratio': 0.6896551724137931, 
                'no_speech_prob': 0.016884278506040573
            }
        ],
        'language': 'zh',
        'origin_timestamp': (426912, 456160)   # (26.682 sec, 28.51 sec)
    }
]
```
注意`origin_timestamp`后的注释，为换算成秒的结果。

第一段的范围太大了，足足将22秒的片段代入whisper。而whisper只在其中2秒的范围内识别出了文本。这2秒具体从哪个时间开始的到什么时间结束，完全不知道。

通常的做法是，取`origin_timestamp`的开头两秒，但是这里，我正确的语音出现的时间却是在后两秒。