# Vérifications

## Tests Python

```sh
.venv/bin/python -m pytest -q
```

Les tests utilisent une base SQLite temporaire, des clés factices, des constructeurs de SDK et des transports interceptés. **Ils ne dépensent pas de crédits et ne simulent pas une réussite de conversation dans l’historique.**

Couverture :

- Connexion, contrôle d’origine, séparation des cookies utilisateur et du secret worker.
- Chiffrement des clés en base, masquage des réponses et suppression.
- Validation des compositions, activation téléphone, durée maximale, source de clé et contrôle du modèle.
- Instantanés de prix : une modification ultérieure n’altère pas le coût enregistré ; notes préservées lors des mises à jour du worker.
- Cache des tokens, conversion EUR, tarifs manquants distincts de zéro, pondération des coûts et percentiles.
- Construction des modèles déclarés, hors Google TTS qui demande un compte de service valide ; absence de substitution du modèle Speechmatics.
- Captures des paquets Cartesia (locale, normalisation, tampon, contrôle de génération), OpenAI-compatible (raisonnement, seed, pénalité), Soniox (format et endpoint), Google TTS (protobuf), Azure (SSML), Realtime (configuration sans altérer l’audio).
- Isolation de deux configurations simultanées, traduction de balises coupées entre deux morceaux de texte, suppression des effets non pris en charge.
- Association des métriques par tour, latence mesurée et facturation TTS par tokens.

Le test de construction de chaque modèle ne remplace pas une vérification réseau de chaque paramètre de son API. Les cas sensibles possèdent des assertions sur les requêtes ; la compatibilité exhaustive de chaque option avancée reste à confirmer auprès du fournisseur pendant les essais réels.

## Front

```sh
cd web
npm run build
npm run typecheck
```

Pour Playwright, lancer l’API de test isolée dans un terminal, le front dans un autre, puis le test :

```sh
# Depuis Rush_vocal
.venv/bin/python -m scripts.dev_api
# Depuis Rush_vocal/web
npm run dev
npx playwright install chromium
npx playwright test
```

L’API de test écoute seulement `127.0.0.1`, utilise `/tmp/rushh-ui-check.db`, accepte `http://127.0.0.1:3000` et le mot de passe factice `test-password`. Elle sert uniquement aux vérifications locales. Ne pas l’utiliser pour le déploiement.

Le test navigateur ouvre les six écrans, enregistre puis recharge une composition, change de mode, ajoute/supprime une clé factice et vérifie l’absence de débordement horizontal à 390 px. Il capture les vues desktop et mobile sous `/tmp/rushh-*.png`.

## Ce qui nécessite un environnement externe

- Conversation réelle, qualité française, latence perçue et interruptions avec microphone.
- Accès et paramètres acceptés par chaque compte fournisseur, modèles en preview ou en retrait.
- Permissions LiveKit du participant enregistreur, connexion SIP et coût facturé.
- Docker/LiveKit Cloud, Neon et R2 déployés, reprise après arrêt brutal d’un worker.

Aucun résultat audio, latence réelle, tarif contractuel ou succès de déploiement n’est annoncé sur la base de tests hors réseau.
