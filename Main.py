import sys, os
from PyQt5.QtCore import QUrl, QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QApplication, QGridLayout, QMainWindow, \
    QFileDialog, QPushButton, QScrollArea, QLineEdit, QWidget, \
    QPushButton, QDoubleSpinBox, QProgressBar, QRadioButton, QButtonGroup, \
    QMessageBox, QHBoxLayout, QLabel, QSlider
from small_tools.pic_video_attribution import get_duration
import pandas as pd
import toml
from math import floor, ceil
from GamMicroTrack import Gam, cut_game_record
from GamMicroTrack import combine_ranges
from small_tools.filemani import get_all_suffixs_files
from small_tools.second_to_hms import seconds_to_hms
import subprocess, cProfile
import threading
from time import time

THREADS = 7
SETTINGS = toml.load("./settings.toml")

class QSSLoader:
    def __init__(self):
        pass

    @staticmethod
    def read_qss_file(qss_file_name):
        with open(qss_file_name, 'r',  encoding='UTF-8') as file:
            return file.read()


class CutRange(QMainWindow):
    def __init__(self):
        # ========== 参数 ============
        self.window_title = "Adjust Cut Range"
        self.video_w = 1200
        self.video_h = 675
        self.scroll_area_w = 560
        self.slider_h = 15
        self.button_w = int(floor(self.video_w-70)/8)
        self.button_h = 30
        self.window_w = self.video_w + self.scroll_area_w + 30
        self.window_h = self.video_h + self.button_h + 40
        self.mode_w = int(floor((self.scroll_area_w-40)/6))
        self.mode_h = 30
        # Something will used
        self.root = ""
        self.abs_video_path = ""
        self.output_cut_video = "output_cut.mp4"
        self.speech_range_path = ""
        self.cut_range_path = ""
        self.data_dict = dict()
        self.duration = 0           # Video Length
        self.widgets_number_per_page = 30
        self.widgets_range_per_page = None
        self.idx_range = range(0, self.widgets_number_per_page)
        self.idx_play_now = 0       # idx of video playing
        self.colored_widget = (0, 0)
        
        # ============== Main Window ==============
        super().__init__()
        self.setFixedSize(self.window_w, self.window_h)
        self.setWindowTitle(self.window_title)
        style_file = './QSS-master/Ubuntu.qss'
        style_sheet = QSSLoader.read_qss_file(style_file)
        self.setStyleSheet(style_sheet)
        
        # ============== Video Play ==============
        self.media_player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.video_widget.mousePressEvent = self._play_pause_video
        self.media_player.setVideoOutput(self.video_widget)
        self.video_widget.setGeometry(10, 10, self.video_w, self.video_h)
        # Timer For Video
        self.mode_timer = QTimer()
        self.mode_timer.timeout.connect(self.video_loop_mode)
        # Range For Video Playing
        self.tL = 0
        self.tR = 0
        # Video Progress Bar
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setGeometry(10, self.video_h+10, self.video_w, self.slider_h)
        self.slider.setRange(0, 1000)
        

        # ============== Button.1 To Open Window ==============
        self.open_folder_button = QPushButton("Open Video File", self)
        self.open_folder_button.setGeometry(10, self.video_h+30, self.button_w, self.button_h)
        self.open_folder_button.clicked.connect(self.open_video_file)

        # ============== Button.2 Analyze Recording Video ==============
        self.analyze_button = QPushButton("Analyze", self)
        self.analyze_button.setGeometry(20+self.button_w, self.video_h+30, self.button_w, self.button_h)
        self.analyze_button.clicked.connect(self.analyze_video)

        # ============== Button.3 Previous Range ==============
        self.prev_range_button = QPushButton("PREV", self)
        self.prev_range_button.setGeometry(30+2*self.button_w, self.video_h+30, self.button_w, self.button_h)
        self.prev_range_button.clicked.connect(self.previous_range)

        # ============== Button.4 PLAY/STOP video ==============
        self.play_button = QPushButton("STOP", self)
        self.play_button.setGeometry(40+3*self.button_w, self.video_h+30, self.button_w, self.button_h)
        self.play_button.clicked.connect(self.play_video)

        # ============== Button.5 Next Range ==============
        self.next_range_button = QPushButton("NEXT", self)
        self.next_range_button.setGeometry(50+4*self.button_w, self.video_h+30, self.button_w, self.button_h)
        self.next_range_button.clicked.connect(self.next_range)

        # ============== Button.6 Export Cut Range ==============
        self.save_button = QPushButton("Save New Range", self)
        self.save_button.setGeometry(60+5*self.button_w, self.video_h+30, self.button_w, self.button_h)
        self.save_button.clicked.connect(self.save_new_range)

        # ============== Button.7 Cut Without Silence ==============
        self.cut_button1 = QPushButton("Cut", self)
        self.cut_button1.setGeometry(70+6*self.button_w, self.video_h+30, self.button_w, self.button_h)
        self.cut_button1.clicked.connect(self.cut_game_video)
        
        # ============== Button.8 Clear Cache ==============
        self.cut_button2 = QPushButton("Clear Cache", self)
        self.cut_button2.setGeometry(80+7*self.button_w, self.video_h+30, self.button_w, self.button_h)
        self.cut_button2.clicked.connect(self.clear_cache)

        # ============== Select Mode ===============
        mode_layout = QHBoxLayout()
        buttongroup = QButtonGroup(self)
        self.mode0 = QRadioButton(f"Loop", self)
        self.mode0.setChecked(True)
        self.mode1 = QRadioButton(f"All", self)
        self.mode2 = QRadioButton(f"Preview", self)
        self.mode0.setGeometry(self.video_w+20, 10, self.mode_w, self.mode_h)
        self.mode1.setGeometry(self.video_w+30+self.mode_w,   10, self.mode_w, self.mode_h)
        self.mode2.setGeometry(self.video_w+40+2*self.mode_w, 10, self.mode_w, self.mode_h)
        mode_layout.addWidget(self.mode0)
        mode_layout.addWidget(self.mode1)
        buttongroup.addButton(self.mode0)
        buttongroup.addButton(self.mode1)
        buttongroup.addButton(self.mode2)

        # ============= Previous Ranges and Next Ranges ==========
        self.text_page = QLineEdit("1", self)
        self.text_page.setGeometry(self.video_w+50+3*self.mode_w, 10, int(floor(self.mode_w/2)), self.mode_h)
        self.text_page.setAlignment(Qt.AlignRight)
        self.text_page.textChanged.connect(self._plot_cut_range)
        self.label_page = QLabel("", self)
        self.label_page.setGeometry(self.video_w+50+3*self.mode_w+int(floor(self.mode_w/2)), 10, int(ceil(self.mode_w/2)), self.mode_h)
        self.btn_pre_page = QPushButton("Prev", self)
        self.btn_pre_page.setGeometry(self.video_w+60+4*self.mode_w, 10, self.mode_w, self.mode_h)
        self.btn_pre_page.clicked.connect(self._pre_page)
        self.btn_nex_page = QPushButton("Next", self)
        self.btn_nex_page.setGeometry(self.video_w+70+5*self.mode_w, 10, self.mode_w, self.mode_h)
        self.btn_nex_page.clicked.connect(self._nex_page)

        # ============== Display Cut Range ==============
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setGeometry(self.video_w+20, 20+self.mode_h, self.scroll_area_w, self.window_h - self.mode_h - 30)
        self.scroll_area.setWidgetResizable(True)
        # Recreate a widget to hold the line edits
        self.scroll_widget = QWidget()
        # self.scroll_widget.setGeometry(self.video_w+20, 20+self.mode_h, self.scroll_area_w-20, self.video_h+self.button_h - self.mode_h-20)
        self.scroll_layout = QGridLayout(self.scroll_widget)
        self.scroll_layout.setVerticalSpacing(1)
        # Refresh page numbers
        self._refresh_data_numbers_per_page()
        # 绘制控件
        self._plot_cut_range()

    def _play_pause_video(self, event):
        """Control playing or pausing video by click
        """
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText('PLAY')
        else:
            self.media_player.play()
            self.play_button.setText('PAUSE')


    """
    ============= Connect to the Button 1 ===================
    
    """
    def open_video_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Video files (*.mp4)")
        if file_dialog.exec():
            # Select '.mkv' or 'mp4' video
            filepath = file_dialog.selectedFiles()[0]
            # Load
            self.abs_video_path = filepath
            self.root, filename = os.path.split(filepath)
            videoname = filename.split(".")[0]
            self.speech_range_path = os.path.join(self.root, videoname+"_SpeechRange.csv")
            self.cut_range_path    = os.path.join(self.root, videoname+"_CutRange.csv")
            self.duration = self.tR = get_duration(filepath, SETTINGS)
            video_url = QUrl.fromLocalFile(os.path.abspath(filepath))
            media_content = QMediaContent(video_url)
            self.media_player.setMedia(media_content)
            self.media_player.positionChanged.connect(self._update_progress_bar)
            self.media_player.play()
            self.mode_timer.start(10)

    def _update_progress_bar(self):
        if self.duration > 0:
            progress = int(round(self.media_player.position() / self.duration))
            self.slider.setValue(progress)

    """
    =============== Connect to the Button 2 ===============
    """
    def analyze_video(self):
        if self.root == "":
            QMessageBox.information(self, "Error", "???\nNo video file has selected!")
            return None
        if not (os.path.exists(self.speech_range_path) or os.path.exists(self.cut_range_path)):
            game = Gam(self.speech_range_path, THREADS, SETTINGS)
            game.get_time_set_to_cut(self.abs_video_path)
        self._load_speech_range_from_file()

    """
    After video analysis is completed.
    """
    def _load_speech_range_from_file(self):
        # If there exists `CutRange.csv`,
        # it may be your last editing record,
        # which should be load at first
        if os.path.exists(self.cut_range_path):
            df = pd.read_csv(self.cut_range_path,    names=["Start Time", "End Time"])
        elif os.path.exists(self.speech_range_path):
            df = pd.read_csv(self.speech_range_path, names=["Start Time", "End Time"])
        else:
            print("Plese analyze video first!"); return None
        # load to self.data_dict
        self.data_dict = dict()
        for i in range(2*len(df)+1):
            if i%2 == 0:
                self.data_dict[i] = self._get_hline_widgets()
            else:
                self.data_dict[i] = self._get_data_widgets(round(df.iloc[(i-1)//2, 0],2), round(df.iloc[(i-1)//2, 1],2), "Chat")
        # Refresh page numbers
        self._refresh_data_numbers_per_page()
        # 更新控件
        self._plot_cut_range()

    def _plot_cut_range(self):
        # Delete all widgets in scroll area.
        try:
            for i in reversed(range(self.scroll_layout.count())):
                self.scroll_layout.itemAt(i).widget().setParent(None)
        except:
            pass
        # Get plot range
        idx1, idx2 = self.widgets_range_per_page[int(self.text_page.text())-1]
        self.idx_range = range(idx1, idx2)
        for row, idx in enumerate(self.idx_range):
            if len(self.data_dict[idx]) == 1:
                # Plot hline widgets
                self.scroll_layout.addWidget(self.data_dict[idx][0], row, 0, 1, 9)
            else:
                # Plot datas
                for j in range(9):
                    # print("Index: %s, scroll layout row: %s, col: %s"%(idx, row, 0))
                    self.scroll_layout.addWidget(self.data_dict[idx][j], row, j)
        # Set the widget for the scroll area
        self.scroll_area.setWidget(self.scroll_widget)

    def _refresh_data_numbers_per_page(self):
        """Refresh data according page num in `self.text_page.text()`
        """
        widgets_num_list = [self.widgets_number_per_page] * (len(self.data_dict)//self.widgets_number_per_page)
        widgets_num_list.append(len(self.data_dict)%self.widgets_number_per_page)
        widget_index_range_list = []
        for pagenum, widget_count in enumerate(widgets_num_list):
            idx_L = pagenum * self.widgets_number_per_page
            widget_index_range_list.append((idx_L, idx_L + widget_count))
        self.label_page.setText("/%s"%len(widget_index_range_list))
        self.widgets_range_per_page=widget_index_range_list

    # ============================================================
    # Get hline widget and connect to `add new row` function
    # ============================================================
    def _get_hline_widgets(self):
        button = QPushButton("-"*int(floor(self.scroll_area_w/7)), self)
        button.setFixedHeight(10)
        button.clicked.connect(self._add_new_row)
        return [button]

    def _add_new_row(self):
        for i in self.idx_range:
            if len(self.data_dict[i]) != 1: continue
            if self.sender() == self.data_dict[i][0]:
                # Change color
                colored_row, colored_col = self.colored_widget
                self.data_dict[colored_row][colored_col].setStyleSheet("QLineEdit { background-color: white; }")
                for j in range(len(self.data_dict)+1, i+1, -1):
                    self.data_dict[j] = self.data_dict[j-2]
                # New line: 1
                if i==0:
                    tL = 0
                else:
                    tL = round(float(self.data_dict[i-1][7].text())+0.01, 2)
                tR = round(float(self.data_dict[i+3][4].text())-0.01, 2)
                self.data_dict[i+1] = self._get_data_widgets(tL, tR, "Trans")
                # New Line: 2
                self.data_dict[i] = self._get_hline_widgets()
                # Refresh page numbers
                self._refresh_data_numbers_per_page()
                # Plot widgets
                self._plot_cut_range()
                # Change video player
                self.tL = tL
                self.tR = tR
                self.media_player.setPosition(int(round(self.tL*1000,2)))
                # Change color
                self.data_dict[i+1][4].setStyleSheet("QLineEdit { background-color: gray; }")
                self.colored_widget = (i+1, 4)
                break

    # ============================================================
    # Get data widgets, and connect to following 6 functions
    # ============================================================
    def _get_data_widgets(self, tL, tR, typestr):
        buttongroup = QButtonGroup(self)
        # radiobutton0: 通过前面`_add_new_row`新加入的过渡段
        # radiobutton1: 有语音的时间段
        # radiobutton2: 要舍弃的垃圾片段
        radiobutton0 = QRadioButton(f"Trans", self.scroll_widget); buttongroup.addButton(radiobutton0)
        radiobutton1 = QRadioButton(f"Chat", self.scroll_widget); buttongroup.addButton(radiobutton1)
        # 判断为"Trans"或者"Chat"，你不能选择"Chat"或者"Trans"
        if typestr == "Chat":
            radiobutton0.setEnabled(False)
            radiobutton1.setChecked(True)
        else:
            radiobutton0.setChecked(True)
            radiobutton1.setEnabled(False)
        radiobutton2 = QRadioButton(f"Noise", self.scroll_widget); buttongroup.addButton(radiobutton2)
        line_edit0 = QLineEdit(str(tL), self.scroll_widget)
        line_edit1 = QLineEdit(str(tR), self.scroll_widget)
        line_edit0.setFixedWidth(80)
        line_edit1.setFixedWidth(80)
        # 时间范围上/下限的减小/增加键
        tL_dcs_btn = QPushButton("-1", self)
        tL_dcs_btn.setFixedSize(25, 25)
        tL_dcs_btn.clicked.connect(self._decrease_text_and_play_tL_by_key)
        tL_ics_btn = QPushButton("+1", self)
        tL_ics_btn.setFixedSize(25, 25)
        tL_ics_btn.clicked.connect(self._increase_text_and_play_tL_by_key)
        tR_dcs_btn = QPushButton("-1", self)
        tR_dcs_btn.setFixedSize(25, 25)
        tR_dcs_btn.clicked.connect(self._decrease_text_and_play_tR_by_key)
        tR_ics_btn = QPushButton("+1", self)
        tR_ics_btn.setFixedSize(25, 25)
        tR_ics_btn.clicked.connect(self._increase_text_and_play_tR_by_key)
        # 事件绑定： 光标更改， 即刻更改播放范围
        line_edit0.cursorPositionChanged.connect(self._tL_select)
        line_edit1.cursorPositionChanged.connect(self._tR_select)
        return [radiobutton0, radiobutton1, radiobutton2, \
                    tL_dcs_btn, line_edit0, tL_ics_btn, \
                        tR_dcs_btn, line_edit1, tR_ics_btn]
                
    def _increase_text_and_play_tL_by_key(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][5]:
                self.mode0.setChecked(True)
                tL = round(float(self.data_dict[i][4].text())+1, 2)
                tR = round(float(self.data_dict[i][7].text()), 2)
                if tL > tR-0.01:
                    print("数值太大")
                elif (i>1) and (tL < round(float(self.data_dict[i-2][7].text())+0.01, 2)):
                    print("数值太小")
                else:
                    self.data_dict[i][4].setText(str(tL))
                    self.tL = tL
                    self.tR = tR
                    self.media_player.setPosition(int(round(self.tL*1000,2)))
                    self._change_marked_LineEdit(i, 4)
                    if self.media_player.state() != QMediaPlayer.PlayingState:
                        print("检测到暂停，马上播放")
                        self.media_player.play()
                        self.play_button.setText('STOP')
                break

    def _decrease_text_and_play_tL_by_key(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][3]:
                self.mode0.setChecked(True)
                tL = round(float(self.data_dict[i][4].text())-1, 2)
                tR = round(float(self.data_dict[i][7].text()), 2)
                if tL > tR-0.01:
                    print("数值太大")
                elif (i>1) and (tL < round(float(self.data_dict[i-2][7].text())+0.01, 2)):
                    print("数值太小")
                else:
                    self.data_dict[i][4].setText(str(tL))
                    self.tL = tL
                    self.tR = tR
                    self.media_player.setPosition(int(round(self.tL*1000,2)))
                    self._change_marked_LineEdit(i, 4)
                    if self.media_player.state() != QMediaPlayer.PlayingState:
                        print("检测到暂停，马上播放")
                        self.media_player.play()
                        self.play_button.setText('STOP')
                break

    def _increase_text_and_play_tR_by_key(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][8]:
                self.mode0.setChecked(True)
                tL = round(float(self.data_dict[i][4].text()), 2)
                tR = round(float(self.data_dict[i][7].text()), 2) + 1
                if tR < tL+0.01:
                    print("数值太小")
                elif (i<len((self.data_dict.keys()))-2) and (tR > round(float(self.data_dict[i+2][4].text()), 2)-0.01):
                    print("数值太大")
                else:
                    tR = min(self.duration, tR)
                    self.data_dict[i][7].setText(str(tR))
                    self.tL = tL
                    self.tR = tR
                    self.media_player.setPosition(int(round(max(self.tR-3, self.tL)*1000,2)))
                    self._change_marked_LineEdit(i, 7)
                    if self.media_player.state() != QMediaPlayer.PlayingState:
                        self.media_player.play()
                        self.play_button.setText('STOP')
                break

    def _decrease_text_and_play_tR_by_key(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][6]:
                self.mode0.setChecked(True)
                tL = round(float(self.data_dict[i][4].text()), 2)
                tR = round(float(self.data_dict[i][7].text()), 2) - 1
                if tR < tL+0.01:
                    print("数值太小")
                elif (i<len(self.data_dict.keys())-2) and (tR > round(float(self.data_dict[i+2][4].text()), 2)-0.01):
                    print("数值太大")
                else:
                    self.data_dict[i][7].setText(str(tR))
                    self.tL = tL
                    self.tR = tR
                    self.media_player.setPosition(int(round(max(self.tR-3, self.tL)*1000,2)))
                    self._change_marked_LineEdit(i, 7)
                    if self.media_player.state() != QMediaPlayer.PlayingState:
                        self.media_player.play()
                        self.play_button.setText('STOP')
                break

    def _tL_select(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][4]:
                self.idx_play_now = i
                self.media_player.pause()
                # Change play position and play range
                self.tL = round(float(self.data_dict[i][4].text()), 2)
                self.tR = round(float(self.data_dict[i][7].text()), 2)
                self.media_player.setPosition(int(round(self.tL*1000)))
                self.media_player.play()
                self.play_button.setText('STOP')
                # Change color
                self._change_marked_LineEdit(i, 4)
                # Change Play mode
                if self.mode0.isChecked():
                    self.mode2.setChecked(True)
                break
    def _tR_select(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][7]:
                self.idx_play_now = i
                self.media_player.pause()
                # Change Play position and play range
                self.tL = round(float(self.data_dict[i][4].text()), 2)
                self.tR = round(float(self.data_dict[i][7].text()), 2)
                self.media_player.setPosition(int(round(max(self.tR-3, self.tL)*1000,2)))
                # Change color
                self._change_marked_LineEdit(i, 7)
                self.media_player.play()
                self.play_button.setText('STOP')
                # Change Play mode
                if self.mode0.isChecked():
                    self.mode2.setChecked(True)
                break


    """
    ================== Connect to the Button 3 and 5. ===================
    """
    def previous_range(self):
        if self.idx_play_now == 1:
            self.media_player.pause()
            self.play_button.setText('PLAY')
            print("已经到头")
            return
        for i in range(self.idx_play_now-2, 0, -2):
            val = self.data_dict[i]
            if val[2].isChecked():
                # 判断为Noise的直接跳过
                continue
            else:
                tmp_tL = round(float(val[4].text()), 2)
                tmp_tR = round(float(val[7].text()), 2)
                self._change_marked_LineEdit(i, 4)
                # Change video position and play range
                self.media_player.setPosition(int(round(tmp_tL*1000)))
                self.tL = tmp_tL
                self.tR = tmp_tR
                self.idx_play_now = i
                print("更改播放范围为： ", self.tL, " ", self.tR)
                self.media_player.play()
                self.play_button.setText('STOP')
                break

    def next_range(self):
        tmp_total_widgets_num = len(self.data_dict)
        if self.idx_play_now == tmp_total_widgets_num-1:
            self.media_player.pause()
            self.play_button.setText('PLAY')
            return
        for i in range(self.idx_play_now+2, tmp_total_widgets_num, 2):
            val = self.data_dict[i]
            if val[2].isChecked():
                # 判断为Noise的直接跳过
                continue
            else:
                tmp_tL = round(float(val[4].text()), 2)
                tmp_tR = round(float(val[7].text()), 2)
                self._change_marked_LineEdit(i, 4)
                # Change video position and play range
                self.media_player.setPosition(int(round(tmp_tL*1000)))
                self.tL = tmp_tL
                self.tR = tmp_tR
                self.idx_play_now = i
                self.media_player.play()
                self.play_button.setText('STOP')
                break


    """
    ================== Connect to the Button 4. ===================
    """
    def play_video(self):
        if self.root == "":
            QMessageBox.information(self, "Error", "???\nNo video file has selected!")
            return None
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText('PLAY')
        else:
            self.media_player.play()
            self.play_button.setText('PAUSE')

    """
    Connect to the Timer.
    """
    def video_loop_mode(self):
        position = self.media_player.position()
        cond1 = position > self.tR*1000
        cond2 = position < self.tL*1000
        if self.mode0.isChecked() and (cond1 or cond2):
            self.media_player.pause()
            self.play_button.setText('PLAY')
            self.media_player.setPosition(int(round(self.tL*1000)))
        elif self.mode1.isChecked() and (cond1 or cond2):
            self.tL = round(0, 2)
            self.tR = round(self.duration, 2)
        elif self.mode2.isChecked() and cond1:
            tmp_total_widgets_num = len(self.data_dict)
            if self.idx_play_now == tmp_total_widgets_num-2:
                self.media_player.pause()
                self.play_button.setText('PLAY')
                return
            for i in range(self.idx_play_now+2, tmp_total_widgets_num, 2):
                val = self.data_dict[i]
                if val[2].isChecked():
                    # 判断为Noise的直接跳过
                    continue
                else:
                    tmp_tL = round(float(val[4].text()), 2)
                    tmp_tR = round(float(val[7].text()), 2)
                    self._change_marked_LineEdit(i, 4)
                    # Change video position and play range
                    self.media_player.setPosition(int(round(tmp_tL*1000)))
                    self.tL = tmp_tL
                    self.tR = tmp_tR
                    self.idx_play_now = i
                    print("更改播放范围为： ", self.tL, " ", self.tR)
                    break
        elif self.mode2.isChecked() and cond2:
            self.media_player.setPosition(int(round(self.tL*1000)))
            


    """
    ======================== Connect to the Button 6 ============================
    """
    def save_new_range(self):
        p = threading.Thread(target=_save_new_range, args=(self.data_dict, self.root, self.cut_range_path))
        p.start()

    def cut_game_video(self):
        if not os.path.exists(self.cut_range_path): return None
        cut_game_record(self.root, THREADS, individual=False)

    def change_cut_button1(self, text):
        self.cut_button1.setText(text)

    def change_cut_button2(self, text):
        self.cut_button2.setText(text)

    """
    ================== Connect to the Button 7. ===================
    """
    def clear_cache(self):
        if self.root == "":
            QMessageBox.information(self, "Error", "???\nNo video file has selected!")
            return None
        _, file_list = get_all_suffixs_files(self.root, [".csv", ".mkv"])
        for file in file_list:
            if file.endswith("CutRange.csv"):
                continue
            if os.path.exists(file):
                os.remove(file)

    def _pre_page(self):
        pagenum = int(self.text_page.text())
        if pagenum > 1:
            self.text_page.setText(str(pagenum-1))
            self._plot_cut_range()
        else:
            self.text_page.setText(str(len(self.widgets_range_per_page)))
            self._plot_cut_range()

    def _nex_page(self):
        pagenum = int(self.text_page.text())
        if pagenum < len(self.widgets_range_per_page):
            self.text_page.setText(str(pagenum+1))
            self._plot_cut_range()
        else:
            self.text_page.setText("1")
            self._plot_cut_range()

    def _change_marked_LineEdit(self, i, j):
        colored_row, colored_col = self.colored_widget
        if (colored_row) != i or (colored_col != j):
            self.data_dict[colored_row][colored_col].setStyleSheet("QLineEdit { background-color: white; }")
            self.data_dict[i][j].setStyleSheet("QLineEdit { background-color: gray; }")
            self.colored_widget = (i, j)


def _save_new_range(data_dict, root, cut_range_path):
    all_choose = True
    t_ranges = []
    for i in range(len(data_dict.keys())):
        if len(data_dict[i])==1: continue
        if data_dict[i][0].isChecked():
            t1 = round(float(data_dict[i][4].text()),2)
            t2 = round(float(data_dict[i][7].text()),2)
            t_ranges.append((t1, t2))
        elif data_dict[i][1].isChecked():
            t1 = round(float(data_dict[i][4].text()),2)
            t2 = round(float(data_dict[i][7].text()),2)
            t_ranges.append((t1, t2))
        elif data_dict[i][2].isChecked():
            continue
        else:
            all_choose = False

    if all_choose==True:
        if root == "":
            print("先指定视频文件")
            return
    # Combine Ranges
    t_ranges = combine_ranges(t_ranges, 1)
    # Remove Short Noise?
    # Write Ranges to file
    df = pd.DataFrame(t_ranges)
    df.to_csv(cut_range_path, index=False, header=False)
    print("Save cut range successfully!")
    _check_cut_range(df)

def _check_cut_range(df):
    """
    `df`: DataFrame, two columns are start time, end time.
    """
    # 检查第一行
    if df.iat[0, 0] > df.iat[0, 1]:
        print("第1行tL>tR")
        return None
    for i in range(1, len(df)):
        if df.iat[i-1, 1] > df.iat[i, 0]:
            print(f"第{i}行tR>第{i+1}行tL")
        if df.iat[i, 0] > df.iat[i, 1]:
            print(f"第{i+1}行tL>tR")
            return None
    print("Cut range no problem!")
    print("Total length: %s h %s min %s sec."%seconds_to_hms(sum(df.iloc[:,1] - df.iloc[:, 0])))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CutRange()
    window.show()
    sys.exit(app.exec())
    # cProfile.run("app = QApplication(sys.argv);window = CutRange();window.show();sys.exit(app.exec())")