# NovaBar 0.6.11 — Cockpit inférieur et NEXUS

La barre inférieure adopte une coque métallique à plusieurs niveaux, des compartiments biseautés, des rails lumineux et des circuits. Elle conserve les couleurs du thème et passe à une hauteur adaptée à de grandes icônes (88 px au réglage par défaut, au lieu de 49 px).

## Applications et fenêtres

- Quatre grands lanceurs visibles, avec conservation de la liste complète des favoris dans NEXUS.
- Icônes natives du thème et icônes réelles EWMH des fenêtres ; pack SVG Papirus en secours quand le thème est absent. Licence et sources dans `src/healthbar/assets/icons/`.
- Fenêtres ouvertes sous forme de boutons lisibles, avec icône, titre tronqué proprement et mise en évidence de la fenêtre active. Cliquer active/réduit ; clic droit permet de fermer.
- NEXUS est une vraie fenêtre de lancement : catégories, favoris, recherche par nom/mots-clés, grille d’icônes de 44 px et listes défilantes. Les règles XDG Hidden/NoDisplay, OnlyShowIn/NotShowIn, TryExec et les remplacements utilisateur sont respectés.

## Zone système fonctionnelle

- Indicateurs Wi-Fi/Ethernet, volume/muet, Bluetooth et batterie/secteur fondés sur les données du système. Aucune valeur fictive quand une mesure est indisponible.
- Volume réglable via un curseur, bouton muet, accès aux connexions, aux notifications, à l’alimentation et au verrouillage.
- Icônes **StatusNotifier/AppIndicator**, avec activation, clic droit et menus DBusMenu. Le watcher XFCE existant reste propriétaire ; NovaBar agit comme hôte supplémentaire, ou crée un watcher si aucun n’existe.
- Icônes **XApp de Linux Mint** découvertes via ObjectManager, avec transmission des clics gauche/droit et de la position du panneau. Les menus XApp ouverts empêchent la rétractation.
- Icônes supplémentaires dans un menu de débordement ; les indicateurs intégrés s’effacent quand un applet équivalent est présent.
- Les anciennes applications utilisant exclusivement XEmbed ne sont pas déplacées. L’accès temporaire à leurs icônes XFCE reste disponible dans le menu système de l’horloge.

## Mise à jour

Le système Upgrade de la 0.6.10 est conservé : **Paramètres → Upgrade** télécharge, vérifie, teste, active puis relance la nouvelle version. Profils, thèmes, plugins, favoris et réglages d’autostart restent conservés. Aucun changement au moteur de mise à jour dans cette refonte.

## Validation et visuels

Tests Qt de la grille/catégories/recherche, des grandes icônes, du rendu des thèmes, de l’ARGB des icônes et des mesures système. La CI Linux teste aussi une vraie session D-Bus (SNI, DBusMenu, XApp) et la restauration du panneau XFCE après fermeture/arrêt brutal. Les quatre builds natifs et leurs paquets passent avant publication.

Les trois aperçus dans Assets sont rendus avec les widgets Qt livrés et des données de démonstration explicites ; ce ne sont pas des captures de bureau ni une maquette d’image substituée à l’application.
