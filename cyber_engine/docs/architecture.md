# Moteur d'investigation V2

Un seul délibérateur Qwen choisit les actions. Aucun agent spécialisé autonome.
Les quatre skills s'échangent des identifiants d'expériences et des preuves dans
une investigation SQLite privée. Le moteur ne simule pas un raisonnement interne
du modèle : il conserve des hypothèses formulées, des prédictions et des observations.

```
Observation → hypothèses concurrentes → prédictions avant test
    → sélection coût / séparation attendue → adaptateur réel
    → résultat + SHA-256 + entrées → reproduction / contre-test
    → rejet explicite des rivaux → conclusion bornée ou PARTIAL
```

Le sélecteur calcule l'entropie de la partition des hypothèses vivantes par les
labels prédits, divisée par le coût déclaré. Une prime explicite favorise les
contrôles et la non-régression. Ce score est une heuristique déterministe, pas
une probabilité de vulnérabilité ni un estimateur appris de performance.
Des prédictions incomplètes ne donnent pas de gain d'information. Une expérience
identique sur les mêmes entrées est dédupliquée ; une répétition doit être demandée.

Le registre contient UUID, périmètre, autorisation, positions source, hashes,
hypothèses ouvertes/rejetées, expériences, sorties, durées, contre-vérifications,
incertitudes et état terminal. Transactions immédiates pour les mutations ;
preuves adressées par contenu ; contrôle d'intégrité des valeurs lues. Ce n'est
pas un registre inviolable contre un utilisateur qui possède le fichier SQLite.

## Les six contrôles

| Contrôle | Où il agit | Refus / résultat |
|---|---|---|
| Evidence Gate | `Engine.gate`, `conclude` | refus d'une preuve absente, périmée, non répétée ou sans contrôle |
| Hypothesis Challenger | `gate`, `challenge`, contexte hooks | concurrent plausible → charger avocat-du-diable et contre-test |
| Experiment Selector | `select`, contexte avant/après outil | expérience justifiée ou raison d'arrêt |
| Regression Guard | `gate(fix=True)`, adaptateur compare | exige divergence ciblée et témoin préservé |
| Completion Gate | `conclude`, hook Stop | PASS seulement avec obligations ; PARTIAL permis sans DONE |
| Knowledge Recorder | hook Stop, `knowledge`, export Karvan | conserve seulement une conclusion à preuves actuelles |

Les hooks s'activent uniquement si le répertoire courant contient
`.astra/state/investigation.sqlite`. Aucune décision de permission d'outil n'est
émise ; les permissions Claude Code restent applicables. Le hook Stop empêche une
clôture structurée prématurée, puis permet un arrêt honnête PARTIAL. Une erreur
d'intégrité bloque la clôture. Claude Code impose lui-même une limite de reprises :
le hook n'est pas une garantie absolue contre toute phrase fausse du modèle.

Les contrôles vérifient une structure de preuve, pas la signification de toute
phrase libre : la pertinence d'un oracle, d'un contrôle et des hypothèses doit être
revue. Un label choisi par un harness ne démontre pas à lui seul une vulnérabilité.

Une base sans ligne d'état ne déclenche aucun hook. Le routage en lecture seule
ne crée pas de base ; seul `init` démarre une investigation avec un périmètre.

## Périmètre et données

Les adaptateurs vérifient racines réelles (symlinks résolus), noms d'adaptateurs et
origines réseau explicites. HTTP : GET seulement, taille/temps bornés, redirections
non suivies. Exécutions : argv sans shell, environnement réduit, processus neuf,
timeout du groupe de processus, CPU et fichiers de sortie limités, core dumps
désactivés. Il n'y a pas de confinement mémoire/egress universel : `trusted_lab`
est réservé aux fixtures contrôlées. Un binaire ou serializer hostile exige un
bac à sable OS fourni séparément.

Les preuves complètes restent dans le dossier privé 0700 / SQLite 0600. Elles
peuvent contenir du code et des données du projet : ne pas les publier en bloc.
Les hooks du moteur journalisent seulement l'événement et une empreinte de
session. Le journal réseau automatique a été retiré du profil à la demande de
l'utilisateur ; les hooks de compactage restent actifs.

## Installation et retour arrière

`python3 -m cyber_engine.install --profile /chemin/config --python /chemin/python3`

Si les outils natifs sont installés hors PATH, ajouter `--toolchain outils.json` :

```json
{"radare2":"/chemin/bin/r2","ghidra":"/chemin/ghidra/support/analyzeHeadless"}
```

Le lanceur `config/astra-runtime/run.py` rend ces exécutables disponibles au seul
processus du moteur. Les liaisons déjà installées sont conservées si l'option
est omise. Elles ne remplacent pas l'autorisation d'un adaptateur dans le périmètre.
Les versions et exécutions vérifiées figurent dans le [rapport](../reports/REPORT.md).

L'installation ajoute le runtime et les skills, sauvegarde les fichiers remplacés
dans `config/backups/astra-v2-*`, et ajoute cinq événements de hooks sans écraser
les précédents. Le manifeste précise les empreintes avant/après et les fichiers
touchés. Rouvrir Claude Code pour charger sa configuration. Pour revenir en arrière,
restaurer uniquement les fichiers du manifeste et retirer les entrées qui appellent
`astra-runtime/hook.py`, en conservant les autres hooks et toute modification plus
récente de l'utilisateur. Ne pas restaurer aveuglément tout un profil.

Référence runtime : [hooks Claude Code](https://code.claude.com/docs/en/hooks).
