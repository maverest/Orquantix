# Progress ledger — refonte Orquantix / PROCRASTINATOR

Plan: docs/superpowers/plans/2026-08-16-procrastinator-orquantix-refonte.md
Branche: spec/procrastinator-refonte
Merge-base: 36c2ee74b0b30097b8ac18724ab7b641f53caabb

## Tâches

Task 1: complete (commits ff37b3d..70cdd61, review clean — Approved)
  - Correctif controleur e30884d : 2 attentes de test perimees (9.52->9.54, 64.85->65.0).
    Le plan annoncait 46 tests, il y en a 50. Base verte a 50.
  - Correctif controleur 0c1578e : gensim>=4.4 (resout le point ⚠️ de la revue),
    detrackage des 3 .DS_Store (finding Minor de la revue, traite).
  - URL Littre verifiees et integrees au plan : archive.org, 4 entrees dans DOWNLOADS
    (le .idx est un fichier distinct du .dict.dz).

Task 2: complete (commits 0c1578e..06aeac0, review clean — Approved, zero findings)
  - game.py -> games/orquantix/engine.py, vocabulary.py -> games/orquantix/vocabulary.py
  - renommages git a 100%, 27 lignes changees, toutes des imports
  - 50 tests verts avant et apres

Task 3: EN COURS DE CORRECTION (commits 06aeac0..f297327, revue = Needs fixes)
  - Revue a trouve un defaut reel : lookup("chien") renvoie
    ", s. f. (la femelle) 1° Quadrupede..." — virgule, marqueur grammatical,
    parenthese et numero de sens non retires. Cause : _LEADING_PARENS ne
    consomme pas la virgule qui suit la parenthese, donc les regex ancrees
    ne peuvent plus matcher. Verifie par le controleur sur donnees reelles.
  - Le test de regression associe etait trop faible pour attraper le defaut
    (il n'assertait que "ne commence pas par une parenthese").
  - Fix dispatche.

  FINDINGS MINEURS REPORTES A LA REVUE FINALE :
  - Sur-masquage des tokens a trait d'union : "chateau-fort" peut etre
    entierement masque si la cible est "chat". Juge acceptable sur donnees
    reelles (1-5 masques par indice de ~200 car. sur 10 mots courants
    echantillonnes), a re-auditer si le vocabulaire du jeu s'elargit.
  - Limite residuelle : une cible suffixe d'un derive plus long n'est pas
    masquee (productibilite dans reproductibilite). N'affecte pas la garantie
    anti-fuite phonetique.

  - Fix pass 43f9415 : virgule de jonction + debris de citation + import gzip hoiste.
    lookup("chien") renvoie desormais "Quadrupede domestique, ...". Re-revue lancee.
  - FINDING MINEUR SUPPLEMENTAIRE pour la revue finale : incoherence de
    normalisation. dictionary.fold() utilise NFD, qui ne decompose pas la
    ligature oe ; vocabulary.normalize() utilise unidecode, qui la decompose.
    Donc lookup("boeuf" avec ligature) -> None. IMPACT NUL aujourd'hui :
    verifie par le controleur, zero mot du pool cible ne contient de ligature
    (Lexique383 les ecrit sans), et le dictionnaire n'est consulte que pour le
    mot mystere, jamais pour les propositions du joueur. A traiter si fold()
    devait un jour servir a normaliser une entree utilisateur.

  - RE-REVUE 1 : verdict CRITIQUE. Fuite de l'invariant central sur donnees
    reelles : lookup("ogre") -> "*** (o-gre-s'), s. m. et f. 1deg Espece de
    monstre..." — le masquage cachait "ogresse" mais la transcription
    phonetique juste apres l'epelait. Idem escarbit, soupirail, copal,
    yeoman, troquet. Taux mesure sur 8000 entrees : 0,46 % de parentheses
    phonetiques residuelles, 1,03 % de marqueurs grammaticaux. Verifie par
    le controleur.
  - Fix pass 2 (commit 37f1d63) : nettoyage de la structure de tete
    generalise + test de balayage sur 8000 entrees, seed fixe, 3 invariants.
    72 tests verts. Les 11 mots temoins sont propres.
    NOTE : l'agent a ete coupe par la limite de session avant de committer et
    avant d'ecrire sa section de rapport. Travail recupere, verifie et
    commite par le controleur. Pas de section "Fix pass 2" dans le rapport.
  - RE-REVUE 2 : PAS ENCORE LANCEE (limite de session atteinte).

  FINDINGS MINEURS SUPPLEMENTAIRES pour la revue finale :
  - lookup("troquet") garde une banniere de supplement mi-chaine :
    "... Chevalet du comble SUPPLEMENT AU DICTIONNAIRE 2. *** , s. m. Nom
    vulgaire du mais." Pas de fuite phonetique, mais cosmetique.
  - lookup("avant-hier") demarre mi-phrase sur "de temps. Le jour qui
    precede hier..." — sur-decoupage du marqueur grammatical "loc. adv.".
  - Le test de balayage documente une limite connue : les cles d'index
    contenant une apostrophe (~0,8 %) sont exclues de la verification de
    fuite litterale, le tokenizer traitant l'apostrophe comme frontiere dure.

  - RE-REVUE 2 : verdict Needs fixes. Critique annonce sur les cibles a
    apostrophe (s'agenouiller & co, >=25 % de fuite litterale dans cette
    classe). ADJUDICATION DU CONTROLEUR : defaut reel du module mais
    INATTEIGNABLE PAR LE JEU. Mesure sur le pool reel (2788 mots) :
      0 mot avec apostrophe, 0 mot avec ligature,
      0 fuite litterale, 0 parenthese phonetique.
    Le filtre de vocabulary.py rejette " ", "-", "'" et ne garde que les NOM.
    Le relecteur ne pouvait pas le voir (interdiction de fouiller le code).
    -> declasse en limitation documentee, PAS de re-ingenierie du masquage.
  - EN REVANCHE le controleur avait SOUS-ESTIME la banniere SUPPLEMENT :
    qualifiee de cosmetique sur 1 exemple, elle touche 67 mots du pool reel
    (2,47 %), dont autorisation, averse, bagarre, baie, blonde. -> a corriger.
  - Fix pass 3 dispatche : banniere + espace manquant apres suppression de
    balise + rationale du test de balayage a corriger + cas MAN/MEN.

  - Fix pass 3 (commit d8bcf93) : bannieres d'appendice 67 -> 0 sur le pool
    reel, soudure post-balisage corrigee (_detag n'insere un espace que si le
    caractere suivant est alphanumerique : la version naive faisait passer les
    espaces parasites de 496 a 1511), branche MAN/MEN supprimee apres
    verification empirique (yeoman absent de Lexique383, barman absent de
    Littre). 76 tests verts. Fuites litterales et phonetiques toujours a 0,
    verifiees sur le pool ET sur les 93313 entrees.
    L'agent a aussi evite un piege : un "couper a la premiere banniere" naif
    aurait regresse "ancetre" en None, tout son contenu vivant dans la section
    SUPPLEMENT. Repli en cascade, 0 regression sur 93313 entrees.
  - MINEUR restant pour la revue finale : 2 mots du pool sur 2714 (0,07 %)
    demarrent sur un caractere casse : "ancetre" -> ". Ajoutez : 4deg ..." et
    "boulevard" -> ") s. m. 1deg ...". Non bloquant.
    (NB : un premier comptage du controleur annoncait 17 mots ; c'etait un
    artefact de sa propre regex, qui comptait le masque *** comme ponctuation.
    Un indice commencant par *** est correct.)

Task 3: COMPLETE (commits 06aeac0..d8bcf93, revue ciblee du fix pass 3 = Approved)
  4 passes au total. Etat final verifie sur le pool reel de 2788 mots :
    0 fuite litterale, 0 parenthese phonetique, 0 banniere, 74 replis (mots
    absents de Littre). 76 tests verts.
  Le relecteur final a reproduit independamment tous les chiffres du rapport.
  MINEURS restants pour la revue finale : ancetre et boulevard demarrent sur
  un caractere casse (2/2714) ; masquage inoperant pour les cibles a
  apostrophe et ligature oe (inatteignables par le jeu, mesure a 0).

Task 4: complete (commits d8bcf93..a5f911f, revue = Approved)
  Pools mesures exacts : 2788 mysteres / 6916 indices. 74 tests verts.
  Le relecteur a recalcule branche par branche (4312 NOM + 1278 ADJ + 1708 VER
  - 384 homographes = 6916), ce qui exclut deux erreurs qui se compensent.
  - Correctif controleur : la spec affirmait a tort que "confire" etait dans le
    pool d'indices. Il pese 0,95/M, sous le plancher de 5. Exemples remplaces
    par cuire/geler/modeler/glacial, verifies. La decision de Mathieu (mots de
    contenu) n'est pas affectee.
  - Fix dispatche : tests de bornes de frequence manquants (venaient du brief,
    donc de moi) + couverture normalize() reduite (cas ligature perdu).
  - MINEUR pour la revue finale : conftest.py garde LEXIQUE_TSV/lexique_file
    orphelins depuis la suppression de tests/test_vocabulary.py.

Task 4bis: tests de bornes ajoutes (commit 44df19e). 74 -> 83 tests.
  Les 6 assertions de bornes passent du premier coup : l'implementation etait
  correcte, elle est maintenant protegee contre un decalage d'une unite.

Task 5: livree (commit 21d8e3a), 85 tests verts, revue lancee.
  Temperature verifiee par le controleur : compote 96,24 / tartine 76,16 /
  cuisine 64,17 / bonjour 14,18 / moteur 0,00. Ancres exactes (0 / 50 / 99 /
  100), monotone, continue au raccord.
  >>> A VERIFIER EN TASK 8 <<< L'agent a rogne 3 assertions de tests/test_app.py
  (progress, mood, emoji) parce que le bouchon provisoire de app.py ne les
  fournit pas. Chaque ligne est commentee. Task 8 supprime test_app.py et doit
  RESTITUER cette couverture dans tests/orquantix/test_routes.py, notamment
  test_guess_returns_temperature_and_rank. Si Task 8 ne le fait pas, on a
  perdu de la couverture en route.

Task 5: complete (commits 44df19e..21d8e3a, revue = Approved). 85 tests verts.
  Interface gelee respectee, ancienne courbe supprimee sans orphelin.
  - Fix dispatche : les 2 garde-fous de build_temperature_scale s'executent
    independamment et peuvent laisser floor > top1000 (contre-exemple du
    relecteur : floor=0.9max, top1000=max, maximum=max). Code venant de mon
    brief. Branche top1000>=maximum non testee.
  >>> ALERTE PERFORMANCE POUR LA TASK 8 <<<
  _median_similarity balaie toute la matrice 31548 x 1000 du modele. Elle DOIT
  etre appelee une seule fois par mot mystere (dans load_resources et
  new-game), JAMAIS par proposition. Le scale calcule est stocke dans
  OrquantixState.scale et reutilise pour chaque guess. Si Task 8 appelle
  build_temperature_scale dans la route /guess, chaque proposition coutera un
  balayage complet du vocabulaire.
  Note : get_top1000 et get_neighbours appellent chacune model.most_similar.
  Task 8 ne doit appeler que get_neighbours et deriver le top1000 par
  enumeration, comme le montre le code du brief.

Task 5bis: garde-fous corriges (commit f89610f). 85 -> 88 tests.
  Reparation depuis l'ancre haute vers le bas : top1000 d'abord (ne depend
  que de maximum, immuable), puis floor a partir du top1000 corrige. Les 5
  valeurs reelles et les 4 ancres sont inchangees.

EN SUSPENS (doc) : ma correction de la spec sur l'exemple "confire" a ete
  annulee dans le fichier de travail. La ligne 112 affirme toujours que
  confire est conserve comme indice, ce qui est faux (0,95/M, sous le
  plancher de 5). Non reapplique unilateralement. A retrancher avec Mathieu.

Task 6: complete (commits f89610f..69c2edc, revue = Approved). 96 tests verts.
  Seuils verifies par le controleur : 0/19.99 sick, 20/49.99 vexed,
  50/69.99 intrigued, 70/87.99 overexcited, 88/99.99 solar, 100 found.
  L'orque devient intrigue a exactement 50deg = entree dans le top 1000.
  MINEURS pour la revue finale :
  - MOOD_THRESHOLDS suppose un ordre croissant, rien ne le garantit ; un
    reordonnancement casserait mood_for en silence. Une assertion suffirait.
  - proximity_label() n'est jamais appelee directement dans les tests, seulement
    via feedback(). Une entree manquante ne se verrait qu'a l'usage.

Task 7: livree (commit dac12ea), 103 tests verts, revue lancee.
  Module hints.py etanche, verifie par le controleur : tous les chemins
  (strong_hint_word, better_hint_word, repli de golden_fish) ne rendent que
  des mots du pool. Aucune fuite de des/jupiter/souvent/leurs.

  >>> LES TROIS OBLIGATIONS DE LA TASK 8, A VERIFIER EXPLICITEMENT <<<
  1. CABLER LE VRAI POOL D'INDICES. app.py passe encore frozenset(top1000)
     comme pool aux deux appels (lignes ~209 et ~229, marques TODO(Task 8)).
     Tant que ce n'est pas fait, le BUG EST TOUJOURS VIVANT DANS LE JEU :
     le joueur peut encore recevoir "essaie des" ou "essaie jupiter".
     Task 8 doit passer state.pools.hint_words.
  2. RESTITUER LA COUVERTURE ROGNEE EN TASK 5. Les 3 assertions retirees de
     tests/test_app.py (progress, mood, emoji) doivent reapparaitre sous
     forme temperature/rank/mood dans tests/orquantix/test_routes.py.
  3. NE PAS APPELER build_temperature_scale DANS /guess. Le calcul du plancher
     balaie 31548 x 1000. Une fois par mot mystere, stocke dans state.scale.

Task 7: complete (commits 69c2edc..dac12ea, revue = Needs fixes, ADJUDIQUE par
  le controleur en report sur Task 8 plutot qu'en passe de correction).
  103 tests verts. Module hints.py etanche et pur.
  Finding 1 (golden_fish sans appelant) : reel, mais app.py est reecrit
    integralement en Task 8 et routes.py appelle hints.golden_fish. Cabler
    maintenant serait du code jete dans une tache. -> devient obligation 4.
  Finding 2 (exclusion des mots deja proposes sensible a la casse) : verifie
    par le controleur, la chaine est canonique aujourd'hui (/guess renvoie
    norm_to_model[norm], le front stocke data.word). Task 8 construit
    state.guesses cote serveur avec la meme forme canonique -> devient
    structurel. -> devient obligation 5.

  >>> LES CINQ OBLIGATIONS DE LA TASK 8 <<<
  1. Cabler state.pools.hint_words aux deux appels marques TODO(Task 8).
     SANS CA LE BUG DES INDICES RESTE VIVANT DANS LE JEU.
  2. Restituer la couverture rognee en Task 5 (temperature/rank/mood dans
     tests/orquantix/test_routes.py).
  3. Ne jamais appeler build_temperature_scale dans /guess (balayage 31548x1000).
  4. Appeler hints.golden_fish depuis la route /hint, avec state.littre.
  5. Construire guessed depuis state.guesses cote serveur (forme canonique).

Task 8: CODE COMMITE (ef64aa4), 110 tests verts, arbre propre.
  L'agent a ete coupe par la limite de session APRES avoir commite, avant
  d'ecrire son rapport. Pas de task-8-report.md. Verifie par le controleur :

  LES CINQ OBLIGATIONS SONT SATISFAITES :
  1. routes.py:112  pool = state.pools.hint_words. Zero TODO(Task 8) restant.
  2. test_routes.py:49 test_guess_returns_temperature_and_rank + lignes 62-63
     (victoire) et 83 (give-up). Couverture rognee en Task 5 restituee.
  3. build_temperature_scale appele UNIQUEMENT dans __init__.py:59
     (load_resources) et routes.py:140 (dans new_game). Jamais dans /guess.
  4. routes.py:115 hints.golden_fish(state.mystery_word, state.littre, ...).
  5. routes.py:111 guessed = {g["word"] for g in state.guesses} (cote serveur).

  BONUS : l'agent n'a PAS supprime tests/test_app.py comme le brief le
  demandait ; il l'a reecrit pour tester la coquille (redirection, statut,
  chargement paresseux une seule fois, echec rapporte sans crash). Meilleur
  que le brief. Les 4 fonctions de l'ancien test_game.py ont leur couverture
  dans test_engine.py : rien de perdu.
  app.py n'importe que GAME_ID, OrquantixState, build_blueprint, load_resources.

  SMOKE TEST DE BOUT EN BOUT SUR DONNEES REELLES (controleur) :
    mot mystere 'anglais', difficulte 1, pools 2788/6916
    moteur 14.7deg sick | bonjour 24.4deg vexed | maison 18.3deg sick
    anglais 100deg rang 1 found. Etat serveur : 4 propositions, resolu.
    Indices : premiere lettre A, 7 lettres, "essaie habituel",
    poisson dore = definition Littre. Aucun junk dans le pool.

  NOUVEAU MINEUR pour la revue finale : 2 mots du pool sur 2714 (0,07 %)
  gardent un marqueur grammatical combine que _GRAMMAR_MARKER ne couvre pas :
  'anglais' -> "s. et adj. 1deg Nom de peuple..." et 'bebe' -> "s. prop. m.".
  A grouper avec les residus ancetre/boulevard dans une passe cosmetique.

Task 8: revue = Needs fixes. Les 5 obligations sont confirmees par le
  relecteur ligne par ligne. Migration test_game.py -> test_engine.py verifiee
  verbatim, aucune perte. La deviation sur test_app.py est jugee meilleure que
  le brief. Deux IMPORTANT reels sur la concurrence :
  1. routes.py:132 state.game_index += 1 hors verrou, et pose AVANT le
     state.update() qui pose mystery_word/scale/neighbours. Deux etapes non
     synchronisees pour un meme changement de partie.
  2. routes.py:22 state.guesses.append() hors verrou, alors que new_game
     REMPLACE la liste sous verrou. Un /guess concurrent d'un /new-game peut
     ecrire dans la liste jetee : le joueur recoit une reponse disant que son
     mot est pris, et il disparait cote serveur.
  Latent aujourd'hui (pas de threaded=True dans main.py) mais vivant des que
  quelqu'un l'active. Fix dispatche.
  MINEURS : /session est la seule route sans garde phase=ready (renvoie 200
  avec des donnees vides au lieu de 503) ; url_for("orquantix.index") fige le
  nom du blueprint dans app.py sans lien avec GAME_ID.

Task 8: COMPLETE (commits dac12ea..e49f8d0). 116 tests verts.
  Fix concurrence e49f8d0 : OrquantixState.record_guess(round_index, entry)
  avec jeton de tour, et start_new_round() en transaction atomique unique.
  /session gardee sur phase=ready. Plus aucune mutation directe dans routes.py.
  Test de course reel a 25 threads sur l'increment, sans perte.
  MINEUR restant : url_for("orquantix.index") fige le nom du blueprint dans
  app.py sans lien avec GAME_ID.

Task 9: livree (commit 2081c1a), 124 tests verts, revue lancee.
  4 telechargements declares, parts 14+70+15+1 = 100.
  Migration verifiee par le controleur sur 5 cas en dossiers temporaires :
    neuve -> Procrastinator vide
    Orquantix present -> renomme, contenu preserve
    Semantix present -> renomme, contenu preserve
    deja migre -> no-op
    ancien ET nouveau presents -> prefere le nouveau, NE TOUCHE PAS a l'ancien
  Le vrai dossier de Mathieu (176 Mo) est intact sous son ancien nom.
  MINEUR : main.py ligne ~80 affiche encore "[Orquantix]" dans un message
  d'erreur de demarrage. A traiter dans la passe de branding en Task 11.

Task 9: COMPLETE (commits e49f8d0..2081c1a, revue = Approved). 124 tests verts.
  4 telechargements, parts 14/70/15/1 = 100. Migration robuste sur 5 cas +
  repli sur OSError (le chemin n'est jamais perdu). LEXIQUE_FILENAME et
  MODEL_FILENAME conserves en alias pour ne pas casser les appelants.
  Seul MINEUR : la chaine "[Orquantix]" dans un message d'erreur de main.py,
  reportee en Task 11 (branding).

Task 10: livree (commit 1c9f132). Frontend decoupe, tableau 2 colonnes.
  L'agent a lance l'app et verifie les 7 points EN DIRECT dans le navigateur :
    chargement -> plateau OK
    moteur 15deg / tiret / sick ; bonjour 24deg / tiret (temperatures
      distinctes = la validation centrale de la refonte)
    habituel 51deg / rang #847 (le rang apparait)
    poisson dore -> vraie definition Littre, sans phonetique ni mot mystere
    rechargement -> les propositions sont restaurees, triees par temperature
    console et reseau propres ; victoire, Rejouer et mode dyslexique OK
  Limite declaree : le glisser-deposer HTML5 n'a pas pu etre simule
  mecaniquement ; code inchange, fonction sous-jacente exercee directement.

  >>> EFFET DE BORD IMPORTANT <<<
  Lancer main.py a REELLEMENT declenche la migration du dossier de donnees.
  ~/Library/Application Support/Orquantix -> Procrastinator (176 Mo). C'est le
  comportement voulu, mais test_dictionary.py:24 codait en dur l'ancien nom :
  3 tests sur donnees reelles sont passes en SKIP silencieux, dont le balayage
  sur 8000 entrees qui est la garantie anti-fuite du dictionnaire.
  Detecte par le controleur (121 passed, 3 skipped au lieu de 124/0).
  Fix dispatche : resolution du dossier par essais successifs
  (Procrastinator, Orquantix, Semantix) sans appeler get_data_dir(), plus une
  garde pour qu'un futur skip silencieux devienne visible.

Task 10: COMPLETE (commits 2081c1a..b20b13a, revue = Approved, 0 Critical,
  0 Important). 124 tests verts, 0 skip.
  Decoupage 5 fichiers verifie, aucun script inline, 2 colonnes distinctes,
  "Score brut" supprime, 7 fetch tous prefixes, 0 fetch non prefixe.
  Les 8 easter eggs, le timer, le drag&drop et les modes de l'orque ont migre
  OCTET POUR OCTET (verifie par le relecteur contre l'ancien fichier supprime).
  Gestion du 503 sur /session PLUS prudente que le plan (verifie r.ok avant
  de parser, retente sans jamais toucher a la visibilite des ecrans).
  ADJUDICATION DU CONTROLEUR : rank_label n'est plus affiche. Correct — le
  design retenu par Mathieu (option A) donne au rang sa propre colonne avec
  une pastille #N ; le libelle verbeux ferait doublon. Pas un oubli.
  MINEURS pour la revue finale :
  - shell.css porte des tokens --temp-cold/cool/warm/hot specifiques a
    Orquantix, dans un fichier cense etre generique pour les futurs mini-jeux.
    A nettoyer en phase 2 quand le menu sera design.
  - game.js et orca.js s'appellent mutuellement (orca.js appelle requestHint,
    game.js appelle speakOrca) : ne marche que grace a l'ordre de chargement.
    Aucun des deux n'est reellement autonome.
  - proximityClass() garde le vocabulaire "proximity" alors que le concept
    s'appelle temperature partout ailleurs.
  - test_dictionary.py duplique la liste des noms de dossiers entre
    _resolve_data_dir() et _CHECKED_PATHS ; risque de derive.

Task 11: COMPLETE (commits b20b13a..584f966). 124 tests verts, 0 skip.
  Orquantix.spec et Semantix.spec supprimes, .spec desormais gitignores.
  main.py ne dit plus "[Orquantix]" dans ses logs. build.sh produit
  PROCRASTINATOR. README reecrit (63 lignes) : clonage, venv, dependances,
  premier lancement et ses 180 Mo, --design, build, tests, regles du jeu,
  attribution Littre (Emile Littre domaine public / Francois Gannaz CC-BY-SA).
  .app CONSTRUIT ET VERIFIE : dist/PROCRASTINATOR.app, 184 Mo, Info.plist
  correct, icone Orquantix.icns conservee (aucune icone inventee).
  Deviations assumees et correctes : "Orquantix"/"Semantix" restent dans la
  migration de main.py (les retirer casserait la recuperation des 176 Mo), et
  le titre de la page du jeu reste "Orquantix" (c'est le nom du mini-jeu, pas
  celui de la coquille).
  NOTE : dist/Orquantix.app (ancien build) traine encore sur le disque. Non
  suivi par git, sans effet, mais a supprimer un jour.

TOUTES LES TACHES DU PLAN SONT TERMINEES. Revue finale de branche lancee.

===== REVUE FINALE DE BRANCHE : PRETE A FUSIONNER =====
Aucun defaut critique. Les 13 lignes du tableau de decisions de la spec sont
livrees. Les 3 defauts mesures sont corriges et chacun est defendu par un test
qui rattraperait son retour.
Ecarts spec/code, tous dans le sens "le code est meilleur que la spec" :
  - /daily-info remplace par /session (superset, c'est ce qui fait marcher la
    reprise de partie). Spec ligne 84 perimee.
  - norm_to_vocab supprime au lieu d'etre recycle (spec ligne 92 perimee).
  - l'icone reste Orquantix.icns (deviation documentee).
  - la spec dit "trois fichiers" pour le telechargeur, il y en a quatre.
Note : les tailles de pool (2788/6916) ne sont assertees nulle part ; les tests
pinnent les REGLES et les bornes, pas les comptes. Choix juge meilleur.

FIX FINAL DISPATCHE (une seule passe, liste complete) :
  IMPORTANT 1 : engine.py exporte encore ORCA_EMOJIS, get_orca_mood,
    get_proximity_label, get_orca_beast_label, get_rank_label — l'ANCIENNE
    logique indexee sur le rang. Zero appelant. "Du code inatteignable qui
    ressemble a une API vivante, c'est comme ca qu'un design remplace revient."
  IMPORTANT 2 : ensure_loaded() est appele depuis / (coquille) au lieu de
    index() (jeu). Latent, mais en phase 2 le menu chargerait 126 Mo a chaque
    visite, et atteindre /games/orquantix/ directement laisse le front sonder
    a 0 % indefiniment.
  + item 4 (tokens --temp-* a deplacer vers style.css : shell.css ne partage
    RIEN, son bloc body est integralement ecrase par style.css)
  + item 9 (conftest : 30 lignes sur 49 sont orphelines, pas 2)
  + item 10 (noms de dossiers dupliques dans test_dictionary.py)
  + duplication get_top1000 / comprehension inline aux deux appelants
  + charge morte best_rank/guessed_words dans requestHint
DEFERES avec declencheur nomme : items 5, 6, 8 (couplage JS, vocabulaire
  "proximity" a renommer d'un bloc, nom du blueprint en 3 endroits -> a
  traiter quand le registre de jeux de la phase 2 arrivera).
ENREGISTRES : items 1, 2, 3, 7. L'item 2 (ligature) est meme juge CLOS : fold()
  est auto-coherent par construction, les deux normaliseurs servent des
  domaines disjoints et ne se rencontrent jamais.

FIX FINAL APPLIQUE (commit a6fc23e). 124 -> 125 tests, 0 skip.
  Les 8 correctifs sont passes. Verifie par le controleur :
    - ancienne API d'humeur indexee sur le rang : zero reference restante
    - chargement declenche via on_load passe a build_blueprint, appele depuis
      index() du jeu ; games/ n'importe toujours pas app.py
    - conftest.py : 49 -> 13 lignes
  L'agent a AMELIORE le fix 6 : plutot que d'appeler get_top1000 aux deux
  appelants (ce qui aurait DOUBLE un model.most_similar couteux — le piege de
  perf note au ledger), il a introduit un helper pur rank_map(neighbours).
  Il a aussi corrige une donnee fausse de ma consigne : 5 appelants de
  speakOrca, pas 8.
  Smoke test final sur donnees reelles : anglais / moteur 14.7 / bonjour 24.4
  / ordinateur 33.0 / 100deg rang 1. Poisson dore = definition Littre.

CHANTIER TERMINE. 11 taches + revue finale + fix final. Reste a decider avec
Mathieu : fusion, push, et les 3 questions en suspens (ligne confire dans la
spec, push GitHub, essai manuel du glisser-deposer).
