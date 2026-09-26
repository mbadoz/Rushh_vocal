"""Speechmatics v2 transport, keeping legacy model and full API configuration explicit.

The bundled plugin uses /v2/agent and silently substitutes linden-1. This adapter
uses /v2 instead, where standard/enhanced and max_delay belong.
"""

import asyncio, json
from livekit import rtc
from livekit.agents import (
    stt,
    DEFAULT_API_CONNECT_OPTIONS,
    APIConnectionError,
)
from .providers import merge
import aiohttp


class STT(stt.STT):
    def __init__(
        self,
        *,
        api_key,
        model="enhanced",
        language="fr",
        sample_rate=16000,
        raw=None,
        **params,
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=True, interim_results=True)
        )
        self.key = api_key
        self.sample_rate = sample_rate
        aliases = {"include_partials": "enable_partials"}
        config = {aliases.get(k, k): v for k, v in params.items()}
        self.config = merge(
            {
                "message": "StartRecognition",
                "audio_format": {
                    "type": "raw",
                    "encoding": "pcm_s16le",
                    "sample_rate": sample_rate,
                },
                "transcription_config": {
                    "language": language,
                    "operating_point": model,
                    "enable_partials": True,
                    **config,
                },
            },
            raw or {},
        )

    def stream(self, *, conn_options=DEFAULT_API_CONNECT_OPTIONS):
        return Stream(self, conn_options)

    async def _recognize_impl(self, buffer, *, conn_options):
        raise NotImplementedError("Streaming uniquement")


class Stream(stt.SpeechStream):
    def __init__(self, owner, options):
        super().__init__(stt=owner, conn_options=options, sample_rate=owner.sample_rate)
        self.owner = owner

    async def _run(self):
        async with aiohttp.ClientSession() as client:
            async with client.ws_connect(
                "wss://eu2.rt.speechmatics.com/v2",
                headers={"Authorization": "Bearer " + self.owner.key},
            ) as ws:
                await ws.send_json(self.owner.config)
                ready = await ws.receive_json()
                if ready.get("message") != "RecognitionStarted":
                    raise APIConnectionError("Speechmatics a refusé la configuration")

                async def send():
                    sequence = 0
                    seconds = 0
                    async for frame in self._input_ch:
                        if isinstance(frame, rtc.AudioFrame):
                            await ws.send_bytes(frame.data.tobytes())
                            sequence += 1
                            seconds += frame.samples_per_channel / frame.sample_rate
                        else:
                            await ws.send_json({"message": "ForceEndOfUtterance"})
                        if seconds >= 1:
                            self._event_ch.send_nowait(
                                stt.SpeechEvent(
                                    type=stt.SpeechEventType.RECOGNITION_USAGE,
                                    recognition_usage=stt.RecognitionUsage(
                                        audio_duration=seconds
                                    ),
                                )
                            )
                            seconds = 0
                    if seconds:
                        self._event_ch.send_nowait(
                            stt.SpeechEvent(
                                type=stt.SpeechEventType.RECOGNITION_USAGE,
                                recognition_usage=stt.RecognitionUsage(
                                    audio_duration=seconds
                                ),
                            )
                        )
                    await ws.send_json(
                        {"message": "EndOfStream", "last_seq_no": sequence}
                    )

                task = asyncio.create_task(send())
                try:
                    async for message in ws:
                        if message.type != aiohttp.WSMsgType.TEXT:
                            continue
                        data = json.loads(message.data)
                        kind = data.get("message")
                        if kind == "Error":
                            raise APIConnectionError(
                                "Erreur de transcription Speechmatics"
                            )
                        if kind == "EndOfTranscript":
                            break
                        if kind in ("AddTranscript", "AddPartialTranscript"):
                            text = data.get("metadata", {}).get("transcript", "")
                            if text:
                                self._event_ch.send_nowait(
                                    stt.SpeechEvent(
                                        type=stt.SpeechEventType.FINAL_TRANSCRIPT
                                        if kind == "AddTranscript"
                                        else stt.SpeechEventType.INTERIM_TRANSCRIPT,
                                        alternatives=[
                                            stt.SpeechData(
                                                language=self.owner.config[
                                                    "transcription_config"
                                                ]["language"],
                                                text=text,
                                            )
                                        ],
                                    )
                                )
                        if kind == "EndOfUtterance":
                            self._event_ch.send_nowait(
                                stt.SpeechEvent(type=stt.SpeechEventType.END_OF_SPEECH)
                            )
                finally:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
