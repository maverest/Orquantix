# Mode Dyslexique — Design Spec

## Objectif

Ajouter un mode optionnel qui propose une correction orthographique automatique lorsque l'utilisateur tape un mot inconnu. Le mode cible les joueurs dyslexiques ou les fautes de frappe courantes.

## Comportement

### Activation
- Bouton toggle dans le header (même style que "Rejouer car je suis addicte")
- Libellé : "Mode dyslexique : OFF" / "Mode dyslexique : ON"
- État persisté en `localStorage` (survit au rechargement de page)
- Désactivé par défaut

### Flow de correction (mode ON)
1. L'utilisateur soumet un mot via le formulaire
2. Le backend répond `{"error": "inconnu"}`
3. Le frontend envoie `POST /suggest` avec le mot original
4. Le backend cherche le mot le plus proche dans les ~31 000 mots acceptés comme propositions
5. Si un mot avec score rapidfuzz ≥ 80 est trouvé :
   - Affiche sous le champ : **"Vouliez-vous dire *X* ?"** + bouton "Oui" + bouton "Non"
   - "Oui" → soumet le mot suggéré comme une proposition normale
   - "Non" → ferme la suggestion, l'utilisateur peut retaper
6. Si aucun mot assez proche (score < 80) : affiche le message d'erreur habituel "pas dans le vocabulaire"

### Flow de correction (mode OFF)
Comportement inchangé — erreur "pas dans le vocabulaire" directement.

## Architecture

### Backend — `app.py`
Nouvel endpoint :
```
POST /suggest
Body: {"word": "mot_mal_orthographié"}
Réponse OK: {"suggestion": "mot_corrigé"}
Réponse sans match: {"suggestion": null}
```
- Utilise `rapidfuzz.process.extractOne()` sur les clés de `state.norm_to_model`
- Seuil : score ≥ 80 (WRatio scorer)
- Retourne le mot original du modèle (pas la forme normalisée)
- Disponible uniquement quand `state.phase == "ready"`

### Frontend — `templates/index.html`
- État JS : `dyslexicMode` (boolean, initialisé depuis localStorage)
- État JS : `pendingSuggestion` (string|null)
- Bouton toggle dans `.game-meta` (à côté de "Rejouer")
- Bloc suggestion : `<div id="suggestionBox">` sous le formulaire, caché par défaut
- La suggestion disparaît automatiquement si l'utilisateur retape dans le champ

### CSS — `static/style.css`
- `.dyslexic-toggle` : style similaire à `.new-game-btn`
- `.dyslexic-toggle.active` : fond légèrement coloré pour indiquer l'état ON
- `.suggestion-box` : bloc inline sous le formulaire, fond jaune pâle, boutons "Oui"/"Non"

## Dépendances
- `rapidfuzz` ajouté à `requirements.txt` et `build.sh`

## Ce qui ne change pas
- Le vocabulaire des mots mystères (sélection du mot du jour) — inchangé
- La logique de score et de rang — inchangée
- Le comportement quand le mode est désactivé — inchangé
