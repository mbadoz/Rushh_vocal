"""Decide when a short acknowledgement belongs in an ongoing user turn."""

import random
import re
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class BackchannelSettings:
    probability: float
    min_words: int
    min_duration: float
    max_pause: float
    cooldown: float

    @classmethod
    def from_slider(cls, value: float) -> "BackchannelSettings":
        value = max(0.0, min(1.0, float(value)))
        if value <= 0.3:
            return cls(value / 0.3, 18, 6.0, 1.8, 8.0)
        progress = (value - 0.3) / 0.7
        return cls(
            1.0,
            round(18 - 12 * progress),
            6.0 - 4.0 * progress,
            1.8 + 0.7 * progress,
            8.0 - 5.8 * progress,
        )


def long_segment(text: str, duration: float, settings: BackchannelSettings) -> bool:
    # Streaming STT may withhold text until VAD has already seen the pause.
    words = len(re.findall(r"\b[\wÀ-ÿ'-]+\b", text))
    return words >= settings.min_words or duration >= settings.min_duration


class BackchannelGate:
    def __init__(self):
        self.speech_started = None
        self.pause_started = None
        self.previous_was_long = False
        self.transcript = ""
        self.last_acknowledgement = float("-inf")
        self.settings = BackchannelSettings.from_slider(0)

    def on_transcript(self, text: str) -> None:
        if len(text) > len(self.transcript):
            self.transcript = text
        if self.pause_started is not None and self.speech_started is not None:
            self.previous_was_long |= long_segment(
                self.transcript, self.pause_started - self.speech_started, self.settings
            )

    def on_state(self, old: str, new: str, frequency: float, *, now=None, rng=None) -> bool:
        now = time.monotonic() if now is None else now
        rng = random.random if rng is None else rng
        self.settings = BackchannelSettings.from_slider(frequency)

        if new == "speaking":
            short_pause = (
                old == "listening"
                and self.pause_started is not None
                and 0 <= now - self.pause_started <= self.settings.max_pause
            )
            acknowledge = (
                short_pause
                and self.previous_was_long
                and now - self.last_acknowledgement >= self.settings.cooldown
                and rng() < self.settings.probability
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
                self.transcript, now - self.speech_started, self.settings
            )
        return False
