# Contre-revue du moteur et de la mesure

La thèse évaluée est « ce paquet aide Qwen à résoudre de nouvelles investigations ».
Le fait que les tests logiciels passent ne confirme pas cette thèse.

| Objection examinée | Preuve / conséquence |
|---|---|
| La sélection calcule-t-elle une valeur informative mesurée ? | Non : `Engine.select` emploie une partition de labels prédits et des coûts déclarés. Ce sont des hypothèses explicites ; le score ne représente pas une probabilité apprise. |
| Une preuve structurée garantit-elle la cause réelle ? | Non : les tests établissent une stabilité et un contrôle. La pertinence des prédictions et du témoin doit être revue ; deux labels d'un harness écrit par l'agent ne suffisent pas à prouver une vulnérabilité réelle. |
| Les adaptateurs sont-ils seulement détectés dans le PATH ? | Les tests exécutent AST, replay, fuzz, réduction, ASan/UBSan, traces, protocole, HTTP. Ghidra et radare2 ont des analyses réelles séparées et des rapports. Leur absence initiale n'a pas été présentée comme un succès. |
| L'environnement est-il un confinement pour programmes hostiles ? | Non : limites de processus et allowlists seulement. Les exécutions sont limitées aux fixtures contrôlées ; un environnement OS isolé est nécessaire pour des programmes hostiles. |
| L'agent sait-il réellement terminer sans bug ? | Le développement V1 a montré un échec. V2 réussit ce cas, mais les cas nouveaux révèlent encore des épuisements de budget. Ce n'est pas une généralisation validée. |
| Le juge de cause racine peut-il rejeter un bon diagnostic ? | Oui : L02 et L03 citent la condition fautive tandis que la ligne attendue est le point choisi pour la mutation. Le score strict est conservé ; l'audit sémantique est séparé et postérieur. |
| Un échec JSON est-il un échec de connaissance cybersécurité ? | Pas nécessairement. Certaines réponses décrivent la bonne cause puis ajoutent de la prose avant JSON ; le lecteur strict les refuse. Il s'agit d'une défaillance d'interface du système évalué, comptée dans la résolution, sans conclusion isolée sur les connaissances du modèle. |
| Vingt cas suffisent-ils pour déclarer un moteur expert ? | Non : cinq familles synthétiques, programmes courts, contrôles finis. Les motifs peuvent être connus du préentraînement. CyberGym est bloqué et les cas historiques sont connus/publics. |
| Les durées isolent-elles l'effet causal des skills ? | Non complètement : cache de préfixe et charge du serveur ne sont pas contrôlés. Les ordres sont alternés ; temps et tokens restent des observations descriptives. |
| Karvan apprend-il directement de nouvelles connaissances vérifiées ? | L'export prépare une candidature avec provenance et interface testée. Aucun registre actif ni poids n'est modifié ; une admission n'est pas une promotion à verified. |

Les défauts d'interface et la règle de notation devront être corrigés avant une
nouvelle étude sur de nouveaux problèmes. Retoucher ces paramètres puis rejouer
les mêmes vingt cas ne constituerait pas une validation indépendante.
