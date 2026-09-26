"""Preserve protobuf request semantics while extending Google TTS per instance."""

from google.protobuf.json_format import MessageToDict
from google.cloud import texttospeech
from .providers import merge


def as_dict(message):
    return MessageToDict(type(message).pb(message), preserving_proto_field_name=True)


class TTSClientProxy:
    def __init__(self, client, raw):
        self.client = client
        self.raw = raw

    def __getattr__(self, name):
        return getattr(self.client, name)

    async def synthesize_speech(self, **kwargs):
        timeout = kwargs.pop("timeout", None)
        payload = {k: as_dict(v) for k, v in kwargs.items()}
        request = texttospeech.SynthesizeSpeechRequest(**merge(payload, self.raw))
        return await self.client.synthesize_speech(request=request, timeout=timeout)

    async def streaming_synthesize(self, requests, **kwargs):
        async def transformed():
            async for request in requests:
                value = as_dict(request)
                if "streaming_config" in value:
                    yield texttospeech.StreamingSynthesizeRequest(
                        **merge(value, {"streaming_config": self.raw})
                    )
                else:
                    yield request

        return await self.client.streaming_synthesize(transformed(), **kwargs)
