# Mode Dyslexique Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un bouton "Mode dyslexique" qui, quand activé, propose une correction orthographique (via rapidfuzz) lorsqu'un mot inconnu est soumis.

**Architecture:** Nouvel endpoint `POST /suggest` dans `app.py` utilisant `rapidfuzz.process.extractOne()` sur `state.norm_to_model`. Le frontend ajoute un toggle persisté en localStorage et un bloc de suggestion inline sous le formulaire.

**Tech Stack:** Python/Flask (backend), rapidfuzz (fuzzy matching), Vanilla JS + localStorage (frontend), CSS (styles)

---

## File Structure

- Modify: `requirements.txt` — ajouter `rapidfuzz`
- Modify: `build.sh` — ajouter `rapidfuzz` au pip install
- Modify: `app.py` — nouvel endpoint `/suggest`, mise à jour du fixture `ready_state` via `norm_to_model`
- Modify: `tests/test_app.py` — tests de `/suggest`
- Modify: `templates/index.html` — bouton toggle + bloc suggestion
- Modify: `static/style.css` — styles toggle et suggestion box

---

### Task 1: Ajouter rapidfuzz comme dépendance

**Files:**
- Modify: `requirements.txt`
- Modify: `build.sh`

- [ ] **Step 1: Ajouter rapidfuzz à requirements.txt**

Remplacer le contenu de `requirements.txt` :
```
flask>=3.0
gensim>=4.3
requests>=2.31
unidecode>=1.3
pywebview>=5.0
rapidfuzz>=3.0
pytest>=8.0
```

- [ ] **Step 2: Ajouter rapidfuzz au pip install dans build.sh**

Dans `build.sh`, remplacer la ligne pip install :
```bash
pip install flask gensim pyinstaller requests unidecode pywebview rapidfuzz --quiet
```

- [ ] **Step 3: Installer rapidfuzz dans le venv actuel**

```bash
source .venv/bin/activate && pip install rapidfuzz --quiet
```

Expected: Installation sans erreur.

- [ ] **Step 4: Vérifier l'import**

```bash
source .venv/bin/activate && python -c "from rapidfuzz import process; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt build.sh
git commit -m "feat: add rapidfuzz dependency for dyslexic mode"
```

---

### Task 2: Endpoint `/suggest` dans app.py

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py`

**Contexte:** `app.py` contient `create_app(state)` qui définit les routes Flask. `state.norm_to_model` est un dict `{normalized_word: original_word}` couvrant les ~31k mots du modèle. `normalize(word)` est importé depuis `vocabulary.py` (unidecode + lower).

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_app.py` :

```python
def test_suggest_finds_close_word(client, ready_state):
    # "chein" est une faute de frappe de "chien" (dans le vocab du modèle)
    resp = client.post("/suggest", json={"word": "chein"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["suggestion"] == "chien"


def test_suggest_returns_null_when_no_match(client, ready_state):
    # "xqzjkl" n'a aucun proche dans le petit vocab de test
    resp = client.post("/suggest", json={"word": "xqzjkl"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["suggestion"] is None


def test_suggest_missing_field(client):
    resp = client.post("/suggest", json={})
    assert resp.status_code == 400


def test_suggest_not_ready():
    state = AppState()
    state.phase = "loading"
    app = create_app(state)
    app.config["TESTING"] = True
    with app.test_client() as c:
        resp = c.post("/suggest", json={"word": "chien"})
        assert resp.status_code == 503
```

- [ ] **Step 2: Mettre à jour le fixture ready_state pour inclure norm_to_model**

Dans `tests/test_app.py`, modifier le fixture `ready_state` — ajouter après `state.norm_to_vocab = build_norm_map(VOCAB)` :

```python
    state.norm_to_model = build_norm_map(VOCAB)  # même vocab en test
```

Le fixture complet devient :
```python
@pytest.fixture
def ready_state(model):
    state = AppState()
    thresholds = compute_difficulty_thresholds(VOCAB, FREQ)
    state.phase = "ready"
    state.progress = 100
    state.detail = "Prêt !"
    state.model = model
    state.vocab = VOCAB
    state.freq_by_word = FREQ
    state.norm_to_vocab = build_norm_map(VOCAB)
    state.norm_to_model = build_norm_map(VOCAB)
    state.difficulty_thresholds = thresholds
    state.top1000 = get_top1000(model, "chien")
    state.daily_word = "chien"
    state.daily_difficulty = 2
    state.game_index = 0
    return state
```

- [ ] **Step 3: Lancer les tests pour vérifier qu'ils échouent**

```bash
source .venv/bin/activate && pytest tests/test_app.py::test_suggest_finds_close_word tests/test_app.py::test_suggest_returns_null_when_no_match tests/test_app.py::test_suggest_missing_field tests/test_app.py::test_suggest_not_ready -v
```

Expected: 4 tests FAIL avec `404 NOT FOUND` (endpoint inexistant).

- [ ] **Step 4: Implémenter l'endpoint /suggest dans app.py**

Ajouter l'import en tête de `app.py`, après les imports existants :
```python
from rapidfuzz import process as fuzz_process
```

Ajouter la route dans `create_app`, après la route `/guess` (avant `return app`) :

```python
    @app.route("/suggest", methods=["POST"])
    def suggest():
        if state.phase != "ready":
            return jsonify({"error": "not ready"}), 503
        data = request.get_json(silent=True)
        if not data or "word" not in data:
            return jsonify({"error": "missing word"}), 400

        word = str(data["word"]).strip()
        norm = normalize(word)

        with state._lock:
            norm_to_model = state.norm_to_model

        result = fuzz_process.extractOne(
            norm,
            norm_to_model.keys(),
            score_cutoff=80,
        )
        if result is None:
            return jsonify({"suggestion": None})

        matched_norm = result[0]
        return jsonify({"suggestion": norm_to_model[matched_norm]})
```

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

```bash
source .venv/bin/activate && pytest tests/test_app.py -v
```

Expected: Tous les tests PASS (les anciens + les 4 nouveaux).

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: add /suggest endpoint using rapidfuzz for dyslexic mode"
```

---

### Task 3: Frontend — toggle et suggestion UI

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`

**Contexte:** Le frontend est une SPA dans `templates/index.html`. Le header `.game-header` contient `.app-title` et `.game-meta` (qui contient `#dailyDifficulty` et `#newGameBtn`). Le formulaire est `#guessForm`. La fonction `submitGuess(event)` gère la soumission — elle affiche `showError(msg)` quand `data.error === 'inconnu'`.

- [ ] **Step 1: Ajouter le bouton toggle dans le HTML**

Dans `templates/index.html`, dans `.game-meta`, ajouter le bouton après `#newGameBtn` :

```html
      <div class="game-meta">
        <span class="daily-difficulty" id="dailyDifficulty"></span>
        <button class="new-game-btn" id="newGameBtn" onclick="newGame()">
          Rejouer car je suis addicte
        </button>
        <button class="new-game-btn dyslexic-toggle" id="dyslexicToggle" onclick="toggleDyslexic()">
          Mode dyslexique : OFF
        </button>
      </div>
```

- [ ] **Step 2: Ajouter le bloc suggestion sous le formulaire**

Dans `templates/index.html`, après `<p class="error-message" id="errorMessage" ...>`, ajouter :

```html
    <div class="suggestion-box" id="suggestionBox" style="display:none">
      Vouliez-vous dire <strong id="suggestionWord"></strong>&nbsp;?
      <button class="suggestion-yes" onclick="acceptSuggestion()">Oui</button>
      <button class="suggestion-no" onclick="dismissSuggestion()">Non</button>
    </div>
```

- [ ] **Step 3: Ajouter les variables d'état et fonctions JS**

Dans le bloc `<script>`, après `let startTime = null;`, ajouter :

```javascript
let dyslexicMode = localStorage.getItem('dyslexicMode') === 'true';
let pendingSuggestion = null;

function toggleDyslexic() {
  dyslexicMode = !dyslexicMode;
  localStorage.setItem('dyslexicMode', dyslexicMode);
  document.getElementById('dyslexicToggle').textContent =
    'Mode dyslexique : ' + (dyslexicMode ? 'ON' : 'OFF');
  document.getElementById('dyslexicToggle').classList.toggle('active', dyslexicMode);
}

function showSuggestion(word) {
  pendingSuggestion = word;
  document.getElementById('suggestionWord').textContent = word;
  document.getElementById('suggestionBox').style.display = 'flex';
}

function dismissSuggestion() {
  pendingSuggestion = null;
  document.getElementById('suggestionBox').style.display = 'none';
}

function acceptSuggestion() {
  const word = pendingSuggestion;
  dismissSuggestion();
  submitWord(word);
}
```

- [ ] **Step 4: Refactoriser submitGuess pour extraire submitWord**

Dans `submitGuess`, la logique de fetch est dupliquée si on appelle depuis `acceptSuggestion`. Refactoriser en extrayant `submitWord(word)` :

Remplacer la fonction `submitGuess` existante par :

```javascript
function submitGuess(event) {
  event.preventDefault();
  const input = document.getElementById('guessInput');
  const word  = input.value.trim();
  if (!word) return;
  input.value = '';
  hideError();
  dismissSuggestion();
  submitWord(word);
}

function submitWord(word) {
  fetch('/guess', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({word})
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        if (data.error === 'inconnu' && dyslexicMode) {
          fetchSuggestion(word);
        } else {
          const msg = data.error === 'inconnu'
            ? '"' + esc(word) + '" n\'est pas dans le vocabulaire.'
            : data.error;
          showError(msg);
        }
        return;
      }
      guesses.push({word, score: data.score, rank: data.rank ?? null});
      guesses.sort((a, b) => b.score - a.score);
      renderTable();
      if (data.win) showVictory();
    })
    .catch(() => showError('Erreur réseau.'));
}

function fetchSuggestion(word) {
  fetch('/suggest', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({word})
  })
    .then(r => r.json())
    .then(data => {
      if (data.suggestion) {
        showSuggestion(data.suggestion);
      } else {
        showError('"' + esc(word) + '" n\'est pas dans le vocabulaire.');
      }
    })
    .catch(() => showError('Erreur réseau.'));
}
```

- [ ] **Step 5: Initialiser l'état du bouton au chargement**

Dans la fonction `activateGame()`, après `document.getElementById('guessInput').focus();`, ajouter :

```javascript
      document.getElementById('dyslexicToggle').textContent =
        'Mode dyslexique : ' + (dyslexicMode ? 'ON' : 'OFF');
      document.getElementById('dyslexicToggle').classList.toggle('active', dyslexicMode);
```

- [ ] **Step 6: Ajouter les styles CSS**

Dans `static/style.css`, à la fin du fichier, ajouter :

```css
/* ===== Dyslexic mode toggle ===== */
.dyslexic-toggle.active {
  background: #e8f4e8;
  border-color: #4caf50;
  color: #2e7d32;
}

/* ===== Suggestion box ===== */
.suggestion-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #fffde7;
  border: 1px solid #f9a825;
  border-radius: 4px;
  font-size: 0.9rem;
}
.suggestion-yes {
  padding: 0.2rem 0.6rem;
  background: #4a90e2;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}
.suggestion-yes:hover { background: #357abd; }
.suggestion-no {
  padding: 0.2rem 0.6rem;
  background: none;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  color: #555;
}
.suggestion-no:hover { background: #eee; }
```

- [ ] **Step 7: Tester manuellement dans le navigateur**

```bash
source .venv/bin/activate && python main.py --design
```

Vérifications :
1. Le bouton "Mode dyslexique : OFF" apparaît dans le header
2. Clic sur le bouton → texte passe à "Mode dyslexique : ON", fond vert
3. Recharger la page → le mode reste ON (localStorage)
4. Taper "chein" (faute de "chien") → suggestion "Vouliez-vous dire **chien** ?" apparaît
5. Clic "Oui" → "chien" soumis, score affiché
6. Taper "coinzer" (faute de "coincer") → suggestion apparaît
7. Clic "Non" → suggestion disparaît
8. Désactiver le mode → "chein" donne "pas dans le vocabulaire"

- [ ] **Step 8: Commit**

```bash
git add templates/index.html static/style.css
git commit -m "feat: dyslexic mode UI — toggle button and suggestion box"
```
