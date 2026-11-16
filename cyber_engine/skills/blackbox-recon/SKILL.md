---
name: blackbox-recon
description: >
  Cartographier une application, API ou un service en boîte noire à partir de
  comportements observés, sans code source. À charger pour recon blackbox,
  découverte de surface exposée, fingerprinting ou cartographie de rôles et
  endpoints. Pour auditer du code disponible, préférer security-audit.
---

# Blackbox recon — une carte vérifiable

Produire une carte des entrées, identités, états et frontières de confiance,
avec des observations rejouables. Un nom de produit ou une bannière ne prouve
ni une version exacte ni une vulnérabilité.

## Départ

Reprendre le périmètre déjà donné : hôtes, ports, comptes de test, environnement,
exclusions et limite de trafic. Une URL découverte, une redirection, un domaine
tiers ou une IP de CDN ne deviennent pas automatiquement des cibles autorisées.
Si la cible manque, exploiter les HAR, captures et documents fournis, puis
demander seulement la donnée nécessaire aux sondes actives.

Dans le dossier de preuves de la mission, noter la cible, l'heure UTC, l'identité
de test et les plafonds. À défaut de budget spécifique : une requête à la fois,
au plus une par seconde, 100 requêtes par lot, timeout explicite. Arrêter le lot
sur 429, blocages répétés ou dégradation observable ; conserver le point d'arrêt.

## Explorer par hypothèses

1. Partir du parcours normal : page d'entrée, navigation, documentation exposée,
   endpoints réellement appelés, formulaires, téléchargements, websocket.
   Lire les assets déjà référencés avant d'inventer des chemins.
2. Relever méthode, chemin normalisé, paramètres et types, authentification,
   rôle, statut, redirections, format et taille de réponse. Comparer une route
   inexistante pour identifier soft-404, pages SPA et réponses génériques WAF.
3. Séparer les surfaces : public, connecté, privilégié, fichiers publics,
   services et protocoles explicitement inclus. DNS/TLS/ports sont des indices,
   pas des raisons de lancer un balayage de plage.
4. Faire varier une dimension par essai : présence du jeton, rôle de test,
   objet appartenant à un autre compte de test, méthode, type de contenu,
   champ absent ou valeur limite. Éviter de modifier des objets réels.
5. Associer à chaque anomalie un contrôle normal, une explication concurrente
   et le prochain essai qui les départage. Distinguer cache, session expirée,
   traitement asynchrone et contrôle serveur.

Un test d'écriture ou une validation intrusive se fait sur un banc isolé adapté
au périmètre. Ne pas transformer une simple découverte en collecte massive,
devinette de mots de passe ou test de charge.

## Preuves et journal

Conserver les requêtes minimales rejouables et les extraits de réponses utiles,
en remplaçant les secrets par des variables. Garder séparés faits observés,
inférences et hypothèses. Pour chaque constat : préconditions, témoin, essai,
résultat attendu/observé et limite de la preuve.

Conserver les preuves HTTP utiles dans le dossier privé de mission.

## Livraison

- Carte `méthode | entrée | identité | paramètres | résultat | preuve`.
- Anomalies classées `OBSERVÉ`, `À CONFIRMER`, `ÉCARTÉ` avec justification.
- Surfaces non explorées et budget consommé.
- Trois prochaines vérifications au maximum, choisies pour réduire une
  incertitude concrète. Ne pas annoncer « aucun risque » après une recon.

## Moteur partagé V2

Pour une investigation multi-méthodes, charge `cyber-investigator` et utilise
[son contrat exécutable](../cyber-investigator/references/engine.md).
Adaptateurs de cette compétence : http_probe, protocol.
Transmets les identifiants E… et hashes des preuves, ainsi que les hypothèses
encore ouvertes. Une preuve périmée ou une analyse statique candidate ne suffit
pas à confirmer une conclusion. Le sélecteur propose la compétence complémentaire.
