# Rushh · Banc vocal

Banc de test construit à partir de `../specs/`, étape 1 : **Composer, Tester, Historique, Comparatif, Prix, Clés API**. Next.js pour le navigateur, FastAPI pour les données et LiveKit Agents Python pour le dialogue.

## Démarrage local

Prérequis : Python **3.11**, Node **22+**, un projet LiveKit Cloud. Le microphone demande `localhost` ou HTTPS.

```sh
cd Rush_vocal
make install
make setup
```

`make setup` crée `.env` avec des secrets aléatoires ; il ne remplace jamais un fichier existant. Définir votre `BENCH_PASSWORD` dans ce fichier et renseigner `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`. Ne pas modifier `ENCRYPTION_KEY` après l’enregistrement de clés, sinon elles ne pourront plus être déchiffrées.

Dans trois terminaux, depuis `Rush_vocal` :

```sh
make api
make web
make worker
```

Ouvrir **http://127.0.0.1:3000** et se connecter avec `BENCH_PASSWORD`. L’API écoute sur `127.0.0.1:8000` ; Next.js lui transmet `/api/*`. `FRONTEND_ORIGIN` doit correspondre exactement à l’adresse utilisée dans le navigateur.

Pour un essai web sur ordinateur, ouvrir **Tester**, cliquer sur **Détecter les micros** puis choisir explicitement le micro du PC avant de commencer. Si macOS propose aussi le micro de l’iPhone, choisir le micro du Mac dans la liste. Le navigateur transmet uniquement le périphérique choisi à LiveKit ; aucun appel téléphonique n'est nécessaire.

Dans **Clés API**, ajouter vos clés Cartesia et Groq, puis sélectionner **Clé enregistrée** pour ces briques dans Composer. La composition initiale utilise Cartesia Ink 2 → Groq GPT-OSS 20B → Cartesia Sonic 3.6. Les voix et modèles dépendent de leur disponibilité dans vos comptes. Les clés de fournisseurs peuvent aussi rester dans `.env` : choisir alors **Clé environnement**. Les clés du POC parent ne sont pas chargées implicitement.

Pour facturer le TTS Sonic 3.6 via LiveKit, garder **Fournisseur : Cartesia** et **Modèle : sonic-3.6**, puis choisir **Accès : Cartesia via LiveKit · facturation LiveKit**. Ce mode utilise `cartesia/sonic-3.6` avec `LIVEKIT_API_KEY` et `LIVEKIT_API_SECRET` du worker ; il n'utilise pas la clé Cartesia pour le TTS. Le changement d'accès conserve la voix, la langue, la vitesse, le volume et les paramètres compatibles. Le mode Cartesia direct reste disponible. La composition initiale utilise aussi Cartesia pour le STT : tant que cette brique reste en accès direct, elle exige toujours une clé Cartesia ; choisissez aussi **LiveKit Inference** pour le STT Cartesia si vous voulez supprimer entièrement cette clé. Sur LiveKit Build/Ship, Sonic 3.6 est tarifé 50 $/million de caractères (Scale : 37,50 $) au 27/09/2026 ; le catalogue distingue les coûts directs et Inference.

Les LLM Groq `llama-3.1-8b-instant`, `openai/gpt-oss-20b` et `openai/gpt-oss-safeguard-20b`, ainsi que Mistral `mistral-small-latest`, sont sélectionnables. Groq classe Safeguard comme modèle de prévisualisation spécialisé dans la classification de sécurité ; Llama 3.1 8B affiche un tarif « Contact Sales », donc son prix reste à saisir dans l'application. `mistral-small-latest` est un alias mobile : son tarif initial est une estimation à revoir selon la version et votre contrat.

OpenRouter propose `meta-llama/llama-3.3-70b-instruct`, `openai/gpt-oss-20b` et `openai/gpt-oss-120b`. Ajoutez une clé OpenRouter dans **Clés API** ou renseignez `OPENROUTER_API_KEY` sur l’API, puis choisissez le modèle dans la brique LLM de Composer. Les tarifs GPT-OSS du catalogue reflètent le fournisseur le moins cher affiché par OpenRouter le 27/09/2026 ; le prix réel dépend du routage et reste révisable dans **Prix**.

Dans Composer, **Détection, interruptions & audio** permet de choisir une ambiance continue (bureau, ville, forêt ou salle animée) et son volume. Les pistes LiveKit sont amplifiées et équilibrées pour rendre le réglage à 100 % audible. Sous **Naturel & balises vocales**, réglez la fréquence des éternuements, raclements de gorge, toux et chuchotements préenregistrés pendant la parole de l’utilisateur. Ces effets sont diffusés sur la piste d'ambiance LiveKit avec un volume propre à chacun et un court fondu ; le chuchotement reste discret. Le curseur « Oui / OK / Hum hum » règle les acquiescements après une pause et une reprise de parole de l’appelant. À 30 %, il reproduit l’ancien réglage à 100 % (18 mots ou 6 secondes, pause de 1,8 seconde au plus, 8 secondes entre deux acquiescements). À 100 %, il accepte dès 6 mots ou 2 secondes, une pause de 2,5 secondes et réduit l’attente à 2,2 secondes, soit environ 3,6 fois plus d’occasions dans un discours comportant suffisamment de pauses. Les curseurs d'effets sont à zéro par défaut ; montez-les pour les activer. Les acquiescements demandent un pipeline STT/LLM/TTS et restent dépendants des pauses détectées. Les effets sonores sont séparés de la voix TTS et restent disponibles avec tous les TTS du pipeline.

Pour le détecteur de tours multilingue, télécharger les modèles une fois :

```sh
.venv/bin/python agent.py download-files
```

Choisir `"turn_detection": "multilingual"` dans les paramètres de session. Le mode par défaut utilise Silero VAD.

## Ce que fait le banc

- Enregistre et duplique les compositions ; une composition indépendante est active pour le téléphone.
- Construit une nouvelle session depuis un instantané JSON à chaque appel, sans redémarrage du worker.
- Propose le pipeline STT/LLM/TTS, LiveKit Inference sur les routes déclarées et OpenAI Realtime, Gemini Live ou Ultravox.
- Expose les réglages usuels, un sélecteur de paramètres additionnels, le JSON complet du plugin et les paramètres API bruts.
- Traduit les balises universelles selon le TTS. Les effets non documentés pour un modèle sont retirés, pas prononcés littéralement.
- Exécute des outils factices modifiables : recherche de biens, créneaux, lead, RDV, transfert et rappel.
- Conserve transcription, appels d’outils, usage, latence, prix figés au début de l’essai, note et commentaire.
- Enregistre les deux voix dans un WAV stéréo via un participant LiveKit caché : appelant à gauche, agent à droite. Pas d’Egress.
- Compare les versions exactes des compositions, avec coût pondéré par durée, médiane, P95 et écoute A/B.
- Chiffre les clés avec Fernet, n’en retourne que les quatre derniers caractères et protège séparément les routes du worker.

## Mesures et tarifs

Le catalogue initial provient des specs. Les montants non confirmés selon le contrat sont marqués **estimations**, les tarifs inconnus restent absents. Le prix payé peut dépendre du plan, du cache, des options supplémentaires et des minimums de facturation. **Un total partiel n’est pas une facture.**

L’écran Prix permet de renseigner des montants **par unité**, et non par million : par exemple `0.000000075` USD par token pour `0.075 $ / million`. Un tarif interne dans Clés API est en **EUR par unité** et s’applique aux briques utilisant cette clé. Renseigner explicitement `seconds: 0` pour une ligne d’infrastructure incluse dans votre forfait.

`USD_TO_EUR` fixe le taux de conversion, lui aussi conservé dans chaque essai. Les tarifs directs et Inference sont distincts. Modifier un prix ne recalcule pas le passé. Les comptes de tokens en cache ne sont pas ajoutés une seconde fois aux tokens d’entrée.

La latence principale mesure **fin de parole utilisateur → début de lecture audio agent**, depuis le worker. Elle ne mesure pas le délai physique jusqu’au haut-parleur du navigateur. Les délais EOU, TTFT et TTFB sont conservés séparément et leur somme est une estimation par brique. Aucun délai fictif ne remplace une mesure absente, notamment avant le premier tour ou lors d’une erreur.

## Validation et limites connues

```sh
make test
make build
```

Les tests Python couvrent l’API, le chiffrement, les instantanés, la facturation, la construction du catalogue et des requêtes sortantes capturées sans accès payant. Le test Playwright couvre connexion, sauvegarde, navigation, clés et mobile. Voir [tests et transport](docs/validation.md).

**Les appels audio réels, le trunk SIP et les déploiements Cloud n’ont pas été validés dans cette livraison.** La réussite d’un constructeur SDK ne prouve pas qu’un compte donne accès à un modèle. Certains réglages restent réservés à un transport ou à un modèle ; les restrictions sont décrites dans [les adaptateurs](docs/adapters.md). Les champs JSON ne peuvent pas contourner les exigences de l’API distante.

La limite locale réserve la durée maximale d’un essai avant sa création et accepte au plus cinq essais simultanés. `MONTHLY_MINUTES_LIMIT` vaut 1 000 par défaut. Ce compteur concerne ce banc, pas les autres applications utilisant votre projet LiveKit. Après une panne du worker, la réservation est libérée au prochain démarrage d’essai, au-delà du délai maximal plus trois minutes ; les dernières mesures connues restent conservées.

## Mise en ligne et téléphone

Pour Vercel + Railway, suivre [la configuration pas à pas](docs/vercel-railway.md). L'autre option (API sur Vercel et worker sur LiveKit Cloud) est décrite dans [le guide de déploiement](docs/deployment.md). Aucun compte ni numéro n'est créé automatiquement.

## Structure

```text
web/                 Next.js, interface et connexion audio LiveKit
api/                 FastAPI, SQLite/Postgres, coffre de clés et calcul des coûts
worker/              Sessions LiveKit, adaptateurs, balises, métriques et audio
agent.py             Entrée CLI du worker
scripts/             Initialisation, catalogue, package API, reprises de télémétrie
tests/               Tests hors réseau payant
```
