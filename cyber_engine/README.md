# Astra Cyber Investigation Engine V2

Moteur local pour un agent principal Qwen : registre partagé de preuves, sélection
d'expériences, quatre compétences spécialisées, adaptateurs exécutables et hooks
de contrôle. **L'efficacité du paquet doit être lue dans les résultats mesurés ;
son architecture seule ne démontre aucun gain de résolution.**

**Résultat mesuré : PARTIAL pour la mission, FAIL pour le gain recherché.**
Sur 20 cas appariés, baseline **15/20**, enhanced **9/20**, avec **3,815 fois**
plus de tokens. Les 36 tests du moteur et les 14 tests du journal passent ; ces
validations techniques ne compensent pas la régression de résolution.
Le [rapport complet et ses preuves](reports/REPORT.md) conservent les résultats
négatifs, l'audit postérieur du juge et les limites de l'évaluation.

- [Architecture, contrôles et limites](docs/architecture.md)
- [Skill d'orchestration et contrat CLI](skills/cyber-investigator/SKILL.md)
- [Protocole de comparaison Qwen](bench/PROTOCOL.md)
- [Rejeux historiques avec modules CPython épinglés](reports/historical.json)
- [État initial et provenance](reports/initial-state.json)

Depuis la racine du dépôt, avec Python 3.11+ :

```sh
python3 -m unittest discover -s cyber_engine/tests -v
python3 -m cyber_engine.bench.historical
python3 -m cyber_engine.bench.verify_results --output /tmp/astra-replay.json
python3 -m cyber_engine.install --profile /chemin/du/profil/config
```

Le test HTTP ouvre seulement un serveur éphémère sur 127.0.0.1. ASan demande
Clang ; Ghidra/radare2/Karvan sont des capacités optionnelles dont l'absence est
signalée, jamais convertie en intégration réussie. Les scripts n'installent pas
silencieusement ces dépendances. La suite principale utilise la bibliothèque
standard Python ; les six skills sont du Markdown Claude Code.

```sh
python3 -m cyber_engine.bench.run --development --output /chemin/prive/dev
python3 -m cyber_engine.bench.run --output /chemin/prive/holdout
```

Ces deux commandes appellent réellement Qwen sur le proxy local 127.0.0.1:8095,
avec budgets bornés et sorties privées. Elles refusent de réutiliser un dossier
de résultats existant. Ne pas utiliser les cas d'évaluation pour ajuster la
procédure puis prétendre les découvrir à nouveau.

L'export `python3 -m cyber_engine.karvan_export --state … --output …
--karvan-package …` valide une candidature contre l'interface Karvan réelle dans
un registre jetable. Il ne modifie aucun registre actif ni aucun poids.
