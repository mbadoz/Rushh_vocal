import math
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from .catalog import CATALOG


class Block(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    model: str
    source: Literal["stored", "env", "inference"] = "env"
    params: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class Composition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    mode: Literal["pipeline", "realtime"] = "pipeline"
    stt: Block
    llm: Block
    tts: Block
    realtime: Block
    prompt: str = Field(max_length=50000)
    greeting: str = Field(max_length=2000)
    session: dict[str, Any] = Field(default_factory=dict)
    vad: dict[str, Any] = Field(default_factory=dict)
    noise: Literal["none", "bvc", "telephony", "krisp"] = "none"
    thinking_sound: bool = False
    background_sound: Literal["none", "office", "city", "forest", "crowd"] = "none"
    background_volume: float = Field(default=0.15, ge=0, le=1)
    max_duration: int = Field(default=180, ge=10, le=1800)
    record_audio: bool = True
    natural: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_blocks(self):
        for kind in ["stt", "llm", "tts"] if self.mode == "pipeline" else ["realtime"]:
            b = getattr(self, kind)
            c = next(
                (c for c in CATALOG if c["id"] == f"{kind}:{b.provider}:{b.model}"),
                None,
            )
            if not c:
                raise ValueError(f"Modèle inconnu : {kind}/{b.provider}/{b.model}")
            if b.source == "inference" and not c["inference"]:
                raise ValueError("Ce modèle ne propose pas Inference dans le catalogue")
            if any(
                k in b.params or k in b.raw
                for k in (
                    "api_key",
                    "api_secret",
                    "http_session",
                    "client",
                    "base_url",
                    "credentials",
                    "credentials_file",
                    "credentials_info",
                    "speech_key",
                    "speech_auth_token",
                    "speech_endpoint",
                    "http_options",
                    "websocket_url",
                    "extra_headers",
                    "extra_query",
                    "authorization",
                    "headers",
                    "access_token",
                )
            ):
                raise ValueError(
                    "Les secrets et endpoints ne sont pas des paramètres de composition"
                )
            if set(b.raw) & {"model", "model_id", "modelId"}:
                raise ValueError(
                    "Choisissez le modèle dans le catalogue, pas dans les paramètres bruts."
                )
            if kind == "tts" and b.provider == "cartesia":
                output = b.raw.get("output_format", {})
                if (
                    output.get("encoding", "pcm_s16le") != "pcm_s16le"
                    or output.get("container", "raw") != "raw"
                ):
                    raise ValueError("Le flux LiveKit Cartesia requiert PCM16 brut.")
                if output.get(
                    "sample_rate", b.params.get("sample_rate", 24000)
                ) != b.params.get("sample_rate", 24000):
                    raise ValueError(
                        "Réglez sample_rate dans les paramètres du plugin pour synchroniser le décodeur."
                    )
            if (
                kind == "stt"
                and "sample_rate" in b.raw
                and b.raw["sample_rate"] != b.params.get("sample_rate", 16000)
            ):
                raise ValueError(
                    "Réglez sample_rate dans les paramètres du plugin STT."
                )
            if b.provider == "cartesia" and kind == "tts":
                speed = b.raw.get("generation_config", {}).get(
                    "speed", b.params.get("speed", 1)
                )
                if (
                    not isinstance(speed, (int, float))
                    or not math.isfinite(speed)
                    or not 0.6 <= speed <= 1.5
                ):
                    raise ValueError("Vitesse Cartesia : 0,6 à 1,5")
        for probability in self.natural.get("tags", {}).values():
            if (
                not isinstance(probability, (int, float))
                or not math.isfinite(probability)
                or not 0 <= probability <= 1
            ):
                raise ValueError("Fréquence des balises : 0 à 1")
        ack = self.natural.get("long_reply_ack", 0)
        if not isinstance(ack, (int, float)) or not math.isfinite(ack) or not 0 <= ack <= 1:
            raise ValueError("Fréquence des acquiescements : 0 à 1")
        if any(not name.isidentifier() for name in self.tools):
            raise ValueError("Nom d’outil invalide")
        return self
