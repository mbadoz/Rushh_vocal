# Déploiement et téléphonie

Pour le montage **Vercel (front) + Railway (API et worker)**, voir [le guide dédié](vercel-railway.md). Les étapes ci-dessous décrivent l'autre montage, avec API Vercel et worker LiveKit Cloud.

Le code est préparé pour les services décrits dans les specs. Les comptes, quotas réels, domaine, numéro SIP et secrets doivent être configurés avant le premier appel. Les commandes ci-dessous ne sont pas exécutées automatiquement.

## API FastAPI / Neon

Créer une base Neon en Europe et placer son URL SSL dans `DATABASE_URL`, avec le schéma `postgresql://` ou `postgresql+psycopg://`. La table des documents et le catalogue initial sont créés au démarrage. Ne pas utiliser SQLite sur un hébergement éphémère.

Le worker dépend de bibliothèques de modèles volumineuses. Le package de déploiement de l’API les exclut :

```sh
.venv/bin/python scripts/package_api.py
cd data/api-deploy
vercel
```

Vercel reconnaît l’instance `app` de `app.py` ; le fichier préparé choisit Francfort. Voir la [documentation FastAPI Vercel](https://vercel.com/docs/frameworks/backend/fastapi).

Variables API :

- `DATABASE_URL`, `BENCH_PASSWORD`, `SESSION_SECRET`, `ENCRYPTION_KEY`, `WORKER_SECRET`.
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_AGENT_NAME=rushh-bench`.
- `FRONTEND_ORIGIN=https://votre-front.example`, `COOKIE_SECURE=true`.
- `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
- `USD_TO_EUR`, `MONTHLY_MINUTES_LIMIT`.
- Clés de fournisseurs utilisant la source **environnement**. Elles doivent être sur l’API, puisque celle-ci fournit les identifiants au worker au début de l’essai.

Les clés saisies dans l’interface sont stockées chiffrées dans Neon. La clé Fernet reste sur l’API ; le worker reçoit uniquement les identifiants nécessaires via l’endpoint interne protégé, en HTTPS. Il ne reçoit jamais les secrets de connexion utilisateur.

Le secret du worker doit être long et distinct du mot de passe utilisateur. La limitation locale des tentatives de connexion n’est pas un limiteur distribué ; pour un accès public, configurer aussi la protection de débit de l’hébergeur sur `/api/login`.

## Front Next.js / Vercel

Importer le dossier `web` dans un **second projet Vercel**, ou le déployer depuis ce dossier. Définir `API_ORIGIN=https://votre-api.vercel.app`, puis construire. Les rewrites Next.js gardent les appels API et cookies sur l’origine du front. Aucun secret de fournisseur n’utilise une variable `NEXT_PUBLIC_*`.

Faire correspondre `FRONTEND_ORIGIN` sur l’API à l’URL réelle du front. Une preview avec une autre URL n’est pas autorisée automatiquement.

## Worker LiveKit Cloud

Le Dockerfile racine installe les plugins, précharge les fichiers Silero / détecteur de tours et lance `agent.py start` sous un utilisateur non privilégié.

```sh
lk agent create
lk agent deploy
```

Choisir le projet/région voulu pendant l’initialisation du CLI. Le fichier `livekit.toml` généré est propre à votre compte : aucun identifiant de projet fictif n’est fourni.

Variables worker : `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_AGENT_NAME`, `BENCH_API_URL` (origine HTTPS de l’API), `WORKER_SECRET`, et les variables R2. Les fournisseurs sont construits avec les clés reçues de l’API ; aucune clé globale n’est changée pendant un appel.

Pour les sessions de développement, `make worker` sur le Mac suffit et évite le déploiement Cloud. Ne pas lancer deux workers de test en pensant qu’un appel sera dirigé vers un exemplaire précis : LiveKit choisit un worker disponible pour le nom d’agent.

## Audio / R2

Créer un bucket **privé**, puis une clé S3 limitée à ce bucket. Exemple d’endpoint : `https://<account-id>.r2.cloudflarestorage.com`. L’identifiant de compte Cloudflare fait donc partie de cet endpoint d’infrastructure.

Le worker enregistre un WAV stéréo et l’envoie **directement à R2**, puis notifie l’API. Cela évite de faire traverser de gros fichiers à une fonction Vercel. L’API délivre une URL de lecture signée pour cinq minutes après authentification ; le bucket n’est pas public.

Sans R2, le mode local écrit sous `data/audio` côté API. Les copies sur le worker sont supprimées après un transfert réussi, conservées en cas d’échec. Une panne d’API conserve la télémétrie dans `data/pending` côté worker :

```sh
.venv/bin/python scripts/replay_telemetry.py
```

La reprise automatique de fichiers audio après arrêt complet d’un conteneur n’est pas garantie : le disque du worker Cloud peut être éphémère. Pour les essais importants, vérifier la présence du lecteur dans l’historique avant de quitter.

## Téléphone SIP entrant

Acheter/configurer un numéro et un trunk entrant chez votre opérateur. Dans LiveKit, créer le trunk avec les règles d’authentification ou d’adresses IP adaptées à cet opérateur. Ne pas exposer un trunk sans restriction.

L’exemple `sip_dispatch_rule.example.json` crée une room distincte préfixée `bench-phone-` et dispatche `rushh-bench`. À adapter aux identifiants de votre trunk avec le [guide officiel des règles de dispatch](https://docs.livekit.io/telephony/accepting-calls/dispatch-rule/).

Sans `run_id` dans les métadonnées de dispatch, le worker demande à l’API de créer un essai **téléphone** à partir de la composition active. Les appels web utilisent un `run_id` explicite. Modifier la composition active n’altère jamais un appel déjà lancé.

Renseigner les lignes `livekit:sip` et `telephony:inbound` dans Prix. Le banc simule les outils de transfert et RDV : il ne transfère pas réellement le prospect vers un conseiller.

## Vérification après configuration

1. Ouvrir l’interface, se connecter, tester les clés d’un trio STT/LLM/TTS.
2. Lancer le worker, vérifier qu’il s’enregistre sous `rushh-bench`.
3. Faire un court essai web avec le microphone : écouter, interrompre, appeler un outil simulé.
4. Terminer l’essai ; vérifier transcription, lecteur stéréo, mesures et postes de coût manquants.
5. Répéter après changement de fournisseur pour confirmer que le compte donne accès au modèle et à la voix.
6. Activer une composition pour le téléphone, appeler le numéro SIP et vérifier le canal dans l’historique.
