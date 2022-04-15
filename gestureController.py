import rtmidi
import numpy as np
from midiDevice import MidiOutDevice
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON


class GestureController:
    def __init__(self, gesture_note_mapping: dict[str, int], midi_device: str = "to Max 2", midi_channel: int = 1, virtual=False):
        self.gesture_note_map = gesture_note_mapping
        self.ch = min(max(1, midi_channel), 16)
        self.midi_device = MidiOutDevice(midi_device, virtual=virtual)

    def send(self, gesture, velocity: int):
        note = self.gesture_note_map.get(gesture) if type(gesture) == str else gesture
        velocity = max(min(127, velocity), 0)
        if note is None:
            print("Warning: gesture not in library")
            return

        msg_type = (self.ch - 1) + (NOTE_ON if velocity > 0 else NOTE_OFF)
        print((self.ch - 1), msg_type, note, velocity)
        self.midi_device.send([msg_type, note, velocity])

    def reset(self):
        self.midi_device.reset()
