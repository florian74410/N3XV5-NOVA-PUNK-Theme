# N3XV5 / HUD HomeNavBar — Slim Neon v1 (prévalidation)

**Objectif :** alléger la Navbar Bottom originale NovaBar 0.8.2.2 sans réécrire son fonctionnement.

## Modifications

- Châssis Qt `CockpitFrame` : bordure ~0,95 px, seconde ligne atténuée, fond Carbone/Bleu Nuit semi-transparent.
- Compartiments favoris et zone système : cadres discrets, sans double halo métallique.
- Rails PCB à faible densité, impulsion lumineuse cyan lente et accents Rouge Sang ponctuels.
- Bordures des fenêtres applicatives réduites via la fonction `glow()`.
- Hauteur 70 px par défaut (modifiable entre 62 et 94), opacité 46 % (15 à 85), boutons et espacements affinés.
- Paramètres via l'icône engrenage de la Navbar. Sauvegarde indépendante dans `~/.config/n3xvs-bottom/appearance.json`.

## Fonctions conservées

Le code natif original `BottomDock` demeure responsable du menu Linux Mint, favoris, applications ouvertes, système/tray, réseau, son, batterie, notification, horloge et accès aux paramètres. Les animations des icônes au survol restent activées. **Aucun HTML ou QtWebEngine.**

## Installer depuis GitHub sans écraser les fichiers locaux

```bash
curl -fL https://raw.githubusercontent.com/florian74410/N3XV5-NOVA-PUNK-Theme/work/n3xvs-bottom-slim-neon-v1/App/Modules/Bottom/HUD_HomeNavBar/install_slim_navbar.sh -o /tmp/n3xvs-install-bottom.sh
bash /tmp/n3xvs-install-bottom.sh
```

Le script utilise le dépôt `~/N3XV5-HUD-Theme-1.0`, récupère la branche de test par `git fetch` **sans changer ta branche locale** et copie les deux fichiers dans le runtime `~/N3XV5-NATIVE-V2`. Il ne supprime pas `start_navbar_bottom.sh`.

```bash
bash ~/N3XV5-NATIVE-V2/App/Modules/Bottom/HUD_HomeNavBar/start_slim_navbar.sh
```

Avant de lancer la nouvelle Navbar, fermer l'ancien dock pour éviter deux instances. Le lanceur utilise `wmctrl` s'il est installé pour demander la fermeture de la fenêtre historique par son titre exact.

## Retour arrière

Fermer N3XV5 Navbar Slim, puis relancer l'ancien `~/N3XV5-NATIVE-V2/start_navbar_bottom.sh`. Aucune configuration d'origine n'a été modifiée.

**Validation :** préversion à contrôler sur XFCE/X11. Aucun déplacement dans `Linux/STABLE_BUILD` sans essai réel.
