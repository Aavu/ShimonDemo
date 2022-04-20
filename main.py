"""
Author: Raghavasimhan Sankaranarayanan
Date: 04/08/2022
"""
from midiDevice import MidiInDevice
from rtmidi.midiconstants import NOTE_ON
import time
from demos import Performer, Demo, BeatDetectionDemo, QnADemo, SongDemo


class ShimonDemo:
    def __init__(self, keyboard_name, mode_key, qna_param, bd_param, song_param, performer_param):
        self.mode_key = mode_key
        self.performer = Performer(ticks=480, **performer_param)
        self.qna_demo = QnADemo(performer=self.performer, **qna_param)

        self.keys = MidiInDevice(keyboard_name, callback_fn=self.keys_callback)
        self.bd_demo = BeatDetectionDemo(performer=self.performer, timeout_callback=self.bd_timeout_callback, **bd_param)
        self.song_demo = SongDemo(performer=self.performer, complete_callback=self.song_complete_callback, **song_param)
        self.running = False
        self.current_demo = self.qna_demo

    def bd_timeout_callback(self, user_data):
        self.manage_demos()

    def set_current_demo(self, current_demo: Demo):
        self.current_demo = current_demo

    def keys_callback(self, msg, dt, user_data):
        if msg[0] == NOTE_ON:
            if msg[1] == self.mode_key and self.current_demo != self.song_demo:
                self.manage_demos()
            else:
                self.current_demo.handle_midi(msg, dt)

    def song_complete_callback(self, user_data):  # Not Implemented
        self.stop()

    def manage_demos(self):
        self.current_demo.stop()
        if self.current_demo == self.qna_demo:
            self.current_demo = self.bd_demo
            print("Beat detection demo")
        elif self.current_demo == self.bd_demo:
            print("Song demo")
            tempo = self.bd_demo.get_tempo()
            if tempo and tempo > 0:
                self.song_demo.set_tempo(tempo)
            self.current_demo = self.song_demo
        self.current_demo.start()

    def run(self):
        self.running = True
        self.current_demo.start()
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.reset()

    def stop(self):
        self.running = False
        if self.qna_demo:
            self.qna_demo.stop()
        self.bd_demo.stop()
        self.song_demo.stop()

    def reset(self):
        self.stop()
        self.keys.reset()


if __name__ == '__main__':
    PHRASE_MIDI_FILES = [["phrases/intro.mid"], ["phrases/phrase_1A.mid", "phrases/phrase_1B.mid"],
                         ["phrases/phrase_2A.mid", "phrases/phrase_2B.mid"],
                         ["phrases/phrase_3A.mid", "phrases/phrase_3B.mid"], ["phrases/korvai.mid"]]
    GESTURE_MIDI_FILES = [["gestures/intro.mid"], ["gestures/gestures_1A.mid", "gestures/gestures_1B.mid"],
                          ["gestures/gestures_2A.mid", "gestures/gestures_2B.mid"],
                          ["gestures/gestures_3A.mid", "gestures/gestures_3B.mid"], ["gestures/korvai.mid"]]
    keyboard = "iRig KEYS 37"  # "iRig KEYS 37", "Vivo S1"
    audio_interface = "HX Stomp"     # "HX Stomp", "Line 6 HX Stomp"

    mode_key = 98

    gesture_note_mapping = {
        "beatOnce": 50,
        "breath": 51,
        "look": 52,
        "circle": 53,
        "nodsway": 54,
        "ar_sway": 55,
        "eyebrows": 56,
        "headcircle": 57,
        "cooldown": 58,
        "scream": 59,
        "headcirclefast": 60
    }

    performer_params = {
        "osc_address": "127.0.0.1",
        "osc_port": 20000,
        "gesture_note_mapping": gesture_note_mapping,
        "osc_arm_route": "/arm",
        "osc_head_route": "/head",
        "min_note_dist_ms": 50,
        "max_notes_per_onset": 4
    }

    bd_params = {
        "smoothing": 4,
        "n_beats_to_track": 8,
        "timeout_sec": 2,
        "tempo_range": (60, 120)
    }

    song_params = {
        "midi_files": PHRASE_MIDI_FILES,
        "gesture_midi_files": GESTURE_MIDI_FILES,
        "start_note_for_phrase_mapping": 96
    }

    # Pass 'None' to not filter audioToMidi by any raga
    bahudari_map = [1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0]
    qna_params = {
        "raga_map": bahudari_map,
        "sr": 16000,
        "frame_size": 2048,
        "activation_threshold": 0.01,
        "n_wait": 4,
        "input_dev_name": audio_interface,
        "outlier_filter_coeff": 2,
        "timeout_sec": 0.5
    }

    # MidiInDevice.list_devices()
    demo = ShimonDemo(keyboard, mode_key=mode_key, qna_param=qna_params,
                      bd_param=bd_params, song_param=song_params, performer_param=performer_params)
    demo.run()
