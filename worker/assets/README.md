Effets joués sur une piste audio LiveKit séparée pendant la parole de l'utilisateur :

- `sneeze.ogg` : [Sneeze](https://commons.wikimedia.org/wiki/File:Sneeze.ogg), Neo139, Wikimedia Commons, conservé pour l'option existante.
- `raclement de gorge.mp4`, `tousser.mp4`, `chuchottement.mp4` : enregistrements originaux fournis pour le banc.
- `throat.wav`, `cough.wav`, `whisper.wav` : versions PCM mono 24 kHz utilisées par LiveKit ; les MP4 ne se décodaient pas correctement avec le décodeur du worker.

Les fichiers sont inclus dans l'image Docker du worker ; aucun téléchargement à l'exécution. Le chuchotement est naturellement plus discret que la toux et le raclement. Les volumes et fondus sont définis dans `worker/sounds.py`.
