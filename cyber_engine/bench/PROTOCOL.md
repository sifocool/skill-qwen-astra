# Calibration préspécifiée

Objectif principal : différence appariée du nombre de diagnostics corrects,
avec reproduction indépendante des témoins. Aucun seuil de gain n'est supposé.
Un échec enhanced doit être compté même si la baseline réussit. Un résultat nul
ne constitue pas une amélioration. Les taux de réussite ne sont pas une mesure
générale de compétence cybersécurité.

Deux conditions : même modèle local annoncé `qwen3.8-27b`, température 0, mêmes
programmes, contrat et outils read/test/analyze. Huit réponses, 1000 tokens maximum
par génération, 120 s par requête, 600 s par tâche, arrêt à 50000 tokens rapportés
(entrée incluant cache + sortie). Un dernier appel peut atteindre le seuil ; ce
plafond est contrôlé entre appels, pas pendant le prefill. Aucune relance silencieuse.

Baseline : instructions d'interface uniquement. Enhanced : mêmes instructions,
orchestrateur et skill de domaine chargé selon la famille, registre Engine,
hooks avant/après actions et contrôles de conclusion. Les quatre skills sont
disponibles dans le système, avec chargement progressif de celui pertinent.
Cette comparaison porte sur le paquet complet, pas sur l'effet isolé d'un hook.

Chaque condition/tâche a une conversation API neuve et un dossier éphémère neuf.
L'agent ne peut lire que subject.py, ni l'oracle ni les solutions ni les résultats
d'autres sessions. Le script ne transmet jamais les métadonnées de mutation.
Les poids restent gelés du point de vue du client ; leur hash n'est pas exposé
par le serveur. Le cache de préfixe peut affecter le temps, sans transmettre de
messages entre conversations. Ordre alterné baseline/enhanced selon le cas.

Quatre cas de développement distincts permettent d'améliorer la procédure.
V1 : enhanced épuise ses tours sur un contrôle négatif. V2 : réserve explicite
pour le verdict et arrêt de contrôles redondants ; aucun témoin/solution transmis.
Le rappel du nombre de tours restants est ajouté aux deux conditions.
La version doit être commitée avant les vingt cas d'évaluation L01–L20.

Les vingt cas sont nouvellement écrits pour cette mission, dans cinq familles
(autorisation, bornes, normalisation, états, désérialisation) : 15 défauts et
5 contrôles négatifs. Ils ne sont pas vingt CVE ni vingt familles indépendantes.
Il est impossible de garantir que leurs motifs génériques sont absents du
préentraînement. Les bugs historiques servent de calibration séparée ; ils ne
sont pas présentés comme inconnus du modèle.

## Juge et métriques

Un diagnostic bug exige un témoin qui diverge du contrat, trois rejouages stables,
un contrôle différent conforme et la ligne responsable. Le texte causal est
conservé pour audit : le juge automatique vérifie la ligne et une explication
non vide, pas la vérité sémantique de chaque mot. La métrique « cause confirmée »
est donc une approximation opérationnelle à auditer, non un score de juge LLM.
Un diagnostic clean est contrôlé sur un domaine fini préspécifié, rejoué trois
fois ; il ne prouve pas une absence universelle de bugs.

Les résultats enregistrent correct/incorrect, faux positif, cause localisée et
reproduite, stabilité, interventions humaines pendant le solve (0 en exécution
automatique), tokens d'entrée/sortie, durée, tours et échecs d'API. Les décisions de
conception du benchmark par Astra ne sont pas comptées comme interventions dans
une session Qwen. Les résultats par problème permettent de recalculer les totaux.

Les erreurs d'environnement et absences de verdict restent des échecs de résolution.
Les preuves privées comprennent les actions textuelles et sorties d'outils, jamais
les blocs internes `thinking` renvoyés par le modèle. Les données publiées sont
filtrées à partir de ces artefacts ; les états réels du profil ne sont pas copiés.

CyberGym exige ici Docker et ses données non installées : **BLOCKED**, sans score.
Voir [l'installation officielle](https://github.com/sunblaze-ucb/cybergym#installation).
Les tâches locales ne sont pas renommées CyberGym pour contourner cette limite.
