"""
Author: Raghavasimhan Sankaranarayanan
Date: 04/08/2022
"""

import pyaudio
import time


class AudioDevice:
    def __init__(self, callback_fn, rate=16000, frame_size=1024, input_dev_name='Universal Audio Thunderbolt', channels=1):
        self.input_device_id = -1
        self.callback_fn = callback_fn
        self.p = pyaudio.PyAudio()
        self._get_dev_id(input_dev_name)

        if self.input_device_id < 0:
            raise AssertionError("Input device not found")

        self.stream = self.p.open(rate=rate, channels=channels, format=self.p.get_format_from_width(2), input=True,
                                  output=False,
                                  frames_per_buffer=frame_size,
                                  stream_callback=self._callback, input_device_index=self.input_device_id)

    def _get_dev_id(self, input_device_name):
        for i in range(self.p.get_device_count()):
            info = self.p.get_device_info_by_index(i)
            print(info)
            if info['name'] == input_device_name:
                print(f"Found - {input_device_name} with id {i} for Input")
                self.input_device_id = i

    def _callback(self, in_data: bytes, frame_count: int, time_info: dict[str, float], status: int) -> tuple[bytes, int]:
        return self.callback_fn(in_data, frame_count, time_info, status)

    def start(self):
        self.stream.start_stream()

    def stop(self):
        self.stream.stop_stream()

    def reset(self):
        self.stop()
        if self.stream:
            self.stream.close()
        self.p.terminate()
