# Une méthode d'invention à transmettre à Qwen 27B

Le livrable est [SKILL.md](SKILL.md) : un protocole compact pour concevoir une
technique, identifier ce qui la rend utile et essayer de la réfuter. Il est
rédigé en français, utilisable dans un agent qui charge des skills ou comme
instruction de travail dans une conversation avec Qwen.

L'idée centrale est de **chercher la distinction qui manque**, puis de fabriquer
un moyen de l'obtenir, de la préserver ou de neutraliser ce qui la masque.
Chaque candidat doit conserver une garantie explicite et payer son coût réel.
Les opérateurs ne forment pas une liste fermée : le skill explique comment en
construire un nouveau à partir d'un échec.

## Trois résultats de cette session

1. **Une construction vérifiée.** Sous un modèle explicite de dérive quadratique,
   six acquisitions avec une lecture adaptée supportent une perte identifiée
   sans augmenter la borne d'erreur due au bruit. La famille de référence à
   poids égaux en demande huit pour annuler la dérive sans perte.
2. **Une idée correcte qui ne gagne rien.** La minimisation d'une alarme réduit
   ses états, mais ne réduit pas les bits par flux pour le seuil demandé.
3. **Une correction de la méthode de vérification.** Le premier modèle imposait
   une sortie consultable à tout moment. Il ne certifiait pas l'interface moins
   exigeante où la sortie est produite à chaque entrée. Ce décalage a été corrigé
   et transformé en garde-fou dans le skill.

Les constructions, conditions et contre-exemples sont dans
[le rapport expérimental](references/experiences.md). Les opérations générales
sont décrites dans [l'atelier](references/atelier.md).

## Utilisation avec Qwen

- **Agent avec prise en charge des skills :** fournir ce dossier en conservant
  `SKILL.md` à sa racine. Activer le skill pour une tâche de conception.
- **Interface de conversation :** coller le corps de `SKILL.md`, sans son en-tête
  YAML, avant le problème. Les fichiers de référence sont facultatifs ; coller
  seulement les passages pertinents si l'interface ne sait pas les lire.
- **Budget court :** demander une proposition et son test décisif. Le skill
  prévoit au plus trois candidats et deux réparations par défaut, paramètres à
  ajuster selon les résultats ; leur optimalité pour Qwen n'est pas établie.

Exemple de demande :

> Applique ce skill à ce problème : [description]. Les contraintes obligatoires
> sont [contraintes]. Le progrès recherché est [mesure]. Les moyens disponibles
> sont [outils, informations, interventions]. Donne la proposition, sa
> justification vérifiable, son coût et sa condition de rupture.

Le skill n'exige ni une API spécifique, ni une syntaxe de raisonnement propre à
une version de Qwen. Employer le modèle et son gabarit de conversation habituels.
Il organise le travail ; il ne transfère pas les poids ou les connaissances
d'un autre modèle.

## Vérifier et évaluer

Python 3.10 ou plus récent suffit ; aucun paquet à installer, aucun service à
démarrer. Vérifié dans cette session avec Python 3.12.14.

```bash
python experiments/verify.py --output /tmp/astra-invention-results.json
python evaluation/prepare.py --output /tmp/astra-qwen-evaluation
```

La première commande reproduit les vérifications mathématiques. La seconde
prépare les requêtes pour une comparaison sur huit tâches, sans appeler de
modèle ni transmettre de données. Le [protocole d'évaluation](evaluation/PROTOCOL.md)
décrit les contrôles et la notation.

**État du transfert :** skill rédigé, constructions vérifiées localement,
évaluation sur Qwen non exécutée. Aucun résultat d'amélioration de Qwen n'est
revendiqué. Le modèle exact et un accès à son exécution restent nécessaires pour
mesurer ce gain.

Cette recherche porte sur des procédures observables de génération et de
vérification. Elle ne donne pas accès aux mécanismes internes du modèle. Les
outils mathématiques employés sont connus ; l'antériorité de la combinaison
proposée n'a pas été recherchée systématiquement.
