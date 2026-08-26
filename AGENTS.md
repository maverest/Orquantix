# AGENTS.md — PROCRASTINATOR / Orquantix

Contexte pour un agent qui reprend ce dépôt. Lire en entier avant de modifier quoi que ce soit :
plusieurs invariants d'apparence anodine ont coûté des heures à établir et se cassent silencieusement.

## Ce qu'est le projet

**PROCRASTINATOR** est une application macOS (Flask + pywebview, packagée par PyInstaller) conçue
comme une **coquille hébergeant des mini-jeux**. Un seul existe aujourd'hui : **Orquantix**, un jeu
de proximité sémantique en français inspiré de Cemantix.

Le menu de PROCRASTINATOR et les autres mini-jeux (quiz géographiques envisagés) sont la **phase 2**
et ne sont pas encore écrits. En attendant, la route `/` redirige vers Orquantix.

## Démarrer

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest          # doit afficher 117 passed, 0 skipped
python main.py --design   # ouvre dans le navigateur au lieu de la fenêtre native
```

`python main.py` (sans `--design`) ouvre une fenêtre native — inutilisable en agent headless.

## Dépendance aux données : à lire avant de s'étonner

Au premier lancement l'application télécharge **~180 Mo** dans
`~/Library/Application Support/Procrastinator/` : Lexique383, un modèle Word2Vec français
(31 548 mots), et le dictionnaire Littré (corps + index, deux fichiers).

Conséquences dans un environnement sans réseau ou sans ces fichiers :
- trois tests sur données réelles se mettent en `skip` au lieu d'échouer ;
- `load_resources()` échoue et l'application reste sur son écran de chargement.

**Un `skip` sur ces trois tests est une régression, pas un événement neutre.** Ils sont la seule
garantie contre les fuites du dictionnaire (voir plus bas). Toujours lancer `pytest -rs` et vérifier
`0 skipped`.

`main.get_data_dir()` **renomme un vrai dossier** en effet de bord (migration depuis les anciens noms
`Orquantix` puis `Semantix`). Ne jamais l'appeler dans un test sans avoir monkeypatché `Path.home()`.

## Architecture

```
main.py              fenêtre webview, port libre, résolution + migration du dossier de données
app.py               LA COQUILLE — monte les blueprints, sert / et /status. Ne connaît AUCUNE règle de jeu.
downloader.py        quatre téléchargements déclarés, parts de progression sommant à 100
games/orquantix/
  routes.py          Blueprint, préfixe /games/orquantix
  state.py           OrquantixState — état serveur, verrouillé
  engine.py          pur : courbe de progression, tirage du mot, difficulté
  vocabulary.py      construit les deux pools depuis Lexique383
  dictionary.py      lecture et nettoyage du Littré
  hints.py           sélection des indices
  orca.py            humeurs de la mascotte
static/orquantix/    game.js, orca.js, style.css
static/shell.css     tokens pour le futur menu — DÉCLARÉ MAIS PAS ENCORE CONSOMMÉ
templates/orquantix/index.html   aucun <script> inline
```

Règle structurante : **`app.py` n'importe que quatre symboles** de `games.orquantix`
(`GAME_ID`, `OrquantixState`, `build_blueprint`, `load_resources`), et `games/` n'importe **jamais**
`app.py`. Si une règle de jeu remonte dans la coquille, la frontière est mal placée.

## Invariants à ne pas casser

### 1. La courbe de progression est volontairement plate en bas

`engine.progress(rank)` vaut `((1001 - rang) / 1000) ** 3.4 * 100`, et **0 hors du top 1000**.
Au rang 800 elle vaut 0,43 %, au rang 400 environ 18 %, et elle ne décolle que dans le top 100.

**Ce n'est pas un bug.** Une version antérieure utilisait une échelle continue basée sur le cosinus,
avec 50 % à l'entrée dans le top 1000 ; le propriétaire l'a rejetée après essai : un voisin de rang 800
n'apprend rien au joueur, et une barre à moitié pleine ment. La colonne Rang signale déjà l'entrée
dans le top 1000, donc la barre n'a pas à le redire.

Ne pas « adoucir » cette courbe sans demande explicite.

### 2. Les humeurs de la mascotte sont indexées sur le RANG, pas sur la progression

`orca.mood_for(rank)` : hors top 1000 `sick`, ≥551 `vexed`, ≥176 `intrigued`, ≥31 `overexcited`,
1–30 `solar`. Découplé de la barre précisément parce que celle-ci est plate en bas — une humeur
indexée dessus ne dépasserait jamais `vexed` avant le rang 300.

### 3. Aucun indice ne doit sortir du pool d'indices

C'est le bug qui a motivé toute la refonte : les indices piochaient dans les 31 548 mots bruts du
modèle, si bien que le jeu pouvait répondre « essaie *des* », « essaie *jupiter* », ou — pour le mot
mystère *glacial* — « essaie *audie* », un prénom qui se trouvait être le plus proche voisin.

`hints._eligible()` est le **point de passage unique** qui filtre sur `hint_words`. Tout chemin qui
renvoie un mot doit passer par lui. `tests/orquantix/test_hints.py` contient le test qui aurait
attrapé le bug d'origine.

### 4. Le dictionnaire ne doit jamais trahir le mot mystère

`dictionary.clean_definition()` alimente le « poisson doré », qui lit la définition Littré du mot
à deviner. Chaque entrée du Littré commence par une transcription phonétique qui **épelle le mot** —
`(kon-fi-tu-r')` pour *confiture*. La laisser passer transforme l'indice en réponse.

Ce module a demandé quatre passes de revue. Trois classes de fuite ont été trouvées et fermées, dont
une où le masquage cachait bien « ogresse » mais où la transcription juste après l'épelait quand même.

**Deux tests balaient 8 000 entrées réelles** et vérifient trois invariants : aucune parenthèse
phonétique résiduelle, aucune structure de tête résiduelle, aucune fuite littérale du mot-vedette.
Toute modification de ce module doit les laisser verts — et ils doivent **tourner**, pas être `skip`.

Limites connues, mesurées et assumées : le masquage est inopérant pour les cibles à apostrophe
(verbes pronominaux) et pour la ligature `œ`. Les deux sont **inatteignables par le jeu** : le filtre
de `vocabulary.py` rejette apostrophes et ligatures du pool. Vérifié à 0 sur les 2 788 mots réels.

### 5. Ne jamais balayer tout le vocabulaire par proposition

Une version antérieure calculait une médiane sur la matrice complète 31 548 × 1 000 à chaque
changement de mot mystère. Ce code a été supprimé. Si un besoin similaire réapparaît, le calcul se
fait **une fois par mot mystère** et se stocke dans l'état, jamais dans la route `/guess`.

### 6. Les mutations de l'état passent par ses méthodes

`OrquantixState.record_guess(round_index, entry)` et `start_new_round(...)` sont des transactions
verrouillées, avec un jeton de tour. Ne pas écrire directement dans `state.guesses` ni
`state.game_index` : une proposition arrivant pendant un « Rejouer » écrirait dans la liste jetée,
et le joueur recevrait une réponse disant que son mot est pris alors qu'il a disparu.

## Front-end : pièges rencontrés

**`filter` en CSS remplace la valeur héritée, il ne s'y ajoute pas.** Une règle
`body.dyslexic-mode .orca-avatar-image { filter: saturate(1.25) }` a effacé les `drop-shadow` qui
font ressortir la mascotte sur le thème sombre : elle disparaissait purement et simplement. Toute
surcharge de `filter` doit répéter les ombres.

**Les couches décoratives ne doivent jamais intercepter les clics** — `pointer-events: none`, sauf
Charlie qui est cliquable et remet `pointer-events: auto`.

**Un conteneur en position absolue sans `right: 0` se rétracte sur son contenu.** Le bateau, le vélo
et les aigles frétillaient sur 100 pixels au bord gauche au lieu de traverser l'écran.

**Le saut de l'orque et la réaction de la fille partagent un cycle de 9 secondes.** La synchronisation
est l'intention : sa joie doit tomber au sommet du saut. Ne pas les désolidariser.

**`prefers-reduced-motion` fige toute la scène.** À conserver : sans ce repli le jeu devient
inutilisable pour qui a désactivé les animations dans macOS.

## Easter eggs

Déclarés dans une **table** en tête de `static/orquantix/orca.js` — dix entrées, treize déclencheurs.
Ajouter un easter egg = une entrée dans la table, un `<div>` dans le template, une animation en CSS.

```js
{ id: 'easterAigles', triggers: ['aigle', 'aigles'], duration: 6700,
  onShow: showGirlJoy, onHide: restoreGirlCycle }
```

Le câblage en dur qui précédait demandait cinq modifications dans trois fichiers par ajout.

## Documents

- `docs/superpowers/specs/2026-08-16-*.md` — la spec de la refonte. **Périmée par endroits** :
  `/daily-info` a été remplacé par `/session`, `norm_to_vocab` a été supprimé plutôt que recyclé,
  et l'exemple citant `confire` comme indice conservé est faux (0,95/M, sous le plancher de 5).
  Le code a raison, la spec traîne.
- `docs/superpowers/plans/2026-08-16-*.md` — le plan d'implémentation suivi.
- `docs/design/` — les maquettes validées du thème Abysse et des personnages, plus le journal
  complet de la refonte avec toutes les mesures et décisions.

## Conventions

- Messages de commit et documentation en **français**, code et identifiants en anglais.
- Les tests sont la spécification exécutable. **Ne jamais affaiblir une assertion** pour faire passer
  du code : si une assertion ne peut pas tenir, c'est un signal, pas un obstacle.
- Vérifier sur **données réelles** avant de conclure. Chaque défaut sérieux de ce projet était
  invisible sur une poignée d'exemples choisis à la main et évident sur un balayage large.
