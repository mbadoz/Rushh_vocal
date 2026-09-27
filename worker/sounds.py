"""Bring LiveKit's quiet ambience clips to a useful, consistent listening level."""

import numpy as np
from livekit import rtc
from livekit.agents import BuiltinAudioClip
from livekit.agents.utils.audio import audio_frames_from_file


AMBIENCE = {
    "office": (BuiltinAudioClip.OFFICE_AMBIENCE, 35.0),
    "city": (BuiltinAudioClip.CITY_AMBIENCE, 3.0),
    "forest": (BuiltinAudioClip.FOREST_AMBIENCE, 14.0),
    "crowd": (BuiltinAudioClip.CROWDED_ROOM, 1.3),
}


def amplify(frame: rtc.AudioFrame, gain: float) -> rtc.AudioFrame:
    samples = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32)
    samples *= gain
    np.clip(samples, -32768, 32767, out=samples)
    return rtc.AudioFrame(
        data=samples.astype(np.int16).tobytes(),
        sample_rate=frame.sample_rate,
        num_channels=frame.num_channels,
        samples_per_channel=frame.samples_per_channel,
    )


async def ambient_frames(name: str, volume: float):
    clip, boost = AMBIENCE[name]
    while True:
        source = audio_frames_from_file(clip.path())
        try:
            async for frame in source:
                yield amplify(frame, boost * volume)
        finally:
            await source.aclose()
