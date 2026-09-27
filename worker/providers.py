"""Per-session adapters. No process-wide monkeypatch or mutation of environment keys."""

import importlib, inspect, json
from copy import deepcopy
import aiohttp

ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "mistral": "https://api.mistral.ai/v1",
}


def merge(base, override):
    result = deepcopy(base)
    for k, v in override.items():
        result[k] = (
            merge(result[k], v)
            if isinstance(v, dict) and isinstance(result.get(k), dict)
            else deepcopy(v)
        )
    return result


def wire_payload(provider, kind, payload, raw):
    """Only configuration/text packets are merged, never audio/control packets."""
    if not isinstance(payload, dict):
        return payload
    if provider == "cartesia" and kind == "tts":
        return merge(payload, raw) if "model_id" in payload else payload
    if provider == "openai" and kind == "realtime":
        if payload.get("type") == "session.update":
            return merge(payload, {"session": raw})
        return payload
    if kind == "stt" and provider in (
        "deepgram",
        "cartesia",
        "elevenlabs",
        "assemblyai",
    ):
        return payload
    if provider == "soniox":
        return merge(payload, raw) if "api_key" in payload else payload
    if provider == "elevenlabs" and kind == "tts":
        return (
            merge(payload, raw)
            if any(
                k in payload
                for k in ("text", "inputs", "voice_id", "voice_settings", "settings")
            )
            else payload
        )
    if provider == "inworld":
        if "create" in payload:
            return merge(payload, {"create": raw})
        return merge(payload, raw) if "text" in payload else payload
    if provider == "hume":
        return merge(payload, raw) if "utterances" in payload else payload
    if provider == "rime":
        return merge(payload, raw) if "text" in payload else payload
    if provider == "gladia":
        return merge(payload, raw) if "sample_rate" in payload else payload
    if provider == "ultravox":
        return merge(payload, raw) if "model" in payload else payload
    return merge(payload, raw)


class SocketProxy:
    def __init__(self, ws, owner):
        self.ws = ws
        self.owner = owner

    def __getattr__(self, name):
        return getattr(self.ws, name)

    def __aiter__(self):
        return self.ws.__aiter__()

    async def send_bytes(self, data, **kw):
        encoding = self.owner.raw.get("audio_format", self.owner.raw.get("encoding"))
        if self.owner.kind == "stt" and encoding in (
            "pcm_mulaw",
            "mulaw",
            "pcm_alaw",
            "alaw",
        ):
            import audioop

            data = (
                audioop.lin2ulaw(data, 2)
                if encoding in ("pcm_mulaw", "mulaw")
                else audioop.lin2alaw(data, 2)
            )
        await self.ws.send_bytes(data, **kw)

    async def send_json(self, data, **kw):
        await self.ws.send_json(self.owner.transform(data), **kw)

    async def send_str(self, data, **kw):
        try:
            payload = json.loads(data)
        except (ValueError, TypeError):
            pass
        else:
            data = json.dumps(self.owner.transform(payload))
        await self.ws.send_str(data, **kw)


class SocketContext:
    def __init__(self, ctx, owner):
        self.ctx = ctx
        self.owner = owner

    async def __aenter__(self):
        return SocketProxy(await self.ctx.__aenter__(), self.owner)

    async def __aexit__(self, *args):
        return await self.ctx.__aexit__(*args)

    def __await__(self):
        async def connect():
            return SocketProxy(await self.ctx, self.owner)

        return connect().__await__()


class WireSession:
    def __init__(self, session, provider, kind, raw):
        self.session = session
        self.provider = provider
        self.kind = kind
        self.raw = raw

    def __getattr__(self, name):
        return getattr(self.session, name)

    def transform(self, payload):
        return wire_payload(self.provider, self.kind, payload, self.raw)

    def ws_connect(self, url, **kwargs):
        # STT providers with query-string configuration: raw is serialized there.
        if (
            self.provider in ("deepgram", "cartesia", "elevenlabs", "assemblyai")
            and self.kind == "stt"
        ):
            from yarl import URL

            url = URL(url).update_query(
                {
                    k: json.dumps(v) if isinstance(v, (bool, list, dict)) else v
                    for k, v in self.raw.items()
                }
            )
        return SocketContext(self.session.ws_connect(url, **kwargs), self)

    def post(self, url, **kwargs):
        if "json" in kwargs:
            kwargs["json"] = self.transform(kwargs["json"])
        if self.provider == "azure" and "data" in kwargs:
            kwargs["data"] = azure_ssml(kwargs["data"], self.raw)
        return self.session.post(url, **kwargs)

    def request(self, method, url, **kwargs):
        if "json" in kwargs:
            kwargs["json"] = self.transform(kwargs["json"])
        return self.session.request(method, url, **kwargs)


class ExtraChat:
    """Mixin: plugins with SDK request kwargs (Anthropic and Google)."""

    def chat(self, *, extra_kwargs=None, **kwargs):
        return super().chat(
            extra_kwargs=merge(extra_kwargs or {}, self.bench_raw), **kwargs
        )


async def build(kind, block, credential, resources):
    provider = block["provider"]
    model = block["model"]
    params = deepcopy(block.get("params", {}))
    raw = deepcopy(block.get("raw", {}))
    key = credential.get("key")
    extras = credential.get("extras", {})
    if block["source"] == "inference" or provider == "livekit":
        from livekit.agents import inference

        cls = getattr(inference, kind.upper())
        model = model if provider == "livekit" else provider + "/" + model
        if provider == "deepgram" and kind == "tts":
            model = "deepgram/aura-2"
        native = {
            k: params.pop(k)
            for k in list(params)
            if k in inspect.signature(cls).parameters and k != "extra_kwargs"
        }
        return cls(model=model, **native, extra_kwargs=merge(params, raw))
    if kind == "llm" and provider in ("openai", "groq", "cerebras", "mistral"):
        from livekit.plugins.openai import LLM

        native = {
            k: params.pop(k)
            for k in list(params)
            if k in inspect.signature(LLM).parameters
        }
        opts = {
            "model": model,
            "api_key": key,
            **native,
            "extra_body": merge(params, raw),
        }
        if provider in ENDPOINTS:
            opts["base_url"] = ENDPOINTS[provider]
        return LLM(**opts)
    if provider == "speechmatics":
        from .speechmatics_legacy import STT

        return STT(api_key=key, model=model, raw=raw, **params)
    plugin = "openai" if provider == "groq" else provider
    mod = importlib.import_module("livekit.plugins." + plugin)
    cls = (
        getattr(mod.realtime, "RealtimeModel")
        if kind == "realtime" and provider in ("openai", "google")
        else getattr(mod, "RealtimeModel" if kind == "realtime" else kind.upper())
    )
    if provider == "deepgram" and kind == "stt" and model.startswith("flux"):
        cls = mod.STTv2
    if provider == "soniox":
        if isinstance(params.get("translation"), dict):
            params["translation"] = mod.stt.TranslationConfig(**params["translation"])
        opts = mod.STTOptions(model=model, **params)
        kwargs = {"params": opts, "api_key": key}
    else:
        kwargs = {"model": model, **params}
        if provider == "cartesia" and kind == "tts":
            # The Sonic 3 plugin rejects an integer, including the UI's "1".
            speed = kwargs.get("speed")
            if isinstance(speed, int) and not isinstance(speed, bool):
                kwargs["speed"] = float(speed)
        if provider == "azure":
            kwargs.pop("model")
            kwargs.update(
                speech_key=key, speech_region=extras.get("region", "francecentral")
            )
            if extras.get("endpoint"):
                kwargs["speech_endpoint"] = extras["endpoint"]
            for name, typ in [
                ("prosody", mod.tts.ProsodyConfig),
                ("style", mod.tts.StyleConfig),
            ]:
                if isinstance(kwargs.get(name), dict):
                    kwargs[name] = typ(**kwargs[name])
        elif provider == "google" and kind == "tts":
            kwargs.pop("model")
            if key.lstrip().startswith("{"):
                kwargs["credentials_info"] = json.loads(key)
            else:
                raise ValueError(
                    "Google TTS exige le JSON du compte de service dans la clé Google."
                )
        else:
            kwargs["api_key"] = key
        if provider == "hume":
            kwargs["model_version"] = kwargs.pop("model")
        if provider == "groq":
            kwargs["base_url"] = ENDPOINTS["groq"]
        if provider == "elevenlabs" and kind == "tts" and "voice_settings" in kwargs:
            kwargs["voice_settings"] = (
                mod.VoiceSettings(similarity_boost=None, **kwargs["voice_settings"])
                if "similarity_boost" not in kwargs["voice_settings"]
                else mod.VoiceSettings(**kwargs["voice_settings"])
            )
    sig = inspect.signature(cls).parameters
    if (
        provider == "google"
        and extras.get("project_id")
        and kind in ("llm", "realtime")
    ):
        kwargs["project"] = extras["project_id"]
    if kind == "llm" and provider in ("google", "anthropic"):
        raw = merge({k: kwargs.pop(k) for k in list(kwargs) if k not in sig}, raw)
        custom = type("Bench" + cls.__name__, (ExtraChat, cls), {})
        obj = custom(**kwargs)
        obj.bench_raw = raw
        return obj
    if provider == "cartesia" and kind == "tts":
        raw = merge(
            {
                k: kwargs.pop(k)
                for k in (
                    "locale",
                    "accent",
                    "normalization",
                    "max_buffer_delay_ms",
                    "add_phoneme_timestamps",
                    "use_normalized_timestamps",
                )
                if k in kwargs
            },
            raw,
        )
    unknown = set(kwargs) - set(sig)
    if unknown:
        raise ValueError(
            f"{provider} : paramètres non exposés par le plugin {sorted(unknown)}. Utilisez Paramètres API bruts si ce transport le permet."
        )
    if raw and provider in ("openai", "groq") and kind in ("stt", "tts"):
        if kind == "stt" and params.get("use_realtime"):
            raise ValueError(
                "Pour les paramètres bruts OpenAI STT, utilisez le transport de transcription HTTP (use_realtime=false)."
            )
        from openai import AsyncOpenAI

        sdk = AsyncOpenAI(
            api_key=key,
            **({"base_url": ENDPOINTS[provider]} if provider in ENDPOINTS else {}),
        )
        resources.append(sdk)
        target = (
            sdk.audio.transcriptions
            if kind == "stt"
            else sdk.audio.speech.with_streaming_response
        )
        original = target.create

        def create(**kw):
            kw["extra_body"] = merge(kw.get("extra_body", {}), raw)
            return original(**kw)

        target.create = create
        kwargs["client"] = sdk
        return cls(**kwargs)
    if raw and provider == "google" and kind == "tts":
        from .google_transport import TTSClientProxy

        class BenchTTS(cls):
            def _ensure_client(self):
                return TTSClientProxy(super()._ensure_client(), raw)

        return BenchTTS(**kwargs)
    if raw and provider == "google" and kind == "realtime":
        from livekit.plugins.google.realtime.realtime_api import RealtimeSession
        from google.genai import types

        class BenchSession(RealtimeSession):
            def _build_connect_config(self):
                config = super()._build_connect_config().model_dump(exclude_none=True)
                return types.LiveConnectConfig(**merge(config, raw))

        class BenchRealtime(cls):
            def session(self, *, turn_detection_disabled=False):
                session = BenchSession(self)
                self._sessions.add(session)
                return session

        return BenchRealtime(**kwargs)
    if raw:
        forbidden = {
            "api_key",
            "api_secret",
            "authorization",
            "headers",
            "url",
            "base_url",
            "access_token",
        }
        if forbidden.intersection(raw):
            raise ValueError(
                "Les paramètres bruts ne peuvent pas remplacer les identifiants."
            )
        if "http_session" not in sig:
            raise ValueError(
                f"{provider}/{kind} : paramètres API bruts non pris en charge par ce transport SDK : {list(raw)}"
            )
        # Reject transports where configuration is hidden in a binary/SDK protocol.
        if provider in ("google",):
            raise ValueError(
                f"{provider}/{kind} : extension de transport nécessaire pour les paramètres bruts."
            )
        session = aiohttp.ClientSession()
        resources.append(session)
        kwargs["http_session"] = WireSession(session, provider, kind, raw)
    return cls(**kwargs)


def azure_ssml(xml, raw):
    import xml.etree.ElementTree as ET

    ns = "http://www.w3.org/2001/10/synthesis"
    mstts = "https://www.w3.org/2001/mstts"
    ET.register_namespace("", ns)
    ET.register_namespace("mstts", mstts)
    root = ET.fromstring(xml)
    voice = root.find("{" + ns + "}voice")
    if voice is None:
        raise ValueError("SSML Azure sans voix")
    allowed = {"role", "style", "styledegree", "silence", "break", "emphasis"}
    if set(raw) - allowed:
        raise ValueError("Paramètre SSML Azure inconnu : " + str(set(raw) - allowed))
    if any(k in raw for k in ("role", "style", "styledegree")):
        wrapper = ET.Element(
            "{" + mstts + "}express-as",
            {k: str(raw[k]) for k in ("role", "style", "styledegree") if k in raw},
        )
        wrapper.text = voice.text
        voice.text = None
        for child in list(voice):
            voice.remove(child)
            wrapper.append(child)
        voice.append(wrapper)
    if "silence" in raw:
        voice.insert(
            0,
            ET.Element(
                "{" + mstts + "}silence", {k: str(v) for k, v in raw["silence"].items()}
            ),
        )
    if "break" in raw:
        voice.insert(0, ET.Element("{" + ns + "}break", {"time": str(raw["break"])}))
    if "emphasis" in raw:
        wrapper = ET.Element("{" + ns + "}emphasis", {"level": str(raw["emphasis"])})
        wrapper.text = voice.text
        voice.text = None
        for child in list(voice):
            voice.remove(child)
            wrapper.append(child)
        voice.append(wrapper)
    return ET.tostring(root, encoding="unicode")
