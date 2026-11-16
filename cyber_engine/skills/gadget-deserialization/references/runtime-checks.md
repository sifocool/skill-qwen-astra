# Repères par runtime

Consulter uniquement la famille détectée. Les noms ci-dessous sont des pistes
de recherche ; confirmer leur présence et leur comportement dans la version
installée et dans sa documentation officielle avant de conclure.

| Famille | Ce qu'il faut vérifier dans la cible |
|---|---|
| Java | `ObjectInputStream`, résolution de classes, `readObject`/`readResolve`/`readExternal`, filtres effectifs du JDK et filtres par flux, classpath réel. Les constructeurs ordinaires et ceux des classes non sérialisables n'ont pas les mêmes règles. |
| PHP | `unserialize`, `allowed_classes`, `__unserialize`/`__wakeup`, autoload et `__destruct`. Le comportement des métadonnées PHAR dépend de la version et de l'API appelée : ne pas extrapoler une ancienne chaîne. |
| Python | `pickle` et dérivés, reducers, `__reduce__`/`__setstate__`, globals résolus. Un `pickle` n'est pas un format de données sûr pour des octets non fiables ; l'inspection d'opcodes ne prouve pas son innocuité. |
| .NET | Serializer réellement utilisé, résolution de types, binders/converters, callbacks et options de polymorphisme. Ne pas confondre comportement d'un ancien framework et limitations d'un runtime récent. |
| JSON/YAML avec types | Activation effective des tags, constructors, polymorphisme ou métadonnées de type. Un parseur JSON qui rend seulement des données primitives n'implique pas de gadgets. Distinguer parsing, fusion d'objet et usage ultérieur. |
| Node/JavaScript | Fonction de reconstruction réelle, reviveurs, résolution de modules, propriétés héritées, fusion d'objets puis sink. La pollution de prototype et la désérialisation sont des mécanismes distincts, même s'ils se composent. |

Pour toute famille, une bibliothèque absente du chemin chargé, un type filtré
avant instanciation ou un callback jamais invoqué casse la chaîne considérée.
Rapporter ces preuves négatives avec le build concerné, sans les généraliser à
toutes les configurations.
