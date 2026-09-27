import asyncio, json
from copy import deepcopy
from unittest.mock import AsyncMock
import pytest
from api.catalog import CATALOG, DEFAULT
from worker.providers import build, WireSession, SocketProxy, wire_payload
from worker.natural import translate, translated_stream
from worker.telemetry import Collector


@pytest.mark.parametrize(
    "entry",
    [x for x in CATALOG if not (x["provider"] == "google" and x["kind"] == "tts")],
    ids=lambda x: x["id"],
)
def test_catalog_constructs_without_silent_model_substitution(entry):
    async def scenario():
        resources = []
        obj = await build(
            entry["kind"],
            {
                **deepcopy(entry),
                "source": "inference" if entry["provider"] == "livekit" else "env",
                "raw": {},
            },
            {"key": "test-only"},
            resources,
        )
        try:
            if entry["provider"] == "speechmatics":
                assert (
                    obj.config["transcription_config"]["operating_point"]
                    == entry["model"]
                )
            elif hasattr(obj, "_opts") and hasattr(obj._opts, "model"):
                assert obj._opts.model == entry["model"]
        finally:
            await obj.aclose()
            for resource in resources:
                await resource.close()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "param,value",
    [
        ("locale", "fr-CA"),
        ("accent", "french"),
        ("normalization", "off"),
        ("max_buffer_delay_ms", 170),
        ("generation_config", {"speed": 1.4, "volume": 1.7}),
        ("add_phoneme_timestamps", True),
    ],
)
def test_cartesia_final_wire_including_forced_buffer_override(param, value):
    async def scenario():
        ws = AsyncMock()
        session = WireSession(None, "cartesia", "tts", {param: value})
        socket = SocketProxy(ws, session)
        await socket.send_str(
            json.dumps(
                {
                    "model_id": "sonic-3.6",
                    "transcript": "Bonjour",
                    "max_buffer_delay_ms": 0,
                    "generation_config": {"speed": 1.0},
                }
            )
        )
        sent = json.loads(ws.send_str.call_args.args[0])
        assert sent[param] == value
        assert sent["transcript"] == "Bonjour"

    asyncio.run(scenario())


def test_cartesia_integer_speed_is_accepted_by_sonic_3_plugin():
    async def scenario():
        block = deepcopy(DEFAULT["tts"])
        block["params"]["speed"] = 1
        obj = await build("tts", block, {"key": "test-only"}, [])
        try:
            assert obj._opts.speed == 1.0
            assert isinstance(obj._opts.speed, float)
        finally:
            await obj.aclose()

    asyncio.run(scenario())


def test_openai_compatible_extra_body_reaches_sdk():
    async def scenario():
        from livekit.agents import llm

        obj = await build(
            "llm",
            {
                "provider": "groq",
                "model": "openai/gpt-oss-20b",
                "source": "env",
                "params": {"reasoning_effort": "low", "max_completion_tokens": 211},
                "raw": {"seed": 42, "frequency_penalty": 0.4},
            },
            {"key": "fake"},
            [],
        )
        seen = {}

        async def create(**kwargs):
            seen.update(kwargs)

            class Stream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

                async def close(self):
                    pass

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *args):
                    pass

            return Stream()

        obj._client.chat.completions.create = create
        ctx = llm.ChatContext()
        ctx.add_message(role="user", content="Bonjour")
        stream = obj.chat(chat_ctx=ctx)
        try:
            async for _ in stream:
                pass
        finally:
            await stream.aclose()
            await obj.aclose()
        assert seen["reasoning_effort"] == "low"
        assert seen["max_completion_tokens"] == 211
        assert (
            seen["extra_body"]["seed"] == 42
            and seen["extra_body"]["frequency_penalty"] == 0.4
        )

    asyncio.run(scenario())


def test_session_raw_packets_are_isolated_and_control_preserved():
    base = {
        "model_id": "sonic-3.6",
        "transcript": "Hi",
        "generation_config": {"speed": 1},
    }
    a = wire_payload("cartesia", "tts", base, {"generation_config": {"speed": 1.5}})
    b = wire_payload("cartesia", "tts", base, {"generation_config": {"speed": 0.7}})
    assert (
        a["generation_config"]["speed"] == 1.5
        and b["generation_config"]["speed"] == 0.7
        and base["generation_config"]["speed"] == 1
    )
    assert wire_payload(
        "openai",
        "realtime",
        {"type": "input_audio_buffer.append", "audio": "x"},
        {"max_output_tokens": 50},
    ) == {"type": "input_audio_buffer.append", "audio": "x"}
    assert (
        wire_payload(
            "openai",
            "realtime",
            {"type": "session.update", "session": {"model": "gpt-realtime"}},
            {"max_output_tokens": 50},
        )["session"]["max_output_tokens"]
        == 50
    )
    assert (
        wire_payload(
            "inworld", "tts", {"create": {"voiceId": "A"}}, {"instruction": "calm"}
        )["create"]["instruction"]
        == "calm"
    )


def test_tags_split_across_chunks_and_unsupported_removed():
    async def scenario():
        async def chunks():
            for chunk in ["Bonjour [", "[la", "ugh]] à vous [[sigh]]"]:
                yield chunk

        result = "".join(
            [
                x
                async for x in translated_stream(
                    chunks(), "cartesia", "sonic-3.6", {"tags": {"laugh": 1, "sigh": 1}}
                )
            ]
        )
        assert result == "Bonjour [laughter] à vous "

    asyncio.run(scenario())
    assert (
        translate(
            "[[sigh]] Oui", "elevenlabs", "eleven_flash_v2_5", {"tags": {"sigh": 1}}
        )
        == " Oui"
    )


def test_telemetry_no_cross_turn_latency():
    c = Collector(DEFAULT)
    c.metric(
        {
            "type": "llm_metrics",
            "speech_id": "a",
            "ttft": 0.2,
            "prompt_tokens": 100,
            "completion_tokens": 10,
        }
    )
    c.metric(
        {"type": "tts_metrics", "speech_id": "b", "ttfb": 0.1, "characters_count": 10}
    )
    assert "latency_ms" not in c.turns["a"]
    c.metric(
        {"type": "tts_metrics", "speech_id": "a", "ttfb": 0.1, "characters_count": 5}
    )
    c.metric({"type": "eou_metrics", "speech_id": "a", "end_of_utterance_delay": 0.3})
    assert c.turns["a"]["estimated_ms"] == 600


def test_google_proto_raw_and_azure_ssml_at_transport_boundary():
    from worker.google_transport import TTSClientProxy
    from worker.providers import azure_ssml
    from google.cloud import texttospeech

    async def scenario():
        client = AsyncMock()
        proxy = TTSClientProxy(client, {"audio_config": {"speaking_rate": 1.25}})
        await proxy.synthesize_speech(
            input=texttospeech.SynthesisInput(text="Bonjour"),
            voice=texttospeech.VoiceSelectionParams(language_code="fr-FR"),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16
            ),
        )
        sent = client.synthesize_speech.call_args.kwargs["request"]
        assert sent.audio_config.speaking_rate == 1.25 and sent.input.text == "Bonjour"

    asyncio.run(scenario())
    ssml = azure_ssml(
        '<speak xmlns="http://www.w3.org/2001/10/synthesis"><voice name="fr-FR-DeniseNeural">Bonjour</voice></speak>',
        {
            "role": "YoungAdultFemale",
            "style": "cheerful",
            "silence": {"type": "Sentenceboundary", "value": "200ms"},
        },
    )
    assert "YoungAdultFemale" in ssml and "200ms" in ssml and "Bonjour" in ssml


def test_soniox_raw_does_not_touch_keepalive_and_transcodes_mulaw():
    async def scenario():
        ws = AsyncMock()
        owner = WireSession(
            None,
            "soniox",
            "stt",
            {"audio_format": "pcm_mulaw", "enable_endpoint_detection": False},
        )
        sock = SocketProxy(ws, owner)
        await sock.send_bytes(b"\x00\x00" * 160)
        assert len(ws.send_bytes.call_args.args[0]) == 160
        await sock.send_json(
            {"api_key": "secret", "model": "stt-rt-v5", "audio_format": "pcm_s16le"}
        )
        assert ws.send_json.call_args.args[0]["enable_endpoint_detection"] is False
        await sock.send_json({"type": "keepalive"})
        assert ws.send_json.call_args.args[0] == {"type": "keepalive"}

    asyncio.run(scenario())


def test_real_response_latency_and_token_tts_billing():

    c = Collector(DEFAULT)
    c.user_state("speaking", "listening")
    c.user_stopped -= 0.4
    c.agent_state("speaking")
    assert 399 < c.turns["response-1"]["latency_ms"] < 450
    config = deepcopy(DEFAULT)
    config["tts"] = {"provider": "openai", "model": "gpt-4o-mini-tts", "source": "env"}
    c = Collector(config)
    c.metric(
        {
            "type": "tts_metrics",
            "characters_count": 500,
            "input_tokens": 10,
            "output_tokens": 20,
        }
    )
    assert c.usage[c.key("tts")] == {"input_tokens": 10, "output_audio_tokens": 20}


def test_disabled_natural_mode_removes_tags():
    assert (
        translate(
            "[[laugh]] Bonjour",
            "cartesia",
            "sonic-3.6",
            {"mode": "none", "tags": {"laugh": 1}},
        )
        == " Bonjour"
    )
