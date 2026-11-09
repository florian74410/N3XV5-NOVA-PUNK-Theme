# ❓ Questions fréquentes

> Des réponses courtes pour distinguer les fonctions déjà livrées des idées futures.

[🏠 Accueil](Home.md) · [🚀 Démarrage](Premiers-pas.md) · [📦 Installation](Installation.md) · [🎛️ Interface](Interface.md) · [🔌 Plugins](Plugins.md) · [🛠️ Dépannage](Depannage.md)

---

### NovaBar doit-elle tourner en administrateur ?

Non pour le HUD standard et ses profils par utilisateur. Le paquet `.deb` requiert les droits d'installation habituels, pas des privilèges pour surveiller la machine au quotidien.

### Une carte graphique AMD ou Intel fonctionne-t-elle ?

La barre fonctionne, mais la collecte GPU ne remonte pas toutes les informations de toutes les marques : elle s'appuie notamment sur `nvidia-smi`. Les valeurs manquantes peuvent apparaître sous forme de **—**.

### Pourquoi le Flatpak montre-t-il moins de sondes ?

Le sandbox isole certaines interfaces de bas niveau et certains utilitaires. Sur Linux Mint XFCE, le `.deb` est recommandé si vous souhaitez surveiller un maximum de capteurs.

### Puis-je changer la largeur et l'épaisseur ?

Oui, longueur **25–100 %**, épaisseur **50–150 px**. L'affichage normal est prévu pour 72 px par défaut et 100 % de longueur.

### Tous les plugins ont-ils une fenêtre Holo ?

Non : seule la **CPU CORE MATRIX** dispose aujourd'hui de la vue Holo native prévue par le runtime.

### Turbo augmente-t-il réellement les fréquences ?

Non : c'est un emplacement réservé, sans commande active des tensions, PWM ou fréquences.

### Faut-il réinstaller NovaBar pour mettre à jour un plugin ?

Non pour un plugin compatible avec l'API du runtime déjà présent ; le gestionnaire peut installer un ZIP plus récent. Une nouvelle API ou une sonde nouvelle peut nécessiter une mise à jour du programme.

### Le Wiki est-il disponible hors ligne ?

Le bouton **? Wiki** ouvre les pages du dépôt GitHub : **Internet est nécessaire** pour consulter le site. Les pages Markdown sont aussi présentes dans les sources `docs/wiki/`, mais l'application ne contient pas encore de navigateur documentaire intégré et hors ligne.

### Y a-t-il des informations transmises automatiquement ?

Les mesures matérielles restent locales. La synchronisation des sources et la recherche de mises à jour font des requêtes GitHub à la demande. Aucun envoi automatisé d'email n'est garanti.

---

<sub>⚡ NovaBar • CYBER NEXUS HUD · Les illustrations sont documentaires, les fonctions non livrées sont signalées.</sub>
