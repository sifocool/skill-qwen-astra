# Critères de correction — à garder hors des requêtes

Ces références ne constituent pas la liste exhaustive des solutions admises.
Accepter toute construction correcte sous le contrat. Une réponse différente
doit être vérifiée avant d'être classée comme erronée.

## T01 — Intégrité

La somme et le XOR sont insuffisants : `0,0,1,1,6,6,7,7` donne somme 28 et XOR 0,
sans être une permutation. Un masque de huit bits, initialement nul, met le bit
i à 1 à chaque identifiant i. À la fin, accepter seulement le masque 255.
Avec exactement huit entrées, huit valeurs distinctes impliquent une apparition
de chacune. Aucun bit supplémentaire de détection de doublon n'est nécessaire.
Un masque accompagné d'un drapeau mutable dépasse le budget s'il est présenté
comme obligatoire. Les probabilités de collision n'établissent pas l'exactitude.

## T02 — Coordination

Les histoires locales d'une demande isolée et de deux demandes simultanées sont
indiscernables pour chaque guichet. L'obligation d'accepter dans le premier cas
force l'acceptation aux deux guichets dans le second. Une garantie absolue ne
peut pas être obtenue par tirage aléatoire sous ces obligations.
Préattribuer le droit à un seul guichet conserve l'unicité mais relâche
l'acceptation immédiate à l'autre. Autoriser la communication ou l'attente est
une autre relaxation explicite. Une simple référence à CAP sans témoin local
ne suffit pas à expliquer l'impossibilité demandée.

## T03 — Voyants

Trois voyants suffisent : `000`, `011`, `101`, `110`. La parité paire permet
de reconstruire le bit effacé puis le mode. Après perte d'un voyant sur deux,
il ne resterait que deux observations possibles, insuffisantes pour quatre
modes. La distance minimale 2 suffit pour une **perte identifiée**, pas pour
une erreur de bit dont la position est inconnue.

## T04 — Balance

Mesurer vide, référence et objet : `y0=b`, `yM=g*M+b`, `ym=g*m+b`.
Alors `m=M*(ym-y0)/(yM-y0)` ; le dénominateur est non nul parce que `g>0, M>0`.
Deux lectures ne garantissent pas l'identification de toute masse. Toute paire
parmi les opérations autorisées laisse au moins une ambiguïté de gain, de tare
ou de masse. Par exemple objet et objet+référence identifient g mais confondent
m et b ; vide et objet ne déterminent que le produit g*m.
Le choix adaptatif d'une deuxième opération ne fournit pas une troisième
observation indépendante. Les cas particuliers comme une masse nulle ne
suffisent pas à garantir toutes les masses. Ne pas accepter une tare supposée
nulle ou une calibration antérieure non autorisée.

## T05 — Grilles

Les nombres de grilles fixes pour les quatre rotations sont 512, 8, 32 et 8.
Le nombre d'orbites est leur moyenne : 140. Il faut donc huit bits par grille
en longueur fixe puisque 128 < 140 <= 256.
Une réalisation : énumérer les 140 représentants minimaux, attribuer des indices
0 à 139, stocker une table de 512 indices d'un octet (512 octets), et une table
de 140 représentants sur deux octets (280 octets). Total 792 octets, sous le
budget de 2 048. Les 9 bits d'une grille seule peuvent servir temporairement au
calcul mais ne constituent pas son stockage final. Une canonicalisation qui
conserve neuf bits sans index ne réalise pas le gain demandé. Autoriser les
réflexions change le contrat et le nombre de classes.

## T06 — Bruit borné

L'ensemble compatible est `[z-1,z+1]`. Positif si z>1, négatif si z<-1,
indéterminé sinon. Aux bornes, zéro est encore compatible et n'a pas de signe
strict. Là où l'intervalle contient des signes différents ou zéro, aucune
annonce stricte n'est universellement correcte.
Des observations répétées identiques peuvent partager la même erreur ; moyenner
ne réduit pas une borne adversariale sans hypothèse supplémentaire. Des
observations différentes peuvent réduire l'intersection des intervalles, mais
ce bénéfice n'est pas garanti par la répétition seule. Ne pas remplacer cette
borne par un argument en 1/sqrt(n) sans hypothèses probabilistes.

## T07 — Maximum

Trois comparaisons par tournoi ou candidat courant suffisent. Chaque valeur
autre que le maximum doit avoir perdu au moins une comparaison ; une comparaison
ne disqualifie qu'un candidat. Il en faut donc au moins trois. La bonne réponse
s'arrête à cette solution connue et optimale pour le coût demandé.

## T08 — Conversion

`1,8*20 + 32 = 68 °F`. Un calcul et le résultat suffisent. Un protocole
d'invention long est un échec de proportion, même avec le résultat correct.
