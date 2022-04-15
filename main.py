"""
Author: Raghavasimhan Sankaranarayanan
Date: 04/08/2022
"""
from midiDevice import MidiOutDevice, MidiInDevice
from rtmidi.midiconstants import NOTE_ON
import time
from demos import Demo, BeatDetectionDemo, QnADemo, SongDemo
from gestureController import GestureController


class ShimonDemo:
    def __init__(self, keyboard_name, shimon_port_name, qna_param, bd_param, song_param, gesture_param):
        self.gesture_controller = GestureController(**gesture_param)
        self.shimon_port = MidiOutDevice(shimon_port_name)
        self.qna_demo = None
        try:
            self.qna_demo = QnADemo(gesture_controller=self.gesture_controller, shimon_port=self.shimon_port, **qna_param)
        except AssertionError:
            self.gesture_controller.reset()
            exit()

        self.keys = MidiInDevice(keyboard_name, callback_fn=self.keys_callback)
        self.bd_demo = BeatDetectionDemo(gesture_controller=self.gesture_controller,
                                         timeout_callback=self.bd_timeout_callback, **bd_param)
        self.song_demo = SongDemo(gesture_controller=self.gesture_controller, shimon_port=self.shimon_port, complete_callback=self.song_complete_callback, **song_param)
        self.running = False
        self.current_demo = self.qna_demo

    def bd_timeout_callback(self, user_data):
        self.manage_demos()

    def set_current_demo(self, current_demo: Demo):
        self.current_demo = current_demo

    def keys_callback(self, msg, dt, user_data):
        if msg[0] == NOTE_ON:
            if msg[1] == 36 and self.current_demo != self.song_demo:
                self.manage_demos()
            else:
                self.current_demo.handle_midi(msg, dt)

    def song_complete_callback(self, user_data):    # Not Implemented
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
        self.gesture_controller.reset()


# def manage_demos(val, bd_demo: BeatDetectionDemo, qa_demo: QnADemo, song_demo: SongDemo):
#     if val == DemoType.Beat:
#         print("Beat Detection Demo")
#         song_demo.stop()
#         qa_demo.stop()
#         bd_demo.start()
#
#     elif val == DemoType.QnA:
#         print("Q & A Demo")
#         song_demo.stop()
#         bd_demo.stop()
#         qa_demo.start()
#
#     elif val == DemoType.Song:
#         print("Song Demo")
#         bd_demo.stop()
#         qa_demo.stop()
#         tempo = bd_demo.get_tempo()
#         if tempo and tempo > 0:
#             song_demo.set_tempo(tempo)
#         song_demo.start()


if __name__ == '__main__':
    PHRASE_MIDI_FILES = ["phrases/intro.mid", "phrases/phrase_1A.mid", "phrases/phrase_1B.mid", "phrases/phrase_2A.mid", "phrases/phrase_2B.mid", "phrases/phrase_3A.mid", "phrases/phrase_3B.mid", "phrases/korvai.mid"]
    GESTURE_MIDI_FILES = ["gestures/intro.mid", "gestures/gestures_1A.mid", "gestures/gestures_1B.mid", "gestures/gestures_2A.mid", "gestures/gestures_2B.mid", "gestures/gestures_3A.mid", "gestures/gestures_3B.mid", "gestures/korvai.mid"]
    keyboard = "Vivo S1" # "iRig KEYS 37"
    audio_interface = "Line 6 HX Stomp"
    shimon_port = "to Max 1"
    gesture_port = "to Max 2"  # "gestures"
    g_virtual = False

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

    gesture_params = {
        "gesture_note_mapping": gesture_note_mapping,
        "midi_channel": 1,
        "midi_device": gesture_port,
        "virtual": g_virtual
    }

    bd_params = {
        "smoothing": 4,
        "n_beats_to_track": 8,
        "timeout_sec": 5,
        "tempo_range": (60, 120)
    }

    song_params = {
        "midi_files": PHRASE_MIDI_FILES,
        "gesture_midi_files": GESTURE_MIDI_FILES
    }

    # Pass 'None' to not filter audioToMidi by any raga
    bahudari_map = [1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0]
    qna_params = {
        "raga_map": bahudari_map,
        "sr": 16000,
        "frame_size": 256,
        "activation_threshold": 0.01,
        "n_wait": 32,
        "input_dev_name": audio_interface,
        "outlier_filter_coeff": 2,
        "timeout_sec": 1
    }

    # MidiInDevice.list_devices()
    demo = ShimonDemo(keyboard, shimon_port_name=shimon_port, qna_param=qna_params, bd_param=bd_params, song_param=song_params, gesture_param=gesture_params)
    demo.run()
