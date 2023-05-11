import sys, os
from PyQt5.QtCore import QUrl, QTimer, QThread, pyqtSignal
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QApplication, QGridLayout, QMainWindow, \
    QFileDialog, QPushButton, QScrollArea, QLineEdit, QWidget, \
    QPushButton, QDoubleSpinBox, QProgressBar, QRadioButton, QButtonGroup, \
    QMessageBox, QHBoxLayout, QLabel
from small_tools.pic_video_attribution import get_duration
import pandas as pd
import toml
from math import floor
from GamMicroTrack import Gam, cut_game_record
from GamMicroTrack import combine_ranges
from small_tools.filemani import get_all_suffixs_files
import subprocess


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
        self.progress_bar_h = 4
        self.button_w = int(floor(self.video_w-60)/6)
        self.button_h = 30
        self.window_w = self.video_w + self.scroll_area_w + 30
        self.window_h = self.video_h + self.button_h + 30
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
        self.pagenum = 0
        self.widgets_range_per_page = None
        self.idx_range = range(0, self.widgets_number_per_page)
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
        self.media_player.setVideoOutput(self.video_widget)
        self.video_widget.setGeometry(10, 10, self.video_w, self.video_h)
        # Timer For Video
        self.mode_timer = QTimer()
        self.mode_timer.timeout.connect(self.video_loop_mode)
        # Range For Video Playing
        self.tL = 0
        self.tR = 0
        self.tL_spinbox = QDoubleSpinBox()
        self.tL_spinbox.valueChanged.connect(self._update_tL)
        self.tR_spinbox = QDoubleSpinBox()
        self.tR_spinbox.valueChanged.connect(self._update_tR)
        # Video Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setGeometry(10, self.video_h+10, self.video_w, 4)
        self.progress_bar.setRange(0, 1000)

        # ============== Button.1 To Open Window ==============
        self.open_folder_button = QPushButton("Open Video File", self)
        self.open_folder_button.setGeometry(10, self.video_h+20, self.button_w, self.button_h)
        self.open_folder_button.clicked.connect(self.open_video_file)

        # ============== Button.2 Analyze Recording Video ==============
        self.analyze_button = QPushButton("Analyze", self)
        self.analyze_button.setGeometry(20+self.button_w, self.video_h+20, self.button_w, self.button_h)
        self.analyze_button.clicked.connect(self.analyze_video)

        # ============== Button.3 PLAY/STOP video ==============
        self.play_button = QPushButton("STOP", self)
        self.play_button.setGeometry(30+2*self.button_w, self.video_h+20, self.button_w, self.button_h)
        self.play_button.clicked.connect(self.play_video)

        # ============== Button.4 Export Cut Range ==============
        self.save_button = QPushButton("Save New Range", self)
        self.save_button.setGeometry(40+3*self.button_w, self.video_h+20, self.button_w, self.button_h)
        self.save_button.clicked.connect(self.save_new_range)

        # ============== Button.5 Cut Without Silence ==============
        self.cut_button1 = QPushButton("Cut", self)
        self.cut_button1.setGeometry(50+4*self.button_w, self.video_h+20, self.button_w, self.button_h)
        self.cut_button1.clicked.connect(self.cut_game_video)
        
        # ============== Button.6 Clear Cache ==============
        self.cut_button2 = QPushButton("Clear Cache", self)
        self.cut_button2.setGeometry(60+5*self.button_w, self.video_h+20, self.button_w, self.button_h)
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
        self.label_page = QLabel("", self)
        self.label_page.setGeometry(self.video_w+50+3*self.mode_w, 10, self.mode_w, self.mode_h)
        self.btn_pre_page = QPushButton("Prev", self)
        self.btn_pre_page.setGeometry(self.video_w+60+4*self.mode_w, 10, self.mode_w, self.mode_h)
        self.btn_pre_page.clicked.connect(self._pre_page)
        self.btn_nex_page = QPushButton("Next", self)
        self.btn_nex_page.setGeometry(self.video_w+70+5*self.mode_w, 10, self.mode_w, self.mode_h)
        self.btn_nex_page.clicked.connect(self._nex_page)

        # ============== Display Cut Range ==============
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setGeometry(self.video_w+20, 20+self.mode_h, self.scroll_area_w, self.video_h+self.button_h - self.mode_h)
        # Recreate a widget to hold the line edits
        self.scroll_widget = QWidget()
        self.scroll_widget.setGeometry(self.video_w+20, 20+self.mode_h, self.scroll_area_w-20, self.video_h+self.button_h - self.mode_h-20)
        self.scroll_layout = QGridLayout(self.scroll_widget)
        self.scroll_layout.setVerticalSpacing(1)
        self._plot_cut_range()

    """
    ============= Connect to the Button 1 ===================
    
    """
    def open_video_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Video files (*.mp4)")
        if file_dialog.exec():
            filepath = file_dialog.selectedFiles()[0]
            self.abs_video_path = filepath
            self.root, filename = os.path.split(filepath)
            videoname = filename.split(".")[0]
            self.speech_range_path = os.path.join(self.root, videoname+"_SpeechRange.csv")
            self.cut_range_path    = os.path.join(self.root, videoname+"_CutRange.csv")
            self.duration = self.tR = get_duration(filepath, SETTINGS)
            self.tL_spinbox.setRange(0, self.duration)
            self.tR_spinbox.setRange(0, self.duration)
            video_url = QUrl.fromLocalFile(os.path.abspath(filepath))
            media_content = QMediaContent(video_url)
            self.media_player.setMedia(media_content)
            self.media_player.positionChanged.connect(self._update_progress_bar)
            self.media_player.play()
            self.mode_timer.start(10)

    def _update_progress_bar(self):
        if self.duration > 0:
            progress = int(round(self.media_player.position() / self.duration))
            self.progress_bar.setValue(progress)

    """
    =============== Connect to the Button 2 ===============
    """
    def analyze_video(self):
        if self.root == "":
            QMessageBox.information(self, "Error", "???\nNo video file has selected!")
            return None
        
        if not os.path.exists(self.speech_range_path):
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
        for i in range(2*len(df)+1):
            if i%2 == 0:
                self.data_dict[i] = self._get_hline_widgets()
            else:
                self.data_dict[i] = self._get_data_widgets(round(df.iloc[(i-1)//2, 0],2), round(df.iloc[(i-1)//2, 1],2), "Chat")
        self._plot_cut_range()


    def _plot_cut_range(self):
        # Delete all widgets in scroll area.
        try:
            for i in reversed(range(self.scroll_layout.count())):
                self.scroll_layout.itemAt(i).widget().setParent(None)
        except:
            pass
        # Refresh page numbers
        self._refresh_data_numbers_per_page()
        # Get plot range
        idx1, idx2 = self.widgets_range_per_page[self.pagenum]
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
        tmp_lst = [self.widgets_number_per_page] * (len(self.data_dict)//self.widgets_number_per_page)
        tmp_lst.append(len(self.data_dict)%self.widgets_number_per_page)
        res_lst = []
        for pagenum, widget_count in enumerate(tmp_lst):
            idx_L = pagenum * self.widgets_number_per_page
            res_lst.append((idx_L, idx_L + widget_count))
        self.label_page.setText("%s/%s"%(self.pagenum+1, len(res_lst)))
        self.widgets_range_per_page=res_lst

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
                # Plot widgets
                self._plot_cut_range()
                # Change video player
                self.tL_spinbox.setValue(tL)
                self.tR_spinbox.setValue(tR)
                self.media_player.setPosition(int(round(self.tL*1000,2)))
                # Change color
                self._change_marked_LineEdit(i+1, 4)
                break

    # ============================================================
    # Get data widgets, and connect to following 6 functions
    # ============================================================
    def _get_data_widgets(self, tL, tR, typestr):
        buttongroup = QButtonGroup(self)
        radiobutton0 = QRadioButton(f"Trans", self.scroll_widget); buttongroup.addButton(radiobutton0)
        radiobutton1 = QRadioButton(f"Chat", self.scroll_widget); buttongroup.addButton(radiobutton1)
        if typestr == "Chat":
            radiobutton0.setEnabled(False)  # 这个按钮暂时不需要
            radiobutton1.setChecked(True)
        else:
            radiobutton0.setChecked(True)
            radiobutton1.setEnabled(False)
        radiobutton2 = QRadioButton(f"Noise", self.scroll_widget); buttongroup.addButton(radiobutton2)
        line_edit0 = QLineEdit(str(tL), self.scroll_widget)
        line_edit1 = QLineEdit(str(tR), self.scroll_widget)
        line_edit0.setFixedWidth(80)
        line_edit1.setFixedWidth(80)
        # 音量减小增加键
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
                tL = round(float(self.data_dict[i][4].text())+1, 2)
                tR = round(float(self.data_dict[i][7].text()), 2)
                if tL > tR-0.01:
                    print("数值太大")
                elif (i>1) and (tL < round(float(self.data_dict[i-2][7].text())+0.01, 2)):
                    print("数值太小")
                else:
                    self.data_dict[i][4].setText(str(tL))
                    self.tL_spinbox.setValue(tL)
                    self.tR_spinbox.setValue(tR)
                    self.media_player.setPosition(int(round(self.tL*1000,2)))
                    self._change_marked_LineEdit(i, 4)
                break

    def _decrease_text_and_play_tL_by_key(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][3]:
                tL = round(float(self.data_dict[i][4].text())-1, 2)
                tR = round(float(self.data_dict[i][7].text()), 2)
                if tL > tR-0.01:
                    print("数值太大")
                elif (i>1) and (tL < round(float(self.data_dict[i-2][7].text())+0.01, 2)):
                    print("数值太小")
                else:
                    self.data_dict[i][4].setText(str(tL))
                    self.tL_spinbox.setValue(tL)
                    self.tR_spinbox.setValue(tR)
                    self.media_player.setPosition(int(round(self.tL*1000,2)))
                    self._change_marked_LineEdit(i, 4)
                break

    def _increase_text_and_play_tR_by_key(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][8]:
                tL = round(float(self.data_dict[i][4].text()), 2)
                tR = round(float(self.data_dict[i][7].text()), 2) + 1
                if tR < tL+0.01:
                    print("数值太小")
                elif (i<len((self.data_dict.keys()))-2) and (tR > round(float(self.data_dict[i+2][4].text()), 2)-0.01):
                    print("数值太大")
                else:
                    tR = min(self.duration, tR)
                    self.data_dict[i][7].setText(str(tR))
                    self.tL_spinbox.setValue(tL)
                    self.tR_spinbox.setValue(tR)
                    self.media_player.setPosition(int(round(max(self.tR-2, self.tL)*1000,2)))
                    self._change_marked_LineEdit(i, 7)
                break

    def _decrease_text_and_play_tR_by_key(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][6]:
                tL = round(float(self.data_dict[i][4].text()), 2)
                tR = round(float(self.data_dict[i][7].text()), 2) - 1
                if tR < tL+0.01:
                    print("数值太小")
                elif (i<len(self.data_dict.keys())-2) and (tR > round(float(self.data_dict[i+2][4].text()), 2)-0.01):
                    print("数值太大")
                else:
                    self.data_dict[i][7].setText(str(tR))
                    self.tL_spinbox.setValue(tL)
                    self.tR_spinbox.setValue(tR)
                    self.media_player.setPosition(int(round(max(self.tR-2, self.tL)*1000,2)))
                    self._change_marked_LineEdit(i, 7)
                break

    def _tL_select(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][4]:
                # Change play position and play range
                self.tL_spinbox.setValue(round(float(self.data_dict[i][4].text()), 2))
                self.tR_spinbox.setValue(round(float(self.data_dict[i][7].text()), 2))
                self.media_player.setPosition(int(round(self.tL*1000)))
                # Change color
                self._change_marked_LineEdit(i, 4)
                break
    def _tR_select(self):
        for i in self.idx_range:
            if len(self.data_dict[i])==1: continue
            if self.sender() == self.data_dict[i][7]:
                # Change Play position and play range
                self.tL_spinbox.setValue(round(float(self.data_dict[i][4].text()), 2))
                self.tR_spinbox.setValue(round(float(self.data_dict[i][7].text()), 2))
                self.media_player.setPosition(int(round(self.tL*1000)))
                # Change color
                self._change_marked_LineEdit(i, 7)
                break


    """
    ================== Connect to the Button 3. ===================
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
            self.media_player.setPosition(int(round(self.tL*1000)))
            print("更改播放范围为： ", self.tL, " ", self.tR)
        elif self.mode1.isChecked() and (cond1 or cond2):
            self.tL_spinbox.setValue(round(0, 2))
            self.tR_spinbox.setValue(round(self.duration, 2))
        elif self.mode2.isChecked() and cond1:
            end = True
            for i, val in enumerate(self.data_dict.values()):
                if len(self.data_dict[i])==1: continue
                tmp_tL = round(float(val[4].text()), 2)
                tmp_tR = round(float(val[7].text()), 2)
                if tmp_tL > self.tR:
                    end = False
                    self._change_marked_LineEdit(i, 4)
                    # Change video position and play range
                    self.media_player.setPosition(int(round(tmp_tL*1000)))
                    self.tL_spinbox.setValue(tmp_tL)
                    self.tR_spinbox.setValue(tmp_tR)
                    break
            if end == True:
                self.media_player.pause()
        elif self.mode2.isChecked() and cond2:
            self.media_player.setPosition(int(round(self.tL*1000)))
            

    def _update_tL(self):
        self.tL = self.tL_spinbox.value()

    def _update_tR(self):
        self.tR = self.tR_spinbox.value()


    """
    ======================== Connect to the Button 4 ============================
    """
    def save_new_range(self):
        df = pd.DataFrame(columns=["Start Time", "End Time"])
        all_choose = True
        t_ranges = []
        for i in range(len(self.data_dict.keys())):
            if len(self.data_dict[i])==1: continue
            if self.data_dict[i][0].isChecked():
                t1 = round(float(self.data_dict[i][4].text()),2)
                t2 = round(float(self.data_dict[i][7].text()),2)
                t_ranges.append((t1, t2))
            elif self.data_dict[i][1].isChecked():
                t1 = round(float(self.data_dict[i][4].text()),2)
                t2 = round(float(self.data_dict[i][7].text()),2)
                t_ranges.append((t1, t2))
            elif self.data_dict[i][2].isChecked():
                continue
            else:
                all_choose = False

        if all_choose==True:
            if self.root == "":
                raise "先指定视频文件"
        else:
            raise "还有的没选呢"
        # Combine Ranges
        t_ranges = combine_ranges(t_ranges, 1.5)
        # Remove Short Noise?
        # Write Ranges to file
        df = pd.DataFrame(t_ranges)
        df.to_csv(self.cut_range_path, index=False, header=False)

    def cut_game_video(self):
        if not os.path.exists(self.cut_range_path): return None
        cut_game_record(self.root, THREADS, individual=False)

    def change_cut_button1(self, text):
        self.cut_button1.setText(text)

    def change_cut_button2(self, text):
        self.cut_button2.setText(text)

    # def if_data_saved(self):
    #     datapath = os.path.join(self.root, "CutRange.csv")
        
    #     if not os.path.exists(datapath):
    #         return False
    #     else:
    #         df = pd.read_csv(datapath, names=["start", "end"])
    #         if len(df) != len(self.data_dict):
    #             print(len(df), " ", len(self.data_dict))
    #             QMessageBox.information(self, "Error", "CutRange hasn't be exported!\n请立即导出!")
    #             return False
    #         else:
    #             all_equal = True
    #             for i in range(len(df)):
    #                 if df.iloc[i, 0] != self.data_dict[i][4]: all_equal=False
    #                 if df.iloc[i, 1] != self.data_dict[i][7]: all_equal=False
    #             if all_equal ==False:
    #                 QMessageBox.information(self, "Error", "CutRange和当前数据不吻合!\n请立即保存!")
    #                 return False
    #             else:
    #                 return True

    def clear_cache(self):
        if self.root == "":
            QMessageBox.information(self, "Error", "???\nNo video file has selected!")
            return None
        _, file_list = get_all_suffixs_files(self.root, [".csv"])
        for file in file_list:
            if os.path.exists(file):
                os.remove(file)

    def _pre_page(self):
        if self.pagenum > 0:
            self.pagenum -= 1
            self.label_page.setText("%s/%s"%(self.pagenum+1, len(self.widgets_range_per_page)))
            self._plot_cut_range()

    def _nex_page(self):
        if self.pagenum < len(self.widgets_range_per_page)-1:
            self.pagenum += 1
            self.label_page.setText("%s/%s"%(self.pagenum+1, len(self.widgets_range_per_page)))
            self._plot_cut_range()

    def _change_marked_LineEdit(self, i, j):
        colored_row, colored_col = self.colored_widget
        self.data_dict[colored_row][colored_col].setStyleSheet("QLineEdit { background-color: white; }")
        self.data_dict[i][j].setStyleSheet("QLineEdit { background-color: gray; }")
        self.colored_widget = (i, j)


def which_line_edit():
    widget = QApplication.focusWidget()
    if isinstance(widget, QLineEdit):
        print("The current QLineEdit is:", widget.objectName())
    else:
        print("No QLineEdit has focus.")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CutRange()
    window.show()
    sys.exit(app.exec())