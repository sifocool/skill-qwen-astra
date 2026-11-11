# Ce qui a réellement été vérifié

Expériences exploratoires réalisées pendant la session du 11 novembre 2026.
Les résultats détaillés sont dans [results.json](../experiments/results.json),
reproductibles avec [verify.py](../experiments/verify.py), sans dépendance externe :

```bash
cd /workspace/skill-qwen-astra
python experiments/verify.py --output /tmp/astra-invention-results.json
```

Le JSON contient l'empreinte SHA-256 du vérificateur. Les générateurs et les
oracles ont été écrits dans la même session : les vérifications sont
reproductibles, mais ne constituent pas une revue indépendante. Aucun appel à
Qwen n'a été réalisé.

## 1. L'alarme : une compression peut être correcte et inutile

Le flux est binaire. Il faut signaler la présence d'au moins trois uns parmi
les cinq dernières entrées, avec un historique initial nul.

Garder seulement la somme courante échoue : `00011` et `10001` ont la même
somme, mais après une entrée `1`, ils donnent respectivement 3 et 2 uns.
Ce témoin impose de conserver davantage de structure temporelle.

Une construction par raffinement de partitions fusionne les historiques qui
répondent de la même manière à toutes les continuations. Mais la notion de
« sortie » est déterminante :

| Contrat de sortie | Seuil | États de la référence simple | États minimaux dans ce modèle | Bits de la référence → quotient |
|---|---:|---:|---:|---:|
| Consultable à tout moment depuis l'état seul (Moore) | 3/5 | 32 | 20 | 5 → 5 |
| Produite à chaque entrée (Mealy) | 3/5 | 16 | 14 | 4 → 4 |
| Consultable à tout moment depuis l'état seul (Moore), variante | 2/5 | 32 | 15 | 5 → 4 |
| Produite à chaque entrée (Mealy), variante | 2/5 | 16 | 11 | 4 → 4 |

Dans le contrat Mealy, quatre bits précédents et l'entrée reçue suffisent à
calculer la sortie ; l'entrée courante ne doit pas être mémorisée avec quatre
autres bits après ce calcul.

Le premier vérificateur utilisait implicitement le contrat Moore. Son résultat
de 20 états était exact, mais ne prouvait pas la minimalité pour le contrat de
sortie à chaque entrée. L'examen d'une autre réalisation a révélé cette
restriction involontaire. Les deux modèles sont maintenant vérifiés séparément.

Pour chacun des quatre cas :

- Toutes les transitions du quotient et leurs sorties sont vérifiées contre les
  historiques complets. Avec l'état initial, cela fournit un argument inductif
  de correction pour des flux de toute longueur.
- Chaque paire d'états distincts possède une continuation produisant une sortie
  différente. Tous les historiques sont atteignables. Ce contrôle certifie la
  minimalité dans le modèle d'automate indiqué, pas dans une autre interface.
- Les 8 191 mots binaires de longueur 0 à 12 sont aussi comparés à une référence
  utilisant la liste des entrées. Cela représente 90 114 sorties par cas.

L'alarme au seuil 3 ne gagne **aucun bit par flux** grâce à cette minimisation,
dans les deux contrats. Dans le modèle Moore, une table générique compacte
ajouterait 200 bits de transitions et 20 bits de sorties. La variante au seuil 2
peut gagner un bit par flux dans ce modèle, au prix d'une table de 135 bits,
avant prise en compte du code, de l'alignement et du stockage physique. Une
réduction globale de mémoire n'est pas démontrée.

**Leçons retenues dans le skill :** choisir une référence simple déjà adaptée
au contrat ; mesurer l'objectif physique ; contrôler les hypothèses du juge.
La minimisation d'automates est connue. La valeur de cet essai est la mise à
l'épreuve de la démarche, y compris la correction d'une mauvaise portée.

## 2. Le capteur : inventer la règle de lecture avec le protocole

À des instants entiers consécutifs, un contrôle vaut +1 ou −1. Le capteur répond :

```text
y[t] = a*x[t] + b0 + b1*t + b2*t² + e[t]
```

Il faut estimer la réponse utile a, malgré une dérive quadratique inconnue et
un bruit borné par epsilon. Une mesure quelconque peut manquer ; sa position
est connue. La réponse a est constante et instantanée, le contrôle est exact,
les horodatages sont conservés et le capteur ne sature pas.

Pour un estimateur linéaire `a_est = sum(w[t]*y[t])`, le certificat est :

```text
sum(w[t]*x[t]) = 1                 conservation du signal
sum(w[t]*t**k) = 0, k = 0,1,2     annulation de la dérive
sum(abs(w[t])) = 1                 erreur au plus epsilon
w[t_perdu] = 0                    indépendance de la mesure perdue
```

La troisième ligne est optimale pour cette classe d'estimateurs, puisque
`1 = abs(sum(w*x)) <= sum(abs(w))` quand `abs(x)=1`.

### Deux familles comparées

Avec des poids signés égaux `w[t]=x[t]/n`, l'énumération trouve la première
séquence annulant les trois moments à huit mesures, sans perte :

```text
+ − − + − + + −
```

C'est la structure connue de Prouhet–Thue–Morse. Ce résultat n'est pas présenté
comme son invention. Supprimer une mesure tout en gardant les autres poids
figés détruit l'annulation.

En autorisant une lecture adaptée à la position manquante, six mesures suffisent :

```text
+ − + − + −
```

Parmi les observations restantes, choisir quatre instants avec des signes
alternés. Une telle sélection existe après n'importe quelle perte unique dans
cette séquence. Pour ces instants `t_i`, poser :

```text
c_i = 1 / produit(t_i - t_j, j différent de i)
w_i = c_i / somme(c_j*x[t_j])
```

Ces coefficients de différence divisée annulent tous les polynômes de degré
au plus deux. Les signes alternés permettent aussi d'obtenir `sum(abs(w))=1`.
Les poids sont choisis à partir des instants et de la perte, sans regarder les
valeurs bruitées.

Par exemple, si la mesure à `t=2` manque, une solution vérifiée est :

```text
t :  0      1    2    3       4       5
x : +1     −1   +1   −1      +1      −1
w : 1/32    0    0  −5/16   15/32  −3/16
```

On mesure six fois pour garantir l'existence d'un sous-ensemble utilisable.
Ce décodeur particulier utilise quatre mesures ; il n'est pas optimal pour
tous les autres critères de bruit.

### Portée du résultat de recherche

Les motifs sont énumérés à une inversion globale du signe près. Pour chaque
motif et chaque perte, le programme cherche le meilleur estimateur linéaire
pour la norme L1.

| Mesures acquises | Motifs examinés | Motifs identifiables après toute perte unique | Meilleure amplification maximale du bruit |
|---:|---:|---:|---:|
| 4 | 8 | 0 | Impossible |
| 5 | 16 | 4 | 3 |
| 6 | 32 | 25 | 1 |

Avec moins de quatre mesures conservées, le signal est indiscernable d'une
dérive quadratique arbitraire. Pour les autres cas, les trois colonnes de
dérive sont indépendantes. Si la colonne du contrôle n'augmente pas le rang,
a est indéterminable. Sinon, minimiser L1 est un programme linéaire avec quatre
égalités ; un optimum existe sur au plus quatre coefficients non nuls.
L'énumération de toutes les bases à quatre mesures couvre donc cette classe.

Six est ainsi minimal pour la garantie `erreur <= epsilon` dans la famille
étudiée : contrôle binaire, instants entiers consécutifs, estimateur linéaire,
dérive quadratique, au plus une perte identifiée. Cinq permet encore une
estimation exacte sans bruit, avec une moins bonne garantie au bruit ; il ne
faut pas appeler cela une impossibilité totale.

Le programme vérifie exactement, avec des fractions rationnelles :

- Les quatre égalités pour les sept situations : aucune perte ou une des six.
- 567 combinaisons de paramètres et de pertes.
- 256 sommets du domaine de bruit borné, et l'atteinte de la borne epsilon.

Les égalités établissent la propriété pour des coefficients de dérive réels
quelconques. Les sommets contrôlent la fonction linéaire du bruit sur tout le
pavé ; le résultat ne repose pas seulement sur un tirage aléatoire favorable.

### Coûts et échecs conservés

Le gain de six contre huit porte sur ces deux familles spécifiées. Il ne s'agit
pas d'une comparaison à l'ensemble des protocoles connus. Le prix est une
lecture conditionnelle et des poids inégaux. Même sans perte, un estimateur
à quatre points consécutifs a une variance `5/16 * sigma²`, contre `1/8 * sigma²`
pour la moyenne signée sur huit points, **si** les bruits sont indépendants,
centrés et de même variance. L'optimalité en bruit borné ne donne donc pas une
optimalité en bruit aléatoire.

Deux contrôles négatifs réussissent à casser les garanties prévues :

- Après perte du premier point, les poids égaux figés laissent passer `−1/8`
  d'une dérive constante unitaire.
- Une dérive cubique unitaire produit un biais de `3/4` dans l'estimateur à
  six acquisitions retenu pour le cas sans perte.

La dynamique réelle du capteur, son temps d'établissement, une perte cachée et
une erreur d'horodatage ne sont pas validés. Un prototype physique pourrait
invalider les hypothèses avant de reproduire le résultat mathématique.

**Leçon retenue dans le skill :** conserver la garantie tout en déplaçant la
liberté de conception vers une autre partie du mécanisme peut ouvrir une
solution. Transmettre sa condition de rupture est aussi important que la recette.

## Ce que ces essais ne démontrent pas

Ils ne démontrent pas une originalité mondiale, une capacité générale
d'invention supérieure, ni un gain chez Qwen 27B. Les outils mathématiques
mobilisés ont des antécédents connus : équivalences d'automates, annulation de
moments, différences divisées, optimisation linéaire et synthèse guidée par
contre-exemples. Le protocole de transfert reste une hypothèse à tester selon
[le plan d'évaluation](../evaluation/PROTOCOL.md).
