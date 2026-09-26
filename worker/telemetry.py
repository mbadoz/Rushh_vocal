from collections import defaultdict
import time


class Collector:
    def __init__(self, config):
        self.config = config
        self.started = time.monotonic()
        self.usage = defaultdict(lambda: defaultdict(float))
        self.turns = {}
        self.transcript = []
        self.events = []
        self.user_stopped = None
        self.response_number = 0

    def user_state(self, old, new):
        if old == "speaking" and new != "speaking":
            self.user_stopped = time.monotonic()
        elif new == "speaking":
            self.user_stopped = None

    def agent_state(self, state):
        if state == "speaking" and self.user_stopped is not None:
            self.response_number += 1
            self.turns["response-" + str(self.response_number)] = {
                "id": "response-" + str(self.response_number),
                "latency_ms": (time.monotonic() - self.user_stopped) * 1000,
                "measurement": "Fin de parole utilisateur → lecture audio agent (worker)",
            }
            self.user_stopped = None

    def key(self, kind):
        b = self.config[kind]
        return f"{kind}:{b['provider']}:{b['model']}" + (
            ":inference"
            if b["source"] == "inference" and b["provider"] != "livekit"
            else ""
        )

    def metric(self, m):
        d = m.model_dump(mode="json") if hasattr(m, "model_dump") else dict(m)
        kind = d.get("type", "")
        self.events.append({"type": "metric", "data": d})
        if kind == "stt_metrics":
            u = self.usage[self.key("stt")]
            if self.config["stt"]["provider"] == "soniox" and d.get("input_tokens"):
                u["input_audio_tokens"] += d.get("input_audio_tokens", 0)
                u["input_text_tokens"] += max(
                    0, d.get("input_tokens", 0) - d.get("input_audio_tokens", 0)
                )
                u["output_tokens"] += d.get("output_tokens", 0)
            else:
                u["audio_seconds"] += d.get("audio_duration", 0)
        elif kind == "llm_metrics":
            u = self.usage[self.key("llm")]
            for dest, src in [
                ("input_tokens", "prompt_tokens"),
                ("cached_tokens", "prompt_cached_tokens"),
                ("output_tokens", "completion_tokens"),
            ]:
                u[dest] += d.get(src, 0)
            if d.get("cache_creation_tokens"):
                u["cache_creation_tokens"] += d["cache_creation_tokens"]
        elif kind == "tts_metrics":
            u = self.usage[self.key("tts")]
            token_billed = self.config["tts"]["provider"] == "openai" and self.config[
                "tts"
            ]["model"].startswith("gpt-4o")
            if token_billed:
                u["input_tokens"] += d.get("input_tokens", 0)
                u["output_audio_tokens"] += d.get("output_tokens", 0)
                if not d.get("input_tokens") and not d.get("output_tokens"):
                    u["unreported_token_usage"] += 1
            else:
                u["characters"] += d.get("characters_count", 0)
        elif kind == "realtime_model_metrics":
            u = self.usage[self.key("realtime")]
            for side, field in [
                ("input", "input_token_details"),
                ("output", "output_token_details"),
            ]:
                details = d.get(field) or {}
                for modality in ("audio", "text"):
                    u[f"{side}_{modality}_tokens"] += details.get(
                        modality + "_tokens", 0
                    )
        sid = d.get("speech_id")
        if sid:
            t = self.turns.setdefault(sid, {"id": sid})
            if kind == "llm_metrics":
                t["llm_ms"] = d.get("ttft", 0) * 1000
            if kind == "tts_metrics":
                t.setdefault("tts_ms", d.get("ttfb", 0) * 1000)
            if kind == "eou_metrics":
                t["endpoint_ms"] = d.get("end_of_utterance_delay", 0) * 1000
            # Same speech_id only. Missing components stay unknown.
            if all(k in t for k in ("llm_ms", "tts_ms", "endpoint_ms")):
                t["estimated_ms"] = t["llm_ms"] + t["tts_ms"] + t["endpoint_ms"]
                t["measurement"] = "EOU + TTFT + TTFB (estimation pipeline)"

    def payload(self, status="running", channel="web", **extra):
        duration = time.monotonic() - self.started
        usage = {k: dict(v) for k, v in self.usage.items()}
        usage["livekit:agent"] = {"seconds": duration}
        if channel == "phone":
            usage.update(
                {
                    "livekit:sip": {"seconds": duration},
                    "telephony:inbound": {"seconds": duration},
                }
            )
        return dict(
            status=status,
            duration=duration,
            usage=usage,
            turns=list(self.turns.values()),
            transcript=self.transcript,
            events=self.events,
            **extra,
        )
