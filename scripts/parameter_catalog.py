"""Build the discoverable plugin argument catalogue against the pinned SDK."""

import importlib, inspect, json
from pathlib import Path
from api.catalog import CATALOG

blocked = {
    "self",
    "model",
    "model_id",
    "api_key",
    "api_secret",
    "client",
    "http_session",
    "credentials",
    "credentials_info",
    "credentials_file",
    "base_url",
    "websocket_url",
    "tokenizer",
    "loop",
    "vad",
    "speech_key",
    "speech_region",
    "speech_endpoint",
    "speech_auth_token",
    "http_options",
    "conn_options",
    "kwargs",
    "extra_headers",
    "extra_query",
    "extra_body",
    "params",
    "_provider_fmt",
    "_strict_tool_schema",
}
result = {}
for c in CATALOG:
    provider = c["provider"]
    kind = c["kind"]
    if provider == "livekit":
        from livekit.agents import inference

        cls = inference.LLM
    elif provider == "speechmatics":
        result[c["id"]] = [
            {"name": name, "value": value}
            for name, value in {
                "language": "fr",
                "max_delay": 0.7,
                "max_delay_mode": "flexible",
                "additional_vocab": [],
                "enable_partials": True,
                "enable_entities": True,
                "diarization": "none",
                "punctuation_overrides": {"sensitivity": 0.5},
                "transcript_filtering_config": {"remove_disfluencies": True},
            }.items()
        ]
        continue
    else:
        module = importlib.import_module(
            "livekit.plugins."
            + ("openai" if provider in ("groq", "cerebras", "mistral") else provider)
        )
        cls = (
            getattr(module.realtime, "RealtimeModel")
            if kind == "realtime" and provider in ("openai", "google")
            else getattr(
                module, "RealtimeModel" if kind == "realtime" else kind.upper()
            )
        )
        if provider == "soniox":
            cls = module.STTOptions
        if provider == "deepgram" and c["model"].startswith("flux"):
            cls = module.STTv2
    fields = []
    for name, param in inspect.signature(cls).parameters.items():
        if name in blocked or name.startswith("_"):
            continue
        value = param.default
        if value is inspect.Parameter.empty or not isinstance(
            value, (str, int, float, bool, list, dict)
        ):
            annotation = str(param.annotation)
            if "bool" in annotation:
                value = False
            elif "float" in annotation:
                value = 0.5
            elif "int" in annotation:
                value = 1
            elif "list" in annotation:
                value = []
            elif "dict" in annotation or "Config" in annotation:
                value = {}
            else:
                value = ""
        try:
            json.dumps(value)
        except TypeError:
            value = {}
        fields.append({"name": name, "value": value})
    if kind == "llm" and provider in ("groq", "cerebras", "mistral", "openai"):
        for name, value in {
            "seed": 42,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "stop": [],
            "top_k": 40,
        }.items():
            fields.append({"name": name, "value": value})
    result[c["id"]] = fields
Path("api/parameters.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print("Catalogue des paramètres généré pour", len(result), "modèles.")
