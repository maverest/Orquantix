let guesses = [];
let startTime = null;
let guessCounter = 0;
let pendingSuggestion = null;
let timerRunning = false;
let timerStartedAt = null;
let timerCompletedMs = null;
let timerInterval = null;
let currentGameUsedHint = false;
let currentGameResolved = false;

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

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(totalSeconds / 60);
  const s = String(totalSeconds % 60).padStart(2, '0');
  return m + ':' + s;
}

function updateTimerDisplay() {
  const el = document.getElementById('timerDisplay');
  if (timerRunning && timerStartedAt !== null) {
    el.textContent = 'Timer : ' + formatDuration(Date.now() - timerStartedAt);
    return;
  }
  if (timerCompletedMs !== null) {
    el.textContent = 'Timer : ' + formatDuration(timerCompletedMs);
    return;
  }
  el.textContent = 'Timer : --:--';
}

function updateTimerButton() {
  const button = document.getElementById('timerBtn');
  if (timerRunning) {
    button.textContent = 'Timer en cours';
    button.disabled = true;
    return;
  }
  if (timerCompletedMs !== null) {
    button.textContent = 'Timer terminé';
    button.disabled = true;
    return;
  }
  button.textContent = 'Mode timer';
  button.disabled = false;
}

function updateGiveUpButton() {
  const button = document.getElementById('giveUpBtn');
  const alreadyResolved = guesses.some(g => g.win);
  button.disabled = alreadyResolved;
}

function updateReplayButton(visible) {
  document.getElementById('orcaReplayBtn').style.display = visible ? 'inline-flex' : 'none';
}

function startTimerMode() {
  if (timerRunning || timerCompletedMs !== null) return;
  timerRunning = true;
  timerStartedAt = Date.now();
  clearInterval(timerInterval);
  timerInterval = setInterval(updateTimerDisplay, 250);
  updateTimerDisplay();
  updateTimerButton();
  speakOrca('timer-start', currentOrcaMood, true);
}

function stopTimer() {
  if (!timerRunning || timerStartedAt === null) return;
  timerCompletedMs = Date.now() - timerStartedAt;
  timerRunning = false;
  clearInterval(timerInterval);
  timerInterval = null;
  updateTimerDisplay();
  updateTimerButton();
}

function resetTimer() {
  timerRunning = false;
  timerStartedAt = null;
  timerCompletedMs = null;
  clearInterval(timerInterval);
  timerInterval = null;
  updateTimerDisplay();
  updateTimerButton();
}

function toggleHintPanel() {
  const panel = document.getElementById('hintPanel');
  panel.style.display = panel.style.display === 'flex' ? 'none' : 'flex';
}

function getBestGuess() {
  if (!guesses.length) return null;
  return guesses.reduce((best, guess) => {
    if (!best) return guess;
    return guess.temperature > best.temperature ? guess : best;
  }, null);
}

function requestHint(type) {
  currentGameUsedHint = true;
  const bestGuess = getBestGuess();
  fetch('/games/orquantix/hint', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      type,
      best_rank: bestGuess ? bestGuess.rank : null,
      guessed_words: guesses.map(g => g.word)
    })
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        showError(data.error);
        return;
      }
      if (data.value && (type === 'better-word' || type === 'golden-fish')) {
        document.getElementById('guessInput').placeholder = 'Indice : ' + data.value;
      }
      speakOrca(type, currentOrcaMood, true);
      if (orcaMode !== 'mute') {
        document.getElementById('orcaBubble').textContent = data.message;
      }
    })
    .catch(() => showError('Erreur réseau.'));
}

function renderDifficulty(d) {
  document.getElementById('dailyDifficulty').textContent =
    'Difficulté : ' + '⭐'.repeat(d) + '☆'.repeat(5 - d);
}

function showError(msg) {
  const el = document.getElementById('errorMessage');
  el.textContent = msg;
  el.style.display = 'block';
}

function hideError() {
  document.getElementById('errorMessage').style.display = 'none';
}

// ─── Polling ─────────────────────────────────────────────────────────────
function pollStatus() {
  fetch('/games/orquantix/status')
    .then(r => r.json())
    .then(data => {
      document.getElementById('progressBar').style.width = data.progress + '%';
      document.getElementById('downloadDetail').textContent = data.detail || '';
      if (data.phase === 'ready') {
        activateGame();
      } else if (data.phase === 'error') {
        document.getElementById('downloadError').textContent = data.detail || 'Erreur inconnue.';
        document.getElementById('downloadError').style.display = 'block';
      } else {
        setTimeout(pollStatus, 500);
      }
    })
    .catch(() => setTimeout(pollStatus, 1000));
}

function activateGame() {
  // /session peut encore répondre 503 juste après que /status soit passé
  // à "ready" (deux routes distinctes). Tant que ce n'est pas le cas, on
  // retente sans jamais basculer sur l'écran de jeu avec un plateau vide.
  fetch('/games/orquantix/session')
    .then(r => {
      if (!r.ok) throw new Error('session not ready');
      return r.json();
    })
    .then(data => {
      document.getElementById('downloadScreen').style.display = 'none';
      document.getElementById('gameScreen').style.display = 'block';
      startTime = Date.now();
      guessCounter = 0;

      renderDifficulty(data.difficulty);
      guesses = data.guesses.map((g, i) => ({...g, attempt: i + 1, temperatureAnimated: true}));
      guessCounter = guesses.length;
      guesses.sort((a, b) => b.temperature - a.temperature);
      renderTable();

      document.getElementById('guessInput').focus();
      document.body.classList.toggle('dyslexic-mode', dyslexicMode);
      document.getElementById('dyslexicToggle').textContent =
        'Mode dyslexique : ' + (dyslexicMode ? 'ON' : 'OFF');
      document.getElementById('dyslexicToggle').classList.toggle('active', dyslexicMode);
      resetTimer();
      currentGameUsedHint = false;
      currentGameResolved = false;
      updateGiveUpButton();
      applyOrcaTool(orcaMode, 'Ola que tal');

      if (data.resolved) showVictory();
    })
    .catch(() => setTimeout(activateGame, 500));
}

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
  triggerEasterEgg(word);
  fetch('/games/orquantix/guess', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({word})
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        if (data.error === 'inconnu') {
          speakOrca('unknown', 'sick', true);
        }
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
      guesses.push({
        ...data,
        attempt: ++guessCounter,
        temperatureAnimated: false,
      });
      guesses.sort((a, b) => b.temperature - a.temperature);
      speakOrca(data.mood, data.mood, false);
      updateGiveUpButton();
      renderTable().then(() => {
        if (data.win) showVictory();
      });
    })
    .catch(() => showError('Erreur réseau.'));
}

function giveUp() {
  fetch('/games/orquantix/give-up', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        showError(data.error);
        return;
      }
      guesses.push({
        ...data,
        attempt: ++guessCounter,
        temperatureAnimated: false,
      });
      guesses.sort((a, b) => b.temperature - a.temperature);
      updateGiveUpButton();
      if (orcaMode !== 'mute') {
        document.getElementById('orcaBubble').textContent = 'Bah alors, on abandonne ??';
      }
      renderTable().then(() => {
        showVictory();
      });
    })
    .catch(() => showError('Erreur réseau.'));
}

function fetchSuggestion(word) {
  fetch('/games/orquantix/suggest', {
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

function animateTemperature(row, guess) {
  const valueEl = row.querySelector('.temperature-value');
  const fillEl = row.querySelector('.temperature-bar-fill');
  const target = Math.max(0, Math.min(100, Number(guess.temperature) || 0));

  guess.temperatureAnimated = true;

  if (!valueEl || !fillEl || target <= 0) {
    if (valueEl) valueEl.textContent = Math.round(target) + '°';
    if (fillEl) fillEl.style.width = target + '%';
    return Promise.resolve();
  }

  fillEl.classList.add('is-animating');

  return new Promise(resolve => {
    const duration = Math.min(2200, 520 + target * 12);
    const start = performance.now();

    function step(now) {
      const ratio = Math.min((now - start) / duration, 1);
      const current = target * ratio;
      fillEl.style.width = current + '%';
      valueEl.textContent = Math.round(current) + '°';

      if (ratio < 1) { requestAnimationFrame(step); return; }

      fillEl.classList.remove('is-animating');
      fillEl.style.width = target + '%';
      valueEl.textContent = Math.round(target) + '°';
      resolve();
    }

    requestAnimationFrame(step);
  });
}

function renderTable() {
  const tbody = document.getElementById('guessTableBody');
  const animations = [];
  tbody.innerHTML = '';

  for (const g of guesses) {
    const tr = document.createElement('tr');
    const shouldAnimate = g.temperatureAnimated !== true;
    const shown = shouldAnimate ? 0 : g.temperature;

    tr.className = 'guess-row orca-' + g.mood;
    tr.innerHTML =
      '<td class="guess-number">' + g.attempt + '</td>' +
      '<td class="guess-word">' + esc(g.word) + '</td>' +
      '<td class="guess-temperature">' +
        '<div class="temperature-row">' +
          '<span class="temperature-value">' + Math.round(shown) + '°</span>' +
          '<div class="temperature-bar">' +
            '<div class="temperature-bar-fill" style="width:' + shown + '%"></div>' +
          '</div>' +
        '</div>' +
      '</td>' +
      '<td class="guess-rank">' +
        (g.rank ? '<span class="rank-badge">#' + g.rank + '</span>' : '<span class="rank-none">—</span>') +
      '</td>' +
      '<td class="guess-orca">' +
        '<img class="orca-emoji" src="' + esc(PROXIMITY_ICONS[g.mood] || PROXIMITY_ICONS.sick) +
        '" alt="' + esc(g.label) + '" title="' + esc(g.label) + '">' +
      '</td>';

    tbody.appendChild(tr);
    if (shouldAnimate) animations.push(animateTemperature(tr, g));
  }

  return Promise.all(animations);
}

function showVictory() {
  if (!currentGameResolved) {
    currentGameResolved = true;
  }
  if (timerRunning) {
    stopTimer();
  }
  document.getElementById('guessForm').style.display    = 'none';
  updateReplayButton(true);
  speakOrca('found', 'found', true);
}

function newGame() {
  fetch('/games/orquantix/new-game', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
      guesses = [];
      guessCounter = 0;
      startTime = Date.now();
      resetTimer();
      currentGameUsedHint = false;
      currentGameResolved = false;
      renderDifficulty(data.difficulty);
      renderTable();
      document.getElementById('guessForm').style.display    = 'flex';
      document.getElementById('hintPanel').style.display = 'none';
      document.getElementById('guessInput').placeholder = 'Proposez un mot…';
      hideError();
      updateGiveUpButton();
      updateReplayButton(false);
      document.getElementById('guessInput').focus();
      setOrcaState('neutral', 'Ola que tal');
    })
    .catch(() => showError('Erreur réseau.'));
}

pollStatus();
