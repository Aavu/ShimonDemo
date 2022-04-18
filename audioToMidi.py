"""
Author: Raghavasimhan Sankaranarayanan
Date: 04/08/2022
"""

import librosa
import madmom
import numpy as np
from pretty_midi import Note


class AudioMidiConverter:
    def __init__(self, raga_map=None, root='D3', sr=16000, note_min='D2', note_max='A5', frame_size=2048,
                 hop_length=441, outlier_coeff=2):
        self.fmin = librosa.note_to_hz(note_min)
        self.fmax = librosa.note_to_hz(note_max)
        self.hop_length = hop_length
        self.frame_size = frame_size
        self.raga_map = np.array(raga_map) if raga_map else None
        self.sr = sr
        self.root = librosa.note_to_midi(root)
        self.m = outlier_coeff
        self.empty_arr = np.array([])
        # Schlüter, Jan, and Sebastian Böck. "Improved musical onset detection with convolutional neural networks." 2014 ieee international conference on acoustics, speech and signal processing (icassp). IEEE, 2014.
        self.onset_processor = madmom.features.CNNOnsetProcessor()

    def convert(self, y, return_onsets=False, velocity=100):
        f0, voiced_flag, voiced_prob = librosa.pyin(y, fmin=self.fmin * 0.9, fmax=self.fmax * 1.1, sr=self.sr,
                                                    frame_length=self.frame_size, hop_length=self.hop_length)
        if len(f0) == 0:
            print("No f0")
            if return_onsets:
                return self.empty_arr, self.empty_arr
            return self.empty_arr

        pitch = librosa.hz_to_midi(f0)
        pitch[np.isnan(pitch)] = 0
        onsets = self.get_onsets(y)  # There is at-least one onset at [0]
        print(onsets)
        notes = np.zeros(len(onsets), dtype=int)
        for i in range(len(onsets) - 1):
            notes[i] = np.round(np.nanmedian(pitch[onsets[i]: onsets[i + 1]]))
        notes[-1] = np.round(np.nanmedian(pitch[onsets[-1]:]))

        onsets = onsets[notes > 0] * self.hop_length / self.sr
        notes = notes[notes > 0]

        if len(notes) > 0:
            if self.raga_map is not None:
                notes = self.filter_raga(notes)
            notes = self.fix_outliers(notes, m=self.m)
        # bpm = self.get_tempo(y)

        temp = []
        for i in range(len(notes)):
            temp.append(Note(velocity, notes[i], start=onsets[i], end=onsets[i] + 0.1))

        if return_onsets:
            return temp, onsets

        return temp

    def filter_raga(self, _notes):
        filtered_notes = _notes.copy()
        _n = _notes - self.root
        code = (_n + 12) % 12
        # filtered_notes += self.raga_map[code] - code              # when raga_map is an index map
        filtered_notes = filtered_notes[self.raga_map[code] == 1]  # when raga_map is 1, 0
        return filtered_notes

    def get_onsets(self, y, threshold: float = 0.35, pre_max: int = 3, post_max: int = 3):
        act = self.onset_processor(y)
        # onsets = librosa.onset.onset_detect(y=y, sr=self.sr, hop_length=self.hop_length)
        # onsets = np.hstack([0, onsets])

        onsets = madmom.features.onsets.peak_picking(activations=act, threshold=threshold, pre_max=pre_max,
                                                     post_max=post_max)
        return np.unique(np.hstack([0, onsets]))
        # return np.unique(onsets)

    @staticmethod
    def fix_outliers(arr, m=2):
        arr_mean = np.mean(arr)
        arr_std = m * np.std(arr)
        for _i in range(len(arr)):
            n = arr[_i]
            if np.abs(n - arr_mean) > arr_std:
                arr[_i] = AudioMidiConverter.shift_octave(arr[_i], arr_mean)
        return arr

    @staticmethod
    def shift_octave(val, ref):
        x = (ref - val) // 6
        res = x % 2
        x = x // 2
        return val + ((x + res) * 12)

    @staticmethod
    def get_tempo(y):
        return librosa.beat.tempo(y=y)[0]
