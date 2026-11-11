# Mesurer le transfert vers Qwen 27B

**Statut : protocole préparé, aucun essai Qwen réalisé.** Les expériences de
`../experiments/` testent des constructions, pas un gain causal du skill.

## Comparaison proposée

Le script `prepare.py` génère quatre conditions pour les huit problèmes de
`cases.json` :

1. **direct** : une instruction de résolution courte.
2. **structured** : un contrôle fort demandant contrat, plusieurs solutions,
   comparaison, vérification et limites.
3. **skill** : le corps exact de `SKILL.md`, sans les exemples de référence.
4. **ablation** : le même skill sans le bloc séparant, fusionnant et neutralisant
   les distinctions. Les garde-fous de validation sont conservés.

Cette ablation retire une procédure détaillée, pas toute mention de ses
concepts : le reste du skill conserve quelques formulations apparentées. Un
effet ne pourrait pas être attribué à une opération isolée sans autre essai.

```bash
python evaluation/prepare.py --output /tmp/astra-qwen-evaluation
```

Les 32 requêtes sont écrites dans `prompts.jsonl`. Les critères de correction
sont exclus des messages. Le manifeste note les empreintes des entrées et ne
contient aucun résultat de modèle. Les références expérimentales ne sont pas
injectées, pour réduire l'imitation des exemples du développement.

## Conditions à enregistrer avant de lancer

Utiliser le même modèle exact dans chaque condition : identifiant complet,
révision des poids si disponible, quantification, moteur, gabarit de conversation
et mode de raisonnement. « Qwen 27B » seul n'identifie pas tout cela.

Garder le même accès aux outils, température, top-p, budget de sortie et budget
total de génération interne si le moteur l'expose. Une limite de mots dans un
prompt ne remplace pas la limite de tokens du moteur. Noter séparément tokens
d'entrée, tokens générés, latence et appels d'outils. Le skill coûte plus de
tokens d'entrée ; la comparaison n'est pas à coût total identique par défaut.

Faire au moins cinq répétitions par tâche et condition si les moyens le
permettent, soit 160 réponses. Randomiser leur ordre et isoler les contextes.
Une graine identique ne garantit pas le déterminisme d'un moteur distribué.
Ne pas retoucher le skill après lecture d'une partie des réponses puis agréger
les essais comme si la version était restée identique.

## Notation

Avant d'ouvrir les réponses, figer les critères dans [rubrics.md](rubrics.md).
Évaluer à l'aveugle de la condition autant que possible ; distinguer les réponses
par un identifiant aléatoire. Un second évaluateur est préférable pour les cas
où la qualité du mécanisme n'est pas entièrement automatique.

Pour chaque tâche, attribuer :

- **Correcte sous contrat :** oui/non/indéterminé ; un test promis n'est pas un
  test exécuté, et une hypothèse ajoutée doit être signalée.
- **Contraintes respectées :** oui/non ; une belle idée qui change la cible ne
  compte pas comme une solution du problème initial.
- **Mécanisme :** 0 = slogan, 1 = incomplet, 2 = exécutable ou dérivable.
- **Vérification :** 0 = affirmation, 1 = exemple limité, 2 = preuve ou essai
  discriminant approprié avec sa portée.
- **Coût et domaine :** 0 = omis, 1 = partiels, 2 = explicites et pertinents.

La nouveauté est un axe séparé : méthode connue, combinaison distincte des
références, ou antériorité inconnue. Ne pas inventer une note d'originalité
mondiale. Ne pas récompenser le changement de vocabulaire.

Rapporter d'abord le taux de solutions correctes respectant le contrat, puis
les critères secondaires et les coûts, sans additionner tout dans un score
arbitraire. Inclure les échecs, abstentions justifiées et sorties tronquées.
Analyser les écarts par tâche ; les répétitions d'un même problème ne sont pas
des problèmes indépendants. Avec huit tâches, la portée statistique reste faible.

## Ce qui pourrait invalider le skill

- Il augmente surtout la longueur sans améliorer les solutions correctes.
- Il invente des impossibilités à cause d'observations artificiellement limitées.
- Il applique les exemples du capteur à un modèle physique différent.
- Il surconçoit les cas où une solution connue est déjà optimale.
- Il déplace le coût hors de la métrique affichée ou modifie la cible.

Les tâches T07 et T08 sont des contrôles contre l'invention forcée. Un résultat
positif sur ce petit lot justifierait une seconde évaluation avec de nouveaux
problèmes fournis par une autre personne. Ce lot est une sonde de transfert,
pas un benchmark indépendant : il a été écrit après la conception du skill.
