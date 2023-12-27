import time
import logging
import numpy as np
import ffmpeg
import whisper
import toml
import torch
from abc import ABC, abstractmethod
from typing import Literal
from pydub import AudioSegment
from tqdm import tqdm

from .segments_mani import (
    expand_time_segments,
    remove_noise,
    combine_time_segments
)


LANG = Literal[
    "zh",
    "en",
    "Afrikaans",
    "Arabic",
    "Armenian",
    "Azerbaijani",
    "Belarusian",
    "Bosnian",
    "Bulgarian",
    "Catalan",
    "Croatian",
    "Czech",
    "Danish",
    "Dutch",
    "Estonian",
    "Finnish",
    "French",
    "Galician",
    "German",
    "Greek",
    "Hebrew",
    "Hindi",
    "Hungarian",
    "Icelandic",
    "Indonesian",
    "Italian",
    "Japanese",
    "Kannada",
    "Kazakh",
    "Korean",
    "Latvian",
    "Lithuanian",
    "Macedonian",
    "Malay",
    "Marathi",
    "Maori",
    "Nepali",
    "Norwegian",
    "Persian",
    "Polish",
    "Portuguese",
    "Romanian",
    "Russian",
    "Serbian",
    "Slovak",
    "Slovenian",
    "Spanish",
    "Swahili",
    "Swedish",
    "Tagalog",
    "Tamil",
    "Thai",
    "Turkish",
    "Ukrainian",
    "Urdu",
    "Vietnamese",
    "Welsh",
]

SETTINGS = toml.load("./settings.toml")


class AbstractSpeech(ABC):
    def __init__(
        self,
        audiopath: str,
        lang: LANG = SETTINGS["whisper"]["lang"],
        method: Literal["vol", "vad"] = "vol",
        sr: int = SETTINGS["whisper"]["sample_rate"],
        device: Literal["cpu", "cuda"] = SETTINGS["whisper"]["device"],
        model_name: Literal[
            "tiny", "base", "small", "medium", "large", "large-v2"
        ] = SETTINGS["whisper"]["model"],
    ):
        """
        Args:
            sr (int, optional): sampling rate. Defaults to 16000.
        """
        self.audiopath = audiopath
        self.method = method
        self.sr = sr
        self.lang = lang
        self.device = device
        self.audio_array = self.load_audio_array_data(audiopath, sr)
        self.whisper_model = whisper.load_model(model_name, device)
        self.speech_array_indices = None

    @abstractmethod
    def get_time_segments_of_speech(self, *args, **kwargs):
        pass

    @abstractmethod
    def _detect_voice_activity(self, *args, **kwargs):
        pass

    def _transcribe(self, audio, seg, lang):
        r = self.whisper_model.transcribe(
            audio[seg[0]:seg[1]],
            task="transcribe",
            language=lang,
        )
        r["origin_timestamp"] = seg
        return r

    def transcribe(self):
        res = []
        if self.device == "cpu":
            # CPU计算
            logging.info("即将用CPU计算")
            sub_res = []
            print(self.speech_array_indices[:10])
            for seg in tqdm(self.speech_array_indices):
                sub_res.append(
                    self._transcribe(self.audio_array, seg, self.lang),
                )
            res = [sub for sub in sub_res]
        else:
            # GPU计算
            for seg in tqdm(self.speech_array_indices):
                r = self.whisper_model.transcribe(
                    self.audio_array[seg[0]:seg[1]],
                    task="transcribe",
                    language=self.lang,
                    verbose=False if len(self.speech_array_indices) == 1 else None,
                )
                r["origin_timestamp"] = seg
                res.append(r)
        return res

    @staticmethod
    def err_call_back(err):
        print(f"CPU计算多进程出错啦~ error：{str(err)}")

    @staticmethod
    def load_audio_array_data(file: str, sr: int) -> np.ndarray:
        try:
            out, _ = (
                ffmpeg.input(file, threads=0)
                .output(
                    "-",
                    format="s16le",
                    acodec="pcm_s16le",
                    ac=1,
                    ar=sr,
                )
                .run(
                    cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True
                )
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

        return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

    @staticmethod
    def load_audio_dB_data(audiopath):
        sound = AudioSegment.from_file(audiopath, format="wav")
        time_arr = np.array([i / 1000 for i in range(len(sound))])
        dbfs_list = [sound[i].rms for i in range(len(sound))]
        dbfs_arr = (
            np.array(dbfs_list) + 1e-300
        )  # Avoid zero when calc `log10` next line
        dbfs_arr = 20 * np.log10(dbfs_arr)
        dbfs_arr[dbfs_arr < 0] = 0
        return time_arr, dbfs_arr


class SpeechVolume(AbstractSpeech):
    def __init__(self, audiopath: str, setting):
        super().__init__(audiopath, method="vol")
        self.cri_dB_ratio = setting["Gam"]["cri_dB_ratio"]
        self.noise_len = setting["Gam"]["noise_sig_length"]
        self.growth_decay_time = setting["Gam"]["growth_or_decay_time_of_voice"]

    def get_time_segments_of_speech(self):
        time_arr, dB_arr = self.load_audio_dB_data(self.audiopath)
        self._detect_voice_activity(time_arr, dB_arr)

    def _detect_voice_activity(self, time_arr, dB_arr):
        """Detect voice activity according to volume.

        This function will change `self.speech_array_indices`
        """
        max_t = float(max(time_arr))
        cri_dB = self.cri_dB_ratio * max(dB_arr)
        time_segments = remove_noise(
            list(time_arr[dB_arr > cri_dB]), max_t, self.noise_len,
        )
        time_segments = expand_time_segments(
            time_segments, self.growth_decay_time, self.growth_decay_time, 0, max_t
        )
        self.speech_array_indices = [
            (
                int(round(self.sr * tL)),
                min(int(round(self.sr * tR)), len(self.audio_array))
                if i == len(time_segments)
                else int(round(self.sr * tR)),
            )
            for i, (tL, tR) in enumerate(time_segments)
        ]


class SpeechVAD(AbstractSpeech):
    def __init__(self, audiopath: str):
        super().__init__(audiopath, method="vad")

    def get_time_segments_of_speech(self):
        audio = self.load_audio_array_data(self.audiopath, self.sr)
        self._detect_voice_activity(audio)

    def _detect_voice_activity(self, audio):
        tic = time.time()
        # torch load limit https://github.com/pytorch/vision/issues/4156
        torch.hub._validate_not_a_forked_repo = lambda a, b, c: True
        self.vad_model, funcs = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True
        )

        fun_detect_speech = funcs[0]

        speeches = fun_detect_speech(
            audio, self.vad_model, sampling_rate=self.sr
        )

        # Remove too short segments
        speeches = remove_noise(speeches, 1.0 * self.sr)

        # Expand to avoid to tight cut. You can tune the pad length
        speeches = expand_time_segments(
            speeches, 0.2 * self.sr, 0.0 * self.sr, 0, audio.shape[0]
        )

        # Merge very closed segments
        speeches = combine_time_segments(speeches, 0.5 * self.sr)

        logging.info(
            f"Done voice activity detection in {time.time() - tic:.1f} sec"
        )
        print(speeches)
        print([(s["start"]/self.sr, s["end"]/self.sr) for s in speeches])
        self.speech_array_indices = [(int(s["start"]), int(s["end"])) for s in speeches]
