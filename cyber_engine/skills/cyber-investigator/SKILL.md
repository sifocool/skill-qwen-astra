---
name: cyber-investigator
description: Orchestrer une investigation de cybersécurité autorisée avec blackbox-recon, patch-diffing, fuzz-crash-triage et gadget-deserialization, un registre de preuves commun, des expériences discriminantes et des contrôles de conclusion. Un seul agent principal ; activer pour une enquête technique, pas pour une simple définition.
---

# Investigation expérimentale partagée

Travaille comme un seul agent. Les compétences spécialisées lisent et enrichissent
la même investigation, sans sous-agents ni copies divergentes du dossier de preuve.

Commence par une observation et deux explications qui prédisent des résultats
différents. Choisis un essai petit qui tranche entre elles, puis un contrôle qui
pourrait invalider ton interprétation. Une répétition démontre la stabilité ; un
contrôle différent vérifie la causalité. Ne confonds pas les deux.

Utilise le moteur pour conserver les hypothèses, expériences et preuves. Dans un
banc qui expose des actions JSON, utilise ses actions ; dans Claude Code, consulte
[le contrat CLI](references/engine.md) pour initialiser `.astra/state` dans le
projet autorisé. Ne remplis jamais un résultat d'expérience à la main.

Le sélecteur classe les expériences selon la séparation attendue des hypothèses
par unité de coût. Ses poids sont des hypothèses de planification, pas des taux
de confiance mesurés. Des prédictions identiques ne justifient pas un nouveau test.
L'empreinte des entrées empêche de recycler une preuve après un changement.

Choisis la compétence à partir de l'incertitude :

| Incertitude à résoudre | Compétence | Expérience complémentaire |
|---|---|---|
| rôle, état, endpoint ou frontière inconnus | blackbox-recon | rejouer une transition avec un autre rôle de test |
| comportement modifié entre versions | patch-diffing | même entrée et témoin sur les deux versions |
| crash ou anomalie d'entrée | fuzz-crash-triage | minimiser puis comparer au contrôle valide |
| reconstruction de types ou callback implicite | gadget-deserialization | casser une précondition et tracer le marqueur |

Charge seulement la compétence courante. Les identifiants d'expérience et les
SHA-256 des preuves servent de relais entre compétences. Reprends les preuves
existantes avant d'explorer la même piste.

Quand une autre explication survit ou qu'une conclusion manque de preuve, applique
`avocat-du-diable` : vise la supposition la plus fragile, formule un rival précis,
et enregistre son contre-test. Exemple : un refus vient-il d'une session expirée
plutôt que de l'autorisation ? Un crash vient-il du harness plutôt que du parseur ?

Avant une conclusion confirmée, exige une expérience discriminante répétée,
un contrôle indépendant conforme et le rejet justifié des explications rivales.
Pour un correctif, ajoute un témoin valide identique avant/après ; rejeter toutes
les entrées n'est pas une correction. Les hooks contrôlent ces obligations, pas
la vérité sémantique d'une phrase libre.

Après trois actions sans observation nouvelle, réexamine les prédictions. S'il
n'existe plus de test justifié ou si le budget est épuisé, arrête en **PARTIAL**,
avec incertitudes et condition concrète de reprise. `PASS` reste limité au contrat
et aux entrées testées. Aucune amélioration du modèle n'est déduite de cette méthode.

Sur un programme court dont le code exprime entièrement le contrat, un cas limite
et un contrôle pertinent peuvent suffire à un verdict **clean borné**. Ne déroule
pas toutes les variantes d'un même contrôle si aucune hypothèse concurrente ne
prédit de différence. Réserve toujours le dernier tour à un verdict, même incertain.
