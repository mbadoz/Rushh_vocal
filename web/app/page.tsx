"use client";
import React, { useEffect, useState, useCallback, useMemo } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  BarVisualizer,
  useVoiceAssistant,
  StartAudio,
  useConnectionState,
} from "@livekit/components-react";
import {
  SlidersHorizontal,
  Mic,
  History,
  ChartNoAxesCombined,
  KeyRound,
  Coins,
  AudioLines,
  Plus,
  ArrowUpRight,
  Phone,
  Play,
  Square,
  Save,
  LogOut,
  Check,
  ChevronRight,
  Headphones,
  FlaskConical,
} from "lucide-react";

type Obj = Record<string, any>;
async function api(path: string, method = "GET", body?: unknown) {
  if (body && method !== "GET" && path !== "/login") {
    const invalid =
      document.querySelector<HTMLTextAreaElement>("textarea:invalid");
    if (invalid) {
      invalid.reportValidity();
      throw new Error("Corrigez le JSON invalide avant d’enregistrer.");
    }
  }
  const r = await fetch("/api" + path, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r
    .json()
    .catch(() => ({ detail: "Réponse serveur illisible" }));
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail),
    );
  return data;
}
const tabs = [
  ["Composer", SlidersHorizontal],
  ["Tester", Mic],
  ["Historique", History],
  ["Comparatif", ChartNoAxesCombined],
  ["Prix", Coins],
  ["Clés API", KeyRound],
] as const;
const money = (n: number | undefined) =>
  n === undefined
    ? "—"
    : new Intl.NumberFormat("fr-FR", {
        style: "currency",
        currency: "EUR",
        minimumFractionDigits: 4,
      }).format(n);
const ms = (n: number | undefined | null) =>
  n == null ? "—" : Math.round(n) + " ms";
const naturalTags: Record<string, string> = {
  breath: "Respiration", sigh: "Soupir", throat: "Raclement de gorge",
  sneeze: "Éternuement", laugh: "Rire", short_pause: "Pause courte",
  long_pause: "Pause longue",
};
const withAudioDefaults = (source: Obj, defaults: Obj) => ({
  ...source,
  background_sound: source.background_sound ?? defaults.background_sound ?? "none",
  background_volume: source.background_volume ?? defaults.background_volume ?? 0.15,
  natural: {
    ...defaults.natural,
    ...source.natural,
    tags: { ...defaults.natural.tags, ...source.natural?.tags },
  },
});
function JsonField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: any;
  onChange: (v: any) => void;
}) {
  const [text, setText] = useState(JSON.stringify(value, null, 2));
  const [error, setError] = useState("");
  useEffect(() => setText(JSON.stringify(value, null, 2)), [value]);
  return (
    <label className="field full">
      {label}
      <textarea
        className="code"
        value={text}
        rows={Math.min(12, Math.max(3, text.split("\n").length))}
        onChange={(e) => {
          setText(e.target.value);
          try {
            const x = JSON.parse(e.target.value);
            if (!x || typeof x !== "object" || Array.isArray(x))
              throw Error("Un objet JSON est requis");
            onChange(x);
            setError("");
            e.target.setCustomValidity("");
          } catch {
            e.target.setCustomValidity("JSON invalide");
            setError(
              "JSON invalide : les modifications ne sont pas encore appliquées.",
            );
          }
        }}
      />
      {error && <small className="error">{error}</small>}
    </label>
  );
}
function Field({
  name,
  value,
  onChange,
}: {
  name: string;
  value: any;
  onChange: (v: any) => void;
}) {
  if (typeof value === "object")
    return <JsonField label={name} value={value} onChange={onChange} />;
  return (
    <label className={"field " + (typeof value === "boolean" ? "toggle" : "")}>
      {name.replaceAll("_", " ")}
      {typeof value === "boolean" ? (
        <input
          type="checkbox"
          checked={value}
          onChange={(e) => onChange(e.target.checked)}
        />
      ) : (
        <input
          type={typeof value === "number" ? "number" : "text"}
          step="any"
          value={value ?? ""}
          onChange={(e) =>
            onChange(
              typeof value === "number"
                ? Number(e.target.value)
                : e.target.value,
            )
          }
        />
      )}
    </label>
  );
}
function VoiceStatus() {
  const { state, audioTrack } = useVoiceAssistant();
  const connection = useConnectionState();
  return (
    <>
      <div className="voice-orb">
        <BarVisualizer state={state} trackRef={audioTrack} barCount={7} />
        <AudioLines size={42} />
      </div>
      <h2>
        {state === "speaking"
          ? "Sophie vous répond"
          : state === "listening"
            ? "À vous de parler"
            : state === "thinking"
              ? "Sophie réfléchit…"
              : "Connexion au worker…"}
      </h2>
      <p className="muted">
        {connection} · {state}
      </p>
      <StartAudio label="Activer le son" />
      <RoomAudioRenderer />
    </>
  );
}

export default function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null),
    [password, setPassword] = useState("");
  const [tab, setTab] = useState("Composer"),
    [catalog, setCatalog] = useState<Obj | null>(null),
    [compositions, setCompositions] = useState<Obj[]>([]),
    [keys, setKeys] = useState<Obj[]>([]),
    [active, setActive] = useState("");
  const [config, setConfig] = useState<Obj | null>(null),
    [selected, setSelected] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [runs, setRuns] = useState<Obj[]>([]),
    [quota, setQuota] = useState<Obj>({}),
    [detail, setDetail] = useState<Obj | null>(null),
    [prices, setPrices] = useState<Obj[]>([]),
    [fx, setFx] = useState(0),
    [comparison, setComparison] = useState<Obj[]>([]);
  const [call, setCall] = useState<Obj | null>(null),
    [live, setLive] = useState<Obj | null>(null),
    [sort, setSort] = useState("eur_per_min"),
    [filter, setFilter] = useState(""),
    [listen, setListen] = useState<string[]>([]);
  const [microphones, setMicrophones] = useState<MediaDeviceInfo[]>([]),
    [microphoneId, setMicrophoneId] = useState(""),
    [microphoneBusy, setMicrophoneBusy] = useState(false);
  const microphoneOptions = useMemo(
    () => ({
      deviceId: { exact: microphoneId },
      echoCancellation: true,
      noiseSuppression: true,
    }),
    [microphoneId],
  );
  const onRoomError = useCallback((e: Error) => setError(e.message), []);
  const detectMicrophones = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        "Le microphone nécessite un navigateur récent et une page HTTPS.",
      );
      return;
    }
    setMicrophoneBusy(true);
    setError("");
    let stream: MediaStream | undefined;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const devices = (await navigator.mediaDevices.enumerateDevices()).filter(
        (device) => device.kind === "audioinput" && device.deviceId,
      );
      const physical = devices.filter(
        (device) => !["default", "communications"].includes(device.deviceId),
      );
      const available = physical.length ? physical : devices;
      setMicrophones(available);
      setMicrophoneId((id) =>
        available.some((device) => device.deviceId === id) ? id : "",
      );
      if (!available.length)
        setError("Aucun microphone détecté sur cet appareil.");
    } catch (e) {
      setError(
        `Accès au microphone impossible : ${(e as Error).message}. Vérifiez l'autorisation du navigateur.`,
      );
    } finally {
      stream?.getTracks().forEach((track) => track.stop());
      setMicrophoneBusy(false);
    }
  };
  const execute = useCallback(async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);
  const refresh = useCallback(async () => {
    const [c, k, r, p, comp] = await Promise.all([
      api("/compositions"),
      api("/keys"),
      api("/runs"),
      api("/prices"),
      api("/compare"),
    ]);
    setCompositions(c.items);
    setActive(c.active?.id);
    setKeys(k);
    setRuns(r.items);
    setQuota(r);
    setPrices(p.items);
    setFx(p.usd_to_eur);
    setComparison(comp);
  }, []);
  useEffect(() => {
    api("/me")
      .then(() => setAuthenticated(true))
      .catch(() => setAuthenticated(false));
  }, []);
  useEffect(() => {
    if (authenticated)
      execute(async () => {
        const cat = await api("/catalog");
        setCatalog(cat);
        await refresh();
        const c = await api("/compositions");
        setSelected(c.items[0]?.id ?? "");
        setConfig(withAudioDefaults(c.items[0]?.config ?? cat.default, cat.default));
      });
  }, [authenticated, execute, refresh]);
  useEffect(() => {
    if (!call) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await api("/runs/" + call.id);
        if (!cancelled) {
          setLive(r);
          if (["completed", "failed", "cancelled"].includes(r.status)) {
            setCall(null);
            setDetail(r);
            await refresh();
          }
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    };
    poll();
    const timer = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [call, refresh]);
  const change = (k: string, v: any) => setConfig((c) => ({ ...c, [k]: v }));
  const save = async (copy = false) => {
    if (!config) return;
    const r = await api(
      copy || !selected ? "/compositions" : "/compositions/" + selected,
      copy || !selected ? "POST" : "PUT",
      config,
    );
    setSelected(r.id);
    await refresh();
    setNotice("Composition enregistrée.");
    return r.id;
  };
  const start = () =>
    execute(async () => {
      if (!microphoneId) {
        setTab("Tester");
        throw new Error(
          "Choisissez le microphone de votre ordinateur avant de commencer.",
        );
      }
      const id = await save();
      const r = await api("/runs", "POST", { composition_id: id });
      setCall(r);
      setLive(null);
      setTab("Tester");
    });
  const stop = () =>
    execute(async () => {
      if (call) {
        await api("/runs/" + call.id + "/stop", "POST");
        setCall(null);
        await refresh();
      }
    });
  const choose = (id: string) => {
    setSelected(id);
    setConfig(withAudioDefaults(structuredClone(compositions.find((c) => c.id === id)!.config), catalog!.default));
    setNotice("");
  };
  if (authenticated === null)
    return (
      <div className="login">
        <AudioLines size={36} />
        <p>Ouverture du banc…</p>
      </div>
    );
  if (!authenticated)
    return (
      <div className="login">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            execute(async () => {
              await api("/login", "POST", { password });
              setPassword("");
              setAuthenticated(true);
            });
          }}
        >
          <div className="brand">
            <span className="brand-icon">
              <AudioLines />
            </span>
            rushh<span className="brand-dot">.</span>
          </div>
          <span className="eyebrow">VOICE LAB</span>
          <h1>
            La bonne voix.
            <br />
            La bonne composition.
          </h1>
          <p>Connectez-vous à votre banc de test vocal.</p>
          <label className="field">
            Mot de passe
            <input
              autoComplete="current-password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="primary" disabled={busy}>
            Ouvrir le laboratoire <ArrowUpRight size={17} />
          </button>
        </form>
      </div>
    );
  const providerReady = (b: Obj) =>
    b.source === "inference" ||
    b.provider === "livekit" ||
    keys.some(
      (k) =>
        k.provider === b.provider && (b.source === "env" ? k.env : k.stored),
    );
  const blocks =
    config?.mode === "pipeline" ? ["stt", "llm", "tts"] : ["realtime"];
  const ready = config && blocks.every((k) => providerReady(config[k]));
  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <span className="brand-icon">
            <AudioLines />
          </span>
          rushh<span className="brand-dot">.</span>
        </div>
        <div className="workspace">
          <span className="workspace-icon">
            <FlaskConical size={18} />
          </span>
          <div>
            Laboratoire vocal<small>Espace de test</small>
          </div>
          <ChevronRight size={15} />
        </div>
        <span className="nav-label">BANC DE TEST</span>
        <nav>
          {tabs.map(([label, Icon]) => (
            <button
              key={label}
              className={tab === label ? "nav active" : "nav"}
              onClick={() => {
                setTab(label);
                setDetail(null);
                if (label !== "Composer") execute(refresh);
              }}
            >
              <Icon size={19} />
              {label}
              {tab === label && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="quota">
            <span>
              Minutes ce mois-ci{" "}
              <b>
                {Math.round(quota.minutes_month ?? 0)} / {quota.limit ?? 1000}
              </b>
            </span>
            <progress
              value={quota.minutes_month ?? 0}
              max={quota.limit ?? 1000}
            />
            <small>Quota de sessions LiveKit</small>
          </div>
          <button
            className="nav"
            onClick={() =>
              execute(async () => {
                if (call) await api("/runs/" + call.id + "/stop", "POST");
                setCall(null);
                await api("/logout", "POST");
                setAuthenticated(false);
              })
            }
          >
            <LogOut size={17} />
            Déconnexion
          </button>
          <small className="version">RUSHH VOICE LAB · V0.1</small>
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Laboratoire <ChevronRight size={14} /> <b>{tab}</b>
          </div>
          <span className="pill">
            <span className="green-dot" />
            Environnement de test
          </span>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <span className="eyebrow">ÉCOUTER. MESURER. CHOISIR.</span>
              <h1>
                {tab === "Composer"
                  ? "Composez votre agent."
                  : tab === "Tester"
                    ? "Place à la conversation."
                    : tab === "Historique"
                      ? "Chaque essai compte."
                      : tab === "Comparatif"
                        ? "Trouvez la bonne combinaison."
                        : tab === "Prix"
                          ? "Un coût transparent."
                          : "Connectez vos fournisseurs."}
              </h1>
              <p className="muted">
                {tab === "Composer"
                  ? "Assemblez les meilleurs modèles et trouvez la voix qui vous ressemble."
                  : tab === "Tester"
                    ? "Parlez naturellement. Les mesures sont collectées pendant votre échange."
                    : tab === "Clés API"
                      ? "Vos clés restent chiffrées sur le serveur. Choisissez leur source dans Composer."
                      : "Vos compositions, vos mesures, vos décisions."}
              </p>
            </div>
            {tab === "Composer" && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() => {
                  setSelected("");
                  setConfig(structuredClone(catalog!.default));
                  setNotice("Nouvelle composition prête à modifier.");
                }}
              >
                <Plus size={16} />
                Nouvelle composition
              </button>
            )}
          </div>
          {error && (
            <div role="alert" className="banner error">
              <b>Une action est nécessaire.</b> {error}
              <button onClick={() => setError("")}>Fermer</button>
            </div>
          )}
          {notice && (
            <div role="status" className="banner success">
              <Check size={16} />
              {notice}
              <button onClick={() => setNotice("")}>Fermer</button>
            </div>
          )}
          {tab === "Composer" && config && catalog && (
            <>
              <div className="composition-bar">
                <div className="composition-name">
                  <label className="field">
                    Composition
                    <select
                      value={selected}
                      onChange={(e) => choose(e.target.value)}
                    >
                      <option value="" disabled>
                        Nouvelle composition
                      </option>
                      {compositions.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.config.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Nom
                    <input
                      value={config.name}
                      onChange={(e) => change("name", e.target.value)}
                    />
                  </label>
                </div>
                <span className="pill">
                  {active === selected ? (
                    <>
                      <Phone size={13} />
                      Active pour le téléphone
                    </>
                  ) : (
                    "Brouillon / test web"
                  )}
                </span>
              </div>
              <div className="section-title">
                <div>
                  <h2>Architecture vocale</h2>
                  <p className="muted">
                    Trois briques indépendantes, ou un modèle qui fait tout.
                  </p>
                </div>
                <div className="segmented">
                  {["pipeline", "realtime"].map((mode) => (
                    <button
                      key={mode}
                      className={config.mode === mode ? "selected" : ""}
                      onClick={() => change("mode", mode)}
                    >
                      {mode === "pipeline"
                        ? "Pipeline STT → LLM → TTS"
                        : "Speech-to-speech"}
                    </button>
                  ))}
                </div>
              </div>
              <div
                className={
                  "pipeline " + (config.mode === "realtime" ? "single" : "")
                }
              >
                {blocks.map((kind, index) => {
                  const b = config[kind],
                    models = catalog.models.filter((x: Obj) => x.kind === kind),
                    entry = models.find(
                      (x: Obj) =>
                        x.provider === b.provider && x.model === b.model,
                    );
                  return (
                    <section className="model-card" key={kind}>
                      <div className="card-top">
                        <span className={"step step-" + index}>
                          {kind === "stt" ? (
                            <Mic size={19} />
                          ) : kind === "llm" ? (
                            <FlaskConical size={19} />
                          ) : (
                            <AudioLines size={19} />
                          )}
                        </span>
                        <span className="eyebrow">
                          0{index + 1} / {kind.toUpperCase()}
                        </span>
                        <span
                          className={
                            "status-dot " + (providerReady(b) ? "ok" : "")
                          }
                        />
                      </div>
                      <h2>
                        {kind === "stt"
                          ? "Comprendre"
                          : kind === "llm"
                            ? "Réfléchir"
                            : kind === "tts"
                              ? "Parler"
                              : "Converser"}
                      </h2>
                      <p className="muted card-caption">
                        {kind === "stt"
                          ? "La parole devient du texte."
                          : kind === "llm"
                            ? "Le sens devient une réponse."
                            : kind === "tts"
                              ? "Les mots prennent vie."
                              : "Une seule intelligence, de bout en bout."}
                      </p>
                      <label className="field">
                        Fournisseur
                        <select
                          value={b.provider}
                          onChange={(e) => {
                            const m = models.find(
                              (x: Obj) => x.provider === e.target.value,
                            );
                            change(kind, {
                              provider: m.provider,
                              model: m.model,
                              source:
                                m.provider === "livekit" ? "inference" : "env",
                              params: structuredClone(m.params),
                              raw: {},
                            });
                          }}
                        >
                          {Array.from(
                            new Set<string>(models.map((m: Obj) => m.provider)),
                          ).map((p) => (
                            <option key={p} value={p}>
                              {p[0].toUpperCase() + p.slice(1)}
                              {!keys.some(
                                (k) => k.provider === p && (k.env || k.stored),
                              ) && p !== "livekit"
                                ? " · clé requise"
                                : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="field">
                        Modèle
                        <select
                          value={b.model}
                          onChange={(e) => {
                            const m = models.find(
                              (x: Obj) =>
                                x.provider === b.provider &&
                                x.model === e.target.value,
                            );
                            change(kind, {
                              ...b,
                              model: m.model,
                              params: structuredClone(m.params),
                              raw: {},
                            });
                          }}
                        >
                          {models
                            .filter((m: Obj) => m.provider === b.provider)
                            .map((m: Obj) => (
                              <option key={m.model}>{m.model}</option>
                            ))}
                        </select>
                      </label>
                      <label className="field">
                        Accès
                        <select
                          value={b.source}
                          onChange={(e) =>
                            change(kind, {
                              ...b,
                              source: e.target.value,
                              params: structuredClone(
                                e.target.value === "inference"
                                  ? (entry?.inference_params ?? {})
                                  : entry?.params,
                              ),
                              raw: {},
                            })
                          }
                        >
                          <option
                            value="env"
                            disabled={b.provider === "livekit"}
                          >
                            Clé environnement
                          </option>
                          <option
                            value="stored"
                            disabled={b.provider === "livekit"}
                          >
                            Clé enregistrée
                          </option>
                          {entry?.inference && (
                            <option value="inference">LiveKit Inference</option>
                          )}
                        </select>
                      </label>
                      {!providerReady(b) && (
                        <button
                          className="missing-key"
                          onClick={() => setTab("Clés API")}
                        >
                          <KeyRound size={14} />
                          Ajouter une clé <ArrowUpRight size={14} />
                        </button>
                      )}
                      <details>
                        <summary>
                          Paramètres du modèle <SlidersHorizontal size={14} />
                        </summary>
                        <div className="params">
                          {Object.entries(b.params).map(([name, value]) => (
                            <Field
                              key={name}
                              name={name}
                              value={value}
                              onChange={(v) =>
                                change(kind, {
                                  ...b,
                                  params: { ...b.params, [name]: v },
                                })
                              }
                            />
                          ))}
                          <label className="field">
                            Ajouter un réglage du plugin
                            <select
                              value=""
                              onChange={(e) => {
                                const field = entry.parameters.find(
                                  (p: Obj) => p.name === e.target.value,
                                );
                                if (field)
                                  change(kind, {
                                    ...b,
                                    params: {
                                      ...b.params,
                                      [field.name]: structuredClone(
                                        field.value,
                                      ),
                                    },
                                  });
                              }}
                            >
                              <option value="">Choisir un paramètre…</option>
                              {(entry?.parameters ?? [])
                                .filter((p: Obj) => !(p.name in b.params))
                                .map((p: Obj) => (
                                  <option key={p.name} value={p.name}>
                                    {p.name}
                                  </option>
                                ))}
                            </select>
                          </label>
                          <JsonField
                            label="Tous les paramètres du plugin (JSON)"
                            value={b.params}
                            onChange={(v) => change(kind, { ...b, params: v })}
                          />
                          <JsonField
                            label="Paramètres API bruts (JSON)"
                            value={b.raw}
                            onChange={(v) => change(kind, { ...b, raw: v })}
                          />
                          <small className="muted">
                            Fusionnés dans la requête finale. Un transport non
                            pris en charge renvoie une erreur explicite.
                          </small>
                        </div>
                      </details>
                    </section>
                  );
                })}
              </div>
              <section className="panel">
                <div className="section-title">
                  <div>
                    <h2>Personnalité & conversation</h2>
                    <p className="muted">
                      Donnez un rôle, une intention et un rythme à votre agent.
                    </p>
                  </div>
                  <span className="pill">Français</span>
                </div>
                <label className="field">
                  Instructions de l’agent
                  <textarea
                    rows={5}
                    value={config.prompt}
                    onChange={(e) => change("prompt", e.target.value)}
                  />
                </label>
                <label className="field">
                  Première phrase
                  <input
                    value={config.greeting}
                    onChange={(e) => change("greeting", e.target.value)}
                  />
                </label>
                <div className="accordion-grid">
                  <details>
                    <summary>Naturel & balises vocales</summary>
                    <div className="params">
                      <label className="field">
                        Insertion des balises
                        <select
                          value={config.natural.mode}
                          onChange={(e) =>
                            change("natural", {
                              ...config.natural,
                              mode: e.target.value,
                            })
                          }
                        >
                          <option value="none">Désactivée</option>
                          <option value="llm">Par le LLM</option>
                          <option value="rules">Par le worker</option>
                          <option value="both">Les deux</option>
                        </select>
                      </label>
                      <label className="field">
                        Hésitations
                        <select
                          value={config.natural.hesitations}
                          onChange={(e) =>
                            change("natural", {
                              ...config.natural,
                              hesitations: e.target.value,
                            })
                          }
                        >
                          <option value="none">Aucune</option>
                          <option value="light">Légères</option>
                          <option value="marked">Marquées</option>
                        </select>
                      </label>
                      {Object.entries(config.natural.tags).map(
                        ([tag, rate]) => (
                          <label key={tag} className="field">
                            {naturalTags[tag] ?? tag}{" "}
                            · {Math.round(Number(rate) * 100)} %
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.05"
                              value={Number(rate)}
                              onChange={(e) =>
                                change("natural", {
                                  ...config.natural,
                                  tags: {
                                    ...config.natural.tags,
                                    [tag]: Number(e.target.value),
                                  },
                                })
                              }
                            />
                          </label>
                        ),
                      )}
                      <label className="field">
                        « Oui / OK / Hum hum » après une longue phrase et une reprise · {Math.round(Number(config.natural.long_reply_ack ?? 0) * 100)} %
                        <input type="range" min="0" max="1" step="0.05"
                          value={Number(config.natural.long_reply_ack ?? 0)}
                          onChange={(e) => change("natural", { ...config.natural, long_reply_ack: Number(e.target.value) })}
                        />
                      </label>
                      <p className="muted">
                        En mode pipeline, les éternuements et raclements sont des sons préenregistrés joués pendant la parole de l’utilisateur. Un acquiescement peut suivre une longue phrase, une courte pause et la reprise de l’appelant ; ce curseur règle sa fréquence. Les autres balises dépendent du TTS choisi.
                      </p>
                    </div>
                  </details>
                  <details>
                    <summary>Détection, interruptions & audio</summary>
                    <div className="params">
                      <JsonField
                        label="Paramètres de session LiveKit"
                        value={config.session}
                        onChange={(v) => change("session", v)}
                      />
                      <JsonField
                        label="VAD Silero"
                        value={config.vad}
                        onChange={(v) => change("vad", v)}
                      />
                      <label className="field">
                        Réduction de bruit
                        <select
                          value={config.noise}
                          onChange={(e) => change("noise", e.target.value)}
                        >
                          {["none", "bvc", "telephony", "krisp"].map((x) => (
                            <option key={x}>{x}</option>
                          ))}
                        </select>
                      </label>
                      <Field
                        name="Sons de réflexion"
                        value={config.thinking_sound}
                        onChange={(v) => change("thinking_sound", v)}
                      />
                      <label className="field">
                        Ambiance sonore
                        <select value={config.background_sound ?? "none"}
                          onChange={(e) => change("background_sound", e.target.value)}>
                          <option value="none">Aucune</option>
                          <option value="office">Bureau</option>
                          <option value="city">Ville</option>
                          <option value="forest">Forêt</option>
                          <option value="crowd">Salle animée</option>
                        </select>
                      </label>
                      <label className="field">
                        Volume de l’ambiance · {Math.round(Number(config.background_volume ?? 0.15) * 100)} %
                        <input type="range" min="0" max="1" step="0.01"
                          value={Number(config.background_volume ?? 0.15)}
                          onChange={(e) => change("background_volume", Number(e.target.value))}
                        />
                      </label>
                      <Field
                        name="Enregistrer les deux voix"
                        value={config.record_audio}
                        onChange={(v) => change("record_audio", v)}
                      />
                      <Field
                        name="Durée maximale (secondes)"
                        value={config.max_duration}
                        onChange={(v) => change("max_duration", v)}
                      />
                    </div>
                  </details>
                  <details>
                    <summary>Outils simulés & données de test</summary>
                    <div className="params">
                      <JsonField
                        label="Outils activés et résultats factices"
                        value={config.tools}
                        onChange={(v) => change("tools", v)}
                      />
                      <p className="muted">
                        Supprimez une entrée pour désactiver un outil. Aucun
                        rendez-vous ou transfert réel n’est effectué.
                      </p>
                    </div>
                  </details>
                </div>
              </section>
              <div className="action-bar">
                <div className="muted">
                  <span className="green-dot" />
                  Vos réglages s’appliqueront au prochain essai.
                </div>
                <div className="actions">
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      execute(async () => {
                        await save(true);
                      })
                    }
                  >
                    Dupliquer
                  </button>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      execute(async () => {
                        const id = await save();
                        await api("/compositions/" + id + "/activate", "POST");
                        await refresh();
                        setNotice(
                          "Composition active pour les prochains appels téléphoniques.",
                        );
                      })
                    }
                  >
                    <Phone size={16} />
                    Activer téléphone
                  </button>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() =>
                      execute(async () => {
                        await save();
                      })
                    }
                  >
                    <Save size={16} />
                    Enregistrer
                  </button>
                  <button
                    className="primary"
                    disabled={busy || !ready || !!call}
                    onClick={() => {
                      if (!microphoneId) {
                        setTab("Tester");
                        setNotice(
                          "Choisissez le microphone de votre ordinateur.",
                        );
                      } else start();
                    }}
                  >
                    <Mic size={16} />
                    Tester cette composition
                  </button>
                </div>
              </div>
            </>
          )}
          {(tab === "Tester" || call) && (
            <div hidden={tab !== "Tester"}>
              <div className="test-grid">
                <section className="panel voice-panel">
                  <span className="eyebrow">SESSION VOCALE</span>
                  {call ? (
                    <LiveKitRoom
                      token={call.token}
                      serverUrl={call.url}
                      connect
                      audio={microphoneOptions}
                      video={false}
                      onError={onRoomError}
                    >
                      <VoiceStatus />
                      <p className="muted">
                        Micro utilisé :{" "}
                        {microphones.find(
                          (device) => device.deviceId === microphoneId,
                        )?.label || "micro sélectionné"}
                      </p>
                      <button className="danger" disabled={busy} onClick={stop}>
                        <Square size={16} />
                        Terminer l’essai
                      </button>
                    </LiveKitRoom>
                  ) : (
                    <>
                      <div className="voice-orb idle">
                        <Mic size={38} />
                      </div>
                      <h2>Testez en conditions réelles.</h2>
                      <p className="muted">
                        Choisissez le micro de votre ordinateur et échangez avec
                        votre agent.
                        <br />
                        Un casque est recommandé.
                      </p>
                      <button
                        className="secondary"
                        disabled={microphoneBusy}
                        onClick={detectMicrophones}
                      >
                        <Mic size={16} />
                        {microphoneBusy
                          ? "Recherche des micros…"
                          : "Détecter les micros"}
                      </button>
                      {microphones.length > 0 && (
                        <label className="field">
                          Microphone utilisé
                          <select
                            value={microphoneId}
                            onChange={(e) => setMicrophoneId(e.target.value)}
                          >
                            <option value="" disabled>
                              Choisir le micro du PC
                            </option>
                            {microphones.map((device) => (
                              <option
                                key={device.deviceId}
                                value={device.deviceId}
                              >
                                {device.label || "Microphone sans nom"}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                      <label className="field">
                        Composition
                        <select
                          value={selected}
                          onChange={(e) => choose(e.target.value)}
                        >
                          {compositions.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.config.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        className="primary"
                        disabled={busy || !ready || !microphoneId}
                        onClick={start}
                      >
                        <Mic size={17} />
                        Commencer l’essai
                      </button>
                    </>
                  )}
                  <small className="muted">
                    {call
                      ? "Enregistrement selon les réglages de la composition."
                      : "Les appels utilisent les crédits de vos fournisseurs."}
                  </small>
                </section>
                <section className="panel transcript-panel">
                  <div className="section-title">
                    <h2>Transcription</h2>
                    <span className="pill">
                      {call ? "En direct" : "En attente"}
                    </span>
                  </div>
                  {(live?.transcript ?? []).length === 0 ? (
                    <div className="empty">
                      <AudioLines />
                      <p>La conversation apparaîtra ici.</p>
                    </div>
                  ) : (
                    live!.transcript.map((t: Obj, i: number) => (
                      <div className={"message " + t.role} key={i}>
                        <b>{t.role === "user" ? "Vous" : "Agent"}</b>
                        <p>{t.text}</p>
                        {t.interrupted && <small>Interrompu</small>}
                      </div>
                    ))
                  )}
                  <div className="live-stats">
                    <div>
                      <small>Durée</small>
                      <b>{Math.round(live?.duration ?? 0)} s</b>
                    </div>
                    <div>
                      <small>Coût mesuré</small>
                      <b>
                        {money(live?.cost?.eur)}
                        {live && !live.cost.complete ? " *" : ""}
                      </b>
                    </div>
                    <div>
                      <small>Latence médiane</small>
                      <b>{ms(live?.median_ms)}</b>
                    </div>
                  </div>
                </section>
              </div>
              {live && <RunMetrics run={live} />}
              <section className="panel phone-panel">
                <Phone />
                <div>
                  <h3>Test par téléphone</h3>
                  <p className="muted">
                    Composition active :{" "}
                    {compositions.find((c) => c.id === active)?.config.name ??
                      "Aucune"}
                    . Le trunk SIP doit router vers le worker{" "}
                    <code>rushh-bench</code>.
                  </p>
                </div>
              </section>
            </div>
          )}
          {tab === "Historique" && (
            <>
              <div className="stats-row">
                <div className="stat">
                  <span>Essais enregistrés</span>
                  <strong>{runs.length}</strong>
                </div>
                <div className="stat">
                  <span>Usage du mois</span>
                  <strong>
                    {Math.round(quota.minutes_month ?? 0)} <small>min</small>
                  </strong>
                </div>
                <div className="stat">
                  <span>Budget connu, hors postes manquants</span>
                  <strong>
                    {money(runs.reduce((a, r) => a + r.cost.eur, 0))}
                  </strong>
                </div>
              </div>
              {detail ? (
                <RunDetail
                  run={detail}
                  onClose={() => setDetail(null)}
                  onSave={(rating: number | null, comment: string) =>
                    execute(async () => {
                      const r = await api(
                        "/runs/" + detail.id + "/rating",
                        "PUT",
                        { rating, comment },
                      );
                      setDetail(r);
                      await refresh();
                    })
                  }
                />
              ) : (
                <section className="panel">
                  <div className="section-title">
                    <h2>Journal des essais</h2>
                    <input
                      placeholder="Filtrer les compositions…"
                      aria-label="Filtrer l’historique"
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                    />
                  </div>
                  {runs.length ? (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Composition</th>
                            <th>Canal</th>
                            <th>Durée</th>
                            <th>Coût</th>
                            <th>Latence</th>
                            <th>Note</th>
                            <th>Statut</th>
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {runs
                            .filter((r) =>
                              r.config.name
                                .toLowerCase()
                                .includes(filter.toLowerCase()),
                            )
                            .map((r) => (
                              <tr key={r.id}>
                                <td>
                                  <b>{r.config.name}</b>
                                  <small>
                                    {new Date(r.created_at).toLocaleString(
                                      "fr-FR",
                                    )}
                                  </small>
                                </td>
                                <td>
                                  {r.channel === "web"
                                    ? "Navigateur"
                                    : "Téléphone"}
                                </td>
                                <td>{Math.round(r.duration)} s</td>
                                <td>
                                  {r.cost.estimated ? "≈ " : ""}
                                  {money(r.cost.eur)}
                                  {!r.cost.complete ? " *" : ""}
                                </td>
                                <td>{ms(r.median_ms)}</td>
                                <td>{r.rating ? `${r.rating} / 5` : "—"}</td>
                                <td>
                                  <span className="pill">{r.status}</span>
                                </td>
                                <td>
                                  <button
                                    className="secondary"
                                    onClick={() =>
                                      execute(async () =>
                                        setDetail(await api("/runs/" + r.id)),
                                      )
                                    }
                                  >
                                    Ouvrir
                                  </button>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <Empty
                      text="Votre premier essai vous attend."
                      action={() => setTab("Tester")}
                    />
                  )}
                  <p className="muted footnote">
                    ≈ Tarif estimatif. * Coût partiel : un ou plusieurs tarifs
                    manquent. Les prix sont figés au début de chaque essai.
                  </p>
                </section>
              )}
            </>
          )}
          {tab === "Comparatif" && (
            <>
              <section className="panel">
                <div className="section-title">
                  <h2>Les compositions à l’épreuve</h2>
                  <div className="actions">
                    <input
                      aria-label="Filtrer le comparatif"
                      placeholder="Filtrer…"
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                    />
                    <select
                      aria-label="Trier le comparatif"
                      value={sort}
                      onChange={(e) => setSort(e.target.value)}
                    >
                      <option value="eur_per_min">Coût / min</option>
                      <option value="median_ms">Latence médiane</option>
                      <option value="p95_ms">Latence P95</option>
                      <option value="rating">Meilleure note</option>
                    </select>
                  </div>
                </div>
                {comparison.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Composition / version</th>
                          <th>Essais</th>
                          <th>Coût / min</th>
                          <th>Médiane</th>
                          <th>P95</th>
                          <th>Note</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparison
                          .filter((c) =>
                            c.name.toLowerCase().includes(filter.toLowerCase()),
                          )
                          .sort((a, b) =>
                            sort === "rating"
                              ? (b[sort] ?? -1) - (a[sort] ?? -1)
                              : (a[sort] ?? Infinity) - (b[sort] ?? Infinity),
                          )
                          .map((c) => (
                            <tr key={c.id}>
                              <td>
                                <b>{c.name}</b>
                                <small>{c.id}</small>
                              </td>
                              <td>{c.count}</td>
                              <td>
                                {money(c.eur_per_min)}
                                {!c.complete ? " *" : ""}
                              </td>
                              <td>{ms(c.median_ms)}</td>
                              <td>{ms(c.p95_ms)}</td>
                              <td>{c.rating?.toFixed(1) ?? "—"}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    text="Terminez un premier essai pour comparer les compositions."
                    action={() => setTab("Tester")}
                  />
                )}
              </section>
              <section className="panel">
                <h2>
                  <Headphones size={19} /> Écoute A / B
                </h2>
                <div className="two-col">
                  {[0, 1].map((index) => (
                    <div key={index}>
                      <label className="field">
                        Essai {index === 0 ? "A" : "B"}
                        <select
                          value={listen[index] ?? ""}
                          onChange={(e) =>
                            setListen((old) => {
                              const n = [...old];
                              n[index] = e.target.value;
                              return n;
                            })
                          }
                        >
                          <option value="">Choisir un enregistrement</option>
                          {runs
                            .filter((r) => r.audio)
                            .map((r) => (
                              <option key={r.id} value={r.id}>
                                {r.config.name} ·{" "}
                                {new Date(r.created_at).toLocaleString("fr-FR")}
                              </option>
                            ))}
                        </select>
                      </label>
                      {listen[index] && (
                        <audio
                          controls
                          src={"/api/runs/" + listen[index] + "/audio"}
                        />
                      )}
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
          {tab === "Prix" && (
            <>
              <div className="banner">
                <Coins size={20} />
                <div>
                  Conversion utilisée : 1 USD = {fx} EUR. Les tarifs initiaux
                  sont des estimations issues des specs.
                  <br />
                  <small>
                    Vérifiez votre plan, renseignez les postes manquants et
                    datez vos modifications. Un tarif absent ne vaut jamais
                    zéro.
                  </small>
                </div>
              </div>
              <input
                aria-label="Filtrer les prix"
                placeholder="Rechercher un fournisseur ou un modèle…"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
              <div className="prices-list">
                {prices
                  .filter((p) =>
                    p.id.toLowerCase().includes(filter.toLowerCase()),
                  )
                  .map((p) => (
                    <PriceCard
                      key={p.id}
                      price={p}
                      save={(v) =>
                        execute(async () => {
                          await api("/prices", "PUT", v);
                          await refresh();
                          setNotice(
                            "Tarif enregistré pour les prochains essais.",
                          );
                        })
                      }
                    />
                  ))}
              </div>
            </>
          )}
          {tab === "Clés API" && (
            <div className="keys-grid">
              {keys.map((k) => (
                <KeyCard
                  key={k.provider}
                  item={k}
                  execute={execute}
                  refresh={refresh}
                  notify={setNotice}
                />
              ))}
            </div>
          )}
        </div>
        <footer>
          Construit pour trouver votre voix.<span>Rushh / Voice Lab</span>
        </footer>
      </main>
    </div>
  );
}
function Empty({ text, action }: { text: string; action: () => void }) {
  return (
    <div className="empty">
      <FlaskConical size={30} />
      <h3>{text}</h3>
      <p>Aucune mesure fictive n’est ajoutée à votre historique.</p>
      <button className="secondary" onClick={action}>
        Lancer un essai <ArrowUpRight size={15} />
      </button>
    </div>
  );
}
function RunMetrics({ run }: { run: Obj }) {
  return (
    <section className="panel">
      <div className="two-col">
        <div>
          <h3>Latence par tour</h3>
          {run.turns?.length ? (
            run.turns.map((t: Obj) => (
              <p key={t.id}>
                {ms(t.latency_ms ?? t.estimated_ms)}{" "}
                <small className="muted">
                  LLM {ms(t.llm_ms)} · TTS {ms(t.tts_ms)} · fin de tour{" "}
                  {ms(t.endpoint_ms)}
                </small>
              </p>
            ))
          ) : (
            <p className="muted">Pas encore de tour mesuré.</p>
          )}
          <small className="muted">
            Médiane et P95 : fin de parole → lecture audio, mesurées par le
            worker. Les lignes LLM/TTS détaillent aussi l’estimation par brique.
          </small>
        </div>
        <div>
          <h3>Outils appelés</h3>
          {run.events
            ?.filter((e: Obj) => e.type === "tools")
            .map((e: Obj, i: number) => (
              <pre key={i}>{JSON.stringify(e, null, 2)}</pre>
            ))}
          <h3>Coût détaillé</h3>
          {run.cost.lines.map((l: Obj, i: number) => (
            <p key={i}>
              <small>
                {l.component} · {Math.round(l.quantity)} {l.unit}
              </small>
              <b className="float-right">{money(l.eur)}</b>
            </p>
          ))}
          {!run.cost.complete && (
            <p className="warning">
              Tarifs manquants : {run.cost.missing.join(", ")}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
function RunDetail({
  run,
  onClose,
  onSave,
}: {
  run: Obj;
  onClose: () => void;
  onSave: (r: number | null, c: string) => void;
}) {
  const [rating, setRating] = useState(run.rating ?? ""),
    [comment, setComment] = useState(run.comment ?? "");
  return (
    <>
      <section className="panel">
        <div className="section-title">
          <h2>{run.config.name}</h2>
          <button className="secondary" onClick={onClose}>
            Retour à la liste
          </button>
        </div>
        {run.audio ? (
          <audio controls src={"/api/runs/" + run.id + "/audio"} />
        ) : (
          <p className="muted">Enregistrement indisponible ou désactivé.</p>
        )}
        {run.error && <p className="error">{run.error}</p>}
        {run.recording_error && (
          <p className="warning">{run.recording_error}</p>
        )}
        {run.events?.find((event: Obj) => event.type === "session_closed") && (
          <p className="muted">
            Fin de session :{" "}
            {run.events.find((event: Obj) => event.type === "session_closed")
              .reason}
          </p>
        )}
        {run.events
          ?.filter((event: Obj) => event.type === "provider_error")
          .map((event: Obj, index: number) => (
            <p className="warning" key={index}>
              Fournisseur : {event.provider}/{event.model} · {event.error_type}
              {event.recoverable ? " (récupérable)" : " (fatal)"}
            </p>
          ))}
        <div className="two-col">
          <label className="field">
            Note
            <select value={rating} onChange={(e) => setRating(e.target.value)}>
              <option value="">Non noté</option>
              {[1, 2, 3, 4, 5].map((x) => (
                <option value={x} key={x}>
                  {x} / 5
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Commentaire
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </label>
        </div>
        <button
          className="primary"
          onClick={() => onSave(rating === "" ? null : Number(rating), comment)}
        >
          Enregistrer l’évaluation
        </button>
        <h3>Transcription</h3>
        {run.transcript.map((t: Obj, i: number) => (
          <div className={"message " + t.role} key={i}>
            <b>{t.role === "user" ? "Vous" : "Agent"}</b>
            <p>{t.text}</p>
          </div>
        ))}
        <details>
          <summary>Composition exacte de cet essai</summary>
          <pre>{JSON.stringify(run.config, null, 2)}</pre>
        </details>
      </section>
      <RunMetrics run={run} />
    </>
  );
}
function PriceCard({ price, save }: { price: Obj; save: (p: Obj) => void }) {
  const [p, setP] = useState(price);
  return (
    <details className="panel price-card">
      <summary>
        <b>{price.id}</b>
        <span className="pill">
          {price.status} · {price.checked_at ?? "non vérifié"}
        </span>
      </summary>
      <div className="two-col">
        <JsonField
          label="Prix par unité (audio_seconds, input_tokens, cached_tokens, output_tokens, characters, seconds…)"
          value={p.rates}
          onChange={(rates) => setP({ ...p, rates })}
        />
        <div>
          <label className="field">
            Devise
            <select
              value={p.currency}
              onChange={(e) => setP({ ...p, currency: e.target.value })}
            >
              <option>USD</option>
              <option>EUR</option>
            </select>
          </label>
          <label className="field">
            Source
            <input
              value={p.source}
              onChange={(e) => setP({ ...p, source: e.target.value })}
            />
          </label>
          <label className="field">
            Date de vérification
            <input
              type="date"
              value={p.checked_at ?? ""}
              onChange={(e) => setP({ ...p, checked_at: e.target.value })}
            />
          </label>
          <p className="muted">{p.note}</p>
        </div>
      </div>
      <button
        className="secondary"
        onClick={() =>
          save({ ...p, status: p.checked_at ? "verified" : "manual" })
        }
      >
        Enregistrer le tarif
      </button>
    </details>
  );
}
function KeyCard({
  item,
  execute,
  refresh,
  notify,
}: {
  item: Obj;
  execute: (f: () => Promise<void>) => void;
  refresh: () => Promise<void>;
  notify: (s: string) => void;
}) {
  const [value, setValue] = useState(""),
    [extras, setExtras] = useState<Obj>(item.extras ?? {}),
    [rates, setRates] = useState(item.internal_rates ?? {});
  if (item.provider === "livekit")
    return (
      <section className="panel key-card">
        <h2>LiveKit</h2>
        <p className="muted">
          Identifiants d’infrastructure à renseigner dans le fichier .env de
          l’API et du worker : URL, API key et API secret.
        </p>
        <span className="pill">
          {item.env ? "Clé environnement présente" : "À configurer"}
        </span>
        <p>
          <a href={item.signup} target="_blank" rel="noreferrer">
            Ouvrir LiveKit Cloud ↗
          </a>
        </p>
      </section>
    );
  return (
    <section className="panel key-card">
      <div className="section-title">
        <h2>{item.provider}</h2>
        <a
          href={item.signup}
          target="_blank"
          rel="noreferrer"
          aria-label={"Créer une clé " + item.provider}
        >
          <ArrowUpRight size={18} />
        </a>
      </div>
      <p className="muted">
        {item.stored
          ? "Clé enregistrée · ••••" + item.suffix
          : "Aucune clé enregistrée"}
        <br />
        {item.env
          ? "Environnement · ••••" + item.env_suffix
          : "Environnement non configuré"}
      </p>
      <span className="pill">{item.status}</span>
      <label className="field">
        {item.stored ? "Remplacer la clé" : "Ajouter une clé"}
        <input
          type="password"
          autoComplete="new-password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Coller la clé API"
        />
      </label>
      {item.provider === "azure" && (
        <>
          <Field
            name="region"
            value={extras.region ?? "francecentral"}
            onChange={(v) => setExtras({ ...extras, region: v })}
          />
          <Field
            name="endpoint"
            value={extras.endpoint ?? ""}
            onChange={(v) => setExtras({ ...extras, endpoint: v })}
          />
        </>
      )}
      {item.provider === "google" && (
        <Field
          name="project_id"
          value={extras.project_id ?? ""}
          onChange={(v) => setExtras({ ...extras, project_id: v })}
        />
      )}
      <details>
        <summary>Tarifs internes en EUR par unité</summary>
        <JsonField
          label="Remplace le catalogue pour cette clé"
          value={rates}
          onChange={setRates}
        />
      </details>
      <div className="actions">
        <button
          className="primary"
          disabled={!value}
          onClick={() =>
            execute(async () => {
              await api("/keys/" + item.provider, "PUT", {
                key: value,
                extras,
                internal_rates: rates,
              });
              setValue("");
              await refresh();
              notify("Clé chiffrée et enregistrée.");
            })
          }
        >
          Enregistrer
        </button>
        {(item.stored || item.env) && (
          <button
            className="secondary"
            onClick={() =>
              execute(async () => {
                const r = await api(
                  "/keys/" +
                    item.provider +
                    "/test?source=" +
                    (item.stored ? "stored" : "env"),
                  "POST",
                );
                await refresh();
                notify(
                  item.provider +
                    " : " +
                    r.status +
                    (r.message ? " · " + r.message : ""),
                );
              })
            }
          >
            Tester
          </button>
        )}
        {item.stored && (
          <button
            className="text-button"
            onClick={() =>
              execute(async () => {
                await api("/keys/" + item.provider, "DELETE");
                await refresh();
              })
            }
          >
            Supprimer
          </button>
        )}
      </div>
    </section>
  );
}
