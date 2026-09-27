"""Versioned model catalogue, independent of plugin defaults. Prices are estimates unless verified."""

from copy import deepcopy

PROVIDERS = {
    "soniox": (
        "SONIOX_API_KEY",
        "https://console.soniox.com",
        "https://api.soniox.com/v1/models",
    ),
    "cartesia": (
        "CARTESIA_API_KEY",
        "https://play.cartesia.ai/keys",
        "https://api.cartesia.ai/voices",
    ),
    "groq": (
        "GROQ_API_KEY",
        "https://console.groq.com/keys",
        "https://api.groq.com/openai/v1/models",
    ),
    "openrouter": (
        "OPENROUTER_API_KEY",
        "https://openrouter.ai/keys",
        "https://openrouter.ai/api/v1/models",
    ),
    "cerebras": (
        "CEREBRAS_API_KEY",
        "https://cloud.cerebras.ai",
        "https://api.cerebras.ai/v1/models",
    ),
    "openai": (
        "OPENAI_API_KEY",
        "https://platform.openai.com/api-keys",
        "https://api.openai.com/v1/models",
    ),
    "google": (
        "GOOGLE_API_KEY",
        "https://aistudio.google.com/apikey",
        "https://generativelanguage.googleapis.com/v1beta/models",
    ),
    "anthropic": (
        "ANTHROPIC_API_KEY",
        "https://console.anthropic.com",
        "https://api.anthropic.com/v1/models",
    ),
    "mistral": (
        "MISTRAL_API_KEY",
        "https://console.mistral.ai/api-keys",
        "https://api.mistral.ai/v1/models",
    ),
    "deepgram": (
        "DEEPGRAM_API_KEY",
        "https://console.deepgram.com",
        "https://api.deepgram.com/v1/projects",
    ),
    "assemblyai": (
        "ASSEMBLYAI_API_KEY",
        "https://www.assemblyai.com/dashboard",
        "https://api.assemblyai.com/v2/transcript?limit=1",
    ),
    "speechmatics": (
        "SPEECHMATICS_API_KEY",
        "https://portal.speechmatics.com",
        "https://asr.api.speechmatics.com/v2/jobs?limit=1",
    ),
    "gladia": (
        "GLADIA_API_KEY",
        "https://app.gladia.io",
        "https://api.gladia.io/v2/pre-recorded?limit=1",
    ),
    "elevenlabs": (
        "ELEVEN_API_KEY",
        "https://elevenlabs.io/app/settings/api-keys",
        "https://api.elevenlabs.io/v1/voices",
    ),
    "rime": ("RIME_API_KEY", "https://app.rime.ai", None),
    "azure": ("AZURE_SPEECH_KEY", "https://portal.azure.com", None),
    "inworld": (
        "INWORLD_API_KEY",
        "https://platform.inworld.ai",
        "https://api.inworld.ai/tts/v1/voices",
    ),
    "hume": (
        "HUME_API_KEY",
        "https://platform.hume.ai",
        "https://api.hume.ai/v0/tts/voices",
    ),
    "ultravox": (
        "ULTRAVOX_API_KEY",
        "https://app.ultravox.ai",
        "https://api.ultravox.ai/api/voices",
    ),
    "livekit": ("LIVEKIT_API_KEY", "https://cloud.livekit.io", None),
}
# params use plugin names; raw is the final provider payload, merged recursively.
CATALOG = []


def add(kind, provider, models, params, inference=False):
    for model in models.split("|"):
        CATALOG.append(
            dict(
                id=f"{kind}:{provider}:{model}",
                kind=kind,
                provider=provider,
                model=model,
                params=deepcopy(params),
                inference=inference,
            )
        )


add(
    "stt",
    "soniox",
    "stt-rt-v5",
    dict(
        language_hints=["fr"],
        language_hints_strict=False,
        max_endpoint_delay_ms=2000,
        endpoint_sensitivity=0.0,
        context={"terms": []},
    ),
)
add(
    "stt",
    "deepgram",
    "nova-3",
    dict(
        language="fr",
        filler_words=False,
        smart_format=True,
        endpointing_ms=25,
        keyterms=[],
    ),
    True,
)
add(
    "stt",
    "deepgram",
    "flux-general-multi",
    dict(language_hint=["fr"], eot_threshold=0.7, eot_timeout_ms=5000),
    True,
)
add(
    "stt",
    "assemblyai",
    "universal-streaming-multilingual",
    dict(language_detection=True, min_turn_silence=100, max_turn_silence=1000),
    True,
)
add(
    "stt",
    "assemblyai",
    "universal-3-5-pro",
    dict(language_codes=["fr"], min_turn_silence=100, max_turn_silence=1000),
    True,
)
add(
    "stt",
    "speechmatics",
    "standard|enhanced",
    dict(language="fr", max_delay=0.7, max_delay_mode="flexible"),
)
add(
    "stt",
    "gladia",
    "solaria-1",
    dict(languages=["fr"], code_switching=False, endpointing=0.05, region="eu-west"),
)
add("stt", "elevenlabs", "scribe_v2_realtime", dict(language_code="fr"))
add("stt", "openai", "gpt-4o-transcribe|gpt-4o-mini-transcribe", dict(language="fr"))
add("stt", "groq", "whisper-large-v3-turbo", dict(language="fr"))
add("stt", "cartesia", "ink-2|ink-whisper", dict(language="fr"), True)
add(
    "llm",
    "cerebras",
    "gpt-oss-120b",
    dict(reasoning_effort="low", max_completion_tokens=300),
)
add(
    "llm",
    "cerebras",
    "qwen-3.8-27b",
    dict(reasoning_effort="none", max_completion_tokens=300),
)
add(
    "llm",
    "groq",
    "openai/gpt-oss-20b|openai/gpt-oss-120b",
    dict(reasoning_effort="low", max_completion_tokens=300),
)
add(
    "llm",
    "groq",
    "openai/gpt-oss-safeguard-20b",
    dict(max_completion_tokens=300),
)
add(
    "llm",
    "groq",
    "llama-3.1-8b-instant",
    dict(temperature=0.4, max_completion_tokens=300),
)
add(
    "llm",
    "openrouter",
    "meta-llama/llama-3.3-70b-instruct",
    dict(temperature=0.4, max_completion_tokens=300),
)
add(
    "llm",
    "openrouter",
    "openai/gpt-oss-20b|openai/gpt-oss-120b",
    dict(reasoning_effort="low", max_completion_tokens=300),
)
add(
    "llm",
    "google",
    "gemini-3.7-flash|gemini-3.8-flash",
    dict(
        thinking_config={"thinking_level": "low"}, temperature=1, max_output_tokens=300
    ),
    True,
)
add(
    "llm",
    "google",
    "gemini-2.5-flash-lite",
    dict(thinking_config={"thinking_budget": 0}, max_output_tokens=300),
)
add(
    "llm",
    "google",
    "gemini-3.5-flash-lite",
    dict(thinking_config={"thinking_level": "minimal"}, max_output_tokens=300),
    True,
)
add(
    "llm",
    "openai",
    "gpt-6-luna|gpt-5.4-mini",
    dict(reasoning_effort="none", max_completion_tokens=300),
)
add(
    "llm",
    "openai",
    "gpt-4.1-mini",
    dict(temperature=0.4, max_completion_tokens=300),
    True,
)
add("llm", "anthropic", "claude-haiku-4-5", dict(max_tokens=300, temperature=0.4))
add(
    "llm",
    "mistral",
    "mistral-small-2603|mistral-small-latest",
    dict(reasoning_effort="none", max_completion_tokens=300),
)
add(
    "llm",
    "livekit",
    "google/gemma-4-31b-it",
    dict(reasoning_effort="none", max_completion_tokens=300),
    True,
)
add(
    "tts",
    "cartesia",
    "sonic-3.6|sonic-3.6-2026-08-27|sonic-3.5|sonic-3|sonic-2|sonic-turbo|sonic-3-2025-10-27",
    dict(
        voice="045b0ec6-3bed-4bc8-b797-b90a7bb5b445",
        language="fr",
        speed=1.0,
        volume=1.0,
        sample_rate=24000,
        word_timestamps=True,
        api_version="2026-08-14",
        locale="fr-FR",
        normalization="auto",
        max_buffer_delay_ms=0,
    ),
    True,
)
add(
    "tts",
    "elevenlabs",
    "eleven_v3_conversational|eleven_v3",
    dict(
        voice_id="EXAVITQu4vr4xnSDxMaL",
        language="fr",
        voice_settings={"stability": 0.5},
    ),
)
add(
    "tts",
    "elevenlabs",
    "eleven_flash_v2_5|eleven_turbo_v2_5|eleven_multilingual_v2",
    dict(
        voice_id="EXAVITQu4vr4xnSDxMaL",
        language="fr",
        voice_settings={"stability": 0.5, "similarity_boost": 0.75, "speed": 1.0},
    ),
)
add("tts", "openai", "gpt-4o-mini-tts|tts-1|tts-1-hd", dict(voice="coral", speed=1.0))
add(
    "tts",
    "deepgram",
    "aura-2-agathe-fr|aura-2-hector-fr",
    dict(sample_rate=24000),
    True,
)
add("tts", "rime", "mistv2|mistv3|coda", dict(speaker="celeste", lang="fra"))
add("tts", "azure", "neural", dict(voice="fr-FR-DeniseNeural", language="fr-FR"))
add(
    "tts",
    "google",
    "chirp-3-hd",
    dict(voice_name="fr-FR-Chirp3-HD-Leda", language="fr-FR", use_streaming=True),
)
add(
    "tts",
    "inworld",
    "inworld-tts-2|inworld-tts-1.5-max",
    dict(voice="Ashley", language="fr-FR", speaking_rate=1.0),
    True,
)
add(
    "tts", "hume", "2", dict(description="Une voix chaleureuse en français.", speed=1.0)
)
add("realtime", "openai", "gpt-realtime|gpt-realtime-mini", dict(voice="marin"))
add(
    "realtime",
    "google",
    "gemini-2.5-flash-native-audio-preview-12-2025",
    dict(voice="Aoede", language="fr-FR"),
)
add("realtime", "ultravox", "fixie-ai/ultravox", dict(voice="Anika-French"))

# Inference exposes gateway parameters, which differ from direct plugin arguments.
for entry in CATALOG:
    if not entry["inference"]:
        continue
    params = deepcopy(entry["params"])
    if entry["provider"] == "google" and entry["kind"] == "llm":
        # Gateway cannot express the direct Gemini thinking_config contract precisely.
        entry["inference"] = False
        continue
    if entry["provider"] == "cartesia" and entry["kind"] == "tts":
        for key in ("api_version", "locale", "normalization"):
            params.pop(key, None)
        params["add_timestamps"] = params.pop("word_timestamps")
        if entry["model"] not in (
            "sonic-3.6", "sonic-3.6-2026-08-27", "sonic-3.5", "sonic-3",
            "sonic-2", "sonic-turbo",
        ):
            entry["inference"] = False
    if entry["provider"] == "deepgram":
        if "endpointing_ms" in params:
            params["endpointing"] = params.pop("endpointing_ms")
        if "keyterms" in params:
            params["keyterm"] = params.pop("keyterms")
        if "language_hint" in params:
            params["language"] = params.pop("language_hint")[0]
        if entry["kind"] == "tts":
            params["voice"] = entry["model"]
    if entry["provider"] == "assemblyai":
        if "min_turn_silence" in params:
            params["min_end_of_turn_silence_when_confident"] = params.pop(
                "min_turn_silence"
            )
        if "language_codes" in params:
            params["language"] = params.pop("language_codes")[0]
    entry["inference_params"] = params
    if entry["provider"] == "cartesia" and entry["model"] in ("sonic-2", "sonic-turbo"):
        for key in ("speed", "volume"):
            entry["params"].pop(key, None)


def block(kind, provider, model):
    item = next(x for x in CATALOG if x["id"] == f"{kind}:{provider}:{model}")
    return dict(
        provider=provider,
        model=model,
        source="env",
        params=deepcopy(item["params"]),
        raw={},
    )


DEFAULT = dict(
    name="Sophie · Premier essai",
    mode="pipeline",
    stt=block("stt", "cartesia", "ink-2"),
    llm=block("llm", "groq", "openai/gpt-oss-20b"),
    tts=block("tts", "cartesia", "sonic-3.6"),
    realtime=block("realtime", "openai", "gpt-realtime"),
    prompt="Tu es Sophie, assistante IA d'une agence immobilière. Parle français, vouvoie, sois chaleureuse et concise. Pose une seule question à la fois. Qualifie le projet, le secteur, le budget et la surface. Les outils sont des simulations de banc de test : ne prétends jamais avoir envoyé un vrai message ou réservé un vrai rendez-vous.",
    greeting="Bonjour, je suis Sophie, l'assistante IA de l'agence. Que puis-je faire pour vous ?",
    session=dict(
        turn_detection="vad",
        min_endpointing_delay=0.3,
        max_endpointing_delay=3.0,
        allow_interruptions=True,
        min_interruption_duration=0.5,
        min_interruption_words=0,
        false_interruption_timeout=2.0,
        resume_false_interruption=True,
        preemptive_generation=False,
        user_away_timeout=15,
    ),
    vad=dict(activation_threshold=0.5, min_silence_duration=0.4),
    noise="none",
    thinking_sound=False,
    background_sound="none",
    background_volume=0.15,
    max_duration=180,
    record_audio=True,
    natural=dict(
        mode="llm",
        hesitations="light",
        tags={
            "breath": 0,
            "sigh": 0,
            "throat": 0,
            "sneeze": 0,
            "cough": 0,
            "whisper": 0,
            "laugh": 0,
            "short_pause": 0.1,
            "long_pause": 0,
        },
        long_reply_ack=0,
    ),
    tools={
        "chercher_bien": [
            {"reference": "DEMO-001", "ville": "Sceaux", "prix": 395000, "surface": 65}
        ],
        "proposer_creneaux": ["Demain à 14 h", "Demain à 16 h"],
        "enregistrer_lead": {"status": "simulation"},
        "reserver_rdv": {"status": "simulation"},
        "transferer_agent": {"status": "simulation"},
        "programmer_rappel": {"status": "simulation"},
    },
)

PRICE_SOURCES = {
    "cartesia": "https://cartesia.ai/pricing",
    "soniox": "https://soniox.com/pricing",
    "groq": "https://console.groq.com/docs/models",
    "openrouter": "https://openrouter.ai/meta-llama/llama-3.3-70b-instruct",
    "openai": "https://developers.openai.com/api/docs/pricing",
    "google": "https://ai.google.dev/gemini-api/docs/pricing",
    "deepgram": "https://deepgram.com/pricing",
    "anthropic": "https://platform.claude.com/docs/en/about-claude/pricing",
    "cerebras": "https://www.cerebras.ai/pricing",
    "mistral": "https://mistral.ai/pricing",
    "livekit": "https://livekit.com/pricing/inference",
}


def prices():
    out = []
    llm = {
        "gpt-oss-120b": (0.35, 0.75),
        "openai/gpt-oss-20b": (0.075, 0.30),
        "openai/gpt-oss-safeguard-20b": (0.075, 0.30),
        "openai/gpt-oss-120b": (0.15, 0.60),
        "meta-llama/llama-3.3-70b-instruct": (0.10, 0.32),
        "gpt-6-luna": (0.10, 0.50),
        "gpt-5.4-mini": (0.75, 4.5),
        "gpt-4.1-mini": (0.4, 1.6),
        "claude-haiku-4-5": (1, 5),
        "mistral-small-2603": (0.15, 0.60),
        "mistral-small-latest": (0.15, 0.60),
        "qwen-3.8-27b": (0.99, 1.49),
        "gemini-3.7-flash": (0.75, 3.75),
        "gemini-3.8-flash": (0.75, 3.75),
        "gemini-2.5-flash-lite": (0.1, 0.4),
        "google/gemma-4-31b-it": (0.4, 1.2),
    }
    for c in CATALOG:
        rates = {}
        if c["kind"] == "stt":
            p = {
                "soniox": 0.002,
                "cartesia": 0.009,
                "deepgram": 0.0077,
                "assemblyai": 0.0025,
                "speechmatics": 0.00215,
                "gladia": 0.0125,
            }.get(c["provider"])
            if p is not None:
                rates = {"audio_seconds": p / 60}
        if c["kind"] == "llm" and c["model"] in llm:
            a, b = llm[c["model"]]
            if c["provider"] == "openrouter":
                a, b = {
                    "openai/gpt-oss-20b": (0.018, 0.09),
                    "openai/gpt-oss-120b": (0.03, 0.17),
                }.get(c["model"], (a, b))
            rates = {
                "input_tokens": a / 1e6,
                "output_tokens": b / 1e6,
                "cached_tokens": a / 1e6,
            }
        if c["kind"] == "tts":
            p = {
                "cartesia": 30,
                "elevenlabs": 100,
                "deepgram": 30,
                "rime": 30,
                "azure": 16,
                "google": 30,
                "inworld": 25,
                "hume": 150,
            }.get(c["provider"])
            if c["model"] in ("tts-1", "tts-1-hd"):
                p = 15 if c["model"] == "tts-1" else 30
            if p:
                rates = {"characters": p / 1e6}
        if c["kind"] == "stt" and c["provider"] == "soniox":
            rates.update(
                input_audio_tokens=2 / 1e6,
                input_text_tokens=4 / 1e6,
                output_tokens=4 / 1e6,
            )
        if (
            c["kind"] == "tts"
            and c["provider"] == "openai"
            and c["model"].startswith("gpt-4o")
        ):
            rates = {"input_tokens": 0.6 / 1e6, "output_audio_tokens": 12 / 1e6}
        out.append(
            dict(
                id=c["id"],
                currency="USD",
                rates=rates,
                source=PRICE_SOURCES.get(c["provider"], PROVIDERS[c["provider"]][1]),
                checked_at=None,
                status="estimate",
                note="Relevé des specs du 26/09/2026, à confirmer selon votre contrat.",
            )
        )
        if c["inference"] and c["provider"] != "livekit":
            cartesia_tts = c["provider"] == "cartesia" and c["kind"] == "tts"
            out.append(
                dict(
                    id=c["id"] + ":inference",
                    currency="USD",
                    rates={"characters": 50 / 1e6} if cartesia_tts else {},
                    source=PRICE_SOURCES["livekit"],
                    checked_at="2026-09-27" if cartesia_tts else None,
                    status="verified" if cartesia_tts else "unknown",
                    note=(
                        "LiveKit Build/Ship : 50 $/million de caractères ; Scale : 37,50 $."
                        if cartesia_tts else "Tarif Inference distinct du tarif direct."
                    ),
                )
            )
    for key in [
        "livekit:agent",
        "livekit:sip",
        "livekit:recording",
        "telephony:inbound",
    ]:
        out.append(
            dict(
                id=key,
                currency="EUR",
                rates={},
                source="https://livekit.com/pricing",
                checked_at=None,
                status="unknown",
                note="Renseigner le coût par seconde applicable à votre offre (0 si inclus).",
            )
        )
    for price in out:
        if price["id"] in (
            "llm:groq:openai/gpt-oss-20b",
            "llm:groq:openai/gpt-oss-120b",
            "llm:groq:openai/gpt-oss-safeguard-20b",
        ):
            price.update(
                checked_at="2026-09-26",
                note="Entrée/sortie vérifiées sur Groq Models ; cache à préciser selon votre accès.",
                status="verified",
            )
            price["rates"].pop("cached_tokens", None)
        if price["id"] in (
            "llm:openrouter:openai/gpt-oss-20b",
            "llm:openrouter:openai/gpt-oss-120b",
        ):
            price.update(
                source="https://openrouter.ai/" + price["id"].split(":", 2)[2],
                checked_at="2026-09-27",
                status="estimate",
                note="Prix du fournisseur le moins cher affiché par OpenRouter ; le coût réel dépend du routage.",
            )
            price["rates"].pop("cached_tokens", None)
        if price["id"] == "llm:groq:llama-3.1-8b-instant":
            price.update(
                status="unknown",
                note="Groq indique Contact Sales : renseigner le tarif de votre contrat.",
            )
        if price["id"] == "llm:mistral:mistral-small-latest":
            price["note"] = (
                "Estimation basée sur Mistral Small 4 ; vérifier la version ciblée "
                "par l'alias et le tarif de votre compte."
            )
        if price["id"] == "stt:soniox:stt-rt-v5":
            price.update(
                checked_at="2026-09-26",
                note="Tarifs tokens vérifiés sur Soniox ; équivalent à la durée estimatif (environ 0,12 $/h).",
            )
    return out
