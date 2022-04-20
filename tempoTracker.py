import time
import numpy as np
import threading


class TempoTracker:
    def __init__(self, n_beats_to_track=8, smoothing=5, timeout_sec=5, timeout_callback=None, tempo_range=(60, 120), default_tempo=80):
        self.smoothing = smoothing
        self.timeout = timeout_sec
        self.history = None
        self.idx = 0
        self.tempo = default_tempo
        self.num_out = 0
        self.last_time = time.time()
        self.first_time = True
        self.active = False
        self.timeout_callback = timeout_callback
        self.tempo_range = tempo_range

        self.n_beats = n_beats_to_track
        self.event = threading.Event()
        self.reset_vars()

    def track_tempo(self, note_on_msg, dt):
        if not self.active:
            self.reset_vars()
            return None

        if self.first_time:
            self.last_time = time.time()
            self.first_time = False

        new_time = time.time() - self.last_time
        if new_time < 100e-3:
            return None

        self.last_time = time.time()
        self.history[self.idx] = self.wrap_tempo(60/new_time)

        self.idx = (self.idx + 1) % len(self.history)
        if self.num_out > 3:
            t = np.nanmean(self.history)
            if self.num_out < self.n_beats:
                self.tempo = t
        self.num_out += 1

        return self.tempo

    def wrap_tempo(self, tempo):
        min_bpm, max_bpm = self.tempo_range
        if min_bpm <= tempo < max_bpm:
            return tempo

        while max_bpm <= tempo:
            tempo = tempo / 2

        while min_bpm > tempo:
            tempo = tempo * 2

        if min_bpm <= tempo < max_bpm:
            return tempo

        print(f"tempo ({tempo}) out of range ({self.tempo_range})")
        return None

    def reset_vars(self):
        self.history = np.zeros(self.smoothing, dtype=float)
        self.idx = 0
        self.num_out = 0
        self.last_time = time.time()
        self.first_time = True

    def start(self):
        self.active = True
        self.event.clear()
        self.check_timeout()

    def stop(self):
        self.active = False
        self.event.set()

    def check_timeout(self):
        if time.time() - self.last_time > self.timeout and not self.first_time:
            print("timeout")
            self.stop()
            if self.timeout_callback is not None:
                self.timeout_callback()

        if not self.event.is_set():
            threading.Timer(1, self.check_timeout).start()
