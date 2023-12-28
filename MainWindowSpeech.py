# 第一按钮：选择视频
#     选择后会：导入视频
# 第二按钮：语音识别
#     1. 导出`.wav`麦克风音轨
#     2. 调用whisper分析麦克风录音，并保存至
#         - `<videoname>_SpeechRange.csv`
#        其格式为："time segments", "text"
#     3. 读取`<videoname>_SpeechRange.csv`，修改、筛选whisper字幕
# 第三按钮：加载剪辑范围
#     1. 如果没有`<videoname>_CutRange.csv`，就读取`<videoname>_SpeechRange.csv`
#        并将其中的"time segments"保存至`<videoname>_CutRange.csv`
#     2. 自动向前后扩展，合并后，调整、筛选视频剪辑范围，并保存到`<videoname>_CutRange.csv`
# Button.2 Analyze speech and load cut range.
# Button.3 Load cut range.
# Button.4 PLAY/STOP
# Button.5 Save cut range.
# Button.6 cut/speed video with/without .srt
# Button.7 Clear cache.

import sys
import os
import logging


import toml
import pandas as pd

from PyQt5.QtCore import QUrl, QTimer, Qt, QRect
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QMainWindow,
    QFileDialog,
    QPushButton,
    QScrollArea,
    QLineEdit,
    QWidget,
    QVBoxLayout,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QHBoxLayout,
    QSlider,
    QCheckBox,
)

from math import floor

from basic_tools import (
    SpeechVolume,
    SpeechVAD,
    SubLineEdit,
    get_duration,
    get_fps,
    get_all_files_with_extensions,
    change_file_extension,
    get_audio_track,
    expand_time_segments,
    save_dataframe,
    combine_time_segments,
    cut_game_record,
)

logging.basicConfig(level=logging.INFO)
pd.set_option("display.max_rows", None)


SETTINGS = toml.load("./settings.toml")
THREADS = SETTINGS["Gam"]["threads"]
SPEECH_CHANNEL = SETTINGS["Gam"]["speech_channel"]
PRE_T = SETTINGS["Gam"]["pre_time"]
AFT_T = SETTINGS["Gam"]["aft_time"]
BET_T = SETTINGS["Gam"]["bet_time"]


class QSSLoader:
    def __init__(self):
        pass

    @staticmethod
    def read_qss_file(qss_file_name):
        with open(qss_file_name, "r", encoding="UTF-8") as file:
            return file.read()


class CutRange(QMainWindow):
    def __init__(self):
        # ========== 参数 ============
        self.window_title = "Adjust Cut Range"
        self.video_w = 1200
        self.video_h = 675
        self.scroll_area_w = 530
        self.slider_h = 15
        self.button_w = int(floor(self.video_w - 80) / 7)
        self.button_h = 30
        self.window_w = self.video_w + self.scroll_area_w + 30
        self.window_h = self.video_h + self.button_h + 40
        self.mode_w = int(floor((self.scroll_area_w - 40) / 6))
        self.mode_h = 30
        # Something will used
        self.root = None  # 视频根目录
        self.abs_video_path = None  # 视频完整路径
        self.speech_range_path = None  # whisper识别的结果，包含语音范围、语音内容
        self.cut_range_path = None
        self.mode = None  # 由于窗口会变化，需要知道模式。"sub"字幕编辑模式；"vid"视频剪辑模式
        self.max_idx = None
        self.duration = 0  # Video Length
        self.fps = 0
        self.idx_play_now = 0  # idx of video playing
        self.colored_widget = (1, 1)

        # ============== Main Window ==============
        super().__init__()
        self.setFixedSize(self.window_w, self.window_h)
        self.setWindowTitle(self.window_title)
        style_file = "./QSS-master/Ubuntu.qss"
        style_sheet = QSSLoader.read_qss_file(style_file)
        self.setStyleSheet(style_sheet)

        # ============== Video Play ==============
        self.media_player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.media_player.setVideoOutput(self.video_widget)
        self.video_widget.mousePressEvent = self._play_pause_video
        self.video_widget.setGeometry(10, 10, self.video_w, self.video_h)
        # Timer For Video
        self.mode_timer = QTimer()
        self.mode_timer.timeout.connect(self.video_loop_mode)
        # Range For Video Playing
        self.tL = 0
        self.tR = 0
        # Video Progress Bar
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setGeometry(
            10,
            self.video_h + 10,
            self.video_w,
            self.slider_h
        )
        self.slider.setRange(0, 1000)

        # ============== Buttons below video player ==============
        # Button.1 Export voice track, open video file and analyze.
        # Button.2 Analyze speech and load cut range.
        # Button.3 Load cut range.
        # Button.4 PLAY/STOP
        # Button.5 Save cut range.
        # Button.6 cut/speed video with/without .srt
        # Button.7 Clear cache.
        self.open_folder_button = self.create_QPushButton(
            "Open Video File",
            10,
            self.video_h + 30,
            self.button_w,
            self.button_h,
            self.open_video_file,
        )
        self.analyze_speech_btn = self.create_QPushButton(
            "Analyze Speech",
            20 + 1 * self.button_w,
            self.video_h + 30,
            self.button_w,
            self.button_h,
            self.analyze_speech,
        )
        self.load_cut_range_btn = self.create_QPushButton(
            "Load Cut Range",
            30 + 2 * self.button_w,
            self.video_h + 30,
            self.button_w,
            self.button_h,
            self.load_cut_range,
        )
        self.play_button = self.create_QPushButton(
            "STOP",
            40 + 3 * self.button_w,
            self.video_h + 30,
            self.button_w,
            self.button_h,
            self.play_video,
        )
        self.save_button = self.create_QPushButton(
            "Save",
            50 + 4 * self.button_w,
            self.video_h + 30,
            self.button_w,
            self.button_h,
            self.save_data,
        )

        # Button.6
        self.cut = self.create_QPushButton(
            "Cut",
            60 + 5 * self.button_w,
            self.video_h + 30,
            self.button_w,
            self.button_h,
            self.cut_video,
        )

        # Button.7
        self.clear_cache_button = self.create_QPushButton(
            "Clear Cache",
            70 + 6 * self.button_w,
            self.video_h + 30,
            self.button_w,
            self.button_h,
            self.clear_cache,
        )

        # ============== Select Mode ===============
        mode_layout = QHBoxLayout()
        buttongroup = QButtonGroup(self)
        self.mode0 = QRadioButton("Loop", self)
        self.mode1 = QRadioButton("All", self)
        self.mode2 = QRadioButton("Preview", self)
        self.mode0.setGeometry(self.video_w + 20, 10, self.mode_w, self.mode_h)
        self.mode1.setGeometry(
            self.video_w + 30 + self.mode_w, 10, self.mode_w, self.mode_h
        )
        self.mode2.setGeometry(
            self.video_w + 40 + 2 * self.mode_w, 10, self.mode_w, self.mode_h
        )
        mode_layout.addWidget(self.mode0)
        mode_layout.addWidget(self.mode1)
        buttongroup.addButton(self.mode0)
        buttongroup.addButton(self.mode1)
        buttongroup.addButton(self.mode2)

        # ============== Display Cut Range ==============
        # self.scroll_area.setWidgetResizable(True)
        # Recreate a widget to hold the line edits
        # 结构：
        #   QVBoxLayout
        #       ↓
        #   QScollArea
        #       ↓
        #   QWidget
        #       ↓
        #   QGridLayout
        self.scroll_grid_layout = QGridLayout()
        self.scroll_grid_layout.setVerticalSpacing(1)
        self.scroll_grid_widget = QWidget()
        self.scroll_grid_widget.setLayout(self.scroll_grid_layout)
        self.adjust_scroll_layout_height(self.window_h - self.mode_h - 50)

        # Set the size and position of the scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.scroll_grid_widget)
        self.scroll_area.setGeometry(
            self.video_w + 30,
            20 + self.mode_h + 10,
            self.scroll_area_w - 20,
            self.window_h - self.mode_h - 30 - 20,
        )
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.addWidget(self.scroll_area)
        self.scroll_layout.setGeometry(
            QRect(
                self.video_w + 20,
                20 + self.mode_h,
                self.scroll_area_w,
                self.window_h - self.mode_h - 30,
            )
        )
        self.scroll_widget = QWidget(self)  # 添加self能看见框
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_widget.setGeometry(
            self.video_w + 20,
            20 + self.mode_h,
            self.scroll_area_w,
            self.window_h - self.mode_h - 30,
        )

    def adjust_scroll_layout_height(self, h):
        x = self.video_w + 30
        y = 20 + self.mode_h + 10
        w = self.scroll_area_w - 40
        self.scroll_grid_layout.setGeometry(QRect(x, y, w, h))
        self.scroll_grid_widget.setGeometry(x, y, w, h)

    def clear_scroll_layout(self):
        # 清空布局中的所有元素
        while self.scroll_grid_layout.count():
            item = self.scroll_grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def remove_scroll_layout_row(self, row):
        # 从布局中移除指定行的所有控件
        for column in range(self.scroll_grid_layout.columnCount()):
            item = self.scroll_grid_layout.itemAtPosition(row, column)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # 从布局中移除指定行
        for column in range(self.scroll_grid_layout.columnCount()):
            self.scroll_grid_layout.removeItem(
                self.scroll_grid_layout.itemAtPosition(row, column)
            )

    def create_radio_button(self, text, buttongroup, typestr=None):
        radiobutton = QRadioButton(text)
        buttongroup.addButton(radiobutton)
        if typestr == "Speech" and text == "Trans":
            radiobutton.setEnabled(False)
        elif typestr == "Trans" and text == "Speech":
            radiobutton.setEnabled(False)
        elif text != "Noise":
            radiobutton.setChecked(True)
        return radiobutton

    def create_line_edit(self, text, width):
        line_edit = QLineEdit(text)
        line_edit.setFixedWidth(width)
        return line_edit

    def create_button(self, text, width, height, clicked_func):
        button = QPushButton(text, self)
        button.setFixedSize(width, height)
        button.clicked.connect(clicked_func)
        return button

    def create_QPushButton(self, text, x, y, w, h, connected_function):
        button = QPushButton(text, self)
        button.setGeometry(x, y, w, h)
        button.clicked.connect(connected_function)
        return button

    def _play_pause_video(self, event):
        """Control playing or pausing video by click"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText("PLAY")
        else:
            self.media_player.play()
            self.play_button.setText("PAUSE")

    """
    ====================== Connect to the Button 1 ======================
    """

    def open_video_file(self):
        """打开视频文件"""
        # 播放进度重置
        self.media_player.setPosition(int(0))
        self.tL = 0
        self.tR = 0
        self.idx_play_now = 0
        # self._play_pause_video(None)

        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Video files (*.mp4)")
        if file_dialog.exec():
            # Select '.mkv' or 'mp4' video
            filepath = file_dialog.selectedFiles()[0]
            # Load
            self.abs_video_path = filepath
            self.root = os.path.split(filepath)[0]
            abs_path_without_ext = os.path.splitext(filepath)[0]
            self.speech_range_path = abs_path_without_ext + "_SpeechRange.csv"
            self.cut_range_path = abs_path_without_ext + "_CutRange.csv"
            self.duration = self.tR = get_duration(filepath, SETTINGS)
            self.fps = get_fps(filepath)
            video_url = QUrl.fromLocalFile(os.path.abspath(filepath))
            media_content = QMediaContent(video_url)
            # 打开视频
            self.media_player.setMedia(media_content)
            self.media_player.positionChanged.connect(
                self._update_progress_bar
            )
            self.media_player.pause()
            self.mode_timer.start(10)

    def _update_progress_bar(self):
        if self.duration > 0:
            progress = int(round(self.media_player.position() / self.duration))
            self.slider.setValue(progress)

    """
    =============== Connect to the Button 2 ===============
    """

    def analyze_speech(self):
        """Analyze video speech.

        It will try to analyze microphone track in `settings.toml`.

        If not exist, it will try to analyze the first track.
        """
        self.mode = "sub"
        self.mode0.setChecked(True)
        self.mode1.setCheckable(False)
        self.mode2.setCheckable(False)
        # 如果连视频都没有选择，就弹窗报错
        if not self.root:
            QMessageBox.information(
                self,
                "Error",
                "\nNo video file has selected!"
            )
            return
        if not os.path.exists(self.speech_range_path):
            logging.info(f"未检测到语音分析结果：{self.speech_range_path}")
            logging.info("即将导出麦克风音轨...")
            get_audio_track(self.abs_video_path, SPEECH_CHANNEL)
            micro_audio_path = change_file_extension(
                self.abs_video_path, "wav"
            )

            if os.path.exists(micro_audio_path):
                logging.info("即将启用whisper分析语音...")
                proj = SpeechVolume(micro_audio_path, SETTINGS)
                proj.get_time_segments_of_speech()  # 基于音量计算的语音范围
            else:
                logging.info("麦克风音轨导出失败")
                logging.info("即将采用VAD进行语音识别第1音轨")
                get_audio_track(self.abs_video_path, 0)
                if not os.path.exists(micro_audio_path):
                    logging.error("视频没有发现第1音轨")
                    return
                logging.info("即将启用whisper分析语音...")
                proj = SpeechVAD(micro_audio_path)
                proj.get_time_segments_of_speech()

            res = proj.transcribe()  # 转义
            save_dataframe(
                self.speech_range_path,
                res,
                SETTINGS["whisper"]["sample_rate"],
                SETTINGS["whisper"]["lang"],
            )
        df = pd.read_csv(self.speech_range_path)
        # 检查两个片段是否边界相同，否则微调
        for i in range(len(df)-1):
            if df.at[i, "end"] == df.at[i+1, "start"]:
                df.at[i, "end"] = df.at[i+1, "start"] - 0.001
        df = df[df["use"] == True]
        df.reset_index(drop=True)
        self.max_idx = len(df)
        self.clear_scroll_layout()
        self.adjust_scroll_layout_height(25 * self.max_idx)
        # 通过窗口来进行编辑
        self._plot_markdown(df)

    def _plot_markdown(self, df):
        for i, (_, row_content) in enumerate(df.iterrows()):
            self._add_one_markdown(
                i + 1,
                row_content["start"],
                row_content["end"],
                row_content["text"],
                row_content["use"]
            )

    def _add_one_markdown(self, i, start, end, text, checked=True):
        text = " " if pd.isna(text) else text
        # 单选框
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        # 起始时间及其调整
        text_edit1 = QLineEdit()
        text_edit1.setFixedWidth(80)
        text_edit1.setAlignment(Qt.AlignRight)
        text_edit1.setInputMask("99:99:99:99")
        text_edit1.setText(str(round(start, 3)))
        text_edit1.cursorPositionChanged.connect(self._tL_select)
        text_edit2 = QLineEdit()
        text_edit2.setFixedWidth(80)
        text_edit2.setAlignment(Qt.AlignRight)
        text_edit2.setInputMask("0000.000")
        text_edit2.setText(str(round(end, 3)))
        text_edit2.cursorPositionChanged.connect(self._tR_select)
        text_edit3 = SubLineEdit(
            self.on_backspace_at_start,
            self.on_enter_in_middle,
            self.on_delete_at_end,
        )
        text_edit3.setText(text)
        # 添加到layout
        self.scroll_grid_layout.addWidget(checkbox, i, 1)
        self.scroll_grid_layout.addWidget(text_edit1, i, 2)
        self.scroll_grid_layout.addWidget(text_edit2, i, 3)
        self.scroll_grid_layout.addWidget(text_edit3, i, 4)

    def on_backspace_at_start(self, sender_widget):
        tR = self.tR
        for i in range(self.max_idx):
            if sender_widget == self.get_data_widget(i + 1, 4):
                if i == 0:
                    break
                tL = float(self.get_data_widget(i, 2).text())
                self.get_data_widget(i, 3).setText(
                    self.get_data_widget(i + 1, 3).text()
                )
                text1 = self.get_data_widget(i, 4).text()
                text2 = self.get_data_widget(i + 1, 4).text()
                self.get_data_widget(i, 4).setText(text1 + text2)
                for j in range(i + 1, self.max_idx):
                    self.get_data_widget(j, 1).setChecked(
                        self.get_data_widget(j + 1, 1).isChecked()
                    )
                    self.get_data_widget(j, 2).setText(
                        self.get_data_widget(j + 1, 2).text()
                    )
                    self.get_data_widget(j, 3).setText(
                        self.get_data_widget(j + 1, 3).text()
                    )
                    self.get_data_widget(j, 4).setText(
                        self.get_data_widget(j + 1, 4).text()
                    )
                self.remove_scroll_layout_row(self.max_idx)
                self.update_max_idx(-1)
                break
        self.tL, self.tR = tL, tR
        self.media_player.setPosition(int(round(tL * 1000)))
        self.media_player.play()

    def on_enter_in_middle(self, sender_widget):
        tR = self.tR
        cursor_position = sender_widget.cursorPosition()
        text = sender_widget.text()
        text1 = text[:cursor_position]
        text2 = text[cursor_position:]
        for i in range(self.max_idx):
            if sender_widget == self.get_data_widget(i + 1, 4):
                self.update_max_idx(1)  # QGridLayout布局增加一行
                # 最后一行添加控件
                j = self.max_idx
                self._add_one_markdown(
                    j,
                    float(self.get_data_widget(j - 1, 2).text()),
                    float(self.get_data_widget(j - 1, 3).text()),
                    self.get_data_widget(j - 1, 4).text(),
                    checked=self.get_data_widget(j - 1, 1).isChecked(),
                )
                # 后移
                for j in range(self.max_idx - 1, i + 2, -1):
                    self.get_data_widget(j, 1).setChecked(
                        self.get_data_widget(j - 1, 1).isChecked()
                    )
                    self.get_data_widget(j, 2).setText(
                        self.get_data_widget(j - 1, 2).text()
                    )
                    self.get_data_widget(j, 3).setText(
                        self.get_data_widget(j - 1, 3).text()
                    )
                    self.get_data_widget(j, 4).setText(
                        self.get_data_widget(j - 1, 4).text()
                    )
                # 临界时间
                cri_time = round(
                    0.5
                    * (
                        float(self.get_data_widget(i + 1, 2).text())
                        + float(self.get_data_widget(i + 1, 3).text())
                    ),
                    3,
                )
                tL = cri_time
                # i + 2行
                self.get_data_widget(i + 2, 1).setChecked(
                    self.get_data_widget(i + 1, 1).isChecked()
                )
                self.get_data_widget(i + 2, 2).setText(str(cri_time + 0.001))
                self.get_data_widget(i + 2, 3).setText(
                    self.get_data_widget(i + 1, 3).text()
                )
                self.get_data_widget(i + 2, 4).setText(text2)
                # i + 1行
                self.get_data_widget(i + 1, 3).setText(str(cri_time))
                self.get_data_widget(i + 1, 4).setText(text1)
                self.media_player.setPosition(int(round(cri_time * 1000)))
                break
        self.tL, self.tR = tL, tR
        self.media_player.setPosition(int(round(tL * 1000)))
        self.media_player.play()

    def on_delete_at_end(self, sender_widget):
        tL = self.tL
        for i in range(self.max_idx):
            if sender_widget == self.get_data_widget(i + 1, 4):
                if i == self.max_idx - 1:
                    break
                self.get_data_widget(i + 1, 3).setText(
                    self.get_data_widget(i + 2, 3).text()
                )
                tR = float(self.get_data_widget(i + 2, 3).text())
                self.get_data_widget(i + 1, 4).setText(
                    self.get_data_widget(i + 1, 4).text()
                    + self.get_data_widget(i + 2, 4).text()
                )
                for j in range(i + 2, self.max_idx):
                    self.get_data_widget(j, 1).setChecked(
                        self.get_data_widget(j + 1, 1).isChecked()
                    )
                    self.get_data_widget(j, 2).setText(
                        self.get_data_widget(j + 1, 2).text()
                    )
                    self.get_data_widget(j, 3).setText(
                        self.get_data_widget(j + 1, 3).text()
                    )
                    self.get_data_widget(j, 4).setText(
                        self.get_data_widget(j + 1, 4).text()
                    )
                self.remove_scroll_layout_row(self.max_idx)
                self.update_max_idx(-1)
                break
        self.tL, self.tR = tL, tR
        self.media_player.setPosition(int(round(tL * 1000)))
        self.media_player.play()

    """
    =============== Connect to the Button 3 ==============
    """

    def load_cut_range(self):
        self.mode = "vid"
        self.mode0.setChecked(True)
        self.mode1.setCheckable(True)
        self.mode2.setCheckable(True)
        if self.root is None:
            QMessageBox.information(self, "Error", "\nNo video file has selected!")
            return
        # 如果有剪辑时间范围
        if os.path.exists(self.cut_range_path):
            df = pd.read_csv(self.cut_range_path)
        # 没有剪辑时间范围，但是有语音范围
        elif os.path.exists(self.speech_range_path):
            df = pd.read_csv(self.speech_range_path)
            df = df[df["use"]==True]
            df.reset_index(drop=True)
            df = df.loc[:, ["start", "end"]]
            t_ranges = [(row["start"], row["end"]) for _, row in df.iterrows()]
            t_ranges = expand_time_segments(
                t_ranges, PRE_T, AFT_T, 0, self.duration
            )
            t_ranges = combine_time_segments(t_ranges, BET_T - PRE_T - AFT_T)
            df = pd.DataFrame(t_ranges, columns=["start", "end"])
            df.to_csv(self.cut_range_path, index=False)
        else:
            QMessageBox.information(self, "Warning", "\nPlease analyse first.")
            return
        self.max_idx = 2 * len(df) + 1
        self.clear_scroll_layout()
        self.adjust_scroll_layout_height(25 * self.max_idx)
        dur = sum([df.at[i, "end"]-df.at[i, "start"] for i in range(len(df))])
        logging.info(f"视频长度变化: {self.duration:.2f}s => {dur:.2f}s")
        logging.info(f"压缩率：{(1-dur/self.duration)*100.0:.2f}%")
        # 更新控件
        self._plot_cut_range(df)

    def _plot_cut_range(self, df):
        for i in range(self.max_idx):
            if i % 2 == 1:
                start = df.at[(i - 1) // 2, "start"]
                end = df.at[(i - 1) // 2, "end"]
                self._refresh_data_widgets(i, start, end, "Speech")
            else:
                button = QPushButton("-" * int(floor(self.scroll_area_w)))
                button.setFixedHeight(10)
                button.setFixedWidth(int(floor(self.scroll_area_w - 40)))
                button.clicked.connect(self._click_hline)
                self.scroll_grid_layout.addWidget(button, i + 1, 1)

    def _refresh_data_widgets(self, i, start, end, typestr):
        buttongroup = QButtonGroup(self)
        radiobutton0 = self.create_radio_button("Trans", buttongroup, typestr)
        radiobutton1 = self.create_radio_button("Speech", buttongroup, typestr)
        radiobutton2 = self.create_radio_button("Noise", buttongroup)

        line_edit0 = self.create_line_edit(str(start), 80)
        line_edit1 = self.create_line_edit(str(end), 80)

        tL_dcs_btn = self.create_button(
            "-1", 25, 25, self._decrease_text_and_play_tL_by_key
        )
        tL_ics_btn = self.create_button(
            "+1", 25, 25, self._increase_text_and_play_tL_by_key
        )
        tR_dcs_btn = self.create_button(
            "-1", 25, 25, self._decrease_text_and_play_tR_by_key
        )
        tR_ics_btn = self.create_button(
            "+1", 25, 25, self._increase_text_and_play_tR_by_key
        )

        line_edit0.cursorPositionChanged.connect(self._tL_select)
        line_edit1.cursorPositionChanged.connect(self._tR_select)

        self.scroll_grid_layout.addWidget(radiobutton0, i + 1, 1)
        self.scroll_grid_layout.addWidget(radiobutton1, i + 1, 2)
        self.scroll_grid_layout.addWidget(radiobutton2, i + 1, 3)
        self.scroll_grid_layout.addWidget(tL_dcs_btn, i + 1, 4)
        self.scroll_grid_layout.addWidget(line_edit0, i + 1, 5)
        self.scroll_grid_layout.addWidget(tL_ics_btn, i + 1, 6)
        self.scroll_grid_layout.addWidget(tR_dcs_btn, i + 1, 7)
        self.scroll_grid_layout.addWidget(line_edit1, i + 1, 8)
        self.scroll_grid_layout.addWidget(tR_ics_btn, i + 1, 9)

    def _click_hline(self):
        for i in range(0, self.max_idx, 2):
            if (
                self.sender()
                == self.scroll_grid_layout.itemAtPosition(i + 1, 1).widget()
            ):
                tL, tR = self.tL, self.tR
                pre_end = 0 if i == 0 else float(self.get_data_widget(i, 8).text())
                nex_sta = (
                    self.duration
                    if i == self.max_idx - 1
                    else float(self.get_data_widget(i + 2, 5).text())
                )

                self.move_widgets_down(i)
                self._refresh_data_widgets(i + 1, pre_end, nex_sta, "Trans")
                self.add_horizontal_line_button(i + 3)
                self.update_max_idx(2)
                self.update_position_and_marked_LineEdit(i + 2, pre_end, nex_sta)
                self.tL, self.tR = tL, tR
                self.media_player.setPosition(int(round(tL * 1000)))
                break

    def move_widgets_down(self, index):
        for j in range(self.max_idx + 2, index + 3, -1):
            if j % 2 == 1:
                self.scroll_grid_layout.addWidget(self.get_data_widget(j - 2, 1), j, 1)
            else:
                for k in range(1, 10):
                    self.scroll_grid_layout.addWidget(
                        self.get_data_widget(j - 2, k), j, k
                    )

    def add_horizontal_line_button(self, index):
        button = QPushButton("-" * int(floor(self.scroll_area_w)))
        button.setFixedHeight(10)
        button.setFixedWidth(int(floor(self.scroll_area_w - 40)))
        button.clicked.connect(self._click_hline)
        self.scroll_grid_layout.addWidget(button, index, 1)

    def update_max_idx(self, n):
        self.max_idx += n
        self.adjust_scroll_layout_height(25 * self.max_idx)

    def update_position_and_marked_LineEdit(self, index, pre_end, nex_sta):
        self.tL = pre_end
        self.tR = nex_sta
        self.media_player.setPosition(int(round(pre_end * 1000, 2)))
        self._change_marked_LineEdit(index, 5)

    def _increase_text_and_play_tL_by_key(self):
        for i in range(2, self.max_idx, 2):
            tmp_widget = self.get_data_widget(i, 6)
            if self.sender() == tmp_widget:
                self._update_tL(i, 1)
                break

    def _decrease_text_and_play_tL_by_key(self):
        for i in range(2, self.max_idx, 2):
            if self.sender() == self.get_data_widget(i, 4):
                self._update_tL(i, -1)
                break

    def _increase_text_and_play_tR_by_key(self):
        for i in range(2, self.max_idx, 2):
            if self.sender() == self.get_data_widget(i, 9):
                self._update_tR(i, 1)
                break

    def _decrease_text_and_play_tR_by_key(self):
        for i in range(2, self.max_idx, 2):
            if self.sender() == self.get_data_widget(i, 7):
                self._update_tR(i, -1)
                break

    def _update_tL(self, i, increment):
        self.mode0.setChecked(True)
        tL = round(float(self.get_data_widget(i, 5).text()) + increment, 2)
        tR = round(float(self.get_data_widget(i, 8).text()), 2)
        if tL > tR - 0.01:
            print("数值太大")
        elif i > 2 and tL < round(float(self.get_data_widget(i - 2, 8).text()) + 0.01, 2):
            print("数值太小")
        else:
            self.get_data_widget(i, 5).setText(str(tL))
            self.tL = tL
            self.tR = tR
            self.media_player.setPosition(int(round(self.tL * 1000, 2)))
            self._change_marked_LineEdit(i, 5)
            if self.media_player.state() != QMediaPlayer.PlayingState:
                print("检测到暂停，马上播放")
                self.media_player.play()
                self.play_button.setText("STOP")

    def _update_tR(self, i, increment):
        self.mode0.setChecked(True)
        tL = round(float(self.get_data_widget(i, 5).text()), 2)
        tR = round(float(self.get_data_widget(i, 8).text()), 2) + increment
        if tR < tL + 0.01:
            print("数值太小")
        elif i < self.max_idx-1 and (tR > round(float(self.get_data_widget(i + 2, 5).text()), 2) - 0.01):
            print("数值太大")
        else:
            tR = min(self.duration, tR)
            self.get_data_widget(i, 8).setText(str(tR))
            self.tL = tL
            self.tR = tR
            self.media_player.setPosition(
                int(round(max(self.tR - 3, self.tL) * 1000, 2))
            )
            self._change_marked_LineEdit(i, 8)
            if self.media_player.state() != QMediaPlayer.PlayingState:
                self.media_player.play()
                self.play_button.setText("STOP")

    def _tL_select(self):
        if self.mode == "sub":
            for i in range(self.max_idx):
                tmp_widget = self.scroll_grid_layout.itemAtPosition(i + 1, 2).widget()
                if self.sender() == tmp_widget:
                    start = float(tmp_widget.text().replace(" ", ""))
                    end = float(
                        self.scroll_grid_layout.itemAtPosition(i + 1, 3).widget().text()
                    )
                    self.tL = start
                    self.tR = end
                    self.media_player.setPosition(int(round(start * 1000)))
                    self.media_player.play()
                    logging.info("更改播放范围："+str(start)+" - "+str(end))
        elif self.mode == "vid":
            for i in range(2, self.max_idx, 2):
                if self.sender() == self.get_data_widget(i, 5):
                    self.idx_play_now = i
                    self.media_player.pause()
                    # Change play position and play range
                    self.tL = round(float(self.get_data_widget(i, 5).text()), 2)
                    self.tR = round(float(self.get_data_widget(i, 8).text()), 2)
                    self.media_player.setPosition(int(round(self.tL * 1000)))
                    self.media_player.play()
                    self.play_button.setText("STOP")
                    # Change color
                    self._change_marked_LineEdit(i, 5)
                    # Change Play mode
                    if self.mode0.isChecked():
                        self.mode2.setChecked(True)
                    break

    def _tR_select(self):
        if self.mode == "sub":
            for i in range(self.max_idx):
                tmp_widget = self.scroll_grid_layout.itemAtPosition(i + 1, 3).widget()
                if self.sender() == tmp_widget:
                    start = float(
                        self.scroll_grid_layout.itemAtPosition(i + 1, 2).widget().text()
                    )
                    end = float(tmp_widget.text().replace(" ", ""))
                    self.tL = start
                    self.tR = end
                    self.media_player.setPosition(int(round(start * 1000)))
                    self.media_player.play()
        elif self.mode == "vid":
            for i in range(2, self.max_idx, 2):
                if self.sender() == self.get_data_widget(i, 8):
                    self.idx_play_now = i
                    self.media_player.pause()
                    # Change Play position and play range
                    self.tL = round(float(self.get_data_widget(i, 5).text()), 2)
                    self.tR = round(float(self.get_data_widget(i, 8).text()), 2)
                    self.media_player.setPosition(
                        int(round(max(self.tR - 3, self.tL) * 1000, 2))
                    )
                    # Change color
                    self._change_marked_LineEdit(i, 8)
                    self.media_player.play()
                    self.play_button.setText("STOP")
                    # Change Play mode
                    if self.mode0.isChecked():
                        self.mode2.setChecked(True)
                    break

    """
    ================== Connect to the Button 4. ===================
    """

    def play_video(self):
        if self.root == "":
            QMessageBox.information(
                self,
                "Error",
                "???\nNo video file has selected!"
            )
            return None
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText("PLAY")
        else:
            self.media_player.play()
            self.play_button.setText("PAUSE")
        self.video_widget.repaint()

    """
    Connect to the Timer.
    """

    def video_loop_mode(self):
        position = self.media_player.position()
        cond1 = position > self.tR * 1000 + 1
        cond2 = position < self.tL * 1000 - 1

        if self.mode0.isChecked() and (cond1 or cond2):
            self._pause_and_set_position(int(round(self.tL * 1000)))
        elif self.mode1.isChecked():
            self.tL = 0
            self.tR = round(self.duration, 2)
        elif self.mode2.isChecked() and cond1:
            if self._should_pause_and_set_position():
                self._pause_and_set_position_of_next_widget()
        elif self.mode2.isChecked() and cond2:
            self.media_player.setPosition(int(round(self.tL * 1000)))

    def _pause_and_set_position(self, position):
        self.media_player.pause()
        self.play_button.setText("PLAY")
        self.media_player.setPosition(position)

    def _should_pause_and_set_position(self):
        """判断是否播放超过了设定范围"""
        if self.idx_play_now == self.max_idx-1:
            self.media_player.pause()
            self.play_button.setText("PLAY")
            return False
        return True

    def _pause_and_set_position_of_next_widget(self):
        """播放下一个time segments"""
        for i in range(self.idx_play_now + 2, self.max_idx, 2):
            if self.get_data_widget(i, 3).isChecked():
                continue
            tmp_tL = round(float(self.get_data_widget(i, 5).text()), 2)
            tmp_tR = round(float(self.get_data_widget(i, 8).text()), 2)
            self._change_marked_LineEdit(i, 5)
            self._pause_and_set_position(int(round(tmp_tL * 1000)))
            self.tL = tmp_tL
            self.tR = tmp_tR
            self.idx_play_now = i
            print("更改播放范围为： ", self.tL, " ", self.tR)
            break

    """
    ======================== Connect to the Button 5 ============================
    """

    def save_data(self):
        if self.root is None:
            QMessageBox.information(
                self,
                "Error",
                "\nNo video file has selected!"
            )
            return
        print("模式：", self.mode)
        if self.mode == "sub":
            df = pd.DataFrame(columns=["start", "end", "text", "use"])
            for i in range(1, self.max_idx+1):
                start = float(self.get_data_widget(i, 2).text())
                end = float(self.get_data_widget(i, 3).text())
                sub_text = self.get_data_widget(i, 4).text()
                use = True if self.get_data_widget(i, 1).isChecked() else False
                df.loc[len(df)] = {
                    "start": start,
                    "end": end,
                    "text": sub_text,
                    "use": use
                }
            df.to_csv(self.speech_range_path, index=False)
            logging.info("保存语音数据成功！")
        elif self.mode == "vid":
            time_segments = []
            for i in range(2, self.max_idx, 2):
                if self.get_data_widget(i, 3).isChecked():  # 判断为Noise的直接跳过
                    continue
                time_segments.append(
                    (
                        float(self.get_data_widget(i, 5).text()),
                        float(self.get_data_widget(i, 8).text()),
                    )
                )
            time_segments = combine_time_segments(
                time_segments,
                max(1.01, BET_T - PRE_T - AFT_T)
            )
            df = pd.DataFrame(time_segments, columns=["start", "end"])
            dur = (df["end"] - df["start"]).sum()
            logging.info(f"视频长度变化: {self.duration:.2f}s => {dur:.2f}s")
            logging.info(f"压缩率：{(1-dur/self.duration)*100.0:.2f}%")
            df.to_csv(self.cut_range_path, index=False)
            logging.info("保存剪辑范围成功！")

    """
    ================== Connect to the Button 5. ===================
    """

    def cut_video(self):
        if not os.path.exists(self.cut_range_path):
            return None
        cut_game_record(self.root, THREADS)

    """
    ================== Connect to the Button 9. ===================
    """

    def clear_cache(self):
        if self.root is None:
            QMessageBox.information(
                self,
                "Error",
                "???\nNo video file has selected!"
            )
            return None
        _, file_list = get_all_files_with_extensions(
            self.root, [".csv", ".mkv", ".wav"]
        )
        for file in file_list:
            if file.endswith("CutRange.csv"):
                continue
            if os.path.exists(file):
                os.remove(file)

    def _change_marked_LineEdit(self, i, j):
        colored_row, colored_col = self.colored_widget
        if (colored_row) != i or (colored_col != j):
            self.get_data_widget(colored_row, colored_col).setStyleSheet(
                "QLineEdit { background-color: white; }"
            )
            self.get_data_widget(i, j).setStyleSheet(
                "QLineEdit { background-color: gray; }"
            )
            self.colored_widget = (i, j)

    def get_data_widget(self, i, j):
        try:
            return self.scroll_grid_layout.itemAtPosition(i, j).widget()
        except:
            raise (i, " ", j, " ", self.scroll_grid_layout.itemAtPosition(i, j))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CutRange()
    window.show()
    sys.exit(app.exec())
