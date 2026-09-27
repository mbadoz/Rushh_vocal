"""Decide when a short acknowledgement belongs in an ongoing user turn."""

import random
import re
import time


def long_segment(text: str, duration: float) -> bool:
    # Streaming STT may withhold text until VAD has already seen the pause.
    words = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", text))
    return words >= 18 or duration >= 6.0


class BackchannelGate:
    def __init__(self):
        self.speech_started = None
        self.pause_started = None
        self.previous_was_long = False
        self.transcript = ""
        self.last_acknowledgement = float("-inf")

    def on_transcript(self, text: str) -> None:
        if len(text) > len(self.transcript):
            self.transcript = text
        if self.pause_started is not None and self.speech_started is not None:
            self.previous_was_long |= long_segment(
                self.transcript, self.pause_started - self.speech_started
            )

    def on_state(self, old: str, new: str, frequency: float, *, now=None, rng=None) -> bool:
        now = time.monotonic() if now is None else now
        rng = random.random if rng is None else rng

        if new == "speaking":
            short_pause = (
                old == "listening"
                and self.pause_started is not None
                and 0 <= now - self.pause_started <= 1.8
            )
            acknowledge = (
                short_pause
                and self.previous_was_long
                and now - self.last_acknowledgement >= 8
                and rng() < frequency
            )
            self.speech_started = now
            self.pause_started = None
            self.previous_was_long = False
            self.transcript = ""
            if acknowledge:
                self.last_acknowledgement = now
            return acknowledge

        if old == "speaking" and new == "listening" and self.speech_started is not None:
            self.pause_started = now
            self.previous_was_long = long_segment(
                self.transcript, now - self.speech_started
            )
        return False
