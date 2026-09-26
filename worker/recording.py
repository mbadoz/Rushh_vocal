"""Two synchronized mono tracks, written as stereo WAV without Egress."""

import asyncio, time, wave
from pathlib import Path
import numpy as np
from livekit import rtc


class Recorder:
    def __init__(self, key, limit=1800):
        self.rate = 24000
        self.started = time.monotonic()
        self.limit = limit
        self.samples = np.zeros((int((limit + 5) * self.rate), 2), dtype=np.int16)
        self.length = 0
        self.tasks = []
        self.path = Path("data/recordings") / (key + ".wav")

    def attach(self, track, channel):
        self.tasks.append(asyncio.create_task(self.consume(track, channel)))

    async def consume(self, track, channel):
        stream = rtc.AudioStream(track, sample_rate=self.rate, num_channels=1)
        cursor = 0
        try:
            async for event in stream:
                data = np.frombuffer(event.frame.data, dtype=np.int16)
                cursor = max(
                    cursor,
                    int((time.monotonic() - self.started) * self.rate) - len(data),
                )
                end = min(len(self.samples), cursor + len(data))
                if end > cursor:
                    self.samples[cursor:end, channel] = data[: end - cursor]
                cursor = end
                self.length = max(self.length, end)
        finally:
            await stream.aclose()

    async def finish(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(self.path), "wb") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(self.rate)
            f.writeframes(self.samples[: self.length].tobytes())
        return self.path
