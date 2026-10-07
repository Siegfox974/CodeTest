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
