---
name: patch-diffing
description: >
  Comparer deux versions de sources ou binaires pour expliquer un correctif de
  sécurité, retrouver la cause racine, vérifier sa portée et prouver la
  non-régression. À charger pour patch diffing, analyse avant/après, correctif
  incomplet ou variantes proches ; pas pour une simple revue stylistique.
---

# Patch diffing — du changement à l'invariant

L'objectif est d'expliquer ce que le correctif interdit désormais, avec une
preuve avant/après. La proximité d'un diff avec une fonction sensible ne suffit
pas à établir une vulnérabilité.

## Fixer la comparaison

Identifier les deux artefacts sans références flottantes : commit complet ou
SHA-256, provenance, architecture, options de compilation et dépendances.
Distinguer un diff de versions `ancien → nouveau` d'un diff de branche depuis
un ancêtre commun. Vérifier l'ordre avant d'interpréter les ajouts/suppressions.
Préserver le travail courant ; utiliser des copies ou worktrees séparés si utile.

Pour un binaire : comparer à architecture, ABI et configuration équivalentes.
Les adresses, tailles et noms peuvent changer avec le compilateur, LTO ou les
symboles supprimés. Un appariement par similarité reste une hypothèse à vérifier.

## Lire le correctif

1. Dresser la liste des fichiers/fonctions changés, y compris tests, configuration,
   dépendances, migrations et backports. Isoler le bruit généré.
2. Lire les appelants et transformations autour du changement. Retracer
   `entrée contrôlée → normalisation → validation → usage` ainsi que les
   transitions d'état et contrôles d'autorisation sans sink dangereux.
3. Énoncer l'invariant en une phrase testable, par exemple : « la longueur
   validée est celle utilisée pour l'allocation et la copie ».
4. Décrire le scénario ancien, le contrôle ajouté et ses préconditions.
   Tester mentalement les chemins voisins : autre type, encodage, signe,
   taille limite, chemin d'erreur, autre appelant, concurrence si pertinente.
5. Examiner les variantes à partir de la cause racine et du graphe d'appels,
   plutôt que d'élargir à tous les fichiers contenant le même mot.

Si seule la version corrigée est disponible, dire que le comportement ancien
reste inféré. Une note de version ou un identifiant CVE ne remplace pas le diff.

## Démontrer sur banc

Construire le plus petit test qui affirme le comportement sûr. Exécuter la
même entrée et le même oracle sur les deux versions avec un environnement
comparable. Le tableau attendu est : ancien = violation observée, nouveau =
comportement sûr, témoin valide = accepté sur les deux versions.

Un échec de build, un crash du harness ou une différence de dépendances n'est
pas le rouge attendu. Si le patch rejette toute entrée, le témoin valide doit
le révéler. Conserver commande, sortie, seed éventuelle et hashes des artefacts.

En présence d'une correction incomplète, préciser le chemin qui reste ouvert
et proposer le contrôle minimal à modifier. Appliquer le fix si la mission
le demande, puis rejouer la preuve et les tests des chemins affectés.

## Livraison

Rapport : invariant ; cause racine ; chemin atteignable et préconditions ;
delta précis avec références source/adresses relatives ; matrice avant/après ;
variantes examinées ; limites. Séparer `PROUVÉ`, `INFÉRÉ`, `NON TESTÉ`.
Ne pas transformer une erreur mémoire en affirmation d'exécution de code.

Documenter les téléchargements et requêtes utiles dans les preuves de mission.

## Moteur partagé V2

Pour une investigation multi-méthodes, charge `cyber-investigator` et utilise
[son contrat exécutable](../cyber-investigator/references/engine.md).
Adaptateurs de cette compétence : semantic_diff, binary, compare.
Transmets les identifiants E… et hashes des preuves, ainsi que les hypothèses
encore ouvertes. Une preuve périmée ou une analyse statique candidate ne suffit
pas à confirmer une conclusion. Le sélecteur propose la compétence complémentaire.
