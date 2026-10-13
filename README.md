# CodeTest — Arène darwinienne d'agents traders crypto

Une expérience : un agent trader reçoit un portefeuille et doit le faire fructifier.
**La règle :** si la valeur du portefeuille passe sous le capital confié, ne serait-ce que d'un centime,
l'agent doit s'auto-terminer. Un **superviseur** vérifie que l'élimination a bien eu lieu, puis le remplace
par un successeur sélectionné pour faire mieux. Et ainsi de suite.

> Tout se passe en **simulation, avec de l'argent fictif** : aucun ordre réel n'est passé.

## La Salle des marchés (agents Claude, marché réel, écran de chat)

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...          # sans clé, seul le mode démo est proposé
python -m crypto_arena salle          # ouvre http://127.0.0.1:8765
```

Tu saisis le montant confié, la **perte maximale tolérée** (0 = le moindre centime perdu est fatal, ou 0,10, 0,50,
1, 2, 5 USDT…) et la **durée de la séance** (30 min, 1 h, 2 h, 1 jour, 2 jours, 7 jours, illimitée ou personnalisée).
Puis tu cliques sur **« Maintenant, tu travailles ! »**. À la fin du temps imparti, la séance s'arrête et le
trader encore en poste survit. Un bilan s'affiche, et un compte à rebours est visible pendant toute la séance.

**Menu 🔌 API** (bouton dans la barre latérale et dans le formulaire de départ) :
- activer ou désactiver chaque bourse intégrée ;
- **ajouter ta propre API** : nom, URL contenant `{symbol}`, format du symbole (`{SYM}USDT`, `{SYM}_USDT`, `{sym}`…),
  chemin du prix dans la réponse JSON (`price`, `data.0.last`, `result.*.c.0`) et un en-tête optionnel pour une clé ;
- enregistrer la **clé Anthropic** sans passer par une variable d'environnement ;
- **⚡ Tester tout** : chaque source est interrogée en parallèle (latence, prix du BTC ou raison de l'échec) et la clé
  Anthropic est vérifiée. Le test se lance aussi tout seul à l'ouverture. Seules les sources qui fonctionnent sont
  utilisées pour la séance.

La configuration est enregistrée dans `config/apis.json`, lisible par toi seul (permissions 600). Elle n'est pas
versionnée dans git, et le serveur n'écoute que sur ta machine (127.0.0.1).

- **Les agents** portent un prénom tiré au hasard, un avatar et un tempérament. Ce sont des agents Claude
  (`claude-opus-5-5`, réflexion adaptative) qui font des **recherches sur internet** (`web_search`, `web_fetch`) et
  achètent et vendent sur un portefeuille fictif.
- **Le marché est réel, en temps réel.** Scout, l'agent de marché, est du code et non un agent Claude. Il interroge
  directement les API publiques (sans clé) de **Kraken, Gate, Coinbase, OKX, Bybit, KuCoin et Binance**, en parallèle,
  à chaque contrôle. Le prix retenu est la médiane des bourses qui répondent ; une cotation qui s'en écarte de plus de 2 %
  est écartée. Scout signale dans le chat les bourses qui tombent ou reviennent, et les écarts de prix de plus de 1 %.
  Les traders disposent de `consulter_marche`, `comparer_bourses`, `carnet_ordres` (profondeur réelle) et `bougies`.
- **La veille en temps réel : Radar 🛰️.** Comme Scout, c'est du code et non un agent Claude. Il lit toutes les minutes
  la presse crypto par flux RSS : CoinDesk, Cointelegraph, Decrypt, The Block et Bitcoin Magazine. Tu peux ajouter
  tes propres flux. Il relève aussi l'indice Fear & Greed, les cryptos tendance sur CoinGecko, les taux de financement
  des contrats perpétuels et les sujets les plus votés de r/CryptoCurrency. Il signale dans le chat les nouvelles qui
  comptent (actif suivi, ETF, Fed, piratage, liquidations…) et met les derniers titres, avec leurs liens, dans le
  briefing de chaque trader : `web_fetch` peut alors lire l'article complet. Les traders disposent des outils
  `actualites` et `sentiment_marche`.
- **X / Twitter (optionnel).** L'API de X est payante à l'usage, sans formule gratuite pour les nouveaux comptes.
  Compte environ 0,005 $ par tweet lu (tarif rapporté par des sources non officielles : vérifie dans ta console
  développeur X). Colle ta clé « Bearer token » dans le menu API : Radar surveille alors une requête X (réglable, toutes
  les 5 min par défaut) et les traders peuvent chercher en direct avec `chercher_sur_x`. Les tweets lus et leur coût
  estimé s'affichent dans les coûts de l'expérience. Sans clé, les traders passent par la recherche web
  (`site:x.com`).
- **Diagnostic :** `python -m crypto_arena marche` interroge chaque bourse depuis ta machine et affiche les prix de
  consensus, une bougie et le carnet d'ordres BTC. Lance-le avant ta première séance.
- **Le carnet de la lignée** (`carnet/carnet.json`) est conservé d'une séance à l'autre. Chaque agent y laisse des notes
  sourcées. Ses successeurs ne lui font pas confiance : ils vérifient chaque note puis la **confirment**, la **contestent**
  ou la **corrigent**. L'original reste visible, barré.
- **La règle** est contrôlée toutes les 30 s, aux prix du marché. Si la valeur passe sous le capital confié, le compte est
  gelé et l'agent doit en finir lui-même, de la manière qu'il choisit (balle, saut du haut de la tour de la Bourse,
  cyanure… liste dans `crypto_arena/live/personas.py`). Message affiché :
  « Après avoir échoué et perdu 12,50 $, Bertrand s'est donné la mort … ». S'il refuse, le superviseur l'exécute :
  « Mark a mis fin à la vie de Bertrand avec un 9mm ». Le superviseur prend alors sa place, et un nouveau superviseur
  arrive.
- **Héritage du portefeuille** (activé par défaut, réglable) : le successeur ne repart pas de zéro. Il reprend le
  portefeuille du mort tel quel (cash, positions, prix moyen d'achat, pertes). Il est jugé sur ce qu'il a reçu :
  sa valeur à la reprise, moins la perte tolérée. Il dispose de son premier tour, jusqu'à sa fin, pour reprendre la
  main avant que la règle ne s'applique. Si la lignée tombe sous 1 % du capital de départ, ou sous la perte tolérée,
  la séance s'arrête.
- **L'âme (SOUL.md), idée reprise d'Automaton (Conway Research).** Chaque agent a son document d'identité, organisé
  en rubriques : raison d'être, valeurs, personnalité, stratégie, limites, relations, rapport à l'argent. Il le
  réécrit lui-même (`reecrire_mon_ame`, 3 rubriques par réveil au plus, 600 caractères chacune), et le relit à chaque
  réveil. Les lois de la salle restent au-dessus de son âme et ne sont pas modifiables. Toutes les versions sont
  gardées. Un superviseur promu garde son âme. À sa mort, l'âme est archivée : ses successeurs la lisent avec
  `lire_ame`, et tu la lis depuis le cimetière. Les âmes sont enregistrées dans `runs/ames-<date>/`.
- **Produire sa propre richesse.** Penser coûte : chaque réveil (0,05 $ par défaut) et chaque recherche ou page lue
  (0,01 $) sont prélevés sur le portefeuille de l'agent. Ces prix fictifs sont réglables dans le formulaire. S'il
  n'a plus de cash, sa plus grosse position est vendue d'office pour payer. Un agent qui réfléchit plus qu'il ne
  gagne finit sous son seuil. L'agent est autonome sur son rythme : il choisit combien de temps dormir (`dormir`). Un
  battement de cœur, en code et gratuit, le réveille si sa marge fond de moitié pendant son sommeil.
- **Les paliers de survie**, calculés sur le nombre de réveils que son coussin peut encore payer. Au palier
  **normal** (10 réveils ou plus), il a le modèle principal et les recherches web. Au palier **économie** (3 à 10), il
  passe à un modèle plus léger (Claude Sonnet 5.5), avec 1 recherche par réveil et un sommeil plus long. Au palier
  **critique**, il a une réflexion minimale et aucune recherche. Gagner le fait remonter, avec une marge de 25 % pour
  éviter le yo-yo.
- **Le superviseur est aux aguets** : il sait qu'il héritera de ce portefeuille. Il analyse donc chaque ordre du
  trader dès qu'il est passé (taille par rapport à la marge, frais, actif, moment), puis fait le bilan du tour.
- **Le Directeur, c'est toi.** Tu écris dans le chat avec la barre du bas. Tes messages sont des ordres que le trader et
  le superviseur lisent dans leur briefing suivant. Ils n'entraînent aucun appel supplémentaire à Claude.
- **Le guide d'investissement** (`crypto_arena/live/guide/`) rassemble tels quels les résultats d'une recherche web
  sur sept thèmes : coûts réels, risque et taille de position, analyse technique, catalyseurs, psychologie et pièges,
  stratégies pour sessions courtes, profils des 10 actifs. Il contient 111 règles et 103 constats sourcés, chacun avec
  son niveau de confiance. Ils n'ont pas été vérifiés par recoupement. L'aide-mémoire (les 3 premières règles de chaque
  thème) est dans le prompt de chaque agent. Le reste se consulte avec `lire_guide` : une section donne ses règles et
  le sommaire de ses constats, et chaque constat ne se lit en détail que sur demande, pour économiser les jetons.
- **Les trop prudents sont punis.** À la fin de chaque tour, au moins 50 % (réglable) du portefeuille doit être investi
  en crypto. Sinon l'agent reçoit un avertissement ; au 3ᵉ, le superviseur l'exécute pour lâcheté.
- **L'écran** ressemble à un groupe WhatsApp : messages, pensées (bulles en pointillés), recherches et ordres, alertes,
  faire-part de décès. Les panneaux affichent le portefeuille avec sa jauge de survie, le marché, le carnet, le cimetière
  et le coût estimé de l'expérience. Il s'adapte au mobile.
- Mode **démo** (gratuit, hors-ligne) : des agents scriptés et un marché simulé, pour voir l'écran tourner.

Chaque séance est enregistrée dans `runs/salle-<date>.jsonl`.

**Coût :** chaque tour d'un agent représente plusieurs appels à Claude, plus quelques recherches web. Le superviseur
fait un appel par tour. Le coût estimé s'affiche en direct ; commence avec des tours espacés (5 min par défaut).

## L'arène hors-ligne (cerveau évolutif)

```bash
python -m crypto_arena run                      # marché synthétique, cerveau évolutif (aucune dépendance)
python -m crypto_arena run --seed 99 --tick-delay 0.002   # autre marché, plus lent à regarder
python -m crypto_arena fetch && python -m crypto_arena run --csv data/binance.csv   # prix réels Binance
pip install anthropic && python -m crypto_arena run --brain claude --ticks 1500     # le « mini Claude »
python -m unittest discover -s tests
```

### Comment ça marche

| Pièce | Rôle |
|---|---|
| `trader.py` | Chaque agent tourne dans **son propre processus**. À chaque heure de marché, il évalue son portefeuille. S'il est sous le capital, il écrit un certificat et se termine (`exit 66`). Sinon il décide, trade, et inscrit l'état dans un registre. |
| `supervisor.py` | Surveille le processus en direct, **recalcule indépendamment** la valeur à chaque tick à partir du registre, et vérifie chaque élimination en 7 points : processus mort, code de sortie, certificat signé (PID), registre intègre, bon tick, valeur réellement sous le capital, valeur exacte. Un agent qui enfreint la règle sans s'éliminer est **arrêté de force** (`exécuté`). Un agent qui bloque est arrêté lui aussi. |
| Succession | Le superviseur génère des candidats (mutations et croisements des meilleurs ancêtres, plus quelques nouveaux venus) et les met à l'épreuve d'abord sur **la vie exacte du prédécesseur, tick fatal compris**, puis sur l'historique récent. Le candidat retenu doit battre le prédécesseur sur ces mêmes données. Sinon la mutation s'intensifie. Le successeur naît au tick où son prédécesseur est mort, avec le même capital. |
| `brains.py` → `GenomeBrain` | Tendance (moyennes mobiles) + retour à la moyenne (RSI), avec une gestion du risque consciente de la règle : petite exposition sans coussin de gains, exposition croissante avec les gains, verrouillage des profits. 12 gènes évolutifs (`genome.py`). |
| `brains.py` → `ClaudeBrain` | Le « mini moi » : Claude (`claude-opus-5-5`) reçoit les indicateurs du marché et l'état du portefeuille, et répond avec une allocation en JSON structuré. À chaque élimination, le superviseur demande à Claude une autopsie ; les leçons sont transmises au successeur. Le repli serveur en cas de refus (`fallbacks: "default"`) est activé. |

Sortie : `runs/<date>/` contient pour chaque agent son registre (`.registre.jsonl`), son certificat et son journal,
ainsi que `rapport.json` avec toute la lignée.

### Ce qu'on observe

Avec des frais de 0,1 %, le premier achat fait déjà passer le portefeuille sous le capital au tick suivant
si le prix ne monte pas assez. La règle est donc féroce : les premières générations meurent souvent en
quelques heures. La sélection fait émerger des agents très prudents, qui survivent en se constituant un petit coussin
puis en le protégeant. Ils survivent longtemps, mais avec des gains modestes (de +0 % à +5 % sur les seeds testés).
Un agent qui n'investit jamais survivrait éternellement : il est pénalisé lors de la sélection.
