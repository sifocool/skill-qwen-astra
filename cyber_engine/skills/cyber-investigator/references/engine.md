# Contrat exécutable

Dans le dépôt : `python3 -m cyber_engine --state .astra/state ACTION 'JSON'`.
Dans le profil installé : `python3 "$CLAUDE_CONFIG_DIR/astra-runtime/run.py" --state .astra/state ACTION 'JSON'`.
Les chemins d'artefacts sont relatifs à la première racine autorisée. Ne mets pas
de credentials dans les arguments ; le dossier `.astra` est privé et hors Git.

Initialiser avec l'autorisation réelle, les racines explicites, les seuls adaptateurs
nécessaires et un budget. `trusted_lab:true` autorise l'exécution de fixtures que tu
contrôles ; cela ne crée pas un bac à sable. Pour un artefact hostile, préparer un
confinement OS séparé avant toute exécution.

```json
{"scope":{"authorization":"mission utilisateur, banc local de ce projet","roots":["/absolute/project"],"adapters":["python_ast","semantic_diff","replay","compare"],"trusted_lab":true,"origins":[]},"question":"Quel invariant est violé ?","max_experiments":20}
```

Actions et paramètres :

| Action | JSON |
|---|---|
| `observe` | `{"note":"fait observé ou indice","locations":[{"path":"parser.py","start":5,"end":8}]}` |
| `hypothesis` | `{"claim":"explication testable","prior":1}` → H1, H2… |
| `plan` | `{"adapter":"replay","args":{"script":"harness.py","input":"x"},"predictions":{"H1":"crash","H2":"clean"},"purpose":"distinguer parser et transport","cost":1,"kind":"discriminate"}` |
| `select` | `{}` → compétence, expérience, score et raison, ou arrêt |
| `run-next` | `{}` → sélection et preuve exécutée |
| `run` | `{"eid":"E1","repeat":true}` → reproduction explicite |
| `reject` | `{"hid":"H2","eid":"E1"}` → exige un résultat contraire à la prédiction |
| `challenge` | `{"rival":"le harness échoue aussi sur le témoin","test":"E2","resolution":"témoin accepté"}` |
| `gate` | `{"hid":"H1","fix":false}` → obligations restantes |
| `conclude` | `{"hid":"H1","statement":"conclusion bornée","fix":false}` |
| `stop` | `{"reason":"pas de test discriminant disponible","uncertainties":["…"]}` |
| `knowledge` | `{}` → découverte validée localement, avec provenance |
| `status` | `{}` → dossier commun |

`kind` vaut discriminate, control, regression ou explore. Une expérience contrôle
est un autre test, pas la répétition du premier. Les prédictions portent sur le
champ `label` des adaptateurs. Elles doivent être écrites avant l'exécution.
Une observation libre n'est jamais une preuve exécutée.

Adaptateurs :

- `python_ast`, `dependencies`, `binary` : `{"path":"…"}`. AST Python seulement,
  flux conservatifs, aucune conclusion automatique de vulnérabilité.
- `semantic_diff` : `{"before":"old.py","after":"new.py"}`. Diff AST structurel.
- `replay` : `{"script":"harness.py","input":"…","timeout":3}`. stdin UTF-8,
  processus neuf. JSON stdout avec `label` facultatif, sinon clean/crash/timeout.
- `compare` : before, after, input, control, expected_after (défaut clean).
- `fuzz` : script, seeds (liste de textes), seed, iterations (1–256), alphabet.
  Mutations de texte déterministes ; pas de mesure de couverture native.
- `minimize` : script, input ; conservation d'une signature d'exception provisoire.
- `sanitizer` : path (C), input ; compilation Clang ASan+UBSan et exécution bornée.
- `deserialize_trace` : script, input ; profilage des fonctions du harness inoffensif.
- `protocol` : script, traces `[ {"role":"guest","steps":[…],"expected":[…]} ]`.
  Le harness reçoit les steps JSON, renvoie la suite des résultats JSON.
- `http_probe` : url, origine explicitement autorisée ; GET borné sans redirection.
- `ghidra`, `radare2` : path ; aucun succès si l'outil ou son analyse manque.

Le moteur vérifie les preuves, les entrées et la cohérence structurelle ; l'agent
reste responsable de la pertinence du contrat, des prédictions et du contrôle.
Les hooks ne transforment pas une assertion arbitraire en théorème.
