# CodeTest — Arène darwinienne d'agents traders crypto

Une expérience : un agent trader reçoit un portefeuille et doit le faire fructifier.
**La règle :** si la valeur du portefeuille passe sous le capital confié, ne serait-ce que d'un centime,
l'agent doit s'auto-terminer. Un **superviseur** vérifie que l'élimination a bien eu lieu, puis le remplace
par un successeur sélectionné pour faire mieux. Et ainsi de suite.

> Tout se passe en **simulation, avec de l'argent fictif** : aucun ordre réel n'est passé.

## Lancer

```bash
python -m crypto_arena run                      # marché synthétique, cerveau évolutif (aucune dépendance)
python -m crypto_arena run --seed 99 --tick-delay 0.002   # autre marché, plus lent à regarder
python -m crypto_arena fetch && python -m crypto_arena run --csv data/binance.csv   # prix réels Binance
pip install anthropic && python -m crypto_arena run --brain claude --ticks 1500     # le « mini Claude »
python -m unittest discover -s tests
```

## Comment ça marche

| Pièce | Rôle |
|---|---|
| `trader.py` | Chaque agent tourne dans **son propre processus**. À chaque heure de marché, il évalue son portefeuille. S'il est sous le capital, il écrit un certificat et se termine (`exit 66`). Sinon il décide, trade, et inscrit l'état dans un registre. |
| `supervisor.py` | Surveille le processus en direct, **recalcule indépendamment** la valeur à chaque tick à partir du registre, et vérifie chaque élimination en 7 points : processus mort, code de sortie, certificat signé (PID), registre intègre, bon tick, valeur réellement sous le capital, valeur exacte. Un agent qui enfreint la règle sans s'éliminer est **arrêté de force** (`exécuté`). Un agent qui bloque est arrêté lui aussi. |
| Succession | Le superviseur génère des candidats (mutations et croisements des meilleurs ancêtres, plus quelques nouveaux venus) et les met à l'épreuve d'abord sur **la vie exacte du prédécesseur, tick fatal compris**, puis sur l'historique récent. Le candidat retenu doit battre le prédécesseur sur ces mêmes données. Sinon la mutation s'intensifie. Le successeur naît au tick où son prédécesseur est mort, avec le même capital. |
| `brains.py` → `GenomeBrain` | Tendance (moyennes mobiles) + retour à la moyenne (RSI), avec une gestion du risque consciente de la règle : petite exposition sans coussin de gains, exposition croissante avec les gains, verrouillage des profits. 12 gènes évolutifs (`genome.py`). |
| `brains.py` → `ClaudeBrain` | Le « mini moi » : Claude (`claude-opus-5-5`) reçoit les indicateurs du marché et l'état du portefeuille, et répond avec une allocation en JSON structuré. À chaque élimination, le superviseur demande à Claude une autopsie ; les leçons sont transmises au successeur. Le repli serveur en cas de refus (`fallbacks: "default"`) est activé. |

Sortie : `runs/<date>/` contient pour chaque agent son registre (`.registre.jsonl`), son certificat et son journal,
ainsi que `rapport.json` avec toute la lignée.

## Ce qu'on observe

Avec des frais de 0,1 %, le premier achat fait déjà passer le portefeuille sous le capital au tick suivant
si le prix ne monte pas assez. La règle est donc féroce : les premières générations meurent souvent en
quelques heures. La sélection fait émerger des agents très prudents, qui survivent en se constituant un petit coussin
puis en le protégeant. Ils survivent longtemps, mais avec des gains modestes (de +0 % à +5 % sur les seeds testés).
Un agent qui n'investit jamais survivrait éternellement : il est pénalisé lors de la sélection.
