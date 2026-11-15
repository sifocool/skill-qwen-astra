---
name: fuzz-crash-triage
description: >
  Concevoir un harness de fuzzing, lancer une campagne bornée sur banc local,
  reproduire, minimiser et dédupliquer les crashes, hangs et erreurs sanitizer.
  À charger pour fuzzing, corpus, coverage ou crash triage ; pour une erreur de
  test classique sans entrées mutées, préférer error-triage.
---

# Fuzz + crash triage — des octets à la cause

Livrer un harness reproductible et des défauts distincts prouvés, pas un nombre
brut de fichiers crash. Ne jamais lancer un crash inconnu par double-clic ou
dans un processus qui possède des credentials de production.

## Choisir une cible utile

Définir l'entrée réellement contrôlable et l'oracle : exception inattendue,
sanitizer, violation d'invariant, divergence différentielle, timeout ou mémoire.
Un rejet documenté du parseur n'est pas un bug. Une divergence entre parseurs
nécessite un contrat de référence pour décider lequel a tort.

Lire l'API du parseur avant d'écrire le harness. Invoquer son chemin réel avec
le minimum d'I/O ; réinitialiser l'état entre entrées ; garder les allocations
et conversions du harness visibles dans le diagnostic. Si un processus long
est instable, comparer avec un processus neuf par entrée.

Choisir le moteur déjà supporté par le projet : libFuzzer/AFL++ pour du natif
instrumentable, moteur adapté au runtime sinon. Vérifier ses options sur la
version installée. Ne pas copier des flags supposés compatibles.

## Campagne bornée

Écrire avant le lancement : hash du binaire, commit, compilateur/runtime,
instrumentation, commande, seed, corpus initial, timeout par entrée, mémoire,
nombre de workers et durée. Par défaut commencer par un smoke test de 60 s
avec un worker ; étendre seulement selon les ressources et le périmètre fixés.

- Corpus petit mais varié : objets valides minimaux, limites, états différents.
  Conserver les seeds originaux et la provenance des ajouts.
- Vérifier qu'au moins une entrée atteint le code cible et que les rejets
  attendus restent distincts des erreurs du harness.
- Utiliser des builds de diagnostic séparés selon les sanitizers supportés.
  Une instrumentation absente interdit de conclure à l'absence de ce défaut.
- Surveiller couverture, exec/s, mémoire et nouvelles entrées intéressantes.
  Un plateau peut être un mauvais harness, une comparaison magique ou un état
  inaccessible ; ne pas prolonger aveuglément.
- Isoler fichiers, comptes et réseau du processus testé. Pour un protocole,
  utiliser un service local jetable et remettre son état à zéro.

## Triage dans cet ordre

1. **Préserver** l'entrée originale et les logs, puis calculer leurs hashes.
2. **Rejouer** avec le même binaire/configuration ; mesurer `k reproductions/N`.
   Un hang ou OOM exige une limite identique et un témoin pour le coût normal.
3. **Symboliser** avec les symboles du bon build. Séparer bug cible, harness,
   instrumentation et épuisement de ressources du banc.
4. **Regrouper provisoirement** par type d'erreur, opération et premières
   frames applicatives normalisées (module + fonction + offset relatif).
   Les adresses ASLR et la frame générique `abort` ne sont pas une identité.
5. **Minimiser une copie** avec un prédicat qui préserve le même défaut,
   pas simplement « exit non nul ». Rejouer original et réduit après réduction.
6. **Expliquer** la première violation et le flot de données ; une même pile
   peut masquer plusieurs causes et une cause produire plusieurs piles.
7. **Corriger et verrouiller**, si demandé, avec un test déterministe du cas
   réduit et un témoin valide ; rejouer les autres groupes affectés.

## Livraison

Une fiche par cause : identifiant, hash original/réduit, environnement,
reproduction exacte, fréquence, diagnostic, impact démontré, limites et état
du fix. Distinguer crash, écriture/lecture hors limites et exploitabilité :
aucune ne prouve automatiquement la suivante. Un résultat sans crash est
« aucun crash observé dans ce budget », avec couverture et durée.

Le [journal réseau](../../network_hooks/network-journal.md) accompagne les acquisitions
de corpus et dépendances. Il ne mesure ni la couverture ni le trafic caché
dans le programme fuzzé.

## Moteur partagé V2

Pour une investigation multi-méthodes, charge `cyber-investigator` et utilise
[son contrat exécutable](../cyber-investigator/references/engine.md).
Adaptateurs de cette compétence : replay, fuzz, minimize, sanitizer.
Transmets les identifiants E… et hashes des preuves, ainsi que les hypothèses
encore ouvertes. Une preuve périmée ou une analyse statique candidate ne suffit
pas à confirmer une conclusion. Le sélecteur propose la compétence complémentaire.
