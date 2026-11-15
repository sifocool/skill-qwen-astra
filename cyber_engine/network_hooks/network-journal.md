# Journal réseau du profil Qwen / Claude Code

Le script `network_journal.py` reçoit les événements `PreToolUse`, `PostToolUse`
et `PostToolUseFailure` déclarés dans `config/settings.json`. Il utilise Python
standard, sans dépendance externe et sans requête réseau.

## Lecture et portée

Fichier actif : `$CLAUDE_CONFIG_DIR/logs/network/network.jsonl`.
Rotation à 5 Mio avec trois fichiers précédents `.1`, `.2`, `.3`, sous verrou
interprocessus. Dossier 0700, fichiers 0600. La rotation efface le plus ancien
segment ; copier les preuves nécessaires à la mission avant cette échéance.

Une ligne JSON par événement pertinent : heure UTC, événement, outil,
origines URL (schéma/hôte/port), indices de programme, empreintes de session,
appel et dossier, empreinte de commande shell, code de sortie et durée lorsque
ces valeurs structurées sont disponibles. Relier les événements par
`session_id_sha256` + `tool_use_id_sha256`, pas seulement par commande.

Le hook inspecte les commandes Bash/PowerShell contenant des outils réseau
connus ou URL, WebFetch/WebSearch, et les MCP dont le nom indique navigateur,
recherche ou réseau, ou dont l'entrée fournit une URL reconnue. Les résultats
et messages d'erreur ne sont pas sauvegardés ; seul un code de sortie numérique
peut être extrait. Headers, corps, query strings, fragments, chemins URL,
userinfo, prompts, recherches et commandes brutes ne sont pas journalisés.
Les noms d'hôtes restent visibles : ils peuvent eux-mêmes être sensibles.

`requested` = intention avant exécution, y compris si la permission est ensuite
refusée. `tool_returned` = l'outil a rendu un résultat, pas nécessairement un
succès HTTP. `tool_failed` = échec d'outil. Aucun statut HTTP n'est déduit d'un
code processus. Une intention sans événement final n'est pas un succès.

`network_observed: false` signifie **réseau non mesuré**, pas « aucun réseau ».
Il n'y a pas de capture de paquets : une URL dans un `echo` peut être relevée,
un script qui ouvre des sockets sans URL visible peut passer inaperçu. Les
hôtes fournis via variables, fichiers, alias SSH ou redirections ne sont pas
résolus. Les requêtes internes au navigateur, les processus détachés et les
appels au modèle Qwen/proxy ne sont pas couverts. Ne pas lire le transcript ou
activer des logs de corps pour compenser ces limites sans besoin explicite.

## Utilisation

Les quatre skills n'ont aucune commande spéciale à ajouter à leurs requêtes.
Vérifier `/hooks` dans le profil Qwen et rouvrir sa session si nécessaire après
installation. Les hooks existants de compactage restent enregistrés.

Pour vérifier le logger sans envoyer de requête réelle :

```sh
printf '%s\n' '{"hook_event_name":"PreToolUse","tool_name":"WebFetch","tool_use_id":"smoke-example","session_id":"smoke","tool_input":{"url":"https://example.invalid/test?token=FAUX"}}' | python3 $CLAUDE_CONFIG_DIR/hooks/network_journal.py --log-dir /tmp/qwen-network-journal-smoke
```

Les tests automatisés emploient des dossiers temporaires et ne contactent
aucune cible :

```sh
python3 $CLAUDE_CONFIG_DIR/hooks/tests/test_network_journal.py
```

Ce logger n'autorise, ne réécrit et ne bloque aucun appel d'outil. Une erreur
de journalisation produit un avertissement sans contenu sensible et un code
non bloquant. La couverture devient alors incomplète. Il ne remplace ni les
permissions, ni le confinement du banc, ni les preuves HTTP de la mission.

Pour le désactiver, retirer seulement les entrées qui appellent
`network_journal.py` des trois événements de `settings.json`. Ne pas supprimer
les autres hooks. Sauvegarde avant installation :
le dossier `backups/` du profil (voir le manifeste de chaque installation).

Contrat des événements : [documentation officielle Claude Code](https://code.claude.com/docs/en/hooks).
