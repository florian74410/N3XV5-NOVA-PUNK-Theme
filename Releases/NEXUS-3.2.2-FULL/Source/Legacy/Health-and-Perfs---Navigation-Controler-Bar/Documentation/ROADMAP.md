# CYBER NEXUS HUD — NovaBar ROADMAP

> Document de référence des fonctionnalités, validé le 31 octobre 2026. Le statut « prévu » ne signifie pas implémenté. Les versions des plugins et du runtime doivent être compatibles avant distribution.

## Réalisé dans le code 0.5.3

- Fond Holo uni teinté à 85 % d’opacité et extérieur transparent.
- Angles biseautés, contours segmentés et détails diagonaux sur le pourtour.
- Palette distincte pour valeurs, libellés et accents ; texte non intégralement vert.

## Réalisé dans le code 0.5.2

- Contour sombre des textes et boutons Holo sur fond transparent.
- Historique réseau de 120 secondes : UP vert, DOWN rouge, ping bleu en histogramme.
- Connexion active prioritaire et unités adaptées aux petits débits.
- Ping ICMP borné vers 1.1.1.1, indisponibilité explicite.

## Réalisé dans le code 0.5.1

- Compte-tours CPU/GPU et cadrans RAM/SSD proportionnels dans la barre compacte.
- Holo CPU 460 × 330 px et capteurs 380 × 280 px, avec tableaux défilants et fonds transparents.
- Ouverture/fermeture uniquement au clic sur le logo du plugin actif, en haut à droite.
- Détails réseau par interface : état, vitesse de lien et débits reçus/émis.
- Consommations CPU/GPU uniquement si mesurées ; aucune puissance par cœur inventée.
- [Guide, vérifications et limites de la 0.5.1](../docs/UPDATE_V051.md) ; [captures Qt](../Assets/README.md).

Les éléments plus ambitieux décrits ci-dessous restent une feuille de route, même lorsqu’un panneau de base existe.

## Vision

NovaBar est une barre HUD résidente, responsive, rétractable, multi-écran et modulaire : CPU, GPU, RAM, stockage, ventilateurs, réseau, raccourcis et modules additionnels. Thème d'origine **Cyber-Futuriste / PCB Electric Blue** : transparence, typographies cyberpunk, tracés de circuits, halos néon, compteurs et jauges. L'application doit rester légère et ne jamais afficher de faux capteur comme une vraie mesure.

## Mécanique générique des panneaux Holographic Details — priorité P0

Chaque bloc cliquable possède 5 états :
- **Idle** : informations compactes et mises à jour sans monopoliser l'interface.
- **Hover** : halo renforcé, pistes PCB lumineuses, curseur de sélection.
- **Active** : clic court sur le logo en haut à droite → panneau transparent ancré près du bloc.
- **Pinned** : panneau épinglé, persistant jusqu'à fermeture volontaire.
- **Alert** : palette jaune/orange/rouge selon des seuils configurables.

Interactions : clic sur un autre bloc ferme/remplace le panneau non épinglé, fermeture par croix, Échap ou clic extérieur ; un panneau épinglé reste ouvert quand la barre se rétracte (sauf fermeture manuelle). Placement automatique dessous/dessus/latéral suivant position de NovaBar et géométrie d'écran. Panneau toujours dans les limites de l'écran actif. Animation d'ouverture ~200–300 ms, légère trame de scan, bordure néon en plusieurs couches, flou simulé et profondeur. Réglages d'effets : Off / Éco / Standard / Ultra, support réduction de mouvement et des machines modestes.

### Architecture et rendu
- **Core/Service** : acquisition matérielle asynchrone, cache, validation des capacités exposées par l'OS ; pas de sonde inventée.
- **Plugin Runtime** : manifest, API versionnée, compacte + vue holographique + réglages, flux de données autorisé ; intégration au service d'arrière-plan installé par CYBER NEXUS HUD.
- **Frontend** : Qt/PySide6 existant à conserver pour la compatibilité installateur. Étudier Qt Quick/QML + shaders/glow/bloom seulement après vérification des bibliothèques incluses et des ressources sur Windows/macOS/Linux.
- **Neon FX** : double halo cyan/bleu, dégradés HDR simulés, pulses dans les pistes PCB, energy nodes, corner LEDs et holo-sweep. Framerate limité, aucune animation gourmande lorsque le HUD est rétracté, charge GPU réduite en mode économie.
- **Sécurité** : importer un ZIP ne doit jamais exécuter silencieusement un `install.sh` arbitraire ; vérification du manifeste/dependencies/digest, confirmation explicite, installation isolée et journaux.

## Plugin 01 : CPU Manager/Viewer — CPU Advanced Holo Panel (P0)

### Compact
Logo CPU, température package si disponible, charge totale, cadran 0–3,5 GHz avec segments verts 0–2 GHz, orange 2–3 GHz et rouges >3 GHz ; adaptation des limites configurable par machine.

### Hologramme « CPU CORE MATRIX »
En-tête : nom du CPU, cœurs physiques et threads logiques, température package, fréquence moyenne/actuelle, charge totale et puissance électrique réelle package si exposée.
Tableau **sans aucune bordure interne ou externe** :
`CORE | FRÉQUENCE (GHz) | TEMPÉRATURE (°C) | PUISSANCE (W)`
Une ligne pour chaque cœur réellement identifiable, pas de confusion entre cœur physique et thread logique. Ligne finale **PACKAGE / TOTAL** : fréquence **moyenne des cœurs** (pas somme de GHz), température package, puissance package. Les fréquences/temps de chaque cœur peuvent être indisponibles selon OS/pilote ; `—` dans ce cas. Le **TDP nominal** n'est pas une puissance instantanée par cœur : ne pas afficher une estimation comme un watt mesuré. Une estimation éventuelle doit être explicitement marquée « estimée » et désactivée par défaut.

Fonctions visuelles : scanline, affichage progressif des lignes, mini graphes de fréquence/température/charge à 30 secondes, épingle, fermeture, couleur d'alerte, options de colonnes/seuils, profils utilisateur.

### Critères d'acceptation
- Clic sur la vraie zone CPU, pas sur un rectangle décoratif global ; glisser-déposer des modules toujours opérationnel sans déclencher un clic.
- Valeurs réelles / indisponible, respect de la topologie CPU, gestion >32 threads et mise à jour non bloquante.
- Hologramme responsive, sans bordures de tableau, accessible au clavier et toujours visible à l'écran.
- Installation du plugin versionné via archive ZIP ; runtime ne requiert pas l'exécution de code ZIP inconnu et l'installateur fournit les dépendances host nécessaires.
- Régression automatisée des autres modules, de l'installateur et des profils.

## Autres panneaux holographiques (après CPU)

- **GPU Holo** : horloges core/VRAM, charge, températures, watts réellement mesurés, VRAM, historique et ventilateurs exposés.
- **RAM Holo** : quantité utilisée/disponible, caches, swap, débit si mesure native disponible, processus principaux.
- **Storage Holo** : disques et partitions, SMART/état lorsque disponible, températures, I/O et espace libre.
- **Fans Holo** : découverte des RPM, courbes et seuils ; écriture PWM uniquement via contrôleur compatible et avec restauration automatique sécurisée.
- **Network Holo** : débit et historique, interfaces, ping/latence sur demande, statistiques selon permissions.

## Améliorations futures prioritaires

1. **Neon FX v2 / Reactive PCB** : intensité lumineuse, lueurs diffuses, pulses synchronisées avec charge, sans performances dégradées.
2. **Holo Panel générique** : tous plugins, position adaptative, transitions et états.
3. **HUD Designer Studio** : organiser/redimensionner modules, thèmes, ZIP d'export, presets et sauvegarde.
4. **Nexus Profiles** : Eco/Balanced/Gaming, conditions de changement automatique ; ne pas overclocker sans autorisation et matériel validé.
5. **Smart Fan Control** : profils PWM, retour en auto et garde-fous thermiques.
6. **Thermal Radar** : schéma thermique PCB, surfaces capteurs et alertes.
7. **Power & Efficiency** : puissance mesurée, historique et bilan perf/watt ; ne pas prétendre mesurer ce que l'OS n'expose pas.
8. **Storage Guardian** : SMART, santé, vitesses et avertissements.
9. **Game Mode** : FPS/frametimes si source de données disponible.
10. **Shell Commander** : macros validées, journaux, autorisations.
11. **Network Radar** : historique du réseau et test de latence.
12. **RGB Sync** : périphériques OpenRGB compatibles uniquement.
13. **Cyber Clock** : horloge, chronomètre et alarmes.
14. **AutoPilot** : changements de profils selon charge/alimentation.
15. **Alert Center & Diagnostics** : notifications et rapports exportables.

## Distribution / compatibilité

Le dépôt principal utilise `main/Executable/` pour les installateurs CYBER NEXUS HUD 0.3.1. Sources du runtime associé : branche `feature/cyber-nexus-installer-v03`. Archives distribuables : `main/Plugins/*.zip` ; les archives sont des ressources/déclarations tant que le plugin runtime ne sait pas charger un fournisseur externe validé.

OS cibles : Mint XFCE / Ubuntu Linux x64, Windows 10/11, macOS 12+ Intel/Apple Silicon ; Bazzite expérimental ; Windows 7/High Sierra requièrent un port legacy distinct. **Modifier les sources ne met pas automatiquement à jour les binaires de `main/Executable/`.**

## Historique
- 2026-10-31 : spécification CPU Holographic Details, effets néon et évolution du plugin API, d'après la maquette de référence.


## Plugin Manager 2-en-1 — NovaBar v0.3.3

La mise à jour d'un plugin compatible est indépendante du lanceur installé. Le gestionnaire compact comporte deux onglets :

- **Plugins** : liste scrollable, version installée et dernière version disponible dans des colonnes adjacentes ; bouton d'installation ou de mise à jour sur sélection, activer/désactiver, import ZIP local et restauration.
- **Sources** : dépôts GitHub HTTPS configurables (URL, branche, dossier `Plugins`, actif/inactif) ; ajouter, modifier, supprimer, resynchroniser.

Le catalogue compare les noms des ZIP versionnés `<id>-vX.Y.Z.zip`, puis l'installation télécharge le paquet, vérifie le SHA du blob GitHub et le manifeste, présente dépendances/permissions et demande confirmation. Aucun script tiers `install.sh` n'est lancé automatiquement.

Les sources sont stockées hors du répertoire de l'exécutable dans `Documents/NovaBar/App/Settings/plugin_sources.json` et les extensions dans `Documents/NovaBar/Plugins/`. L'installateur initialise la source officielle lors de la première installation, **sans écraser les autres sources utilisateur**. Une mise à jour du moteur reste nécessaire uniquement lorsque le plugin exige une API non prise en charge. Le support de GitLab / dépôts Git privés est prévu ultérieurement.

**État** : sources et interface implémentées sur la branche `feature/cyber-nexus-installer-v03` ; compilation et tests de la v0.3.3 à valider avant distribution. Les installateurs v0.3.1 déjà présents dans `main/Executable/` ne fournissent pas ces fonctions.
