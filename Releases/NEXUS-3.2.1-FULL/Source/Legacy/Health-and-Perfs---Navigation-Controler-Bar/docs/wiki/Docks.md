> **0.6.11 :** barre de 88 px au réglage par défaut, grandes icônes, fenêtres avec titres et coques biseautées. NEXUS propose catégories, favoris, recherche et grille de 44 px. Les indicateurs réseau/volume/Bluetooth/batterie sont réels ; les icônes StatusNotifier et XApp sont affichées avec leurs menus. [Détails et limites](../UPDATE_V0611.md).

# Les quatre surfaces NovaBar — 0.6.11

- HUD de performances : CPU, GPU, RAM, SSD, ventilateurs, réseau et Holo.
- Dock Dossiers : répertoires personnels XDG, favoris et Récents.
- Dock Applications : raccourcis locaux `.desktop` valides, réorganisables.
- Barre inférieure Linux/X11 : menu d’applications avec recherche, lanceurs XFCE, fenêtres ouvertes, horloge, préférences et commandes système.

## Bords invisibles

Les deux colonnes se replient complètement : aucun trait bleu et aucune languette. Approcher le pointeur à **moins de 10 pixels du bord de l’écran** révèle le module correspondant. Il reste ouvert au survol et se referme **3 secondes après la sortie**. La zone surveillée se situe entre le HUD supérieur et la barre inférieure lorsqu’ils sont actifs. Les clics passent aux applications quand la colonne est cachée.

Dans **Préférences → Docks**, chaque surface peut être activée séparément. Les dossiers et applications peuvent échanger de côté via ↔ ou la poignée. Glisser-déposer, réorganisation et listes personnelles restent conservés. Retirer un raccourci ne supprime pas sa cible. Les applications sont lancées par GIO, sans interprétation de leur chemin par un shell.

## Barre inférieure

Le bouton **NEXUS** ouvre les applications installées avec recherche. Cliquer une fenêtre l’active ; cliquer la fenêtre déjà active la réduit. Clic droit : activer ou demander sa fermeture. Le menu **Système** ouvre les outils réseau, volume, Bluetooth, notifications et session disponibles sur le système. Les commandes absentes sont désactivées.

La barre existe même sans panneau XFCE détecté. Elle se replie après le délai réglé dans les préférences et réapparaît dans les 10 pixels du bord inférieur, sans trait visible.

Le panneau XFCE inférieur d’origine est masqué pendant la session NovaBar, sans suppression de sa configuration. Il revient à la fermeture. Un processus de secours le restaure après un arrêt brutal. **Système → Afficher les icônes XFCE pendant 30 s** donne accès aux applets de notification, qui restent hébergées par XFCE.

## Espaces de travail

Sous XFCE/X11, les panneaux demandent à rester présents sur tous les bureaux virtuels. La barre liste les fenêtres du bureau courant et les fenêtres épinglées sur tous les bureaux. Ces fonctions ne sont pas garanties sous Wayland, Windows ou macOS.

[Upgrade](Mises-a-jour.md) · [Diagnostic XFCE](XFCE-Cyber-Skin.md)
