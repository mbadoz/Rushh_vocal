# Adaptateurs et réglages

Version du framework et des plugins : **LiveKit Agents 1.8.3**. Le catalogue de modèles est maintenu dans `api/catalog.py`, indépendamment des valeurs par défaut du SDK. Le catalogue des paramètres est généré depuis les signatures du SDK : `python -m scripts.parameter_catalog`.

## Passage des paramètres

| Famille | Chemin vers la requête |
| --- | --- |
| OpenAI, Groq, Cerebras, Mistral LLM | Arguments natifs et `extra_body` fusionné par le SDK OpenAI |
| Gemini et Anthropic LLM | Arguments natifs et `extra_kwargs` sur chaque appel `chat` |
| Cartesia TTS | Proxy HTTP/WS propre à la session ; fusion après construction du paquet, donc après le tampon forcé à zéro du plugin |
| Soniox STT | `STTOptions`, puis fusion du paquet de démarrage ; conversion PCM16 vers µ-law/A-law si demandée |
| Deepgram, AssemblyAI, ElevenLabs STT | Arguments natifs ; paramètres bruts dans la query WebSocket |
| Speechmatics STT | Adaptateur WebSocket v2 dédié pour garder `standard` / `enhanced`, le plugin fourni remplaçant ces modèles par `linden-1` sur `/v2/agent` |
| Gladia | Fusion de la requête d’ouverture de session |
| ElevenLabs TTS | Fusion des paquets texte / contexte et des requêtes HTTP |
| Inworld TTS | Fusion dans `create` en WS, ou dans la requête de synthèse HTTP |
| Hume, Rime | Fusion des requêtes de synthèse |
| Azure TTS | Arguments natifs et extension SSML : `role`, `style`, `styledegree`, `silence`, `break`, `emphasis` |
| Google TTS | Compte de service JSON ; fusion des requêtes protobuf, ou de `streaming_config` en streaming |
| OpenAI/Groq STT HTTP et OpenAI TTS | Extension du client SDK propre à la session via `extra_body` |
| OpenAI Realtime | Fusion dans le contenu de `session.update` |
| Gemini Live | Extension de `LiveConnectConfig` par session |
| Ultravox | Fusion de la requête de création d’appel, notamment `vadSettings` |
| LiveKit Inference | Arguments du gateway et `extra_kwargs` ; tarifs séparés des appels directs |

Aucun monkeypatch global ni modification des variables d’environnement n’est utilisé pour changer un fournisseur. Les réglages d’un essai ne doivent pas déborder sur un autre.

## Exemples de paramètres API bruts

Cartesia :

```json
{"locale":"fr-CA","accent":"french","normalization":"off","max_buffer_delay_ms":120}
```

Speechmatics :

```json
{"transcription_config":{"max_delay":0.8,"max_delay_mode":"flexible","transcript_filtering_config":{"remove_disfluencies":true}},"audio_filtering_config":{"volume_threshold":0}}
```

Soniox : `{"enable_endpoint_detection":false,"audio_format":"pcm_mulaw"}` ; régler aussi `sample_rate: 8000` dans les paramètres du plugin pour un flux à 8 kHz.

OpenAI Realtime : `{"max_output_tokens":300}`. Le champ est ajouté à la session, pas aux paquets audio.

Azure : `{"role":"YoungAdultFemale","style":"cheerful","silence":{"type":"Sentenceboundary","value":"200ms"}}`.

## Restrictions explicites

- Les paramètres avancés dépendent du modèle et du fournisseur ; une valeur non acceptée peut être rejetée par l’API. Les champs ajoutés depuis le sélecteur ont une valeur initiale indicative à ajuster.
- Le catalogue ne certifie pas l’accès aux modèles depuis votre compte. Les modèles en fin de vie restent soumis à la disponibilité du fournisseur. Gemini Live est un modèle preview.
- Le gateway Inference n’expose pas exactement les mêmes paramètres que les plugins directs. Changer de source réinitialise les paramètres à ceux de cette source. Gemini LLM est proposé en direct pour garantir le passage explicite de `thinking_config` ; les modèles Cartesia Inference sont limités aux entrées déclarées par le SDK.
- Les plugins peuvent rejeter un paramètre incompatible. Notamment ElevenLabs v3 n’utilise que `stability` dans ses réglages de voix. `similarity_boost`, `speed` et `style` ne sont pas des réglages v3. Les champs avancés ne rendent pas ces fonctions disponibles côté fournisseur.
- Les effets universels sont `[[breath]]`, `[[sigh]]`, `[[throat]]`, `[[laugh]]`, `[[short_pause]]`, `[[long_pause]]`. `breath` est actuellement supprimé faute de correspondance documentée retenue. Cartesia n’a ni soupir ni raclement ; les contrôles d’émotion peuvent dépendre de la langue. Les modes LLM, règles et combiné sont disponibles ; la fréquence LLM est une consigne probabiliste, pas un quota garanti.
- OpenAI STT utilise le transport HTTP pour les modèles du catalogue ; en activant `use_realtime`, le champ de paramètres bruts n’est pas accepté. Le mode speech-to-speech OpenAI possède son propre transport étendu.
- Google TTS nécessite le JSON d’un compte de service dans la clé Google, pas une clé Gemini AI Studio. Pour employer les deux dans une composition, garder une clé Gemini dans l’environnement et le compte de service dans le coffre, puis sélectionner les sources séparément.
- Le flux Cartesia TTS LiveKit est décodé en PCM16 brut. L’API refuse les changements de format qui rendraient l’audio incohérent avec le décodeur. La fréquence se règle dans les paramètres du plugin.
- G.711 natif de bout en bout pour les modèles speech-to-speech n’est pas implémenté. LiveKit transporte l’audio et les plugins assurent les conversions PCM prévues ; ne pas forcer les formats G.711 dans le JSON Realtime.
- Le bouton de validation des clés fait un appel minimal. Rime, Inworld selon les droits, et certaines API ne proposent pas de validation universelle sans synthèse : un état « indisponible » ou « validation par essai » ne signifie pas automatiquement clé invalide.

Les évolutions de SDK doivent repasser les tests de transport. Tester un constructeur seul ne garantit pas l’intégralité du comportement du fournisseur.
