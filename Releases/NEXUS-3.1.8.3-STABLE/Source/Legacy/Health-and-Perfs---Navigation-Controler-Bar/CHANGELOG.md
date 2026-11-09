# NovaBar 0.6.11 — Cockpit inférieur et NEXUS

La barre inférieure adopte une coque métallique à plusieurs niveaux, des compartiments biseautés, des rails lumineux et des circuits. Elle conserve les couleurs du thème et passe à une hauteur adaptée à de grandes icônes (88 px au réglage par défaut, au lieu de 49 px).


- Grandes icônes, titres de fenêtres, menu NEXUS par catégories, favoris et recherche.
- Indicateurs système réels et hôtes StatusNotifier/DBusMenu/XApp.
- Upgrade conservé.

# NovaBar 0.6.10 — barre inférieure autonome et Upgrade

- Barre inférieure Linux/X11 indépendante de `xfconf-query` : applications avec recherche, lanceurs XFCE, fenêtres actives, activation/réduction, clic droit fermer, horloge et accès réseau/volume/Bluetooth/session selon les outils installés.
- Panneau XFCE inférieur masqué après sauvegarde de ses fenêtres ; restauration à la fermeture, au redémarrage après mise à jour et via un processus de secours en cas d’arrêt brutal. La configuration XFCE n’est pas supprimée. Les icônes de notification tierces restent sur le panneau XFCE, accessible 30 s depuis le menu Système.
- Docks latéraux repliés cachés, sans trait coloré ni fenêtre interceptant les clics. Détection du pointeur à 10 px ; fermeture après 3 s hors du module.
- Paramètres → Upgrade : vérification de la release officielle, téléchargement du runtime correspondant à la plateforme, contrôle SHA-256, autotest isolé, activation et redémarrage automatique. Préférences, thèmes et plugins conservés.
- Migration des raccourcis Linux : le raccourci utilisateur utilise le même identifiant que le paquet DEB pour ouvrir la version mise à jour.
- Environnement des commandes XFCE/GIO isolé des bibliothèques embarquées PyInstaller.


# NovaBar 0.6.9 — correctif XFCE (développement, non publié)

- HUD CPU/GPU/RAM/SSD : demande EWMH `_NET_WM_DESKTOP=0xFFFFFFFF` et fenêtre « sticky » après mise en carte par XFWM4 ; vérification toutes les 2,5 secondes et réparation uniquement si nécessaire, y compris après un changement d'espace de travail.
- Docks Dossiers/Applications : panneaux PCB à angles coupés, circuit néon animé en bordure, couleurs de l'HUD synchronisées, style du déclencheur rétracté assorti au thème. Conservation des dossiers, lanceurs et fonction glisser-déposer.
- Panneau système inférieur natif : détection X11 améliorée y compris fenêtres reparentées ; dialogue d'activation proposé une seule fois aux profils où l'habillage XFCE était désactivé, sans masquer définitivement le panneau original.
- Depuis l'icône de notification NovaBar : diagnostic en lecture seule du panneau inférieur (identifiant XFCE, taille, masquage, détection visuelle).
- Garde l'habillage réversible, la barre d'origine et ses icônes, le réglage de délai 1–120 secondes, l'épaisseur 100–200 % et la palette CYBER NEXUS.
- Tests automatisés ajoutés ; validation visuelle sur vrai Linux Mint XFCE/X11 encore nécessaire.

# NovaBar 0.6.0 — développement (non publié)

- Quatrième surface facultative XFCE Cyber Skin : panneau système natif conservé (icônes, Wi-Fi, fenêtres, horloge) avec habillage GTK3, microcircuits PCB et impulsions animées transparentes aux clics. Rétractation native avec bord de rappel 1 px, temporisation réglable de 1 à 120 s (10 s par défaut), épaisseur de 100 à 200 % de l'originale (175 % par défaut), et couleurs synchronisées aux thèmes. Sauvegarde et restauration du panneau d'origine, y compris lors d'un arrêt normal.
- Docks Dossiers et Applications, mode multi-espaces de travail X11, activation indépendante des trois fenêtres NovaBar.
- Logo/miniature CYBER NEXUS partagé entre icône de notification, Linux DEB et Windows EXE.
- Module Power read-only avec détails CPU/GPU/RAM et capteurs absents explicitement notés « — » ; modules visibles configurables par profil.
- Tests de non-régression multi-plateformes, packaging à confirmer avant toute release.

# NovaBar 0.5.4 — développement (non publiée)

- Barre réduite en véritable bandeau de télémétrie visible en haut, bas, gauche ou droite (au lieu de ne laisser que 4 px à l'écran).
- Suppression des compte-tours et déclencheurs Holo dans ce mode, mesures essentielles toujours affichées.
- CPU/GPU/FANS : compte-tours à segments lumineux, sans aiguille, valeurs et unités recentrées dans le cercle.
- RAM/SSD : jauges de remplissage façon batterie, à sept segments et couleurs d'alerte.
- Contrôle de survol évitant la réouverture immédiate après une minimisation manuelle.
- Tests multi-OS de géométrie, de visibilité, de télémétrie et de rendu.

# NovaBar 0.5.3

- Fond Holo uni sombre à 85 % d’opacité, teinté selon le thème, commun aux tableaux et graphiques.
- Cadres fins avec angles biseautés, décrochement asymétrique et gardes diagonales.
- Valeurs blanches, libellés gris bleuté et titres accentués ; les plugins et fenêtres ne sont plus entièrement recolorés en vert.
- Couleurs réseau inchangées : UP vert, DOWN rouge et ping bleu.
- 77 tests locaux réussis ; nouveaux aperçus Qt dans Assets/Previews.

# NovaBar 0.5.2

- Lisibilité des Holo : caractères et boutons avec contour sombre, fonds toujours transparents.
- Réseau : courbe UP verte, DOWN rouge et histogramme de ping bleu sur 120 secondes, avec deux échelles.
- Ping ICMP vers 1.1.1.1 toutes les 10 secondes, timeout borné, indisponibilité explicite.
- Petits débits visibles en B/s et kB/s ; connexion active prioritaire, sans double comptage des bridges Docker.
- Collecte réseau indépendante d’une erreur CPU et protection contre les compteurs réinitialisés.
- 75 tests locaux réussis et comparaison visuelle sur fonds clair/sombre.

# NovaBar 0.5.1

- Compte-tours circulaires dans la barre compacte : CPU/GPU en GHz, RAM/SSD en pourcentage. Les cadrans restent proportionnels de 50 à 150 px ; en espace réduit, les valeurs restent prioritaires.
- Holo CPU réduit à 460 × 330 px, autres Holo à 380 × 280 px ; tableaux défilants.
- Surfaces des Holo entièrement transparentes, y compris les zones de défilement ; seuls textes, cadres et circuits néon sont dessinés.
- Réseau : état, vitesse de lien et débits par interface ; valeurs initiales ou indisponibles signalées par un tiret.
- Détails GPU/CPU : puissance mesurée si disponible. Capacité RAM/VRAM/volume système et I/O disque clairement identifiés.
- 68 tests locaux réussis. Rendu Qt inspecté avec des données de démonstration.

# Changelog

## 0.5.0 — Update 2

- Service `cpu_mode_controller`, backend sysfs Linux Intel/AMD et fallback explicite Windows/macOS.
- Turbo Off / Turbo On / Auto 85 °C ; hystérésis 5 °C, coupure demandée en cas de sonde absente.
- Aucun changement CPU au lancement ; état effectif vérifié, erreurs de permissions visibles.
- Downloader séparé des paquets hors ligne, formats natifs et vérification SHA-256 avant exécution.
- Configuration initiale des thèmes, position, épaisseur, repli, priorité et Holo.
- Packaging Windows contenant le runtime, manifestes de release natifs et bootstrap multi-OS.
- Plugins CPU 2.1.0 et autres modules 1.1.0 ; kit Holo partagé, données indisponibles affichées « — ».
- Première installation : plugins officiels intégrés ; versions et activations existantes préservées.
- Demande X11 ABOVE / Windows TOPMOST sans voler le focus ; limites Wayland/macOS documentées.

## 0.4.0 — Update 1

- Kit Holo partagé, trois thèmes et traces PCB bord à bord.
- Logo puce partagé avec l’installateur.
- Logos de plugins en haut à droite : clic uniquement pour ouvrir/fermer le Holo.
- Panneaux GPU, RAM, SSD, FANS, NETWORK en complément de CPU CORE MATRIX.
- Flèche de minimisation et trois politiques de rétractation.
- Onglet Wiki et migration des préférences existantes.
