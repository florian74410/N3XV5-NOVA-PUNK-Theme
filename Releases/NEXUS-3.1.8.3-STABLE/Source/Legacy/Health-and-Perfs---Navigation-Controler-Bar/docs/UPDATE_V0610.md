# NovaBar 0.6.10 — barre inférieure autonome et Upgrade

- Barre inférieure Linux/X11 indépendante de `xfconf-query` : applications avec recherche, lanceurs XFCE, fenêtres actives, activation/réduction, clic droit fermer, horloge et accès réseau/volume/Bluetooth/session selon les outils installés.
- Panneau XFCE inférieur masqué après sauvegarde de ses fenêtres ; restauration à la fermeture, au redémarrage après mise à jour et via un processus de secours en cas d’arrêt brutal. La configuration XFCE n’est pas supprimée. Les icônes de notification tierces restent sur le panneau XFCE, accessible 30 s depuis le menu Système.
- Docks latéraux repliés cachés, sans trait coloré ni fenêtre interceptant les clics. Détection du pointeur à 10 px ; fermeture après 3 s hors du module.
- Paramètres → Upgrade : vérification de la release officielle, téléchargement du runtime correspondant à la plateforme, contrôle SHA-256, autotest isolé, activation et redémarrage automatique. Préférences, thèmes et plugins conservés.
- Migration des raccourcis Linux : le raccourci utilisateur utilise le même identifiant que le paquet DEB pour ouvrir la version mise à jour.
- Environnement des commandes XFCE/GIO isolé des bibliothèques embarquées PyInstaller.

## Depuis une installation 0.6.9

Ouvrir **Préférences → Mises à jour…**, puis **Vérifier les mises à jour → Installer la mise à jour → Redémarrer NovaBar**. Le téléchargement est pris en charge par NovaBar ; aucun fichier à récupérer manuellement. La 0.6.10 automatise ensuite ce parcours derrière le bouton **Upgrade**.

La mise à jour intégrée installe un runtime par utilisateur. Elle ne modifie pas la version enregistrée dans `dpkg` et ne nécessite pas de mot de passe administrateur. Les raccourcis et le démarrage automatique pointent vers le nouveau runtime ; un ancien `/usr/bin/novabar` provenant d’un DEB 0.6.9 peut encore lancer sa copie système. Pour remplacer également le paquet système, installer le DEB 0.6.10.

## Style et limites

Fond sombre teinté légèrement translucide, angles coupés, textes blanc/gris et accents du thème. Les courbes réseau existantes restent UP vert, DOWN rouge et ping bleu.

La liste de fenêtres et le remplacement du panneau sont destinés à **XFCE/X11**. Les restrictions des compositeurs Wayland ne permettent pas d’y garantir le même fonctionnement. Les applets de notification XFCE ne sont pas déplacées dans NovaBar.

## Validation

Suite automatisée Qt, déclencheurs 10 px, restauration du panneau, raccourcis et progression automatique Upgrade. La CI Linux exécute aussi une session isolée réelle Xvfb + XFWM4 + xfce4-panel : détection, masquage/restauration après fermeture et arrêt brutal, et activation/réduction d’une fenêtre. Les installateurs des quatre plateformes sont construits et soumis à leurs autotests avant publication. L’aperçu Assets provient des widgets Qt livrés avec des données de démonstration.
