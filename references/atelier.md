# Atelier : fabriquer un opérateur d'invention

Ce document décrit une méthode de travail proposée et éprouvée sur deux
problèmes. Il ne décrit pas une trace interne du modèle. Les noms ci-dessous
servent à manipuler les opérations ; ils ne constituent pas des revendications
d'originalité scientifique.

## Une représentation peut échouer de deux façons opposées

Un système observe O(w) du monde w et doit prendre une décision D(w).

- S'il existe u et v tels que O(u) = O(v), mais D(u) != D(v), aucune décision
  déterministe fondée uniquement sur O ne peut toujours être correcte.
- Si plusieurs différences entre observations ne changent aucune décision
  requise, une représentation plus compacte peut parfois les oublier.

Pour un processus, D doit inclure les réponses aux événements futurs pertinents.
Deux historiques donnant la même sortie aujourd'hui peuvent diverger demain.
Pour une expérience active, O dépend aussi de l'intervention choisie.

Cette double question donne un objet précis à l'invention : conserver les
distinctions utiles et éliminer les autres. Elle est apparentée à la suffisance
statistique, à l'observabilité et aux équivalences d'automates. Son intérêt ici
est d'en faire une routine de conception transférable à un modèle de langage.

## Opérateur A — Transformer une collision en exigence

**Déclencheur.** Une solution semble manquer d'information, ou accumule des
exceptions sans explication commune.

**Transformation.** Construire deux cas indiscernables pour cette solution, mais
qui demandent des réponses différentes. Transformer leur différence en exigence
de mesure, de mémoire ou d'intervention. Tester une modification à la fois.

**Invariant.** Les contraintes du problème restent identiques ; seule change
l'information disponible à la décision.

**Coût.** Obtenir la distinction peut exiger une question, un capteur, un bit,
une synchronisation ou une attente.

**Réfutation.** Si les cas restent indiscernables après la modification, elle
n'a pas réparé le mécanisme. Si l'information est interdite ou inaccessible,
le témoin établit une limite ; il ne donne pas le droit de contourner le contrat.

Exemple vérifié : les historiques `00011` et `10001` ont la même somme, 2.
Après une entrée `1`, leurs cinq derniers bits contiennent respectivement 3 et
2 uns. Une alarme « au moins trois sur cinq » ne peut utiliser seulement la somme
courante comme état. Le problème est la perte d'une distinction temporelle.

Un usage sans calcul : si deux dossiers ont les mêmes champs disponibles mais
des autorisations différentes, une meilleure rédaction de la règle ne crée pas
l'information manquante. Le candidat pertinent peut être une preuve
d'autorisation, une question ciblée ou une décision différée. Il reste à vérifier
leur coût et leur faisabilité dans le contexte réel.

## Opérateur B — Supprimer une différence après avoir essayé de la rendre utile

**Déclencheur.** La solution conserve un historique ou un état coûteux.

**Transformation.** Proposer une fusion, puis chercher une continuation qui
exigerait de distinguer les états fusionnés. Raffiner la représentation si cette
continuation existe. Pour un domaine fini, itérer jusqu'à stabilité.

**Invariant.** Les décisions requises sont conservées, y compris après les
évolutions couvertes par le contrat.

**Coût.** Une table de transition ou une logique plus compliquée peut remplacer
les bits économisés. L'encodage physique peut annuler le gain théorique.

**Réfutation.** Une seule continuation avec sorties différentes invalide une
fusion. Une baisse du nombre d'états sans baisse de mémoire invalide seulement
la promesse de gain mémoire, pas nécessairement la correction de l'automate.

Résultat instructif : avec une sortie consultable depuis l'état seul, 32 états
deviennent 20, mais 20 états demandent encore 5 bits. Avec une sortie produite
seulement à chaque entrée, la référence garde déjà seulement 4 bits : 16 états
deviennent 14, soit toujours 4 bits. Dans les deux cas, la fusion ne réduit pas
le nombre de bits par flux. Le premier vérificateur avait involontairement
ajouté la première exigence au problème ; la correction de cette portée fait
partie des résultats, pas d'une réussite à dissimuler.

## Opérateur C — Faire porter la souplesse sur le décodeur

**Déclencheur.** Un protocole échoue lorsqu'une observation disparaît, alors que
la nature de cette disparition est connue.

**Transformation.** Conserver le contrat d'erreur et rendre la règle de lecture
conditionnelle à l'information disponible : horodatages, positions manquantes,
précision mesurée. Déduire ses paramètres des invariants à conserver.

**Invariant.** Dans l'expérience du capteur, préserver la réponse au signal et
annuler les composantes de la dérive ; borner la norme des poids.

**Coût.** Calcul ou stockage de coefficients, connaissance fiable des instants
et des pertes, hypothèses sur la réponse du dispositif.

**Réfutation.** Un décodeur qui dépend des valeurs bruitées peut introduire une
sélection biaisée. Une perte non identifiée, une dérive hors modèle ou une
réponse physique non instantanée peut invalider le certificat.

Le procédé étudié autorise des poids inégaux. Il produit un protocole à six
mesures avec une perte identifiée, là où la famille à poids égaux a besoin de
huit mesures pour annuler la même dérive sans perte. C'est une construction
dans un modèle explicite ; les poids inégaux ne sont pas une idée nouvelle en
eux-mêmes.

## Fabriquer un quatrième opérateur

Ne pars pas nécessairement d'une liste de techniques. Pars de ce que le témoin
interdit à la solution courante.

| Témoin observé | Propriété à obtenir | Transformation candidate | Coût à regarder |
|---|---|---|---|
| Même mesure, décisions incompatibles | Distinction accessible | Intervention ou mesure supplémentaire | Acquisition, délai |
| Même décision pour toutes les continuations admissibles | État plus petit | Fusion d'états | Décodage, table |
| Composante parasite identifiée | Invariance à cette composante | Combinaison ou symétrie d'expériences | Contrôle, modèle du parasite |
| Action correcte mais trop tôt | Information avant irréversibilité | Différer ou scinder l'action | Latence, stockage |
| Validation coûteuse sur chaque cas | Condition locale suffisante | Certificat puis repli si absent | Calcul du certificat, coût du repli |

Les deux dernières lignes sont des pistes, non testées dans cette session.
Une ligne peut engendrer une technique, puis un nouveau témoin révéler qu'elle
déplace le problème. Il faut alors modifier l'opérateur, pas simplement son nom.

Exemple de composition : obtenir une mesure supplémentaire seulement lorsque
deux décisions restent compatibles avec les observations. Ce couplage peut
réduire les acquisitions moyennes, mais son coût maximal et sa condition d'arrêt
doivent être vérifiés. Aucun gain chiffré n'est revendiqué ici.

## Hypothèses sur ce qui rend la démarche productive

Les deux constructions suggèrent des hypothèses opérationnelles : un témoin
court rend la modification nécessaire plus précise ; un invariant commun permet
de transposer une opération entre domaines ; une réfutation externe élimine une
proposition séduisante mais fausse.

Cela ne démontre pas comment les paramètres du modèle produisent une idée.
La génération à partir de régularités apprises, la recombinaison et l'adaptation
au contexte sont des explications générales compatibles avec ce comportement.
Cette session ne mesure pas leurs contributions respectives.

Pour Qwen 27B, limiter les candidats simultanés et conserver un petit registre
de contre-exemples est un choix de conception à évaluer. Il n'a pas été montré
ici que cette organisation améliore ses performances.

## Registre court utilisable entre deux itérations

```text
Contrat :
Référence et son coût :
Témoin qui bloque la référence :
Modification proposée :
Invariant à conserver :
Résultat observé / résultat encore attendu :
Coût déplacé :
Condition de rupture :
Prochain test décisif :
```

Ce registre décrit des objets de travail et des preuves communicables. Il ne
demande pas un récit exhaustif des pensées du modèle.
