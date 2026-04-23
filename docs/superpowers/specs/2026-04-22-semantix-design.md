# Semantix — Design Spec
*Date: 2026-04-22*

## Vue d'ensemble

Clone de Cemantix jouable localement sur Mac. L'utilisateur double-clique sur `Semantix.app` et joue dans son navigateur en local. Backend Flask + embeddings Word2Vec Fauconnier, packagé en `.app` via PyInstaller.

---

## Architecture générale

```
Semantix/
├── main.py              # Point d'entrée PyInstaller : lance Flask + ouvre browser
├── app.py               # Application Flask (routes, orchestration)
├── game.py              # Logique pure : mot du jour, score, voisins, difficulté
├── downloader.py        # Téléchargement modèle + Lexique383 avec progression
├── vocabulary.py        # Filtrage vocabulaire avec Lexique383
├── templates/
│   └── index.html       # UI unique (jeu + download screen)
├── static/
│   └── style.css        # CSS minimal placeholder
└── build.sh             # Script de build PyInstaller
```

### Flux au lancement

1. `main.py` démarre Flask dans un daemon thread, poll `http://localhost:5000/` toutes les 200ms (max 15s), puis ouvre le navigateur
2. Flask démarre → vérifie la présence du modèle et de Lexique383 dans `~/Library/Application Support/Semantix/`
3. **Si fichiers absents** : `downloader.py` démarre en thread de fond, télécharge Lexique383 puis le modèle en séquence, Flask sert la page de téléchargement, `/status` expose la progression
4. **Si fichiers présents** : chargement gensim en thread de fond, Flask sert la page jeu une fois le modèle prêt
5. Cache des 1000 voisins du mot du jour pré-calculé après chargement

**Gestion du port occupé :** si 5000 est pris, tenter 5001, 5002 — ouvrir le navigateur sur le bon port.

---

## Backend Flask

### Routes

| Route | Méthode | Description |
|---|---|---|
| `/` | GET | Sert `index.html` |
| `/status` | GET | État du système : phase + progression |
| `/guess` | POST | Soumet un mot, retourne score/rang/win |
| `/daily-info` | GET | Infos publiques du mot du jour |
| `/new-game` | POST | Incrémente game_index, nouveau mot du jour |

### Détail des réponses

**`GET /status`**
```json
{
  "phase": "downloading" | "loading" | "ready",
  "progress": 0-100,
  "detail": "Téléchargement du modèle… 342 Mo / 600 Mo"
}
```

**`POST /guess`** — body: `{"word": "chien"}`
```json
{"score": 67.24, "rank": 342, "win": false}
// ou
{"error": "inconnu"}
```

**`GET /daily-info`**
```json
{"difficulty": 3, "word_length": 5}
```

**`POST /new-game`**
```json
{"difficulty": 3, "word_length": 5}
```

---

## Logique jeu — `game.py`

### Mot du jour

- Paramètre `game_index` (entier, défaut 0)
- Seed : `f"{date.today().isoformat()}-{game_index}"`
- Sélection déterministe dans le vocabulaire filtré
- Index 0 = partie quotidienne, index 1/2/3... = reparties du même jour (bouton "Rejouer")
- `game_index` stocké en mémoire dans `app.py`, réinitialisé au redémarrage

### Score

- Cosine similarity × 100, arrondi 2 décimales
- Mot exact → 100.00 (cosine similarity = 1.0 avec lui-même)
- Victoire : `win: true` quand score = 100.00

### Top 1000

- `get_top1000(model, target)` → dict `{mot: rang}` (rang 1 = plus proche)
- Pré-calculé au chargement, lookup O(1) pendant la partie
- Recalculé après chaque `/new-game`

### Difficulté

- `get_difficulty(word, lexique_freq)` → entier 1–5
- Quintiles sur la fréquence Lexique383 de l'ensemble du vocabulaire éligible
- 1 = mot très fréquent (facile), 5 = mot rare (difficile)
- Affiché dès le début : `⭐⭐⭐☆☆`

### Normalisation des entrées

- lowercase + `unidecode` sur chaque guess avant lookup
- "Église", "eglise", "EGLISE" → tous matchent le même vecteur

---

## Vocabulaire — `vocabulary.py`

### Source : Lexique383

Fichier TSV téléchargé depuis `http://www.lexique.org/databases/Lexique383/Lexique383.tsv`

### Critères de filtrage

Un mot est éligible si toutes ces conditions sont remplies :

1. Présent dans le vocabulaire gensim du modèle Fauconnier
2. Présent dans Lexique383 avec l'une des catégories grammaticales :
   - `NOM` + forme singulière
   - `ADJ` + forme masculine singulière
   - `VER` + forme infinitive
3. Aucun espace, tiret ou apostrophe dans le mot
4. Fréquence Lexique383 ≥ 5 occurrences/million (seuil calibrable)

Les noms propres sont automatiquement exclus car absents de la catégorie `NOM` dans Lexique383.

---

## Téléchargement — `downloader.py`

### Fichiers téléchargés

Répertoire cible : `~/Library/Application Support/Semantix/`

1. **Lexique383** (~9 Mo)
   - URL : `http://www.lexique.org/databases/Lexique383/Lexique383.tsv`
2. **Modèle Word2Vec Fauconnier** (~195 Mo)
   - Fichier : `frWiki_no_phrase_no_postag_1000_skip_cut200.bin`
   - URL : `https://embeddings.net/embeddings/frWiki_no_phrase_no_postag_1000_skip_cut200.bin`

### Comportement

- Téléchargements en séquence (Lexique383 d'abord, modèle ensuite)
- Streaming HTTP avec progression byte-by-byte via `requests`
- `/status` retourne progression 0–100 globale sur l'ensemble des deux téléchargements
- Au lancement : si l'un des deux fichiers manque → retéléchargement

---

## Frontend — `templates/index.html`

### Deux écrans dans un seul template

Visibilité gérée par JS selon la `phase` retournée par `/status`.

#### `.download-screen`

Affiché quand `phase != "ready"` :
- Message d'accueil + explication
- `.download-progress-bar`
- `.download-detail` (texte de progression, ex. "Téléchargement du modèle… 97 Mo / 195 Mo")

#### `.game-screen`

Affiché quand `phase == "ready"` :

```
.game-header
  .daily-difficulty     ← ex. ⭐⭐⭐☆☆
  .new-game-btn         ← "Rejouer car je suis addicte"

.guess-form
  input[type=text]
  button.submit-btn

.guess-table
  thead: Mot | Score | Rang | Temp.
  tbody: .guess-row (triées par score décroissant)
    .guess-word | .guess-score | .guess-rank | .guess-temp

.victory-screen         ← caché jusqu'à score 100.00
  .victory-message
  .victory-stats        ← nb de tentatives, temps
```

### Logique JS

- `pollStatus()` — polling `/status` toutes les 500ms jusqu'à `phase == "ready"`
- `submitGuess()` — POST `/guess`, insère `.guess-row`, re-trie par score décroissant
- Soumission via Enter ou bouton
- Si `win: true` → affiche `.victory-screen`
- Bouton "Rejouer" → POST `/new-game`, reset tableau, mise à jour difficulté

### Classes de température

| Score | Classe CSS |
|---|---|
| < 20 | `.temp-glacial` |
| 20–39 | `.temp-froid` |
| 40–59 | `.temp-tiede` |
| 60–79 | `.temp-chaud` |
| 80–99 | `.temp-brulant` |
| 100 | `.temp-victoire` |

Le JS assigne uniquement la classe. Le contenu (texte/emoji/blague) est défini dans le CSS via `::before` ou dans un `<span>` remplaçable — aucune modification JS requise pour personnaliser.

---

## Packaging — `build.sh`

1. Crée et active un virtualenv Python 3.11
2. `pip install flask gensim pyinstaller requests unidecode`
3. PyInstaller avec :
   - `--onedir` → `dist/Semantix.app`
   - `--windowed` → pas de terminal visible
   - `--add-data "templates:templates"`
   - `--add-data "static:static"`
   - `--hidden-import` pour les modules gensim/numpy
4. Copie le `.app` à la racine du projet

---

## Décisions techniques retenues

| Sujet | Décision | Raison |
|---|---|---|
| Chargement modèle | Thread de fond | Flask répond immédiatement, pas de timeout browser |
| Difficulté | Quintiles fréquence Lexique383 | Simple, stable, corrèle avec la rareté perçue |
| PyInstaller | `--onedir` | Plus rapide au lancement, plus facile à déboguer |
| Score | cosine × 100, 2 décimales | Fidèle à l'original Cemantix |
| Normalisation | lowercase + unidecode | Tolérance aux accents et majuscules |
| Reparties | game_index en mémoire | Simple, acceptable pour usage solo |
