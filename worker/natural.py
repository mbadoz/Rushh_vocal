import random, re

TAGS = {
    "cartesia": {
        "laugh": "[laughter]",
        "short_pause": '<break time="300ms"/>',
        "long_pause": '<break time="800ms"/>',
    },
    "elevenlabs": {
        "sigh": "[sighs]",
        "throat": "[clears throat]",
        "laugh": "[laughing]",
        "short_pause": "[short pause]",
        "long_pause": "[long pause]",
    },
    "google": {"short_pause": "[pause short]", "long_pause": "[pause long]"},
}


def translate(text, provider, model, options, rng=random.random):
    supported = TAGS.get(provider, {})
    if provider == "elevenlabs" and not model.startswith("eleven_v3"):
        supported = {}
    rates = {} if options.get("mode") == "none" else options.get("tags", {})

    def replace(match):
        tag = match.group(1)
        return supported.get(tag, "") if rates.get(tag, 0) > 0 else ""

    text = re.sub(
        r"\[\[(breath|sigh|throat|laugh|short_pause|long_pause)\]\]", replace, text
    )
    if options.get("mode") in ("rules", "both"):
        for tag, rate in rates.items():
            if rng() < rate and tag in supported:
                text = supported[tag] + " " + text
                break
    return text


def prompt_suffix(options):
    suffix = ""
    h = options.get("hesitations", "none")
    if h != "none":
        suffix += (
            " Ajoute "
            + ("occasionnellement" if h == "light" else "régulièrement")
            + " des hésitations naturelles (euh, hmm), sans en abuser."
        )
    if options.get("mode") in ("llm", "both"):
        tags = [
            f"[[{k}]] (environ {v:.0%} des tours)"
            for k, v in options.get("tags", {}).items()
            if v > 0
        ]
        if tags:
            suffix += (
                " Pour les effets vocaux, utilise seulement ces balises universelles : "
                + ", ".join(tags)
                + "."
            )
    return suffix


async def translated_stream(stream, provider, model, options):
    # Retain incomplete tags, but stream normal speech without waiting for the full reply.
    pending = ""
    async for chunk in stream:
        pending += chunk
        start = pending.rfind("[[")
        if start >= 0 and "]]" not in pending[start:]:
            cut = start
        elif pending.endswith("["):
            cut = len(pending) - 1
        else:
            cut = len(pending)
        if cut:
            yield translate(
                pending[:cut],
                provider,
                model,
                {**options, "mode": "none" if options.get("mode") == "none" else "llm"},
            )
            pending = pending[cut:]
    if pending:
        yield translate(
            pending,
            provider,
            model,
            {**options, "mode": "none" if options.get("mode") == "none" else "llm"},
        )
