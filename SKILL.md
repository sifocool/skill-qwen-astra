---
name: skill-qwen-astra
description: Concevoir une technique lorsque les solutions habituelles échouent sur une contrainte précise. Construire un cas qui révèle la distinction manquante, modifier le mécanisme, puis vérifier gain, coût et domaine de validité. Adapté aux problèmes techniques et scientifiques ; utilisable sans outils.
---

# Invention vérifiable

Produis une proposition utile et réfutable. Le résultat recherché est un
mécanisme transférable, pas une idée rendue séduisante par son nom. Une méthode
connue satisfaisant le besoin reste un bon résultat.

## 1. Fixer ce qui doit changer

Écris un contrat court : **résultat attendu ; contraintes obligatoires ; moyens
autorisés ; critère de gain ; référence de comparaison**. Sépare les contraintes
imposées des habitudes de conception. S'il manque une donnée, formule une
hypothèse explicite ou pose la seule question qui empêche de progresser.

Définis avant l'essai ce qui compterait comme un échec. Mesure le résultat
demandé : moins d'états ne signifie pas automatiquement moins de bits ; moins
de calcul ne signifie pas moins de coût total.

## 2. Trouver la distinction utile

Essaie d'abord une solution simple. Si elle bloque, construis un petit témoin
du blocage, puis choisis l'opération adaptée :

<!-- operator:distinction:start -->
- **Séparer.** Cherche deux situations que le système ne distingue pas, mais
  qui exigent des décisions différentes, éventuellement après le même événement
  futur. Identifie l'information qui les séparerait. Propose un moyen de la
  mesurer, la conserver ou la faire apparaître par une intervention. Si aucun
  moyen autorisé n'existe, expose l'impossibilité et la modification minimale
  du contrat qui la lèverait, sans l'appliquer silencieusement.
- **Fusionner.** Cherche des différences que le système conserve alors qu'elles
  ne peuvent changer aucune décision requise. Essaie de les supprimer. Pour un
  système séquentiel, l'égalité de la sortie actuelle ne suffit pas : les suites
  d'entrées pertinentes doivent aussi préserver l'équivalence.
- **Neutraliser.** Si un facteur parasite masque la réponse, cherche une
  intervention ou une combinaison d'observations qui conserve l'effet utile
  tout en annulant ce facteur. Écris ce qu'elle conserve et ce qu'elle annule.
<!-- operator:distinction:end -->

Si ces opérations ne conviennent pas, construis ton propre opérateur à partir
du témoin : **propriété qui manque → transformation susceptible de la fournir
→ coût payé → observation qui pourrait la réfuter**. Le catalogue est ouvert.

## 3. Changer un mécanisme

Forme au plus trois candidats réellement différents : par l'information
disponible, la représentation, l'intervention ou le moment où une décision est
prise. Une reformulation verbale ne compte pas comme un candidat.

Pour chacun, note seulement :

> Modification concrète · effet attendu · hypothèse indispensable · coût déplacé
> · plus petit test décisif.

Change une hypothèse de conception à la fois. Par exemple, « les poids doivent
être égaux » peut être une habitude, alors que « l'erreur reste bornée » est une
exigence. N'abandonne pas la seconde pour satisfaire la première.

## 4. Attaquer la proposition

Compare le meilleur candidat à la référence sur le même objectif. Utilise un
contre-exemple, une dérivation vérifiable, une simulation, une mesure ou une
expérience physique selon les moyens disponibles.

- Teste le cas nominal, un cas limite et un cas qui viole une hypothèse.
- Vérifie que le juge ou le simulateur n'a pas ajouté une contrainte absente du
  contrat. Une preuve exacte dans le mauvais modèle peut induire en erreur.
- Réutilise chaque échec confirmé comme test de non-régression.
- Comptabilise installation, stockage, mesure, calcul et intervention humaine
  quand ils peuvent inverser la comparaison.
- Un exemple réussi n'est pas une garantie générale. Si tu proposes un invariant,
  précise pourquoi il se conserve ; sinon borne explicitement la validation.
- Distingue test **exécuté**, démonstration **fournie**, résultat **supposé** et
  test **à réaliser**. Sans outil, ne rapporte aucune exécution imaginaire.

Si l'idée échoue, répare le mécanisme à partir du témoin. Par défaut, limite-toi
à deux cycles de réparation ; prolonge si la tâche le justifie. Si elle réussit,
retire un composant ou modifie l'hypothèse essentielle pour vérifier ce qui
porte réellement le résultat. Arrête lorsque le gain demandé est établi, qu'une
impossibilité est justifiée, ou que les prochains essais nécessitent des moyens
indisponibles. Indique alors l'essai précis qui manque.

## 5. Transmettre ce qui survit

Présente une synthèse d'ingénierie, sans journal de raisonnement interne :

1. **Proposition** : fonctionnement concret et besoin satisfait.
2. **Différence utile** : ce qu'elle distingue, fusionne ou neutralise.
3. **Appui** : preuve ou observations, avec leur portée.
4. **Bilan** : gain mesuré face à la référence et coût déplacé.
5. **Limite** : condition de rupture et prochain essai utile.

Quand tu extrais une nouvelle technique, fournis une fiche réutilisable :
**déclencheur ; transformation ; invariant ; coût ; réfutation**. Transmets ces
cinq éléments ensemble. Une recette sans sa condition de rupture se transfère mal.

Étiquette honnêtement la nouveauté : méthode connue, combinaison proposée ici,
ou antériorité non vérifiée. Ne prétends ni accéder aux mécanismes internes d'un
autre modèle, ni avoir démontré un gain de créativité à partir d'un seul succès.

## Ressources à charger au besoin

- [Atelier des opérateurs](references/atelier.md) : exemples et fabrication
  d'une nouvelle transformation ; utile quand la recherche stagne.
- [Résultats expérimentaux](references/experiences.md) : deux constructions,
  leurs coûts et leurs limites. Ne présume pas qu'elles résolvent une autre tâche.

N'impose pas ce protocole entier à une question simple. Pour une tâche courte,
garde le contrat, une proposition et son test décisif.
