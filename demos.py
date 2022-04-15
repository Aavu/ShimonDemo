"""
Author: Raghavasimhan Sankaranarayanan
Date: 04/08/2022
"""
import os.path
from copy import copy

import pretty_midi
from pretty_midi import Note
import pyaudio
from midiDevice import MidiOutDevice
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON
from audioToMidi import AudioMidiConverter
from audioDevice import AudioDevice
from tempoTracker import TempoTracker
from gestureController import GestureController
import numpy as np
from threading import Thread, Lock, Event
import time
import threading
from queue import Queue


class Phrase:
    def __init__(self, notes, onsets, tempo=None, name=None):
        self.name = name
        self.notes = notes
        self.onsets = onsets
        self.tempo = tempo
        self.is_korvai = name == "korvai"
        self.is_intro = name == "intro"

    def get(self):
        return self.notes, self.onsets

    def __len__(self):
        return len(self.notes)


class Performer:
    def __init__(self, device, tempo=None, ticks=None, gesture_controller=None):
        self.tempo = tempo
        self.device = device
        self.gesture_controller = gesture_controller
        self.ticks = ticks
        self.note_on_thread = Thread()
        self.note_off_thread = Thread()
        self.stop_event = threading.Event()
        self.timer = None

    def perform_gestures(self, gestures: Phrase, tempo=None, wait_for_measure_end=False):
        self.note_on_thread = Thread(target=self.handle_note_ons, args=(gestures.notes, tempo))
        self.note_off_thread = Thread(target=self.handle_note_offs, args=(gestures.notes, tempo))
        if self.timer and self.timer.is_alive():
            self.timer.join()
        self.stop_event.set()
        self.timer = threading.Timer(0.5, self.delay_start_thread)
        self.timer.start()

    def delay_start_thread(self):
        if self.note_on_thread.is_alive():
            self.note_on_thread.join()
        if self.note_off_thread.is_alive():
            self.note_off_thread.join()
        self.stop_event.clear()
        self.note_on_thread.start()
        self.note_off_thread.start()

    def handle_note_ons(self, notes: [Note], tempo: int):
        m = 1
        if tempo and self.tempo:
            m = self.tempo / tempo

        prev_start = 0
        now = time.time()
        for note in notes:
            if self.stop_event.is_set():
                return
            dly = max(0, ((note.start - prev_start) * m) - (time.time() - now))
            self.stop_event.wait(dly)
            # time.sleep(dly)
            now = time.time()
            self.gesture_controller.send(note.pitch, note.velocity)
            prev_start = note.start

    def handle_note_offs(self, notes: [Note], tempo: int):
        m = 1
        if tempo and self.tempo:
            m = self.tempo / tempo

        prev_end = 0
        now = time.time()
        for note in notes:
            if self.stop_event.is_set():
                return
            dly = max(0, ((note.end - prev_end) * m) - (time.time() - now))
            self.stop_event.wait(dly)
            # time.sleep(dly)
            now = time.time()
            self.gesture_controller.send(note.pitch, 0)
            prev_end = note.end

    def test_perform(self, gestures: Phrase, tempo=None, wait_for_measure_end=False):
        self.perform_gestures(gestures=gestures, tempo=tempo, wait_for_measure_end=wait_for_measure_end)
        self.note_on_thread.join()
        self.note_off_thread.join()

    def perform(self, phrase: Phrase, gestures: Phrase or None, tempo=None, wait_for_measure_end=False):
        notes, onsets = phrase.get()
        m = 1
        if self.tempo and tempo:
            m = self.tempo / tempo
        i = 0

        if gestures is not None:
            self.perform_gestures(gestures=gestures, tempo=tempo, wait_for_measure_end=wait_for_measure_end)
        while i < len(notes):
            poly_notes = []
            poly_onsets = []
            while i < len(onsets):
                if len(poly_notes) > 0 and poly_onsets[-1] == onsets[i]:
                    poly_notes.append(notes[i])
                    poly_onsets.append(onsets[i])
                    i += 1
                elif len(poly_notes) == 0 and i < len(notes) - 1 and onsets[i] == onsets[i + 1]:
                    poly_notes.append(notes[i])
                    poly_notes.append(notes[i + 1])
                    poly_onsets.append(onsets[i])
                    poly_onsets.append(onsets[i + 1])
                    i += 2
                else:
                    break

            duration = 0
            if len(poly_notes) > 0:
                if i < len(notes):
                    duration = notes[i].start - poly_notes[0].start
                for j in range(len(poly_notes)):
                    note_on = [NOTE_ON, poly_notes[j].pitch, poly_notes[j].velocity]
                    note_off = [NOTE_OFF, poly_notes[j].pitch, 0]
                    self.device.send(note_on)
                    self.device.send(note_off)
            else:
                if i < len(notes) - 1:
                    duration = notes[i + 1].start - notes[i].start
                note_on = [NOTE_ON, notes[i].pitch, notes[i].velocity]
                note_off = [NOTE_OFF, notes[i].pitch, 0]
                self.device.send(note_on)
                self.device.send(note_off)
                i += 1

            time.sleep(duration * m)

        if wait_for_measure_end and tempo and self.ticks:
            self.wait_for_measure_end(onsets, tempo)

        # if gestures is not None:
        #     self.note_on_thread.join(0.1)
        #     self.note_off_thread.join(0.1)

    def wait_for_measure_end(self, onsets, tempo):
        # Assume 4/4
        bar_tick = self.ticks * 4
        # measure_tick = bar_tick * 4
        while bar_tick < onsets[-1]:
            bar_tick += bar_tick
        remaining_ticks = bar_tick - onsets[-1]
        print(remaining_ticks, bar_tick, onsets[-1])
        if remaining_ticks > 0:
            time.sleep(remaining_ticks * 60 / (tempo * self.ticks))


class Demo:
    def __init__(self):
        pass


class QnADemo(Demo):
    def __init__(self, gesture_controller: GestureController, raga_map, shimon_port: MidiOutDevice, sr=16000, frame_size=256,
                 activation_threshold=0.02, n_wait=16, input_dev_name='Line 6 HX Stomp', outlier_filter_coeff=2,
                 timeout_sec=2):
        super().__init__()
        self.active = False

        self.gesture_controller = gesture_controller
        self.activation_threshold = activation_threshold
        self.n_wait = n_wait
        self.wait_count = 0
        self.playing = False
        self.phrase = []
        self.midi_notes = []
        self.midi_onsets = []

        self.process_thread = Thread()
        self.event = Event()
        self.lock = Lock()

        self._midi_out_device = shimon_port     # MidiOutDevice("Q&A output", virtual=True)

        self.audioDevice = AudioDevice(self.callback_fn, rate=sr, frame_size=frame_size, input_dev_name=input_dev_name,
                                       channels=4)
        self.audio2midi = AudioMidiConverter(raga_map=raga_map, sr=sr, frame_size=frame_size,
                                             outlier_coeff=outlier_filter_coeff)
        self.audioDevice.start()

        self.current_inst = 0  # 0 : violin, 1: keys
        self.timeout = timeout_sec
        self.last_time = time.time()
        self.performer = Performer(self._midi_out_device, None)

    def reset_var(self):
        self.wait_count = 0
        self.playing = False
        self.phrase = []
        self.last_time = time.time()

    def handle_midi(self, msg, dt):
        if self.current_inst != 1:
            print("Its violin's turn")
            return

        if msg[0] == NOTE_ON:
            self.last_time = time.time()
            note = pretty_midi.Note(msg[2], msg[1], self.last_time, self.last_time + 0.1)
            self.midi_notes.append(note)
            self.midi_onsets.append(self.last_time)

    def callback_fn(self, in_data: bytes, frame_count: int, time_info: dict[str, float], status: int) -> tuple[
        bytes, int]:
        if not self.active:
            self.reset_var()
            return in_data, pyaudio.paContinue

        y = np.frombuffer(in_data, dtype=np.int16)
        y = y[::2][1::2]  # Get all the even indices then get all odd indices for ch-3 of HX Stomp
        y = self.int16_to_float(y)
        activation = np.abs(y).mean()
        if activation > self.activation_threshold:
            print(activation)
            if self.current_inst != 0:
                print("Its keyboard's turn")
                self.reset_var()
                return in_data, pyaudio.paContinue
            self.playing = True
            self.wait_count = 0
            self.lock.acquire()
            self.phrase.append(y)
            self.lock.release()
        else:
            if self.wait_count > self.n_wait:
                self.playing = False
                self.wait_count = 0
            else:
                self.lock.acquire()
                if self.playing:
                    self.phrase.append(y)
                self.lock.release()
                self.wait_count += 1
        return in_data, pyaudio.paContinue

    def reset(self):
        self.stop()
        self.audioDevice.reset()

    @staticmethod
    def int16_to_float(x):
        return x / (1 << 15)

    # @staticmethod
    # def to_float(x):
    #     if x.dtype == 'float32':
    #         return x
    #     elif x.dtype == 'uint8':
    #         return (x / 128.) - 1
    #     else:
    #         bits = x.dtype.itemsize * 8
    #         return x / (2 ** (bits - 1))

    def start(self):
        self.reset_var()
        if self.process_thread.is_alive():
            self.process_thread.join()
        self.lock.acquire()
        self.active = True
        self.lock.release()
        self.process_thread = Thread(target=self._process)
        self.process_thread.start()
        self.event.clear()
        self.check_timeout()

    def _process(self):
        while True:
            time.sleep(0.1)
            self.lock.acquire()
            if not self.active:
                self.lock.release()
                return

            if not (self.playing or len(self.phrase) == 0):
                self.lock.release()
                break
            self.lock.release()

        self.lock.acquire()
        phrase = np.hstack(self.phrase)
        self.phrase = []
        self.lock.release()

        if len(phrase) > 0:
            notes, onsets = self.audio2midi.convert(phrase, return_onsets=True)
            print("notes:", notes)  # Send to shimon
            print("onsets:", onsets)
            phrase = Phrase(notes, onsets)
            self.perform(phrase)

        self._process()

    def stop(self):
        self.lock.acquire()
        self.active = False
        self.lock.release()
        if self.process_thread.is_alive():
            self.process_thread.join()
        self.audioDevice.stop()
        self.event.set()

    def perform(self, phrase):
        self.current_inst ^= 1
        self.gesture_controller.send(gesture="look", velocity=3)  # Look straight
        self.gesture_controller.send(gesture="headcircle", velocity=80)
        # threading.Timer(0.5, self.gesture_controller.send, kwargs={"gesture": "headcircle", "velocity": 80}).start()
        # time.sleep(0.5)     # Shimon hardware wait simulation
        self.performer.perform(phrase=phrase, gestures=None)
        self.gesture_controller.send(gesture="headcircle", velocity=0)
        self.gesture_controller.send(gesture="look", velocity=self.current_inst + 1)  # Look at the respective artist

    def process_midi_phrase(self, phrase):
        n_notes_to_change = np.random.randint(0, len(phrase), 1)
        indices = np.random.choice(np.arange(len(phrase)), n_notes_to_change, replace=False)
        for i in indices:
            phrase.notes[i].pitch += np.random.randint(-12, 12, 1)
        self.perform(phrase)

    def check_timeout(self):
        if time.time() - self.last_time > self.timeout and len(self.midi_notes) > 0:
            midi_notes = copy(self.midi_notes)
            midi_onsets = copy(self.midi_onsets)
            self.midi_notes = []
            self.midi_onsets = []
            t = midi_notes[0].start
            for i in range(len(midi_notes)):
                midi_notes[i].start -= t
                midi_notes[i].end -= t
                midi_onsets[i] -= t

            phrase = Phrase(midi_notes, midi_onsets)
            self.process_midi_phrase(phrase)

        if not self.event.is_set():
            threading.Timer(1, self.check_timeout).start()


class BeatDetectionDemo(Demo):
    def __init__(self, gesture_controller: GestureController, tempo_range: tuple= (60, 120), smoothing=4, n_beats_to_track=16, timeout_sec=5,
                 timeout_callback=None, user_data=None):
        super().__init__()
        self.gesture_controller = gesture_controller
        self.timeout_callback = timeout_callback
        self.user_data = user_data
        self.tempo_tracker = TempoTracker(smoothing=smoothing, n_beats_to_track=n_beats_to_track, tempo_range=tempo_range,
                                          timeout_sec=timeout_sec, timeout_callback=self.timeout_handle)
        self._event = threading.Event()
        self._first_time = True
        self._last_time = time.time()
        self._beat_interval = -1

    def start(self):
        self._first_time = True
        self.tempo_tracker.start()
        self._event.clear()

    def stop(self):
        self.tempo_tracker.stop()
        self._event.set()
        self._first_time = True

    def reset(self):
        self.stop()

    def handle_midi(self, msg, dt):
        self.update_tempo(msg, dt)

    def update_tempo(self, msg, dt):
        if msg[0] == NOTE_ON:
            tempo = self.tempo_tracker.track_tempo(msg, dt)
            if tempo:
                print(tempo)
                self.set_beat_interval(tempo)
                if self._first_time:
                    self.gesture_ctl()
                    self._first_time = False

    def set_beat_interval(self, tempo: float):
        self._beat_interval = 60 / tempo

    def get_tempo(self):
        return self.tempo_tracker.tempo

    def timeout_handle(self):
        self.timeout_callback(self.user_data)

    def gesture_ctl(self):
        self.gesture_controller.send("beatOnce", 80)
        if not self._event.is_set():
            threading.Timer(self._beat_interval, self.gesture_ctl).start()


class SongDemo(Demo):
    def __init__(self, gesture_controller, midi_files: [str], gesture_midi_files: [str], shimon_port: MidiOutDevice,
                 start_note_for_phrase_mapping: int = 36, complete_callback=None, user_data=None):
        super().__init__()
        self.gesture_ctl = gesture_controller
        self.phrase_note_map = start_note_for_phrase_mapping
        self.user_data = user_data
        self.phrases = self._parse_midi(midi_files)
        self.g_phrases = self._parse_midi(gesture_midi_files)
        self.file_tempo = self.phrases[0].tempo
        self.ticks = 480
        self.tempo = self.file_tempo
        self.playing = False
        self.thread = Thread()
        self.lock = Lock()
        self.callback_queue = Queue(1)
        self.callback_queue.put(complete_callback)
        self.next_phrase = self.phrases[0]  # intro phrase
        self.next_g_phrase = self.g_phrases[0]  # intro gesture
        self._midi_out_device = shimon_port
        self.performer = Performer(self._midi_out_device, self.file_tempo, self.ticks, self.gesture_ctl)

    def __del__(self):
        self.reset()

    def set_tempo(self, tempo):
        self.tempo = tempo

    def start(self):
        self.playing = True
        self.thread = Thread(target=self.perform, args=(self.next_phrase, self.next_g_phrase))
        self.thread.start()

    def stop(self):
        self.lock.acquire()
        self.playing = False
        self.lock.release()

    def handle_midi(self, msg, dt):
        if msg[0] == NOTE_ON:
            # print(msg)
            self.set_phrase((msg[1] - self.phrase_note_map))

    def set_phrase(self, idx):
        if len(self.phrases) > idx >= 0:
            self.next_phrase = self.phrases[idx]
            self.next_g_phrase = self.g_phrases[idx]
            print(self.next_phrase.name)

    def perform(self, phrase: Phrase or None, gestures: Phrase or None):
        if phrase.is_korvai:
            self.next_phrase = None
            self.next_g_phrase = None

        if phrase.is_intro and len(self.phrases) > 1:
            self.next_phrase = self.phrases[1]
            self.next_g_phrase = self.g_phrases[1]

        # self.performer.test_perform(phrase=phrase, tempo=self.tempo, wait_for_measure_end=True)
        self.performer.perform(phrase, gestures, self.tempo, wait_for_measure_end=True)

        if self.next_phrase and self.next_g_phrase:
            self.perform(phrase=self.next_phrase, gestures=self.next_g_phrase)

    def wait(self):
        if self.thread.is_alive():
            self.thread.join()

    def _parse_midi(self, midi_files):
        if not midi_files:
            return None

        def note_sort(_note):
            return _note.start

        phrases = []

        for midi_file in midi_files:
            name = os.path.splitext(os.path.split(midi_file)[-1])[0]
            midi_data = pretty_midi.PrettyMIDI(midi_file)
            self.ticks = midi_data.resolution
            notes = sorted(midi_data.instruments[0].notes, key=note_sort)
            onsets = []
            for note in notes:
                onsets.append(midi_data.time_to_tick(note.start))

            # print(name)
            # print(notes)
            # print(onsets)
            # print()

            phrases.append(Phrase(notes, onsets, round(midi_data.get_tempo_changes()[1][0], 3), name))
        return phrases

    def reset(self):
        self.stop()
        self.wait()
