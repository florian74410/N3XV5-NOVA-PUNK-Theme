# Navbar_Bottom — migration conservatrice vers N3XV5

Statut : **migration fonctionnelle non encore réalisée**. Ce document verrouille la stratégie de conservation avant toute modification de code.

## Sources
- Ancien dépôt : `florian74410/Health-and-Perfs---Navigation-Controler-Bar`
- Nouvelle structure : `App/Modules/Bottom/`
- Prototype visuel existant : `App/Modules/Bottom/HUD_HomeNavBar/Settings/HTML/index.html` sur `work/electric-carbon-bottomdock-v1`.
- Le prototype HTML n'est PAS le portage de la barre réelle : ses clics montrent des notifications de démonstration.

## Exigences non négociables
1. Ne supprimer ni écraser aucun fichier, asset, profil ou paramètre de l'ancienne Navbar_Bottom.
2. Identifier la version exacte du code source de la Navbar_Bottom en usage avant la copie, établir l'inventaire et les SHA-256.
3. Adapter via un **adaptateur de compatibilité** vers le Core N3XV5, sans refaire le métier de la barre.
4. Conserver lanceurs, favoris, liste et gestion des fenêtres, bureaux virtuels, zone système, audio, Bluetooth, réseau, notifications, menus NEXUS, raccourcis et intégrations XFCE/X11 lorsque présents dans la version source.
5. Conserver hauteur/largeur/position, auto-rétractation, thèmes, animations, effets, assets, réglages et profils.
6. Aucun remplacement par la maquette HTML ; celle-ci est uniquement une référence esthétique optionnelle.
7. Créer une branche de migration isolée ; ne pas modifier la release stable.
8. Prévoir sauvegarde et rollback du code ET de la configuration locale ; ne jamais effacer les données utilisateurs à l'installation.
9. Tests : lancement XFCE/X11, lancement d'apps, focus/minimiser/restaurer fenêtres, plateaux StatusNotifier/XApp, horloge, rétractation, multi-écrans, profils, mise à jour, démarrage, désinstallation et rollback.
10. Ne promouvoir en STABLE_BUILD ou STABLE_UPDATE qu'après validation fonctionnelle et visuelle explicite.

## Architecture cible proposée
```text
App/Modules/Bottom/Navbar_Bottom/
  Core/           # logique d'origine préservée
  UI/             # widgets et layouts adaptés
  Animations/     # animations existantes + ajouts facultatifs
  Assets/         # ressources d'origine préservées
  Settings/       # schémas et migration non destructive des préférences
  Compatibility/  # adaptateur N3XV5/Core et couche XFCE
  Tests/
```

## Étapes de migration
- [ ] Localiser la version source exacte de Navbar_Bottom (branche, commit, chemin).
- [ ] Inventorier toutes les fonctionnalités + réglages + assets, avec checksums.
- [ ] Copier le code d'origine sur une branche dédiée sans aucune suppression.
- [ ] Adapter les chemins et API du Core N3XV5 derrière Compatibility/.
- [ ] Vérifier la parité fonctionnelle avant tout changement esthétique.
- [ ] Tester sous Linux Mint XFCE/X11.
- [ ] Publier un diff lisible et un rollback avant intégration.

**Règle : priorité absolue à zéro régression / zéro perte de fonction.**
