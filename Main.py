import sys, os
from PyQt5.QtCore import QUrl, QTimer, QThread, pyqtSignal
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import QApplication, QGridLayout, QMainWindow, \
    QFileDialog, QPushButton, QScrollArea, QLineEdit, QWidget, \
    QPushButton, QDoubleSpinBox, QProgressBar, QRadioButton, QButtonGroup, \
    QMessageBox
from small_tools.pic_video_attribution import get_size, get_duration
import pandas as pd
import toml
from math import floor
from GamMicroTrack import Gam
from GamMicroTrack import combine_ranges
from small_tools.filemani import get_all_suffixs_files


THREADS = 5
SETTINGS = toml.load("./settings.toml")

class ThreadCut(QThread):
    """剪切视频的线程
    """
    finished = pyqtSignal()

    def __init__(self, game, root):
        super().__init__()
        self.game = game
        self.root = root
    def run(self):
        self.game.cut_game_record("output_cut.mp4", self.root)
        self.finished.emit()

class ThreadSpeed(QThread):
    """剪切视频的线程
    """
    finished = pyqtSignal()
    def __init__(self, game, root):
        super().__init__()
        self.game = game
        self.root = root
    def run(self):
        self.game.adjust_speed_game_record("output_speed.mp4", self.root)
        self.finished.emit()


class CutRange(QMainWindow):
    def __init__(self):
        # ========== 参数 ============
        self.window_title = "Adjust Cut Range"
        self.video_w = 800
        self.video_h = 450
        self.scroll_area_w = 480
        self.progress_bar_h = 4
        self.button_w = int(floor(self.video_w-60)/7)
        self.button_h = 30
        self.window_w = self.video_w + self.scroll_area_w + 30
        self.window_h = self.video_h + self.button_h + 30
        # Something will used
        self.root = ""
        self.data_dict = dict()
        self.duration = 0           # Video Length
        
        # ============== Main Window ==============
        super().__init__()
        self.setFixedSize(self.window_w, self.window_h)
        self.setWindowTitle(self.window_title)
        
        # ============== Video Play ==============
        self.media_player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.media_player.setVideoOutput(self.video_widget)
        self.video_widget.setGeometry(10, 10, self.video_w, self.video_h)
        # Timer For Video
        self.timer = QTimer()
        self.timer.timeout.connect(self.loop_video)
        # Range For Video Playing
        self.tL = 0
        self.tR = 0
        self.tL_spinbox = QDoubleSpinBox()
        self.tL_spinbox.valueChanged.connect(self.update_tL)
        self.tR_spinbox = QDoubleSpinBox()
        self.tR_spinbox.valueChanged.connect(self.update_tR)
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
        self.analyze_button.clicked.connect(self.get_time_set)

        # ============== Button.3 PLAY/STOP video ==============
        self.play_button = QPushButton("Stop", self)
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

        # ============== Button.6 Cut With Accelerated Silence ==============
        self.cut_button2 = QPushButton("Acc Cut", self)
        self.cut_button2.setGeometry(60+5*self.button_w, self.video_h+20, self.button_w, self.button_h)
        self.cut_button2.clicked.connect(self.speed_game_video)
        
        # ============== Button.7 Clear Cache ==============
        self.cut_button2 = QPushButton("Clear Cache", self)
        self.cut_button2.setGeometry(70+6*self.button_w, self.video_h+20, self.button_w, self.button_h)
        self.cut_button2.clicked.connect(self.clear_cache)

        # ============== Display Cut Range ==============
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setGeometry(self.video_w+20, 10, self.scroll_area_w, 10+self.video_h+self.button_h)
        self.plot_cut_range()


    def load_cut_range_from_file(self):
        speech_range_data = os.path.join(self.root, "SpeechRange.csv")
        cut_range_data = os.path.join(self.root, "CutRange.csv")
        if os.path.exists(cut_range_data):
            df = pd.read_csv(cut_range_data, names=["Start Time", "End Time"])
        elif os.path.exists(speech_range_data):
            df = pd.read_csv(speech_range_data, names=["Start Time", "End Time"])
        else:
            print("???")
            return None
        for i in range(len(df)):
            self.data_dict[i] = [None, None, None, None, df.iloc[i, 0], None, None, df.iloc[i, 1], None]  #????麻烦
        # 删除全部QCheckBox, QLineEdit, 
        self.delete_cut_range_area()
        self.plot_cut_range()
        
    def open_video_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("Video files (*.mp4)")
        if file_dialog.exec():
            filename = file_dialog.selectedFiles()[0]
            self.root = os.path.split(filename)[0]
            self.duration = self.tR = get_duration(filename, SETTINGS)
            self.tL_spinbox.setRange(0, self.duration)
            self.tR_spinbox.setRange(0, self.duration)
            video_url = QUrl.fromLocalFile(os.path.abspath(filename))
            media_content = QMediaContent(video_url)
            self.media_player.setMedia(media_content)
            self.media_player.positionChanged.connect(self.update_progress_bar)
            self.media_player.play()
            self.timer.start(10)
        
    def play_video(self):
        if self.root == "":
            QMessageBox.information(self, "Error", "???\nNo video file has selected!")
            return None
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_button.setText('Play')
        else:
            self.media_player.play()
            self.play_button.setText('Pause')

    def update_progress_bar(self):
        if self.duration > 0:
            progress = int(round(self.media_player.position() / self.duration))
            self.progress_bar.setValue(progress)

    def loop_video(self):
        position = self.media_player.position()
        cond1 = position > self.tR*1000
        cond2 = position < self.tL*1000
        if cond1 or cond2:
            self.media_player.setPosition(int(round(self.tL*1000)))
            print("更改播放范围为： ", self.tL, " ", self.tR)

    def update_tL(self):
        self.tL = self.tL_spinbox.value()

    def update_tR(self):
        self.tR = self.tR_spinbox.value()
    
    def delete_cut_range_area(self):
        for i in reversed(range(self.scroll_widget.layout().count())):
            self.scroll_widget.layout().itemAt(i).widget().setParent(None)

    def plot_cut_range(self):
        # Create a widget to hold the line edits
        self.scroll_widget = QWidget()
        # Create a grid layout for the widget
        self.scroll_layout = QGridLayout(self.scroll_widget)
        if len(self.data_dict)==0:
            for i in range(10):
                buttongroup = QButtonGroup(self)
                radiobutton0 = QRadioButton(f"Trans", self.scroll_widget); buttongroup.addButton(radiobutton0)
                radiobutton0.setEnabled(False)  # 这个按钮暂时不需要
                radiobutton1 = QRadioButton(f"Chat", self.scroll_widget); buttongroup.addButton(radiobutton1)
                radiobutton2 = QRadioButton(f"Noise", self.scroll_widget); buttongroup.addButton(radiobutton2)
                line_edit0 = QLineEdit(str(""), self.scroll_widget); line_edit0.setFixedWidth(80)
                line_edit1 = QLineEdit(str(""), self.scroll_widget); line_edit1.setFixedWidth(80)
                radiobutton1.setChecked(True)
                # 音量减小增加键
                tL_dcs_btn = QPushButton("-1", self)
                tL_dcs_btn.setFixedSize(20, 20)
                tL_dcs_btn.clicked.connect(self.decrease_text_and_play_tL_by_key)
                tL_ics_btn = QPushButton("+1", self)
                tL_ics_btn.setFixedSize(20, 20)
                tL_ics_btn.clicked.connect(self.increase_text_and_play_tL_by_key)
                tR_dcs_btn = QPushButton("-1", self)
                tR_dcs_btn.setFixedSize(20, 20)
                tR_dcs_btn.clicked.connect(self.decrease_text_and_play_tR_by_key)
                tR_ics_btn = QPushButton("+1", self)
                tR_ics_btn.setFixedSize(20, 20)
                tR_ics_btn.clicked.connect(self.increase_text_and_play_tR_by_key)
                self.data_dict[i] = [radiobutton0, radiobutton1, radiobutton2, \
                                        tL_dcs_btn, line_edit0, tL_ics_btn, \
                                            tR_dcs_btn, line_edit1, tR_ics_btn]

                # Add the widgets to the grid layout
                self.scroll_layout.addWidget(radiobutton0, i, 0)
                self.scroll_layout.addWidget(radiobutton1, i, 1)
                self.scroll_layout.addWidget(radiobutton2, i, 2)
                self.scroll_layout.addWidget(tL_dcs_btn, i, 3)
                self.scroll_layout.addWidget(line_edit0, i, 4)
                self.scroll_layout.addWidget(tL_ics_btn, i, 5)
                self.scroll_layout.addWidget(tR_dcs_btn, i, 6)
                self.scroll_layout.addWidget(line_edit1, i, 7)
                self.scroll_layout.addWidget(tR_ics_btn, i, 8)
        else:
            for i in range(0, len(self.data_dict)):
                buttongroup = QButtonGroup(self)
                radiobutton0 = QRadioButton(f"Trans", self.scroll_widget); buttongroup.addButton(radiobutton0)
                radiobutton0.setEnabled(False)  # 这个按钮暂时不需要
                radiobutton1 = QRadioButton(f"Chat", self.scroll_widget); buttongroup.addButton(radiobutton1)
                radiobutton2 = QRadioButton(f"Noise", self.scroll_widget); buttongroup.addButton(radiobutton2)
                line_edit0 = QLineEdit(str(round(self.data_dict[i][4],3)), self.scroll_widget)
                line_edit1 = QLineEdit(str(round(self.data_dict[i][7],3)), self.scroll_widget)
                line_edit0.setFixedWidth(80)
                line_edit1.setFixedWidth(80)
                radiobutton1.setChecked(True)
                # 音量减小增加键
                tL_dcs_btn = QPushButton("-1", self)
                tL_dcs_btn.setFixedSize(20, 20)
                tL_dcs_btn.clicked.connect(self.decrease_text_and_play_tL_by_key)
                tL_ics_btn = QPushButton("+1", self)
                tL_ics_btn.setFixedSize(20, 20)
                tL_ics_btn.clicked.connect(self.increase_text_and_play_tL_by_key)
                tR_dcs_btn = QPushButton("-1", self)
                tR_dcs_btn.setFixedSize(20, 20)
                tR_dcs_btn.clicked.connect(self.decrease_text_and_play_tR_by_key)
                tR_ics_btn = QPushButton("+1", self)
                tR_ics_btn.setFixedSize(20, 20)
                tR_ics_btn.clicked.connect(self.increase_text_and_play_tR_by_key)
                # 事件绑定： 光标更改， 即刻更改播放范围
                line_edit0.cursorPositionChanged.connect(self.change_play_range_tL)
                line_edit1.cursorPositionChanged.connect(self.change_play_range_tR)
                # 更新总体数据
                self.data_dict[i] = [radiobutton0, radiobutton1, radiobutton2, \
                                        tL_dcs_btn, line_edit0, tL_ics_btn, \
                                            tR_dcs_btn, line_edit1, tR_ics_btn]

                # Add the widgets to the grid layout
                self.scroll_layout.addWidget(radiobutton0, i, 0)
                self.scroll_layout.addWidget(radiobutton1, i, 1)
                self.scroll_layout.addWidget(radiobutton2, i, 2)
                self.scroll_layout.addWidget(tL_dcs_btn, i, 3)
                self.scroll_layout.addWidget(line_edit0, i, 4)
                self.scroll_layout.addWidget(tL_ics_btn, i, 5)
                self.scroll_layout.addWidget(tR_dcs_btn, i, 6)
                self.scroll_layout.addWidget(line_edit1, i, 7)
                self.scroll_layout.addWidget(tR_ics_btn, i, 8)
        # Set the widget for the scroll area
        self.scroll_area.setWidget(self.scroll_widget)
        self.update()

    def increase_text_and_play_tL_by_key(self):
        for i in range(len(self.data_dict)):
            if self.sender() == self.data_dict[i][5]:
                tL = round(float(self.data_dict[i][4].text()), 3) + 1
                if tL > round(float(self.data_dict[i][7].text()), 3) - 0.001:
                    print("数值太大")
                elif (i>0) and (tL < round(float(self.data_dict[i-1][7].text()), 3)+0.001):
                    print("数值太小")
                else:
                    self.data_dict[i][4].setText(str(tL))
                    self.tL_spinbox.setValue(tL)
                    self.media_player.setPosition(int(round(self.tL*1000,3)))

    def decrease_text_and_play_tL_by_key(self):
        for i in range(len(self.data_dict)):
            if self.sender() == self.data_dict[i][3]:
                tL = round(float(self.data_dict[i][4].text()), 3) - 1
                if tL > round(float(self.data_dict[i][7].text()), 3) - 0.001:
                    print("数值太大")
                elif (i>0) and (tL < round(float(self.data_dict[i-1][7].text()), 3)+0.001):
                    print("数值太小")
                else:
                    self.data_dict[i][4].setText(str(tL))
                    self.tL_spinbox.setValue(tL)
                    self.media_player.setPosition(int(round(self.tL*1000,3)))

    def increase_text_and_play_tR_by_key(self):
        for i in range(len(self.data_dict)):
            if self.sender() == self.data_dict[i][8]:
                tR = round(float(self.data_dict[i][7].text()), 3) + 1
                if tR < round(float(self.data_dict[i][4].text()), 3)+0.001:
                    print("数值太小")
                elif (i<len(self.data_dict)) and (tR > round(float(self.data_dict[i+1][4].text()), 3)-0.001):
                    print("数值太大")
                else:
                    self.data_dict[i][7].setText(str(tR))
                    self.tR_spinbox.setValue(tR)
                    self.media_player.setPosition(int(round(max(self.tR-1, self.tL)*1000,3)))

    def decrease_text_and_play_tR_by_key(self):
        for i in range(len(self.data_dict)):
            if self.sender() == self.data_dict[i][6]:
                tR = round(float(self.data_dict[i][7].text()), 3) - 1
                if tR < round(float(self.data_dict[i][4].text()), 3)+0.001:
                    print("数值太小")
                elif (i<len(self.data_dict)) and (tR > round(float(self.data_dict[i+1][4].text()), 3)-0.001):
                    print("数值太大")
                else:
                    self.data_dict[i][7].setText(str(tR))
                    self.tR_spinbox.setValue(tR)
                    self.media_player.setPosition(int(round(max(self.tR-1, self.tL)*1000,3)))

    def change_play_range_tL(self):
        for i in range(len(self.data_dict)):
            if self.sender() == self.data_dict[i][4]:
                self.tL_spinbox.setValue(float(self.data_dict[i][4].text()))
                self.tR_spinbox.setValue(float(self.data_dict[i][7].text()))
    def change_play_range_tR(self):
        for i in range(len(self.data_dict)):
            if self.sender() == self.data_dict[i][7]:
                self.tL_spinbox.setValue(float(self.data_dict[i][4].text()))
                self.tR_spinbox.setValue(float(self.data_dict[i][7].text()))


    def save_new_range(self):
        df = pd.DataFrame(columns=["Start Time", "End Time"])
        all_choose = True
        t_ranges = []
        for i in range(len(self.data_dict)):
            if self.data_dict[i][0].isChecked():
                t1 = round(float(self.data_dict[i][4].text()),3)
                t2 = round(float(self.data_dict[i][7].text()),3)
                t_ranges.append((t1, t2))
            elif self.data_dict[i][1].isChecked():
                t1 = round(float(self.data_dict[i][4].text()),3)
                t2 = round(float(self.data_dict[i][7].text()),3)
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
        t_ranges = combine_ranges(t_ranges, 1.002)
        # Remove Short Noise?
        # Write Ranges to file
        df = pd.DataFrame(t_ranges)
        df.to_csv(os.path.join(self.root, "CutRange.csv"), index=False, header=False)

    def get_time_set(self):
        if self.root == "":
            QMessageBox.information(self, "Error", "???\nNo video file has selected!")
            return None
        path_initial_cut_range = os.path.join(self.root, "SpeechRange.csv")
        if not os.path.exists(path_initial_cut_range):
            game = Gam(path_initial_cut_range, THREADS, SETTINGS)
            game.get_time_set_to_cut(self.root)
        self.load_cut_range_from_file()


    def cut_game_video(self):
        # if self.if_data_saved() == False: return None
        if not os.path.exists(os.path.join(self.root, "CutRange.csv")): return None
        # self.change_cut_button1("Cutting...")
        # game_thread = ThreadCut(Gam(os.path.join(self.root, "CutRange.csv"), THREADS, SETTINGS), self.root)
        # game_thread.finished.connect(lambda x: self.change_cut_button1("Finished!"))
        # game_thread.start()
        game = Gam(os.path.join(self.root, "CutRange.csv"), THREADS, SETTINGS)
        game.cut_game_record("output_cut.mp4", self.root)

    def speed_game_video(self):
        # if self.if_data_saved() == False: return None
        if not os.path.exists(os.path.join(self.root, "CutRange.csv")): return None
        # self.change_cut_button1("Cutting...")
        # game_thread = ThreadSpeed(Gam(os.path.join(self.root, "CutRange.csv"), THREADS, SETTINGS), self.root)
        # game_thread.finished.connect(lambda x: self.change_cut_button2("Finished!"))
        # game_thread.start()
        game = Gam(os.path.join(self.root, "CutRange.csv"), THREADS, SETTINGS)
        game.adjust_speed_game_record("output_speed.mp4", self.root)

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
        _, file_list = get_all_suffixs_files(self.root, ".csv")
        for file in file_list:
            if os.path.exists(file):
                os.remove(file)

def which_line_edit():
    widget = QApplication.focusWidget()
    if isinstance(widget, QLineEdit):
        print("The current QLineEdit is:", widget.objectName())
    else:
        print("No QLineEdit has focus.")

app = QApplication(sys.argv)
window = CutRange()
window.show()
sys.exit(app.exec())