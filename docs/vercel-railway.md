# Mise en ligne : Vercel + Railway

Un simple branchement du dépôt GitHub ne suffit pas pour le premier déploiement. Cette configuration utilise **un projet Vercel** pour `web`, **deux services Railway** pour l'API et le worker, **un PostgreSQL Railway**, **un projet LiveKit Cloud** pour les sessions vocales et **un bucket Cloudflare R2** pour conserver les enregistrements. Une fois les services et les variables configurés, les nouveaux commits sur la branche de production redéploient les services liés au dépôt.

## 1. Préparer le dépôt et les services

Pousser le dépôt dont la racine contient `web/`, `api/`, `worker/`, `Dockerfile` et `Dockerfile.api`. Le fichier `.env` local est ignoré par Git : placer les secrets dans les variables des hébergeurs, jamais dans le dépôt.

Dans Railway, créer un projet puis ajouter un **PostgreSQL** et deux services depuis le **même dépôt GitHub**, avec la racine du service à la racine du dépôt :

| Service Railway | Réglage de construction | Réseau |
| --- | --- | --- |
| API | Variable `RAILWAY_DOCKERFILE_PATH=Dockerfile.api` | Générer un domaine public HTTPS ; health check `/api/health` |
| Worker vocal | Dockerfile racine détecté automatiquement | Aucun domaine public nécessaire |

Le worker se connecte en sortie à LiveKit et à l'API. Le Dockerfile du worker télécharge les modèles LiveKit pendant la construction ; son image est donc sensiblement plus lourde que celle de l'API. Vérifier dans les logs Railway qu'il s'enregistre sous le nom `rushh-bench`.

Dans Vercel, importer le même dépôt et définir **Root Directory = `web`**. Ajouter `API_ORIGIN=https://<domaine-public-de-l-api-railway>` sans slash final aux variables de production, puis déployer. Le rewrite `/api/*` de Next.js relaie les demandes à l'API. Garder un domaine de production stable ; une URL de preview différente exige sa propre configuration d'origine côté API.

## 2. Variables Railway

Dans le service **API** :

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
BENCH_PASSWORD=<mot-de-passe-partagé-long>
SESSION_SECRET=<secret-aléatoire-long>
ENCRYPTION_KEY=<clé-Fernet>
WORKER_SECRET=<autre-secret-aléatoire-long>
FRONTEND_ORIGIN=https://<domaine-de-production-vercel>
COOKIE_SECURE=true
LIVEKIT_URL=wss://<votre-projet-livekit>
LIVEKIT_API_KEY=<clé-livekit>
LIVEKIT_API_SECRET=<secret-livekit>
LIVEKIT_AGENT_NAME=rushh-bench
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<clé-r2>
R2_SECRET_ACCESS_KEY=<secret-r2>
R2_BUCKET=<bucket-privé>
```

Le nom du service PostgreSQL dans l'expression Railway doit correspondre exactement à celui affiché dans votre projet. `FRONTEND_ORIGIN` est l'URL exacte ouverte dans le navigateur, avec `https://` et sans slash final. Il faut parfois déployer une première fois pour obtenir les domaines, renseigner les deux URL croisées, puis redéployer.

Dans le service **worker** :

```text
LIVEKIT_URL=<même valeur que l'API>
LIVEKIT_API_KEY=<même valeur que l'API>
LIVEKIT_API_SECRET=<même valeur que l'API>
LIVEKIT_AGENT_NAME=rushh-bench
BENCH_API_URL=https://<domaine-public-de-l-api-railway>
WORKER_SECRET=<même valeur que l'API>
R2_ENDPOINT=<même valeur que l'API>
R2_ACCESS_KEY_ID=<même valeur que l'API>
R2_SECRET_ACCESS_KEY=<même valeur que l'API>
R2_BUCKET=<même valeur que l'API>
```

Générer les trois secrets indépendamment avec `python -c 'import secrets; print(secrets.token_urlsafe(48))'` (utiliser une sortie différente pour chacun) et la clé Fernet avec `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. Conserver `ENCRYPTION_KEY` stable après l'ajout de clés fournisseurs dans l'application. Les clés Groq, Cartesia, Mistral et des autres fournisseurs peuvent être entrées dans **Clés API** après connexion, ou définies sur **l'API Railway** avec les noms de `.env.example` et sélectionnées comme « Clé environnement » dans Composer. Elles ne sont pas nécessaires sur le worker.

Créer le bucket R2 **privé** et une clé limitée à ce bucket. Dans Cloudflare, ouvrir **Stockage et bases de données → R2 → Vue d'ensemble → Gérer les jetons d'API**. Créer un **jeton d'API du compte** (adapté à un service partagé qui reste actif indépendamment d'un utilisateur) ou un **jeton d'API de l'utilisateur** (également utilisable, mais dépendant de cet utilisateur), avec la permission **Lecture et écriture des objets**, limitée au bucket choisi. Après création, Cloudflare affiche **Access Key ID** et **Secret Access Key** : copier ces deux valeurs immédiatement dans `R2_ACCESS_KEY_ID` et `R2_SECRET_ACCESS_KEY`. Le jeton d'API Cloudflare lui-même n'est pas le secret S3 attendu par l'application. `R2_BUCKET` est le nom exact du bucket ; `R2_ENDPOINT` est l'URL **S3 API** de l'account ID affiché sur R2, sans nom de bucket. Pour un bucket créé dans la juridiction **EU**, utiliser `https://<account-id>.eu.r2.cloudflarestorage.com` ; pour un bucket standard, `https://<account-id>.r2.cloudflarestorage.com`. Voir la [documentation Cloudflare R2](https://developers.cloudflare.com/r2/api/tokens/) et le [guide S3](https://developers.cloudflare.com/r2/get-started/s3/).

Le worker dépose directement les WAV sur R2 ; l'API donne au navigateur une URL de lecture temporaire. Sans R2, les enregistrements passent par le disque éphémère des services et ne constituent pas un historique durable.

`LIVEKIT_URL`, `LIVEKIT_API_KEY` et `LIVEKIT_API_SECRET` identifient le projet LiveKit. `LIVEKIT_AGENT_NAME=rushh-bench` n'est pas un quatrième secret ni un nom à créer dans la console : c'est le nom sous lequel le worker Railway s'enregistre auprès de LiveKit. À chaque essai web, l'API demande explicitement à LiveKit d'envoyer ce worker dans la room et transmet l'identifiant de l'essai dans les métadonnées. Le nom doit être identique sur l'API et le worker. L'agent peut tourner sur Railway ; il n'est pas nécessaire de le déployer aussi sur LiveKit Cloud. Un agent sans nom est affecté automatiquement aux nouvelles rooms, pratique pour un petit prototype mais incompatible avec le dispatch explicite de ce banc. Voir le [dispatch LiveKit](https://docs.livekit.io/agents/server/agent-dispatch/) et les [déploiements tiers](https://docs.livekit.io/deploy/custom/deployments/).

## 3. Vérifier l'accès

1. Ouvrir `https://<domaine-api-railway>/api/health` : la réponse doit être `{"ok":true}`.
2. Ouvrir le site Vercel, entrer `BENCH_PASSWORD`, puis vérifier que Composer, Prix et Clés API se chargent.
3. Ajouter les clés de votre trio STT/LLM/TTS, lancer un essai web au microphone et vérifier la transcription et l'enregistrement dans Historique.
4. Si la connexion réussit mais qu'aucun agent ne répond, lire les logs du worker Railway et vérifier `LIVEKIT_AGENT_NAME`, le projet LiveKit et `BENCH_API_URL`.

**Toute personne connaissant `BENCH_PASSWORD` peut se connecter à ce site partagé, modifier les compositions et les clés, et lancer des essais facturables** dans les limites configurées. Il n'existe pas encore de comptes individuels ou de rôles. La limite locale de tentatives de connexion de l'API n'est pas distribuée ; activer aussi une protection de débit de l'hébergeur pour `/api/login` avant de diffuser largement l'URL. Le téléphone demande en plus un numéro, un trunk SIP et une règle de dispatch LiveKit ; voir [téléphonie](deployment.md#téléphone-sip-entrant).

Sources hébergeurs : [Vercel Root Directory](https://vercel.com/docs/monorepos), [Railway Dockerfile](https://docs.railway.com/builds/dockerfiles), [Railway PostgreSQL](https://docs.railway.com/databases/postgresql), [LiveKit agents sur un hébergement tiers](https://docs.livekit.io/deploy/custom/deployments/).
