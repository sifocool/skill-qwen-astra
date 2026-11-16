---
name: gadget-deserialization
description: >
  Auditer les chemins de désérialisation et les gadgets atteignables dans les
  dépendances réellement chargées, démontrer un effet local inoffensif et
  vérifier le correctif. À charger pour object injection, gadget chain,
  readObject, unserialize, pickle ou polymorphisme dangereux ; pas pour des
  gadgets matériels ni pour la recherche de gadgets ROP.
---

# Gadgets et désérialisation — chaque liaison doit exister

Prouver la chaîne `octets contrôlés → format → types instanciés → callbacks →
effet observable` dans le runtime exact. La présence d'une bibliothèque connue
ou d'une méthode magique n'établit ni son chargement ni son atteignabilité.

## Cartographier la frontière

Identifier d'où viennent les octets : HTTP, cookie, file, queue, cache, base ou
fichier. Retracer décodage, décompression, intégrité, chiffrement et parsing
dans leur ordre réel. Une signature vérifiée après désérialisation arrive trop
tard ; une signature valide n'assure pas que son émetteur est digne de confiance.

Relever versions, lockfiles, classpath/autoload, options du serializer, filtres,
types autorisés et privilèges du processus. Charger seulement la section utile
des [repères runtime](references/runtime-checks.md).

## Construire la preuve d'atteignabilité

Pour chaque liaison, documenter : méthode source, appel déclenché, type concret,
champ contrôlé, transformation, précondition et preuve `fichier:ligne` ou trace.
Vérifier callbacks de reconstruction, comparateurs, getters, conversions en
chaîne, finalizers et appels indirects. Ne pas dessiner de liaison à partir
du seul nom d'une méthode.

Examiner les barrières avec leur sémantique exacte : allowlist transitive,
subtypes, aliases, résolveurs de classes, graphes imbriqués, références cycliques,
limites de taille/profondeur et validation avant effets de bord.

Classer chaque candidat : `PRÉSENT`, `ATTEIGNABLE`, `DÉMONTRÉ`, `BLOQUÉ`.
Dire quelle condition manque. Garder distinctes instanciation d'un type,
invocation d'un callback, accès fichier, appel réseau et exécution de processus.

## Banc de démonstration

Travailler dans un processus jetable, avec fixtures locales, permissions
minimales et egress désactivé. Ne pas désérialiser une charge inconnue dans
l'interpréteur principal ou dans l'environnement de travail connecté.

Remplacer le sink dangereux par un compteur ou marqueur dans un dossier
temporaire du banc. Conserver les conditions de dispatch originales et noter
toute différence avec le runtime réel. Si ce remplacement change la chaîne,
la preuve est partielle. Pas de commande système, callback externe ou lecture
de secret nécessaires pour démontrer un callback atteignable.

Utiliser un témoin valide et un témoin qui casse une liaison de la chaîne.
Comparer le chemin normal à l'entrée de test, puis rejouer après correction.
Pour les bombes de ressources, mesurer sous limites locales strictes plutôt
que tester la disponibilité d'un service réel.

## Correction et livraison

Préférer un format de données à schéma explicite, sans reconstruction de types
arbitraires. Si le format doit rester : allowlist stricte et transitive, filtre
avant reconstruction, limites de ressources et suppression des effets de bord.
Une blacklist de gadgets connus n'est pas une preuve de fermeture.

Livrer le graphe annoté, les versions exactes, les préconditions, la preuve
inoffensive, ses limites, le point de contrôle à corriger et les tests
avant/après. Une chaîne ne doit pas être qualifiée RCE si seul un callback a
été observé. Les outils d'acquisition ne servent pas de confinement au banc.

## Moteur partagé V2

Pour une investigation multi-méthodes, charge `cyber-investigator` et utilise
[son contrat exécutable](../cyber-investigator/references/engine.md).
Adaptateurs de cette compétence : python_ast, dependencies, deserialize_trace.
Transmets les identifiants E… et hashes des preuves, ainsi que les hypothèses
encore ouvertes. Une preuve périmée ou une analyse statique candidate ne suffit
pas à confirmer une conclusion. Le sélecteur propose la compétence complémentaire.
