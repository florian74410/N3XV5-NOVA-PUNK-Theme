# CYBER NEXUS HUD / NovaBar 0.6.9 — publication et validation

La version 0.6.9 reprend le HUD de performance, les deux docks et la quatrième surface XFCE, avec les corrections demandées sous Linux Mint XFCE X11.

## Corrections livrées

- **Tous les workspaces XFCE :** requêtes EWMH `_NET_WM_DESKTOP=0xFFFFFFFF` et `_NET_WM_STATE_STICKY` après mapping de la fenêtre, puis vérification et remise en place toutes les 2,5 s du HUD supérieur, des docks et de l'overlay.
- **Docks latéraux :** angles taillés et remplissage sombre semi-opaque, micro-pistes PCB, vias et impulsions lumineuses animées, palette synchronisée avec Blue Neon / Green Matrix / Red Blood, toujours avec glisser-déposer et ouverture des vrais dossiers ou applications.
- **Panneau système du bas :** habillage du vrai `xfce4-panel` existant, sans recréer les applets, icônes Wi-Fi, son, horloge et fenêtres ; détection des fenêtres X11 reparentées, préférence d'activation proposée une seule fois, état et diagnostic depuis la zone de notification.
- **Stabilité :** initialisation du statut XFCE avant la construction du menu de notification, empêchant un plantage au lancement.
- **Rétractation XFCE :** délai configurable de 1 à 120 s (10 s par défaut) ; taille native configurable de 100 à 200 % (175 % par défaut) ; conservation d'une zone native de rappel de 1 px ; restitution des réglages initiaux à la désactivation et à la fermeture normale.
- **Modules :** les modules visibles peuvent être sélectionnés par machine ; Power est présenté uniquement avec les valeurs réellement fournies par les capteurs.

## Installation Linux Mint XFCE

Télécharger le paquet de la [release v0.6.9](https://github.com/florian74410/Health-and-Perfs---Navigation-Controler-Bar/releases/tag/v0.6.9) dans le dossier **Executable / Linux** ou via la page Releases :

```bash
cd "$(xdg-user-dir DOWNLOAD)"
sudo apt install ./NovaBar_0.6.9_amd64.deb
novabar
```

Le paquet met à jour l'installation sans effacer les préférences de l'utilisateur. Évitez de lancer en parallèle l'ancienne instance.

## Vérification sur XFCE X11

1. Dans un terminal : `echo "$XDG_SESSION_TYPE"` doit afficher `x11` pour la gestion des workspaces et l'habillage natif.
2. Survoler et déployer le HUD. Passer entre **tous les bureaux virtuels** et vérifier qu'il reste visible.
3. Ouvrir les docks gauche et droit : leur thème PCB doit correspondre au thème NovaBar. Vérifier le repli et les raccourcis.
4. Ouvrir l'icône NovaBar > **Barre système XFCE** > **Habillage CYBER NEXUS** pour activer la quatrième surface si elle n'est pas encore active.
5. Si le panneau inférieur n'est pas visible, lancer **Diagnostiquer le panneau inférieur** depuis le même menu et lire l'état, l'identifiant et la géométrie détectée.
6. Vérifier les applications ouvertes, l'horloge, les notifications, les icônes son et Wi-Fi.
7. Désactiver l'habillage pour vérifier que XFCE retrouve sa taille et ses paramètres d'origine.

**Limites :** les tests de compilation et les tests Qt automatisés ne remplacent pas le test visuel sur le vrai XFCE/X11. La présence sur tous les bureaux dépend du gestionnaire de fenêtres ; elle n'est pas garantie sous Wayland, macOS Spaces et les bureaux virtuels Windows. Le panneau reste natif ; son apparence peut varier avec le thème GTK. Ne pas recopier une valeur estimée pour une sonde Power absente.

## Fichiers et intégrité

Les paquets sont produits par GitHub Actions sur Linux, Windows, macOS Intel et Apple Silicon ; les binaires compilés sont enregistrés dans les assets de release. Le dossier [Executable/](../Executable/README.md) présente les liens, les chemins et le manifeste SHA-256 généré par la chaîne de publication.

Les installateurs ne sont pas signés par une autorité de confiance ni notarisés pour macOS. Contrôlez les sommes SHA-256 publiées et la provenance GitHub avant toute installation.
