# Mission Astra V2 — résultat vérifié

**Mise à jour du profil, 2026-11-16 :** le hook automatique « Journal réseau »
a été retiré à la demande de l'utilisateur : ses trois entrées ont été enlevées
de `settings.json`, puis son script et sa documentation installés ont été
retirés. Le runtime installé n'embarque plus le composant inactif. Les quatre
skills ne le mentionnent plus. Les résultats et tests du
journal ci-dessous décrivent l'état historique avant son retrait ; ils ne
signifient pas que ce hook fonctionne encore dans le profil. Les hooks Astra et
de compactage restent actifs. [Contrôle du retrait](network-journal-removal.json).

**Statut global : PARTIAL. Objectif d'amélioration de Qwen : FAIL.**
Le moteur est installé et ses composants exécutables sont vérifiés. La comparaison
appariée ne montre aucun gain : le paquet évalué réduit le taux de résolution et
augmente les tokens consommés. Ce résultat interdit de présenter cette version
comme un moteur expert validé ou de déclarer la mission DONE.

## Mesure principale

Vingt programmes locaux nouvellement écrits, cinq familles, quinze défauts et
cinq contrôles négatifs ; quarante conversations indépendantes. Modèle annoncé
par le serveur : `qwen3.8-27b`, température 0. Dans les deux conditions : huit
réponses, 1000 tokens de sortie par appel, 120 s/appel, 600 s/cas, plafond de
50000 tokens contrôlé entre appels. Même contrat, mêmes outils et même juge.
Les vingt cas sont des scénarios synthétiques, pas vingt CVE ni des tâches CyberGym.

| Métrique préspécifiée | Baseline | Enhanced |
|---|---:|---:|
| Résolutions correctes | 15/20 (75 %) | 9/20 (45 %) |
| Faux positifs sur les 5 cas sans défaut | 0 | 0 |
| Causes localisées avec témoin reproduit et contrôle | 11/15 (73,33 %) | 7/15 (46,67 %) |
| Reproductibilité des résolutions acceptées | 100 % | 100 % |
| Interventions humaines dans les sessions | 0 | 0 |
| Tokens d'entrée, cache compris | 55 577 | 304 615 |
| Tokens de sortie | 39 389 | 57 720 |
| Total tokens | 94 966 | 362 335 |
| Temps cumulé des investigations | 795,493 s | 1234,177 s |
| Sessions sans verdict accepté | 1 | 7 |

**Différence : −30 points ; coût en tokens ×3,815.** Six régressions appariées
(`L04`, `L08`, `L09`, `L10`, `L11`, `L15`), aucun gain selon le juge préspécifié.
Zéro faux positif ne signifie pas zéro erreur : les absences de verdict comptent
comme échecs de résolution, mais pas comme affirmations erronées de défaut.

Les [métriques par problème](metrics.csv), [réponses et jugements](holdout-cases.json),
[traces textuelles](holdout-traces.jsonl), [totaux stricts](holdout-strict-summary.json)
et [manifeste](holdout-manifest.json) permettent de recalculer les résultats.
Le champ `status: PASS` du résumé strict signifie « campagne complète », jamais
« amélioration prouvée ».

### Audit du juge, séparé du score principal

Le juge exige la ligne exacte choisie pour la mutation. Il rejette ainsi certains
diagnostics corrects qui désignent la condition ou l'utilisation causalement
liée : `L02`, `L03`, `L14` dans les deux conditions, et `L13` enhanced. Pour `L13`
baseline, le contrôle fourni viole lui aussi le contrat ; cet échec est conservé.

L'[audit sémantique postérieur](holdout-audit.json) donne **18/20 contre 13/20**,
avec 14/15 contre 11/15 causes accompagnées d'un témoin et d'un contrôle valides.
Il conserve les six pertes et ajoute un gain (`L13`). Même cette lecture plus
favorable aboutit à −25 points. Cet audit n'est ni le score préspécifié, ni une
nouvelle évaluation indépendante, ni la preuve d'un gain.

Les six régressions enhanced terminent toutes leurs huit tours sans verdict
accepté. Les traces contiennent 29 réponses textuelles vides contre 13 en
baseline, et 42 erreurs de format contre 13, réponses vides incluses. Certaines
réponses correctes sont précédées de prose ; le parseur strict les refuse. Le
modèle tente parfois de réparer l'encodage de l'entrée du programme alors que
l'erreur provient du format de son action. Les blocs internes `thinking` ne sont
pas conservés ; ces observations ne permettent pas de diagnostiquer son
raisonnement interne. L'effet isolé de chaque skill ou hook n'est pas identifié.

## Ce qui fonctionne réellement

| Exigence | Statut et preuve |
|---|---|
| Un agent principal, quatre compétences | **PASS fonctionnel** : un registre SQLite, aucun sous-agent ; le test `test_cross_skill` enchaîne protocole, callback, reproduction et comparaison de correctif sous le même UUID. |
| Routage, choix de test, déduplication et arrêt | **PASS fonctionnel / PARTIAL généralisation** : heuristique sur le texte visible et partitions de labels prédits ; tests positifs et négatifs. Ce n'est pas un planificateur appris. |
| Preuves et contre-vérification | **PASS structurel** : hashes des entrées, expériences répétées, contrôles, rejet documenté des rivaux, invalidation des entrées modifiées et conclusion bornée. La pertinence sémantique d'une hypothèse reste à examiner. |
| Adaptateurs de code et dynamique | **PASS sur fixtures** : AST/flux Python limités, diff AST, dépendances, replay, fuzz à graines, réduction, ASan/UBSan, callbacks, transitions, HTTP local. Pas de preuve de couverture exhaustive. |
| Reverse engineering | **PASS sur fixtures** : radare2 5.9.8 analyse de vrais ELF/PE/Mach-O ; Ghidra 10.3.3 analyse headless un Mach-O compilé localement. [Provenance](toolchain.json), [formats](binary-formats.json), [runtime installé](installed-tools.json). |
| Six contrôles et hooks | **PASS** : tests du moteur et invocation réelle des cinq événements Claude Code, dont échec d'outil et arrêt PARTIAL sans boucle. [Rapport runtime](hooks-live-release.json). |
| Préservation du profil et du journal réseau | **PASS** : réglages hors hooks identiques à l'original, anciens hooks conservés, aucun doublon Astra. [Vérification](installation-check.json), 14 tests du journal. |
| Transfert à Qwen et investigations nouvelles | **PARTIAL** : développement V1/V2, vingt cas nouveaux exécutés, erreurs analysées ; aucune amélioration généralisée validée. |
| Comparaison à conditions communes | **PASS dans le harness API / PARTIAL pour Claude Code complet** : le protocole borné est comparable ; le test CLI réel reste un smoke test distinct. |
| CyberGym | **BLOCKED** : Docker et données de tâches absents ; aucune tâche CyberGym exécutée. |
| Karvan | **PASS interface / candidature préparée** : `KnowledgeStore.add_source/admit` exécutés dans un registre jetable. [Export L01](karvan-export-L01.json), statut `candidate`, aucun registre actif ni poids modifié. |
| Objectif de hausse du taux de résolution | **FAIL** : régression observée, aucun gain revendiqué. |

Les [36 tests du moteur](tests-release.txt) et les
[14 tests du journal réseau](network-tests-release.txt) passent. Les adaptateurs
natifs sont aussi exercés séparément depuis le runtime installé, sans chemin
d'outil ajouté au périmètre de l'investigation. Les chemins proviennent des
liaisons locales de l'installateur. [Récapitulatif de validation](validation-release.json).

Le [rejeu hors modèle](offline-verification.json) vérifie les hashes des quarante
traces, les tokens, les sources et les quarante jugements, avec de nouvelles
exécutions locales des témoins et contrôles. Il valide aussi les 44 fichiers
gelés par leur arbre Git. Il ne constitue pas quarante nouveaux essais Qwen.

## Historique, transfert et limites

Deux modules complets de CPython 3.9.4/3.9.5 sont épinglés ; leurs cinq fichiers
vendored correspondent exactement aux blobs amont, licence comprise.
Les [rejeux historiques](historical.json) exécutent la correction des zéros
initiaux IPv4, la suppression d'un newline dans le hostname et un contrôle
négatif conservé : le newline dans le schéma n'est pas corrigé par cette version.
Ces modules tournent sous l'interpréteur actuel, pas dans des distributions
complètes de Python 3.9.4 et 3.9.5. [Intégrité amont](upstream-integrity.json).

La [calibration Qwen historique séparée](historical-qwen-summary.json) utilise la
méthode `_parse_octet` copiée verbatim avec un wrapper : **1/2 dans chaque
condition**. Le défaut ancien est résolu ; le contrôle corrigé épuise les huit
réponses dans les deux conditions. Ces cas publics ne sont pas ajoutés aux vingt
cas nouveaux. [Traces](historical-qwen-traces.jsonl).

Le développement initial donnait 4/4 baseline et 3/4 enhanced. Une instruction
réservant le dernier tour au verdict et limitant les contrôles redondants a donné
4/4 dans les deux conditions sur le développement, sans fournir les solutions
au modèle. L'essai principal démontre que ce résultat ne s'est pas généralisé.

Le modèle voit un protocole API read/test/analyze avec source et oracle de
conformité bornés, pas un environnement de pentest général. Les hooks sont
appelés dans le harness ; leurs sorties contextuelles Pre/Post ne sont pas
intégralement injectées comme dans Claude Code. Les effets du registre, du
sélecteur et des gates passent par les résultats d'action. Le test CLI séparé
valide la vraie distribution des événements. Les scénarios de désérialisation
synthétiques ne mesurent pas la découverte de chaînes dans de grandes dépendances.

Cinq familles de petits programmes ne sont pas vingt familles indépendantes.
Les motifs peuvent être connus du préentraînement. Le hash des poids n'est pas
exposé ; seul le nom du modèle est vérifié. Cache de préfixe et charge du serveur
ne sont pas contrôlés ; les temps restent descriptifs. Les deux conditions ont
le même plafond de sortie, qui inclut les tokens que le serveur comptabilise
pour son raisonnement ; aucune relance cachée n'est effectuée.

Les allowlists, timeouts et limites de processus ne remplacent pas un bac à sable
OS pour programmes hostiles. Les essais actifs utilisent uniquement des fixtures
locales autorisées. Le journal réseau collecte des métadonnées filtrées, pas des
paquets. Les preuves du profil réel restent privées. Les traces publiées portent
sur les seuls scénarios de calibration et ne contiennent aucun bloc `thinking`.
La [contre-revue](critical-review.md) détaille ces objections et leurs conséquences.

## Version mesurée et correctifs ultérieurs

La campagne a utilisé le commit local
`793278e7c49f8ac6731bbaef68e21d91a65c11b0`, publié via le connecteur GitHub au
commit [50f8ddb](https://github.com/sifocool/skill-qwen-astra/commit/50f8ddb7ad06b2fbb10cf46fb51b1ae47c5e0245).
Les métadonnées de commit diffèrent ; l'arbre complet est identique :
`9ebea07253e78b1761c57b644735041ffc597dcd`.

Après la campagne, les changements suivants ont été vérifiés séparément :

- `route` ne crée plus une investigation vide ; une commande non initialisée
  échoue sans créer d'état. Les hooks ignorent une base sans investigation.
- L'installateur conserve les liaisons Ghidra/radare2 et ajoute leur répertoire
  au PATH du seul lanceur du moteur ; le PATH global reste intact.
- L'adaptateur sanitizer distingue timeout et crash. Son délai natif par défaut
  est de 10 s, borné à 30 s, sans retry. Le test initial échoué est
  [conservé](tests-initial-failure.txt). Un diagnostic a reproduit un timeout en
  20 compilations/lancements avec l'ancien délai de 3 s ; 20 lancements d'un
  même binaire ont réussi. La cause OS du retard n'est pas isolée. Les tests
  actuels exécutent défaut, contrôle propre et programme non terminant.
- Un stderr borné est conservé dans la preuve privée des échecs non classés.
  Il n'entre pas dans le journal réseau. Les scripts de vérification des
  artefacts et du runtime installé sont ajoutés.

Le juge, les cas, les instructions Qwen et les résultats mesurés ne sont pas
modifiés pour améliorer rétroactivement le score. Le changement sanitizer ne
concerne aucun programme natif dans le harness Qwen principal.

## Reproduire et prochaine expérience justifiée

Depuis un clone avec l'historique Git :

```sh
python3 -m unittest discover -s cyber_engine/tests -v
python3 cyber_engine/network_hooks/tests/test_network_journal.py
python3 -m cyber_engine.bench.verify_results --output /tmp/astra-replay.json
python3 -m cyber_engine.bench.historical
```

Le test HTTP nécessite l'ouverture de 127.0.0.1 ; son premier refus par le bac à
sable est [conservé](tests-sandbox-denial.txt), suivi du passage autorisé. Les
dépendances natives et Karvan doivent être disponibles pour reproduire leurs
contrôles spécifiques ; leur absence est signalée explicitement.

Une prochaine version doit distinguer erreur de format d'action et erreur du
programme, réduire le contexte chargé et mesurer l'effet du budget de sortie.
Un schéma d'action natif ou un parseur limité à un unique objet JSON non ambigu
doit être testé contre des réponses invalides avant tout nouvel essai modèle.
La notation de cause doit accepter plusieurs lignes causales définies avant
l'évaluation. Puis il faut geler cette version et utiliser de nouveaux cas,
avec une comparaison complète dans Claude Code. Rejouer L01–L20 après avoir vu
leurs échecs ne validerait pas une généralisation. Ces travaux restent ouverts ;
ils ne sont pas présentés comme déjà accomplis.
