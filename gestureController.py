import rtmidi
import numpy as np
from midiDevice import MidiOutDevice
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON
from pythonosc import udp_client


class GestureController:
    def __init__(self, client: udp_client.SimpleUDPClient, gesture_note_mapping: dict[str, int], osc_head_route: str):
        self.gesture_note_map = gesture_note_mapping
        self.osc_head_route = osc_head_route
        self.client = client

    def send_gesture(self, gesture, velocity: int):
        note = self.gesture_note_map.get(gesture) if type(gesture) == str else gesture
        if note is None:
            print("Warning: gesture not in library")
            return

        self.client.send_message(self.osc_head_route, [note, velocity])
