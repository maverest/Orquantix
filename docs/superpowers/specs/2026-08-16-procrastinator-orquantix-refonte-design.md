# PROCRASTINATOR — Refonte d'Orquantix — Design Spec

*Date : 2026-08-16*

## Vue d'ensemble

Deux mouvements en un seul chantier.

1. **L'application devient PROCRASTINATOR**, une coquille qui héberge plusieurs mini-jeux. Orquantix, le jeu de mots sémantique existant, en devient le premier.
2. **Orquantix est refondu** : pool de mots mystères resserré, retour au joueur repensé autour d'une température continue, indices débogués, poisson doré transformé en lecteur de dictionnaire.

Le menu de PROCRASTINATOR lui-même n'est **pas** dans le périmètre de cette spec — il sera designé en phase 2. Cette phase livre la coquille, l'isolation d'Orquantix, et la refonte du gameplay.

---

## Motivation — ce que l'audit a montré

Trois problèmes mesurés sur le code et les données réelles, qui justifient les décisions qui suivent.

**Les indices sont cassés.** Ils piochent dans `model.most_similar()`, c'est-à-dire les 31 548 mots bruts du modèle, sans aucun filtre — alors que le mot mystère provient d'un pool filtré par Lexique383. Les deux ensembles ne coïncident pas. Environ 8 à 9 % des 1000 voisins d'un mot ne pourraient jamais être le mot mystère. Le jeu peut donc proposer `des`, `du`, `souvent`, `très`, `leurs`, `davantage`, ou des noms propres comme `jupiter`, `charlie`, `uranus`. Cas le plus parlant : pour le mot **glacial**, le voisin de rang 1 est `audie` (un prénom, cos 0.466) — le poisson doré, censé être l'indice le plus fort du jeu, répond « essaie audie ».

**Les mots mystères sont tirés uniformément.** `get_daily_word` tire au hasard dans 6 916 mots sans pondération. Une partie sur cinq tombe donc dans le quintile le plus rare (5 à 7 occurrences par million) : *péripétie, parvis, madone, impénétrable*. À l'autre extrémité, le haut du pool est tout aussi mauvais comme cible : *être, avoir, faire, dire, tout, aller* — des mots-outils aux voisinages sémantiques vides. Le pool a un plancher de fréquence mais aucun plafond.

**La barre de progression est morte 96,7 % du temps.** La formule `((1001 − rang) / 1000) ^ 3.4 × 100` renvoie 0,00 % pour tout mot hors du top 1000, soit environ 30 500 des 31 548 mots proposables. Même à l'intérieur du top 1000 elle reste indiscernable de zéro au-delà du rang 900 (0,04 %). Le seul signal continu existant, le cosinus, est relégué dans une colonne « Score brut » qui a l'apparence d'un affichage de debug.

---

## Décisions

| Sujet | Décision |
|---|---|
| Nom de l'application | PROCRASTINATOR |
| Nom du mini-jeu | Orquantix (inchangé) |
| Navigation | Une vraie page par jeu, blueprints Flask |
| État de partie | Côté serveur, survit à la navigation |
| Chargement des ressources | Paresseux, déclenché à l'entrée dans le jeu |
| Pool des mots mystères | Noms communs singuliers, fréquence 10–400/M (~2 788 mots) |
| Pool des indices | Mots de contenu : NOM, VER infinitif, ADJ masc. sing. (~6 900 mots) |
| Vocabulaire de proposition | Inchangé — les 31 548 mots du modèle |
| Retour au joueur | Deux signaux : température continue + rang dans le top 1000 |
| Affichage | Deux colonnes distinctes (Température, Rang) |
| Humeurs de l'orque | Indexées sur la température |
| Portée de l'orque | Spécifique à Orquantix |
| Poisson doré | Définition Littré du mot mystère, repli sur le voisin fort |

---

## Architecture

### Structure cible

```
PROCRASTINATOR/
├── main.py                      # fenêtre webview, port libre, dossier de données
├── app.py                       # coquille : monte les jeux, route /, route /status
├── downloader.py                # téléchargement des ressources (3 fichiers)
├── games/
│   ├── __init__.py
│   └── orquantix/
│       ├── __init__.py          # expose le blueprint et le chargeur de ressources
│       ├── routes.py            # Blueprint, préfixe /games/orquantix
│       ├── state.py             # OrquantixState — état isolé du jeu
│       ├── engine.py            # pur : température, rang, victoire
│       ├── vocabulary.py        # construction des deux pools
│       ├── hints.py             # sélection d'indices
│       ├── dictionary.py        # accès et nettoyage Littré
│       └── orca.py              # humeurs, modes, banques de répliques
├── templates/
│   └── orquantix/index.html     # structure seule, aucun <script> inline
├── static/
│   ├── shell.css                # tokens partagés : couleurs, typo, tuiles
│   └── orquantix/
│       ├── style.css
│       ├── game.js
│       └── orca.js
└── tests/
    └── orquantix/
```

### Principes

**`app.py` ne connaît aucune règle d'Orquantix.** Il monte les blueprints, sert la route `/` et expose `/status`. En phase 2 il gagnera un registre de jeux et le menu ; Orquantix ne bougera pas.

**Un blueprint par jeu.** Les routes d'Orquantix passent sous le préfixe `/games/orquantix/` : `guess`, `give-up`, `hint`, `suggest`, `new-game`, `daily-info`. Le préfixe est gratuit avec Flask et supprime le risque de collision quand un futur quiz voudra son propre `/guess`.

**Navigation par pages.** Cliquer sur un jeu depuis le menu est une navigation réelle, pas un échange d'écrans en JavaScript. Ajouter un mini-jeu devient purement additif : une route, un template, un dossier statique, zéro ligne touchée dans les jeux existants. L'isolation du CSS est structurelle et non conventionnelle.

**L'état de partie vit côté serveur**, dans `OrquantixState`. Une conséquence directe : quitter vers le menu et revenir retrouve la partie en cours, tableau compris. C'est ce qui rend la navigation par pages viable.

**Chargement paresseux.** Les ressources d'un jeu sont chargées à la première entrée dans ce jeu, plus au démarrage de l'application. En phase 1 le comportement visible est identique, puisque `/` redirige vers Orquantix. En phase 2, un quiz géographique s'ouvrira instantanément sans attendre un modèle Word2Vec dont il n'a aucun usage.

**`AppState` éclate en deux.** Ce qui est global — phase de téléchargement, progression — reste dans la coquille. Ce qui est propre à Orquantix — modèle, pools, mot mystère, voisins — descend dans `OrquantixState`. Le champ `norm_to_vocab`, aujourd'hui calculé, stocké et jamais lu, retrouve un usage réel dans le filtrage des indices.

---

## Le moteur de jeu

### Les trois vocabulaires

| Ensemble | Règle | Taille mesurée |
|---|---|---|
| Mots mystères | Lexique383 `cgram = NOM`, `nombre ∈ {s, ""}`, sans espace ni tiret ni apostrophe, fréquence `freqlemlivres` dans [10, 400), présent dans le modèle | 2 788 |
| Indices | Mêmes contraintes de forme, `cgram ∈ {NOM sing., VER infinitif, ADJ masc. sing.}`, fréquence ≥ 5, présent dans le modèle | 6 916 |
| Propositions acceptées | Tout le vocabulaire du modèle — inchangé | 31 548 |

Le vocabulaire de proposition reste volontairement permissif : empêcher le joueur de taper un mot serait frustrant, et un mauvais mot se punit de lui-même par une température basse.

À noter, ce n'est pas une coïncidence : le nouveau pool d'indices (6 916) est exactement l'ancien pool de mots mystères. La refonte resserre la cible et recycle l'ancien ensemble comme réservoir d'indices.

Les noms propres sont exclus gratuitement des deux premiers pools : ils sont absents de Lexique383. C'est ce qui élimine `jupiter` et `charlie` des indices.

Le pool d'indices garde un plancher de fréquence plus bas (5) que celui des mots mystères (10) : un indice n'a pas à être un mot avec lequel on pourrait gagner, il doit orienter. C'est ce qui permet de conserver `confire` comme indice pour *confiture*, tout en éliminant `des` et `jupiter`.

Les bornes 5, 10 et 400 sont des paramètres nommés, ajustables après quelques parties.

### La température

Calibrée sur chaque mot mystère au moment de son tirage, à partir de trois ancres :

- `cos_max` — cosinus du voisin de rang 1
- `cos_1000` — cosinus du voisin de rang 1000
- `cos_plancher` — médiane des cosinus sur l'ensemble du vocabulaire

```
cos ≤ cos_plancher                    →  0.0
cos_plancher < cos < cos_1000         →  50 × (cos − cos_plancher) / (cos_1000 − cos_plancher)
cos ≥ cos_1000                        →  50 + 49 × (cos − cos_1000) / (cos_max − cos_1000)
mot exact                             →  100.0
```

**50° signifie exactement « je viens d'entrer dans le top 1000 », quel que soit le mot mystère.** C'est l'intérêt de la calibration par cible : le seuil du top 1000 varie fortement d'un mot à l'autre — 0.155 pour *confiture*, 0.196 pour *guerre* — donc une échelle fixe mentirait. Ici le repère est stable, et le joueur apprend à le lire.

Le voisin de rang 1 plafonne à 99° ; 100° est réservé à la victoire.

Vérification sur données réelles, cible **confiture** :

| Mot | cosinus | rang | température |
|---|---|---|---|
| compote | 0.680 | 2 | 96° |
| tartine | 0.452 | 78 | 76° |
| cuisine | 0.316 | 290 | 64° |
| bonjour | 0.072 | 5 968 | 14° |
| moteur | 0.038 | 16 324 | 0° |

Ancres mesurées pour *confiture* : plancher 0.0391, `cos_1000` 0.1551, `cos_max` 0.7113.

Le cas `bonjour` est celui qui justifie toute la refonte : aujourd'hui il affiche 0,00 %, exactement comme `moteur`. Demain il affiche 14°, et le joueur perçoit enfin une différence.

### Le rang

Affiché uniquement à l'intérieur du top 1000. Hors du top 1000, la cellule affiche un tiret. Son apparition est l'événement — un palier franchi, pas une donnée continue.

### Affichage du tableau

Cinq colonnes : `#`, `Mot`, `Température` (valeur + barre), `Rang`, `Orque`. Tri par température décroissante.

La colonne « Score brut » disparaît : la température dit la même chose en lisible. L'animation de remplissage de barre existante est conservée et animera la température.

### L'orque

Ses humeurs s'indexent désormais sur la température, et non plus sur le rang :

| Température | Humeur |
|---|---|
| 0 – 20 | malade 🤢 |
| 20 – 50 | vexé 😤 |
| 50 – 70 | intrigué 🤨 |
| 70 – 88 | surexcité 🤯 |
| 88 – 99 | solaire ☀️ |
| 100 | trouvé |

Les seuils sont alignés sur le repère des 50° : l'orque devient intrigué au moment précis où le joueur perce dans le top 1000.

Ses modes — eau calme, scotché, trash talk — leurs banques de répliques, le glisser-déposer des outils et le refus du poisson doré en mode trash talk sont **inchangés**. L'orque reste propre à Orquantix : les autres mini-jeux auront leur propre identité, ou aucune.

### Les indices

Tous les indices qui proposent un mot piochent dans le **pool d'indices**, jamais dans le vocabulaire brut du modèle. C'est la correction du bug central.

| Indice | Comportement |
|---|---|
| Première lettre | Inchangé |
| Nombre de lettres | Inchangé |
| Mot plus proche | Logique de progression inchangée, mais restreinte au pool d'indices |
| Poisson doré | **Nouveau** : lit la définition du mot mystère |

### Le poisson doré et le dictionnaire

Source : **Littré**, fichiers `XMLittre.dict.dz` et `XMLittre.idx` déjà présents dans le dossier de données. Domaine public. 123 221 entrées, couvrant **97,3 %** du pool de mots mystères.

Format de l'index : suite de `MOT\0` suivi de l'offset et de la longueur, chacun sur 4 octets big-endian. Le `.dict.dz` est un gzip standard.

**Nettoyage obligatoire avant affichage**, dans cet ordre :

1. **Retirer la transcription phonétique de tête.** Chaque entrée commence par une parenthèse du type `(kon-fi-tu-r')` — c'est le mot épelé. Sans ce retrait, le poisson doré ne donne pas un indice mais la réponse. C'est le point de défaillance le plus grave de la fonctionnalité.
2. **Extraire le premier sens** (jusqu'au marqueur `2°`, ou la première phrase à défaut). La longueur brute varie de 883 caractères pour *nausée* à 9 107 pour *genou*.
3. **Masquer le mot mystère et sa famille morphologique** dans le corps du texte — Littré écrit « Confitures de groseilles » dans l'entrée *confiture*.
4. **Retirer le balisage** `<i>`, `<small>`, `<b>`, `<big>` et les références d'auteurs en capitales.
5. **Tronquer** à une longueur lisible dans la bulle de l'orque.

**Repli.** Pour les 74 mots du pool absents de Littré — tous modernes : *avion, autobus, cinéma, autoroute, barman, bicyclette* — le poisson doré retombe sur son comportement actuel, le voisin fort. Le pool de mots mystères n'est **pas** restreint aux entrées de Littré : ces mots sont de bonnes cibles et méritent d'être conservés.

Littré date de 1870. Certaines définitions sont datées — *nausée* y est d'abord le mal de mer. C'est assumé.

### La difficulté

Étoiles conservées, quintiles de fréquence recalculés sur le nouveau pool. Les repères se resserrent — 1★ autour de 300/M, 5★ autour de 11/M — ce qui est précisément l'effet recherché : plus de *péripétie* ni de *madone* en 5★.

### Inchangé

Mode timer, bouton « I give up », mode dyslexique et sa suggestion rapidfuzz, les huit easter eggs, et le tirage déterministe sur `date + game_index` — « Rejouer » continue de donner un nouveau mot le même jour.

---

## Frontend

Les 909 lignes d'`index.html` se découpent :

- `templates/orquantix/index.html` — structure seule, aucun `<script>` inline
- `static/shell.css` — tokens partagés : couleurs, typographie, espacements, style des tuiles. C'est ce fichier qui fera que le menu et les mini-jeux se ressemblent, sans machinerie de design system.
- `static/orquantix/style.css` — habillage propre au jeu
- `static/orquantix/game.js` — propositions, tableau, température
- `static/orquantix/orca.js` — humeurs, modes, glisser-déposer, répliques

Le modèle de données d'une ligne de proposition porte désormais `temperature` et `rank` ; le tri se fait sur la température.

**Claude Design / `DesignSync` n'est pas retenu à ce stade.** L'outil sert à maintenir une bibliothèque de composants synchronisée avec claude.ai/design, ce qui paie quand de nombreux composants sont consommés à de nombreux endroits. Le menu n'étant pas encore designé, il n'y a rien à systématiser, et le problème actuel du projet est qu'il est trop emmêlé, pas trop éclaté. Un fichier de tokens partagé apporte l'essentiel du bénéfice. À reconsidérer si le nombre de mini-jeux croît réellement.

---

## Tests

Les 46 tests existants sont conservés ; ceux qui portent sur `get_progress_percent`, qui disparaît, sont **réécrits et non supprimés**.

Nouveaux tests :

- **Calibration de la température** — les trois ancres, la continuité aux points de raccord, le plafond à 99° pour le rang 1, les 100° réservés à la victoire
- **Composition des pools** — bornes de fréquence, filtres grammaticaux, tailles attendues
- **Étanchéité des indices** — aucun indice proposé ne sort du pool d'indices. C'est le test qui aurait attrapé `des` et `jupiter`
- **Extraction Littré** — en particulier que la transcription phonétique est retirée, cas où un bug rendrait le jeu injouable ; et le repli sur le voisin fort quand le mot est absent
- **Humeurs de l'orque** — correspondance température → humeur aux bornes

**Préalable bloquant :** il n'existe aucun environnement virtuel dans le projet, et ni `flask` ni `gensim` ne sont installés sur le Python du système. Les tests ne peuvent pas tourner aujourd'hui. Créer le venv et installer les dépendances est la première étape du plan, avant toute modification de code.

---

## Migration et hygiène

**Dossier de données.** `~/Library/Application Support/Orquantix/` → `Procrastinator/`, en réutilisant le mécanisme de renommage déjà présent dans `main.py` pour la migration Semantix → Orquantix. Sans cela, chaque utilisateur retélécharge environ 180 Mo.

**Téléchargement.** Le téléchargeur gère désormais trois fichiers au lieu de deux — Lexique383 (25 Mo), modèle Word2Vec (126 Mo), Littré (29 Mo). La répartition de la barre de progression est à revoir en conséquence.

**Résidus de nommage.** `SEMANTIX_TEMPLATES` et `SEMANTIX_STATIC` renommés, `Semantix.spec` supprimé, le `.spec` PyInstaller et l'icône passent à PROCRASTINATOR.

**`.gitignore`.** Le fichier n'existe pas. `dist/` (4 761 fichiers, 365 Mo), `build/` (16 fichiers, 59 Mo) et `__pycache__/` sont des sorties de build committées. Vérification faite : les 20 fichiers d'assets nécessaires au jeu — `orca_assets`, `easter_assets`, `proximity_assets` — ainsi que les templates et `requirements.txt` sont tous suivis par git. Ignorer les répertoires de build ne retire donc rien à la capacité de cloner le dépôt et de jouer. On ajoute `.gitignore` couvrant `dist/`, `build/`, `__pycache__/`, `.venv*/` et `.superpowers/`.

**Réserve :** les 130 Mo sont déjà présents dans l'historique git. Les en extraire suppose une réécriture d'historique et un force-push vers GitHub. **Hors périmètre de cette spec** — à décider séparément et explicitement.

**README.** Il ne documente aujourd'hui aucune procédure de lancement, alors que l'objectif déclaré est que n'importe qui puisse cloner le dépôt et jouer localement. Ajouter une section d'installation et de lancement.

---

## Hors périmètre

- **Le menu de PROCRASTINATOR.** La phase 1 livre la coquille et la route `/`, qui redirige vers Orquantix. L'écran de choix sera designé en phase 2.
- **Les autres mini-jeux** (quiz géographiques et suivants).
- **La réécriture de l'historique git.**

---

## Annexe — données mesurées

Mesures effectuées le 2026-08-16 sur les fichiers réels du dossier de données.

**Modèle** `frWiki_no_phrase_no_postag_1000_skip_cut200.bin` : 31 548 mots, 1000 dimensions.

**Distribution des cosinus** (cible → reste du vocabulaire) :

| Cible | médiane | p90 | p99 | seuil top 1000 | max | % sous 0.10 |
|---|---|---|---|---|---|---|
| confiture | 0.039 | 0.094 | 0.302 | 0.155 | 0.711 | 91,4 % |
| genou | 0.037 | 0.096 | 0.207 | 0.144 | 0.682 | 91,0 % |
| guerre | 0.047 | 0.130 | 0.254 | 0.196 | 0.542 | 82,4 % |

C'est ce qui interdit d'utiliser le cosinus brut comme température : 91 % des mots vivraient sous 10°.

**Pool actuel** (avant refonte) : 6 916 mots — 4 076 NOM, 1 701 VER, 1 139 ADJ.

**Pool cible** : 2 788 noms communs, bande 10–400/M. Échantillon : *peine, matin, table, guerre, leçon, tristesse, corde, révolte, flèche, cigare, détour, berger, contrat, lucarne, nausée, passeport, gravure*.

**Courbe de progression actuelle**, pour mémoire :

| rang | barre | rang | barre |
|---|---|---|---|
| 1 | 99,99 % | 700 | 1,69 % |
| 100 | 70,16 % | 850 | 0,16 % |
| 300 | 29,88 % | 900 | 0,04 % |
| 500 | 9,54 % | > 1000 | 0,00 % |

**Couverture Littré** : 2 714 / 2 788 mots du pool cible, soit 97,3 %.
