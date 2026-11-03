# Bibliothèque d'assets — N3XV5

## Politique de récupération
- Inventorier chaque asset 0.1 → 1.0 (branches, dépôts, archives .deb, .zip et planches).
- Originals/ : copies binaires intactes, version et dépôt de provenance.
- Sheets/ : planches intégrales inchangées.
- Extracted/ : sprites séparés de chaque planche, individuellement nommés.
- Transparent/ : copies RGBA avec fond périphérique transparent.
- Manifests/ : hash SHA-256, origine, dimensions, découpage, doublons.
- Ne jamais écraser une source ; le fond blanc n'est rendu transparent que lorsqu'il touche le bord pour préserver le blanc interne.
- Les captures d'écran ne sont pas des planches de sprites.
- Respecter licences et exclure secrets et données privées.

## État
Le fichier legacy-main-inventory.json est uniquement le recensement des médias de la branche main de l'ancien dépôt ; ces ressources ne sont pas encore copiées. D'autres branches et archives locales sont nécessaires pour l'exhaustivité.

## Livraisons
Aucune archive non testée ne va dans Linux/STABLE_BUILD ou Linux/STABLE_UPDATE.
