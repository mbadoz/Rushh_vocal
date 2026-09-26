import hashlib, hmac, json, os, time, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from cryptography.fernet import Fernet
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import httpx
from .catalog import CATALOG, DEFAULT, PROVIDERS, prices
from .models import Composition
from .store import db, get, put, listing, Document
from .costs import cost, compare, percentile


def now():
    return datetime.now(timezone.utc).isoformat()


def required(name):
    value = os.getenv(name)
    if not value:
        raise HTTPException(503, f"Configuration serveur manquante : {name}")
    return value


def signer():
    return URLSafeTimedSerializer(required("SESSION_SECRET"), salt="rushh-bench")


def vault():
    return Fernet(required("ENCRYPTION_KEY").encode())


@asynccontextmanager
async def lifespan(app):
    with db() as s:
        if not get(s, "composition:default"):
            put(
                s,
                "composition:default",
                "composition",
                dict(id="composition:default", config=DEFAULT, updated_at=now()),
            )
            put(s, "active", "setting", {"id": "composition:default"})
        if not get(s, "quota-lock"):
            put(s, "quota-lock", "setting", {"version": 0})
        for p in prices():
            if not get(s, "price:" + p["id"]):
                put(s, "price:" + p["id"], "price", p)
    yield


app = FastAPI(title="Rushh — Banc vocal", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def guard(request, call_next):
    if request.method not in (
        "GET",
        "HEAD",
        "OPTIONS",
    ) and not request.url.path.startswith("/internal/"):
        origin = request.headers.get("origin")
        allowed = {
            os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000"),
            str(request.base_url).rstrip("/"),
        }
        if origin and origin not in allowed:
            return Response(
                json.dumps({"detail": "Origine refusée : vérifiez FRONTEND_ORIGIN."}),
                403,
                media_type="application/json",
            )
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def auth(request: Request):
    try:
        signer().loads(request.cookies.get("rushh_session", ""), max_age=43200)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Connexion requise")


def worker_auth(request: Request):
    if not hmac.compare_digest(
        request.headers.get("authorization", ""), "Bearer " + required("WORKER_SECRET")
    ):
        raise HTTPException(401, "Worker non autorisé")


attempts = {}


class Login(BaseModel):
    password: str = Field(max_length=1024)


@app.post("/api/login")
def login(body: Login, request: Request, response: Response):
    ip = request.client.host if request.client else "unknown"
    ts = time.monotonic()
    previous = [t for t in attempts.get(ip, []) if ts - t < 60]
    attempts[ip] = previous
    if len(previous) >= 10:
        raise HTTPException(429, "Réessayez dans une minute")
    attempts[ip].append(ts)
    if not hmac.compare_digest(body.password, required("BENCH_PASSWORD")):
        raise HTTPException(401, "Mot de passe incorrect")
    response.set_cookie(
        "rushh_session",
        signer().dumps("bench"),
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false") == "true",
        samesite="lax",
        max_age=43200,
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie("rushh_session")
    return {"ok": True}


@app.get("/api/me", dependencies=[Depends(auth)])
def me():
    return {"authenticated": True}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/catalog", dependencies=[Depends(auth)])
def catalog():
    parameters = json.loads(Path(__file__).with_name("parameters.json").read_text())
    models = [{**m, "parameters": parameters.get(m["id"], [])} for m in CATALOG]
    return {
        "models": models,
        "default": DEFAULT,
        "providers": {k: {"signup": v[1]} for k, v in PROVIDERS.items()},
    }


@app.get("/api/compositions", dependencies=[Depends(auth)])
def compositions():
    with db() as s:
        return {"items": listing(s, "composition"), "active": get(s, "active")}


@app.post("/api/compositions", dependencies=[Depends(auth)])
def save(body: Composition):
    key = "composition:" + str(uuid.uuid4())
    with db() as s:
        return put(
            s,
            key,
            "composition",
            dict(id=key, config=body.model_dump(), updated_at=now()),
        )


@app.put("/api/compositions/{key}", dependencies=[Depends(auth)])
def update(key: str, body: Composition):
    with db() as s:
        if not get(s, key, "composition"):
            raise HTTPException(404, "Composition introuvable")
        return put(
            s,
            key,
            "composition",
            dict(id=key, config=body.model_dump(), updated_at=now()),
        )


@app.post("/api/compositions/{key}/activate", dependencies=[Depends(auth)])
def activate(key: str):
    with db() as s:
        if not get(s, key, "composition"):
            raise HTTPException(404, "Composition introuvable")
        return put(s, "active", "setting", {"id": key})


class KeyInput(BaseModel):
    key: str = Field(min_length=1, max_length=20000)
    extras: dict[str, str] = Field(default_factory=dict)
    internal_rates: dict[str, float] = Field(default_factory=dict)


def provider_check(provider):
    if provider not in PROVIDERS:
        raise HTTPException(404, "Fournisseur inconnu")


def key_value(s, provider, source):
    provider_check(provider)
    if source == "stored":
        entry = get(s, "key:" + provider)
        if not entry:
            raise HTTPException(409, f"Clé enregistrée manquante : {provider}")
        return json.loads(vault().decrypt(entry["encrypted"].encode()))
    key = os.getenv(PROVIDERS[provider][0])
    if not key:
        raise HTTPException(409, f"Clé environnement manquante : {provider}")
    return {
        "key": key,
        "extras": {"region": os.getenv("AZURE_SPEECH_REGION", "francecentral")},
        "internal_rates": {},
    }


@app.get("/api/keys", dependencies=[Depends(auth)])
def keys():
    with db() as s:
        out = []
        for provider, (env, signup, _) in PROVIDERS.items():
            value = get(s, "key:" + provider)
            ek = os.getenv(env)
            out.append(
                dict(
                    provider=provider,
                    signup=signup,
                    stored=bool(value),
                    env=bool(ek),
                    suffix=value.get("suffix") if value else None,
                    env_suffix=ek[-4:] if ek else None,
                    status=value.get("status", "untested") if value else "missing",
                    internal_rates=value.get("internal_rates", {}) if value else {},
                    extras=value.get("extras", {}) if value else {},
                )
            )
        return out


@app.put("/api/keys/{provider}", dependencies=[Depends(auth)])
def save_key(provider: str, body: KeyInput):
    provider_check(provider)
    if any(v < 0 for v in body.internal_rates.values()):
        raise HTTPException(422, "Tarif négatif")
    endpoint = body.extras.get("endpoint")
    if endpoint:
        from urllib.parse import urlparse

        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not (parsed.hostname or "").endswith(
            ".speech.microsoft.com"
        ):
            raise HTTPException(422, "Endpoint Azure Speech HTTPS requis")
    encrypted = vault().encrypt(json.dumps(body.model_dump()).encode()).decode()
    with db() as s:
        put(
            s,
            "key:" + provider,
            "key",
            dict(
                encrypted=encrypted,
                suffix=body.key[-4:],
                status="untested",
                extras=body.extras,
                internal_rates=body.internal_rates,
            ),
        )
    return {"ok": True}


@app.delete("/api/keys/{provider}", dependencies=[Depends(auth)])
def delete_key(provider: str):
    provider_check(provider)
    with db() as s:
        row = s.get(Document, "key:" + provider)
        if row:
            s.delete(row)
    return {"ok": True}


@app.post("/api/keys/{provider}/test", dependencies=[Depends(auth)])
async def test_key(provider: str, source: str = "stored"):
    if source not in ("stored", "env"):
        raise HTTPException(422, "Source inconnue")
    with db() as s:
        k = key_value(s, provider, source)
    url = PROVIDERS[provider][2]
    headers = {"Authorization": "Bearer " + k["key"]}
    if provider == "azure":
        region = k["extras"].get("region", "francecentral")
        if not region.isalnum():
            raise HTTPException(422, "Région invalide")
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
        headers = {"Ocp-Apim-Subscription-Key": k["key"]}
    if not url:
        return {
            "status": "unsupported",
            "message": "Validation par un essai vocal requise pour ce fournisseur.",
        }
    if provider == "google":
        if k["key"].lstrip().startswith("{"):
            import asyncio
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request as GoogleRequest

            try:
                credentials = service_account.Credentials.from_service_account_info(
                    json.loads(k["key"]),
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                await asyncio.to_thread(credentials.refresh, GoogleRequest())
            except Exception:
                return {
                    "status": "invalid",
                    "message": "Compte de service Google non validé.",
                }
            headers = {"Authorization": "Bearer " + credentials.token}
            url = "https://texttospeech.googleapis.com/v1/voices"
        else:
            headers = {"x-goog-api-key": k["key"]}
    if provider == "anthropic":
        headers = {"x-api-key": k["key"], "anthropic-version": "2023-06-01"}
    if provider == "cartesia":
        headers = {"X-API-Key": k["key"], "Cartesia-Version": "2026-08-14"}
    if provider == "elevenlabs":
        headers = {"xi-api-key": k["key"]}
    if provider == "gladia":
        headers = {"x-gladia-key": k["key"]}
    if provider == "assemblyai":
        headers = {"authorization": k["key"]}
    if provider == "hume":
        headers = {"X-Hume-Api-Key": k["key"]}
    if provider == "ultravox":
        headers = {"X-API-Key": k["key"]}
    if provider == "deepgram":
        headers = {"Authorization": "Token " + k["key"]}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, headers=headers)
        status = (
            "valid"
            if r.is_success
            else "quota"
            if r.status_code in (402, 429)
            else "invalid"
            if r.status_code in (401, 403)
            else "unavailable"
        )
    except httpx.HTTPError:
        status = "unavailable"
    if source == "stored":
        with db() as s:
            entry = get(s, "key:" + provider)
            if entry:
                put(s, "key:" + provider, "key", {**entry, "status": status})
    return {"status": status}


@app.get("/api/prices", dependencies=[Depends(auth)])
def get_prices():
    with db() as s:
        return {
            "items": listing(s, "price"),
            "usd_to_eur": float(os.getenv("USD_TO_EUR", ".92")),
        }


class Price(BaseModel):
    id: str
    currency: str = Field(pattern="^(USD|EUR)$")
    rates: dict[str, float]
    source: str = Field(max_length=2000)
    checked_at: str | None = None
    status: str = "manual"
    note: str = ""


@app.put("/api/prices", dependencies=[Depends(auth)])
def save_price(body: Price):
    import math

    if any(not math.isfinite(v) or v < 0 for v in body.rates.values()):
        raise HTTPException(422, "Tarif invalide")
    with db() as s:
        return put(s, "price:" + body.id, "price", body.model_dump())


def new_run(s, config, channel):
    # Price/key-source/config snapshots preserve reproducibility after later edits.
    config = Composition.model_validate(config).model_dump()
    allprices = {p["id"]: p for p in listing(s, "price")}
    for kind in ["stt", "llm", "tts"] if config["mode"] == "pipeline" else ["realtime"]:
        b = config[kind]
        if b["source"] != "inference" and b["provider"] != "livekit":
            creds = key_value(s, b["provider"], b["source"])
            if creds.get("internal_rates"):
                key = f"{kind}:{b['provider']}:{b['model']}"
                allprices[key] = {
                    **allprices.get(key, {}),
                    "rates": creds["internal_rates"],
                    "currency": "EUR",
                    "status": "internal",
                }
    from sqlalchemy import update

    s.execute(
        update(Document)
        .where(Document.id == "quota-lock")
        .values(value={"updated_at": now()})
    )
    rows = listing(s, "run")
    month = now()[:7]
    for row in rows:
        age = (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(row.get("updated_at", row["created_at"]))
        ).total_seconds()
        if (
            row["status"] in ("starting", "running")
            and age > row["config"]["max_duration"] + 180
        ):
            row.update(
                status="failed",
                error="Worker absent ou interrompu : dernières mesures conservées.",
            )
            put(s, row["id"], "run", row)
    running = [r for r in rows if r["status"] in ("starting", "running")]
    if len(running) >= 5:
        raise HTTPException(
            409, "Cinq essais sont déjà en cours. Terminez un essai avant de continuer."
        )
    used = sum(
        r.get("duration", 0) / 60 for r in rows if r["created_at"].startswith(month)
    )
    reserved = sum(
        max(0, r["config"]["max_duration"] - r.get("duration", 0)) / 60
        for r in rows
        if r["status"] in ("starting", "running") and r["created_at"].startswith(month)
    )
    if used + reserved + config["max_duration"] / 60 > float(
        os.getenv("MONTHLY_MINUTES_LIMIT", "1000")
    ):
        raise HTTPException(409, "Quota mensuel réservé ou consommé")
    key = str(uuid.uuid4())
    r = dict(
        id=key,
        composition_version=hashlib.sha256(
            json.dumps(config, sort_keys=True).encode()
        ).hexdigest()[:16],
        config=config,
        channel=channel,
        created_at=now(),
        status="starting",
        duration=0,
        usage={},
        events=[],
        turns=[],
        transcript=[],
        rating=None,
        comment="",
        price_snapshot=allprices,
        fx=float(os.getenv("USD_TO_EUR", ".92")),
        cost={
            "eur": 0,
            "complete": False,
            "missing": ["Essai non terminé"],
            "lines": [],
        },
        room="bench-" + key,
    )
    put(s, key, "run", r)
    return r


class Start(BaseModel):
    composition_id: str


@app.post("/api/runs", dependencies=[Depends(auth)])
async def start(body: Start):
    from livekit import api

    required("LIVEKIT_URL")
    required("LIVEKIT_API_KEY")
    required("LIVEKIT_API_SECRET")
    with db() as s:
        c = get(s, body.composition_id, "composition")
        if not c:
            raise HTTPException(404, "Composition introuvable")
        r = new_run(s, c["config"], "web")
    try:
        async with api.LiveKitAPI() as lk:
            await lk.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    room=r["room"],
                    agent_name=os.getenv("LIVEKIT_AGENT_NAME", "rushh-bench"),
                    metadata=json.dumps({"run_id": r["id"]}),
                )
            )
        token = (
            api.AccessToken()
            .with_identity("tester-" + r["id"])
            .with_ttl(timedelta(minutes=35))
            .with_grants(api.VideoGrants(room_join=True, room=r["room"]))
            .to_jwt()
        )
        return {"id": r["id"], "token": token, "url": os.environ["LIVEKIT_URL"]}
    except Exception:
        with db() as s:
            put(
                s,
                r["id"],
                "run",
                {
                    **r,
                    "status": "failed",
                    "error": "Échec de connexion à LiveKit. Vérifiez les identifiants et le worker.",
                },
            )
        raise HTTPException(502, "LiveKit indisponible")


@app.get("/api/runs", dependencies=[Depends(auth)])
def runs():
    with db() as s:
        rows = listing(s, "run")
        summaries = [
            {k: v for k, v in r.items() if k not in ("price_snapshot", "events")}
            for r in rows
        ]
        return {
            "items": sorted(summaries, key=lambda r: r["created_at"], reverse=True),
            "minutes_month": sum(
                r.get("duration", 0) / 60
                for r in rows
                if r["created_at"].startswith(now()[:7])
            ),
            "limit": float(os.getenv("MONTHLY_MINUTES_LIMIT", "1000")),
        }


@app.get("/api/runs/{key}", dependencies=[Depends(auth)])
def run(key: str):
    with db() as s:
        r = get(s, key, "run")
    if not r:
        raise HTTPException(404, "Essai introuvable")
    return r


class Rating(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str = Field(default="", max_length=5000)


@app.put("/api/runs/{key}/rating", dependencies=[Depends(auth)])
def rating(key: str, body: Rating):
    with db() as s:
        r = get(s, key, "run", lock=True)
        if not r:
            raise HTTPException(404, "Essai introuvable")
        return put(s, key, "run", {**r, **body.model_dump()})


@app.post("/api/runs/{key}/stop", dependencies=[Depends(auth)])
async def stop(key: str):
    from livekit import api

    r = run(key)
    if r["status"] in ("starting", "running"):
        try:
            async with api.LiveKitAPI() as lk:
                await lk.room.delete_room(api.DeleteRoomRequest(room=r["room"]))
        except Exception:
            raise HTTPException(502, "Impossible de fermer la room LiveKit")
        with db() as s:
            current = get(s, key, "run")
            if current["status"] == "starting":
                put(s, key, "run", {**current, "status": "cancelled"})
    return {"ok": True}


@app.get("/api/compare", dependencies=[Depends(auth)])
def comparison():
    with db() as s:
        return compare(listing(s, "run"))


class Claim(BaseModel):
    run_id: str | None = None
    room: str


@app.post("/internal/claim", dependencies=[Depends(worker_auth)])
def claim(body: Claim):
    with db() as s:
        if body.run_id:
            r = get(s, body.run_id, "run", lock=True)
            if not r or r["room"] != body.room:
                raise HTTPException(404, "Essai introuvable")
            if r["status"] != "starting":
                raise HTTPException(409, "Essai déjà démarré ou terminé")
        else:
            active = get(s, "active")
            c = get(s, active["id"], "composition") if active else None
            if not c:
                raise HTTPException(409, "Aucune composition active")
            r = new_run(s, c["config"], "phone")
            r["room"] = body.room
        creds = {}
        for kind in (
            ["stt", "llm", "tts"] if r["config"]["mode"] == "pipeline" else ["realtime"]
        ):
            b = r["config"][kind]
            if b["source"] != "inference" and b["provider"] != "livekit":
                creds[kind] = key_value(s, b["provider"], b["source"])
        r = {**r, "status": "running"}
        put(s, r["id"], "run", r)
        return {"run": r, "credentials": creds}


class Telemetry(BaseModel):
    status: str = Field(pattern="^(running|completed|failed)$")
    duration: float = Field(ge=0, le=86400)
    usage: dict[str, dict[str, float]]
    transcript: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    error: str | None = None
    recording_error: str | None = None


@app.put("/internal/runs/{key}", dependencies=[Depends(worker_auth)])
def telemetry(key: str, body: Telemetry):
    import math

    if any(
        not math.isfinite(v) or v < 0
        for counts in body.usage.values()
        for v in counts.values()
    ):
        raise HTTPException(422, "Usage invalide")
    with db() as s:
        r = get(s, key, "run", lock=True)
        if not r:
            raise HTTPException(404, "Essai introuvable")
        data = body.model_dump()
        data["updated_at"] = now()
        data["cost"] = cost(data["usage"], r["price_snapshot"], r["fx"])
        data["median_ms"] = percentile(
            [t["latency_ms"] for t in body.turns if t.get("latency_ms") is not None],
            0.5,
        )
        if body.status == "running" and r["status"] in ("completed", "failed"):
            return {"ok": True}
        put(s, key, "run", {**r, **data})
        return {"ok": True}


@app.put("/internal/runs/{key}/audio", dependencies=[Depends(worker_auth)])
async def upload_audio(key: str, request: Request):
    run(key)
    path = Path("/tmp/rushh-audio" if os.getenv("VERCEL") else "data/audio")
    path.mkdir(parents=True, exist_ok=True)
    target = path / (key + ".wav")
    size = 0
    with target.open("wb") as f:
        async for chunk in request.stream():
            size += len(chunk)
            if size > 200_000_000:
                f.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, "Audio trop volumineux")
            f.write(chunk)
    object_key = "runs/" + key + ".wav"
    if os.getenv("R2_BUCKET"):
        import asyncio

        await asyncio.to_thread(
            r2().upload_file,
            str(target),
            os.environ["R2_BUCKET"],
            object_key,
            ExtraArgs={"ContentType": "audio/wav"},
        )
        target.unlink()
    with db() as s:
        r = get(s, key, "run")
        put(
            s,
            key,
            "run",
            {**r, "audio": object_key if os.getenv("R2_BUCKET") else str(target)},
        )
    return {"ok": True}


def r2():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=required("R2_ENDPOINT"),
        aws_access_key_id=required("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=required("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


@app.get("/api/runs/{key}/audio", dependencies=[Depends(auth)])
def audio(key: str):
    r = run(key)
    if not r.get("audio"):
        raise HTTPException(404, "Audio non disponible")
    if r["audio"].startswith("runs/"):
        return RedirectResponse(
            r2().generate_presigned_url(
                "get_object",
                Params={"Bucket": required("R2_BUCKET"), "Key": r["audio"]},
                ExpiresIn=300,
            )
        )
    return FileResponse(r["audio"], media_type="audio/wav")


@app.post("/internal/runs/{key}/audio-ready", dependencies=[Depends(worker_auth)])
async def audio_ready(key: str):
    import asyncio

    run(key)
    object_key = "runs/" + key + ".wav"
    try:
        await asyncio.to_thread(
            r2().head_object, Bucket=required("R2_BUCKET"), Key=object_key
        )
    except Exception:
        raise HTTPException(409, "Enregistrement R2 introuvable")
    with db() as s:
        r = get(s, key, "run")
        put(s, key, "run", {**r, "audio": object_key})
    return {"ok": True}
