# Protocole exploratoire — 11 novembre 2026

Ces expériences testent des mécanismes proposés pendant cette session. Elles ne
mesurent ni les mécanismes internes du modèle, ni le gain causal du futur skill,
ni l'originalité dans la littérature. Problèmes, générateur et vérificateur sont
construits ici : il ne s'agit pas d'une évaluation indépendante.

## A. Alarme en flux

Entrées binaires. Après chaque entrée, signaler si au moins trois des cinq
dernières entrées valent 1. L'historique initial contient cinq zéros.

- Référence correcte : conserver les cinq bits, soit 32 états possibles.
- Proposition à réfuter : conserver seulement leur somme courante.
- Construction : distinguer les historiques lorsque leur sortie présente ou
  leur réponse à une continuation diffère ; fusionner les autres.
- Validation : vérifier toutes les sorties et transitions du quotient ; chercher
  une continuation distinguant chaque paire de ses états. Ces propriétés,
  avec l'état initial, établissent la correction pour toute longueur de flux.
- Coûts : nombre d'états, bits par flux, taille d'une table générique. Réduire le
  nombre d'états n'établit pas une réduction de la mémoire totale du programme.

### Amendement après examen du premier résultat

Le premier constructeur a utilisé un automate de Moore : la sortie doit être
recalculable depuis l'état seul, à tout moment. Cette exigence est plus forte
que « produire une sortie à chaque entrée », qui autorise un automate de Mealy.
La minimalité obtenue ne pouvait donc pas être attribuée au contrat initial.
On conserve le résultat Moore avec sa portée exacte, et on ajoute une vérification
Mealy dont la référence conserve seulement les quatre entrées précédentes.
Une variante au seuil 2 est examinée séparément ; elle ne remplace pas le seuil 3.

## B. Capteur avec dérive et perte d'une mesure

À l'instant entier t, on choisit x[t] dans {-1,+1} et on observe :

    y[t] = a*x[t] + b0 + b1*t + b2*t² + e[t]

On veut estimer a. La dérive quadratique est inconnue ; |e[t]| <= epsilon.
La réponse a est constante et instantanée. Le contrôle x est supposé exact,
sans saturation, coût de commutation ni hystérésis. Les mesures manquantes
sont identifiées, avec leurs horodatages conservés.

- Référence : moyenne signée à poids égaux. Chercher la plus courte séquence
  qui annule les trois moments de la dérive, sans perte de mesure.
- Proposition : autoriser des poids différents, calculés avec les horodatages
  et les positions perdues, indépendamment des valeurs mesurées.
- Garantie visée : estimateur linéaire exact sans bruit, avec erreur <= epsilon
  même si une mesure quelconque manque. Cette garantie exige une norme L1 des
  poids <= 1 ; elle est optimale puisque sum(w[t]*x[t]) = 1.
- Recherche : énumérer les signes et résoudre exactement les sous-systèmes à
  quatre mesures, puis minimiser la norme L1 dans chaque cas de perte.
- Comparaison : nombres de mesures et amplification du bruit. Ne pas confondre
  bruit borné et variance d'un bruit aléatoire indépendant.
- Réfutations : tester des poids figés après perte et une dérive cubique.

Pour la minimisation L1 à quatre égalités indépendantes, il existe un optimum
avec au plus quatre coefficients non nuls (programme linéaire en parties
positives et négatives). L'énumération des bases est donc suffisante quand la
matrice des contraintes a rang quatre. Vérifier ce rang ou expliquer les cas
singuliers avant de conclure à une impossibilité.

## Transfert

Le succès d'une construction ne prouve pas que le protocole améliore Qwen 27B.
Une comparaison avec/sans skill, à modèle et budgets contrôlés, sera définie
séparément. Aucun résultat Qwen ne doit être inventé.
