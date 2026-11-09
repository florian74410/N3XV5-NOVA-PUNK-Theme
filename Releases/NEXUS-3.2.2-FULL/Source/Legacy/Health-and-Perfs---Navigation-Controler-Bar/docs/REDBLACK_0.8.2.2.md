# NOVA / REDBLACK 0.8.2.2

Branche parallèle de refonte graphique complète `0.8.2.2REDBLACK`, base
fonctionnelle NovaBar 0.8.1 Linux polish, indépendante du projet de simple
recolorisation. **Le nom de la branche ne signifie pas que 0.8.2 existait déjà.**

## Interfaces redessinées

- **HUD** : cartes métalliques biseautées, cavités opaques pour les mesures,
  jauges rouges et pistes lumineuses animées. `HudCanvas.module_rect` est
  toujours la géométrie commune au rendu, clic sur plugin et drag/drop.
- **Holo** : nouveau cadre indépendant, zone des capteurs opaque et lisible,
  sections graphiques rouge/noir, nouveaux boutons Épingler/Fermer.
  Aucun changement aux sources réelles de puissance/tension.
- **Paramètres** : panneau chrome avec bords découpés, texture PCB,
  courant animé et menu latéral conservant toutes les pages et actions.
- **Docks** : habillage mécanique des conteneurs, boutons et tâches ;
  applications et dossiers réels, favoris et menus contextuels conservés.
- **Plugin Manager / NEXUS** : nouveau style sombre contrasté, contrôles
  d'origine reliés aux mêmes fonctions.
- **Icône NOVA** : variante rouge, palette XFCE native facultative et
  restauration sans supprimer le panneau existant.
- **Notification** : composant natif `NovaRedToast` utilisé pour confirmer
  l'activation via menu tray (ce n'est pas un remplacement des notifications système).
- **Fond d'écran** : image originale rouge/noire incluse, option facultative
  « Appliquer le fond REDBLACK » et « Restaurer le fond précédent » dans
  Paramètres → Thèmes & Couleurs, avec sauvegarde XFCE de chaque espace.

Tous les panneaux restent des widgets Qt/PySide6 natifs : aucune image
statique n'est utilisée pour simuler un bouton et aucun moteur de trading
ou collecteur de capteurs n'est remplacé.

## Assets et rendu

`src/healthbar/assets/redblack/` contient des calques SVG originaux
metalliques, tracés PCB, mailles et chevrons. L'image PCB rouge du pack
`blackred-studio` installé localement peut être composée dans les cadres
par le moteur de peinture. Les références contenant des filigranes
commerciaux ne sont **pas** redistribuées.

`redblack_shell.paint_surface` clippe chaque matériau et chaque reflet dans
le contour biseauté. L'intérieur des panneaux de lecture est délibérément
presque opaque pour rester lisible sur un bureau blanc.

Animations locales à cadence contrôlée : `HudCanvas` conserve son timer
existant, `Holo` conserve son cycle de lumière, les paramètres n'animent
leur cadre que lorsqu'ils sont visibles.

## Installation Linux (après succès CI)

```bash
gh run list --repo florian74410/Health-and-Perfs---Navigation-Controler-Bar --branch 0.8.2.2REDBLACK --limit 3
gh run download <RUN_ID_SUCCESS> \
  --repo florian74410/Health-and-Perfs---Navigation-Controler-Bar \
  --name NovaBar-0.8.2.2-REDBLACK-LINUX-QA -D "$HOME/NovaBar-RedBlack"
sudo apt install "$HOME/NovaBar-RedBlack/NovaBar_0.8.2.2_amd64.deb"
```

Toujours quitter **normalement** l'ancienne NovaBar avant de mettre à jour,
pour permettre la restauration du panneau XFCE. Ne pas supprimer
`~/.config/health-perfs-bar` : il contient les réglages et raccourcis.

Le nom Debian reste `novabar` : le paquet met à jour l'application
existante, sans duplicata. Pour revenir au thème d'origine, sélectionner
**Blue Neon** dans les paramètres ou le menu de la zone de notification.

## Qualité et limites

Tests unitaires existants + nouvelles assertions sur la géométrie,
transparence ARGB des quatre coins, palette, ressources et API Holo ;
exécution du runtime PyInstaller en mode `--self-test` avec vérification
de la version `0.8.2.2`. Les PNG générés par GitHub CI représentent des
**tests de dessin**, pas des captures d'un bureau XFCE réel.

Une validation manuelle sur XFCE/X11 reste indispensable : gestionnaire
de fenêtres, boutons natifs, chevauchement des barres, raccourcis,
retour du panneau XFCE et performances multi-écrans.
