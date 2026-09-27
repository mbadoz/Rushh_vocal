import asyncio, json, logging, os, random, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
import httpx
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.agents.voice import room_io
from livekit.plugins import silero
from .providers import build
from .natural import long_user_phrase, prompt_suffix, translated_stream, translate
from .recording import Recorder
from .telemetry import Collector

log = logging.getLogger("rushh-bench")


class Sophie(Agent):
    def __init__(self, config):
        self.config = config
        tools = []
        for name, result in config["tools"].items():
            # A new closure per tool, never a shared mutable result.
            def factory(tool_name, tool_result):
                async def execute(demande: str) -> str:
                    return json.dumps(
                        {
                            "simulation": True,
                            "outil": tool_name,
                            "demande": demande,
                            "resultat": tool_result,
                        },
                        ensure_ascii=False,
                    )

                return function_tool(
                    execute,
                    name=tool_name,
                    description="Simulation de banc de test : "
                    + tool_name
                    + ". Décris les informations de la demande dans demande.",
                )

            tools.append(factory(name, result))
        super().__init__(
            instructions=config["prompt"] + prompt_suffix(config["natural"]),
            tools=tools,
        )

    async def tts_node(self, text, model_settings):
        b = self.config["tts"]
        options = self.config["natural"]

        async def with_rules():
            first = True
            async for chunk in translated_stream(
                text, b["provider"], b["model"], options
            ):
                yield (
                    translate(chunk, b["provider"], b["model"], options)
                    if first
                    else chunk
                )
                first = False

        async for frame in Agent.default.tts_node(self, with_rules(), model_settings):
            yield frame


async def entrypoint(ctx: JobContext):
    client = httpx.AsyncClient(
        base_url=os.environ["BENCH_API_URL"],
        headers={"Authorization": "Bearer " + os.environ["WORKER_SECRET"]},
        timeout=30,
    )
    resources = []
    session = None
    recorder = None
    rec_room = None
    stats = None
    run = None
    sync_task = None
    timer = None
    bg = None
    effect_task = None
    acknowledgement_task = None
    last_acknowledgement = 0.0
    finished = False
    fatal_error = None

    async def sync(status="running", **extras):
        if not run:
            return
        data = stats.payload(status, run["channel"], **extras)
        for attempt in range(3):
            try:
                r = await client.put("/internal/runs/" + run["id"], json=data)
                r.raise_for_status()
                return
            except httpx.HTTPError:
                if attempt == 2:
                    # Durable retry artifact has usage/transcript only, never credentials.
                    path = Path("data/pending")
                    path.mkdir(parents=True, exist_ok=True)
                    (path / (run["id"] + ".json")).write_text(json.dumps(data))
                    log.error("Télémétrie non envoyée, conservée dans data/pending")
                else:
                    await asyncio.sleep(attempt + 1)

    async def finish():
        nonlocal finished
        if finished:
            return
        finished = True
        if sync_task:
            sync_task.cancel()
        if timer:
            timer.cancel()
        if effect_task:
            effect_task.cancel()
        if acknowledgement_task:
            acknowledgement_task.cancel()
        if session:
            await session.aclose()
        recording_error = None
        if recorder:
            try:
                path = await recorder.finish()
                if os.getenv("R2_BUCKET"):
                    from .storage import upload

                    await asyncio.to_thread(upload, path, run["id"])
                    response = await client.post(
                        "/internal/runs/" + run["id"] + "/audio-ready"
                    )
                    response.raise_for_status()
                else:
                    with path.open("rb") as f:
                        response = await client.put(
                            "/internal/runs/" + run["id"] + "/audio",
                            content=f.read(),
                            headers={"Content-Type": "audio/wav"},
                        )
                        response.raise_for_status()
                path.unlink()
            except Exception:
                recording_error = "Enregistrement conservé sur le worker si disponible ; transfert audio échoué."
                log.exception("Enregistrement échoué")
        if stats:
            await sync(
                "failed" if fatal_error else "completed",
                recording_error=recording_error,
                error=fatal_error,
            )
        if bg:
            await bg.aclose()
        if rec_room:
            await rec_room.disconnect()
        for resource in resources:
            await resource.close()
        await client.aclose()

    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        metadata = json.loads(ctx.job.metadata or "{}")
        reply = await client.post(
            "/internal/claim",
            json={"run_id": metadata.get("run_id"), "room": ctx.room.name},
        )
        reply.raise_for_status()
        claimed = reply.json()
        run = claimed["run"]
        config = run["config"]
        stats = Collector(config)
        components = {}
        for kind in (
            ["stt", "llm", "tts"] if config["mode"] == "pipeline" else ["realtime"]
        ):
            components["llm" if kind == "realtime" else kind] = await build(
                kind, config[kind], claimed["credentials"].get(kind, {}), resources
            )
        options = dict(config["session"])
        if options.get("turn_detection") == "multilingual":
            from livekit.plugins.turn_detector.multilingual import MultilingualModel

            options["turn_detection"] = MultilingualModel()
        if config["mode"] == "realtime":
            options["turn_detection"] = "realtime_llm"
        session = AgentSession(
            **components, vad=silero.VAD.load(**config["vad"]), **options
        )

        def provider_error(event):
            nonlocal fatal_error
            stats.events.append(
                {
                    "type": "provider_error",
                    "provider": getattr(event.source, "provider", "unknown"),
                    "model": getattr(event.source, "model", "unknown"),
                    "error_type": type(event.error).__name__,
                    "recoverable": getattr(event.error, "recoverable", True),
                }
            )
            log.error(
                "Erreur fournisseur : %s/%s (%s, récupérable=%s)",
                getattr(event.source, "provider", "unknown"),
                getattr(event.source, "model", "unknown"),
                type(event.error).__name__,
                getattr(event.error, "recoverable", True),
            )
            if not getattr(event.error, "recoverable", True):
                fatal_error = (
                    "Erreur fournisseur non récupérable ; consultez les logs du worker."
                )

        session.on("error", provider_error)
        session.on("metrics_collected", lambda event: stats.metric(event.metrics))
        def user_state(event):
            nonlocal effect_task
            stats.user_state(event.old_state, event.new_state)
            if effect_task:
                effect_task.cancel()
                effect_task = None
            if event.new_state == "speaking" and bg and config["mode"] == "pipeline":
                rates = config.get("natural", {}).get("tags", {})
                effects = [(name, float(rates.get(name, 0))) for name in ("sneeze", "throat")]
                if any(rate > 0 for _, rate in effects):
                    async def play_effect():
                        while session.user_state == "speaking":
                            await asyncio.sleep(random.uniform(3.0, 7.0))
                            if session.user_state != "speaking":
                                break
                            for name, rate in effects:
                                if random.random() < rate:
                                    bg.play(AudioConfig(str(Path(__file__).parent / "assets" / (name + ".ogg")), volume=0.35))
                                    break
                    effect_task = asyncio.create_task(play_effect())

        session.on("user_state_changed", user_state)
        session.on("agent_state_changed", lambda event: stats.agent_state(event.new_state))

        def user_transcript(event):
            nonlocal acknowledgement_task, last_acknowledgement
            rate = config.get("natural", {}).get("long_reply_ack", 0)
            if (config["mode"] != "pipeline" or not rate or session.user_state != "speaking"
                or not long_user_phrase(event.transcript)
                or time.monotonic() - last_acknowledgement < 12
                or acknowledgement_task and not acknowledgement_task.done()
                or random.random() >= rate):
                return
            last_acknowledgement = time.monotonic()

            async def acknowledge():
                await asyncio.sleep(0.25)
                if session.user_state == "speaking" and session.agent_state != "speaking":
                    session.say(random.choice(("Ouiii.", "OK.")), allow_interruptions=False, add_to_chat_ctx=False)

            acknowledgement_task = asyncio.create_task(acknowledge())

        session.on("user_input_transcribed", user_transcript)

        def conversation(event):
            item = event.item
            if getattr(item, "type", "") == "message":
                stats.transcript.append(
                    {
                        "role": item.role,
                        "text": item.text_content,
                        "at": getattr(item, "created_at", None),
                        "interrupted": getattr(item, "interrupted", False),
                    }
                )

        session.on("conversation_item_added", conversation)

        def tools_event(event):
            stats.events.append(
                {
                    "type": "tools",
                    "calls": [x.model_dump(mode="json") for x in event.function_calls],
                    "outputs": [
                        x.model_dump(mode="json") for x in event.function_call_outputs
                    ],
                }
            )

        session.on("function_tools_executed", tools_event)
        closed = asyncio.Event()
        def session_closed(event):
            nonlocal fatal_error
            close_reason = getattr(event, "reason", None)
            reason = getattr(close_reason, "value", str(close_reason))
            stats.events.append({"type": "session_closed", "reason": reason})
            log.info("Session vocale fermée : %s", reason)
            if getattr(event, "error", None):
                fatal_error = "Session vocale interrompue par une erreur fournisseur ; consultez les logs du worker."
            closed.set()

        def room_disconnected(reason):
            try:
                disconnect_reason = rtc.DisconnectReason.Name(reason)
            except ValueError:
                disconnect_reason = str(reason)
            stats.events.append(
                {"type": "session_closed", "reason": "room_disconnected: " + disconnect_reason}
            )
            log.info("Salle LiveKit déconnectée : %s", disconnect_reason)
            closed.set()

        session.on("close", session_closed)
        ctx.room.on("disconnected", room_disconnected)
        ctx.add_shutdown_callback(finish)
        participant = await asyncio.wait_for(ctx.wait_for_participant(), timeout=60)
        if config["record_audio"]:
            from livekit import api

            recorder = Recorder(run["id"], config["max_duration"])
            rec_room = rtc.Room()

            def subscribe(track, publication, participant):
                if track.kind == rtc.TrackKind.KIND_AUDIO:
                    recorder.attach(
                        track,
                        1
                        if participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT
                        else 0,
                    )

            rec_room.on("track_subscribed", subscribe)
            token = (
                api.AccessToken()
                .with_identity("recorder-" + run["id"])
                .with_grants(
                    api.VideoGrants(
                        room_join=True,
                        room=ctx.room.name,
                        can_publish=False,
                        can_subscribe=True,
                        hidden=True,
                    )
                )
                .to_jwt()
            )
            await rec_room.connect(os.environ["LIVEKIT_URL"], token)
        noise = None
        if config["noise"] != "none":
            from livekit.plugins import noise_cancellation

            noise = {
                "bvc": noise_cancellation.BVC,
                "telephony": noise_cancellation.BVCTelephony,
                "krisp": noise_cancellation.NC,
            }[config["noise"]]()
        await session.start(
            agent=Sophie(config),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                participant_identity=participant.identity,
                audio_input=room_io.AudioInputOptions(noise_cancellation=noise),
            ),
        )
        if config["thinking_sound"] or config.get("background_sound", "none") != "none" or any(
            config.get("natural", {}).get("tags", {}).get(name, 0) > 0
            for name in ("sneeze", "throat")
        ):
            from livekit.agents import (
                BackgroundAudioPlayer,
                AudioConfig,
                BuiltinAudioClip,
            )

            ambience = {
                "office": BuiltinAudioClip.OFFICE_AMBIENCE,
                "city": BuiltinAudioClip.CITY_AMBIENCE,
                "forest": BuiltinAudioClip.FOREST_AMBIENCE,
                "crowd": BuiltinAudioClip.CROWDED_ROOM,
            }.get(config.get("background_sound", "none"))
            bg = BackgroundAudioPlayer(
                ambient_sound=AudioConfig(ambience, volume=config.get("background_volume", 0.15)) if ambience else None,
                thinking_sound=AudioConfig(BuiltinAudioClip.KEYBOARD_TYPING, volume=0.3) if config["thinking_sound"] else None,
            )
            await bg.start(room=ctx.room, agent_session=session)

        async def periodic():
            while True:
                await sync()
                await asyncio.sleep(2)

        async def deadline():
            await asyncio.sleep(config["max_duration"])
            closed.set()

        sync_task = asyncio.create_task(periodic())
        timer = asyncio.create_task(deadline())
        # Browser dispatch can precede microphone connection. Wait for a real participant.
        if config["greeting"]:
            if config["mode"] == "pipeline":
                session.say(
                    config["greeting"],
                    allow_interruptions=options.get("allow_interruptions", True),
                )
            else:
                session.generate_reply(
                    instructions="Dis cette phrase pour accueillir : "
                    + config["greeting"]
                )
        await closed.wait()
        await finish()
        from livekit import api

        try:
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
        except Exception:
            pass
    except Exception as error:
        log.exception("Essai vocal échoué")
        if stats:
            await sync(
                "failed",
                error=f"{type(error).__name__} : échec du worker. Consultez ses logs privés pour le détail.",
            )
        finished = True
        if sync_task:
            sync_task.cancel()
        if timer:
            timer.cancel()
        if session:
            await session.aclose()
        if recorder:
            await recorder.finish()
        if rec_room:
            await rec_room.disconnect()
        for resource in resources:
            await resource.close()
        await client.aclose()
        from livekit import api

        try:
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
        except Exception:
            pass
        raise


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=os.getenv("LIVEKIT_AGENT_NAME", "rushh-bench"),
        )
    )
