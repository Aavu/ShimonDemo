"""
Author: Raghavasimhan Sankaranarayanan
Date: 04/08/2022
"""

import rtmidi
from rtmidi import midiutil


class MidiInDevice:
    def __init__(self, name, callback_fn=None, user_data=None):
        self.initialized = False
        self.midi_in = rtmidi.MidiIn(queue_size_limit=1024)
        self.input = None
        self.name = name
        self.callback_fn = callback_fn
        self.user_data = user_data
        if self.name in self.midi_in.get_ports():
            self.input, _ = midiutil.open_midiinput(self.name)
            self.input.ignore_types()
            print(f"Using MIDI In Device: {self.name}")

            self.input.set_callback(self.callback, self)
            self.initialized = True
        else:
            print(f"Warning: MIDI device - {self.name} - not found")
            AssertionError("Midi Device Not found")

    @staticmethod
    def list_devices():
        print(rtmidi.MidiIn().get_ports())

    def reset(self):
        if self.input:
            self.input.close_port()
            self.input.delete()

    def set_callback(self, callback_fn):
        self.callback_fn = callback_fn

    @staticmethod
    def callback(msg, dev):
        dev.callback_fn(msg[0], msg[1], dev.user_data)


class MidiOutDevice:
    def __init__(self, name: str, virtual: bool = False):
        self._initialized = False
        self.midi_out = rtmidi.MidiOut()
        # self.output = None
        self.name = name

        if virtual:
            self.midi_out.open_virtual_port(name)
            print(f"Creating virtual midi device - {name}")
        else:
            ports = self.midi_out.get_ports()
            for i, name in enumerate(ports):
                if self.name == name:
                    self.midi_out.open_port(i)
                    print(f"Using MIDI Out Device: {self.name}")
                    self._initialized = True
                    return

            # Fallback to virtual port
            print(f"Warning: MIDI device - {self.name} - not found")
            self.midi_out.open_virtual_port(self.name)
            print(f"Creating virtual midi device - {self.name}")
        self._initialized = True

    @staticmethod
    def list_devices():
        print(rtmidi.MidiOut().get_ports())

    def reset(self):
        # if self.output:
        #     self.output.close_port()
        #     self.output.delete()
        self.midi_out.close_port()

    def send(self, msg):
        if not self._initialized:
            return
        self.midi_out.send_message(msg)
