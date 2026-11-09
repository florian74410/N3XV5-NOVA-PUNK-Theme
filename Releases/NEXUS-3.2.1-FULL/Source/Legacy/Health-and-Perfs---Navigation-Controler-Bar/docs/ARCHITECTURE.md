# Architecture v0.1

## Arborescence

```text
src/healthbar/
  __main__.py       point d’entrée python -m healthbar
  app.py            fenêtre overlay, boutons visibles, rétractation, géométrie, tray
  hud.py            dessin vectoriel, gabarits horizontaux/compacts/verticaux
  dialogs.py        première configuration, préférences, gestionnaire d’extensions
  config.py         préférences validées et sauvegarde atomique par utilisateur
  autostart.py      adaptateurs XDG / registre HKCU / LaunchAgents
  plugins.py        manifeste API v1, staging, activation, mise à jour et restauration
scripts/
  install.py        installation source dans un venv privé + raccourci de session
  build.py          build PyInstaller natif
  entrypoint.py     entrée du binaire autonome
  install-binary-linux.sh
  windows-installer.iss
.github/workflows/build.yml
  tests et fabrication des paquets Linux / Windows / macOS
```

## Séparation des responsabilités

Le shell connaît les emplacements et leur présentation. Il n’accède pas au matériel.
HudCanvas dessine les éléments du prototype avec QPainter ; aucune image de bureau n’est embarquée
comme fond de fenêtre. Le fond général est entièrement transparent. Seuls les fonds des modules et boutons
ont une opacité réglable de 0 à 100 % ; les textes, icônes et contours gardent leur lisibilité.
Les valeurs dessinées sont volontairement constantes et signalées comme telles.
Les six slots sont cpu, gpu, ram, storage, fans, network ; Turbo et la console sont réservés.

Le gestionnaire prend des paquets locaux .hbp. La v1 expose uniquement des métadonnées,
avec un nom rendu dans un slot quand le paquet est activé. Les futurs fournisseurs de mesures,
la gestion de leurs permissions et le protocole de communication restent hors de cette version.
Pas de téléchargement automatique ni d’exécution de scripts à l’installation d’un paquet.

## État de la fenêtre

Au repos la fenêtre occupe 100 % de la largeur de l’écran sélectionné, ou 100 % de la hauteur à droite.
Le timer de 15 s s’arrête au survol et pendant un dialogue ou menu.
La rétractation déplace la fenêtre vers l’extérieur de l’écran et laisse 4 px accessibles.
Le retour anime la géométrie complète. Les préférences reconfigurent la fenêtre sans redémarrage.
Une icône de notification et le clic droit donnent accès aux réglages et à Quitter.

## Persistance

| Système | Dossier des préférences/extensions |
| --- | --- |
| Linux | `$XDG_CONFIG_HOME/health-perfs-bar` ou `~/.config/health-perfs-bar` |
| Windows | `%APPDATA%/HealthPerfsBar` |
| macOS | `~/Library/Application Support/HealthPerfsBar` |

settings.json et plugins/ sont séparés du programme installé. `HEALTHBAR_DATA_DIR` peut
isoler une session de développement. QLockFile empêche deux fenêtres d’écrire simultanément
sur le même profil. Les paramètres utilisent un remplacement de fichier atomique.
